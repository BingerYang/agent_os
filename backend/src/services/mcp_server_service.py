from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceConflict, ResourceNotFound
from src.models.mcp_server import MCPServer, MCPServerStatus
from src.models.tool import Tool, ToolProtocol


class MCPServerService:
    async def list(
            self,
            db: AsyncSession,
            keyword: str | None = None,
            enabled: bool | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> tuple[Sequence[MCPServer], int]:
        q = select(MCPServer)
        if keyword:
            q = q.where(MCPServer.name.contains(keyword) | MCPServer.display_name.contains(keyword))
        if enabled is not None:
            q = q.where(MCPServer.enabled == enabled)
        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, server_id: int) -> MCPServer:
        obj = await db.get(MCPServer, server_id)
        if not obj:
            raise ResourceNotFound(f"MCP Server {server_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> MCPServer:
        exists = (await db.execute(select(MCPServer).where(MCPServer.name == data["name"]))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("MCP Server 名称已存在")
        obj = MCPServer(**data)
        db.add(obj)
        await db.flush()
        return obj

    async def update(self, db: AsyncSession, server_id: int, data: dict[str, Any]) -> MCPServer:
        obj = await self.get(db, server_id)
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(UTC)
        return obj

    async def delete(self, db: AsyncSession, server_id: int) -> None:
        obj = await self.get(db, server_id)
        await db.delete(obj)

    async def toggle(self, db: AsyncSession, server_id: int, enabled: bool) -> MCPServer:
        obj = await self.get(db, server_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(UTC)
        return obj

    @classmethod
    def build_header(cls, obj: MCPServer) -> dict:
        if obj.transport_type.value != "HTTP_SSE":
            return {}
        import base64
        headers: dict[str, str] = {}
        auth = obj.auth_config or {}
        if obj.auth_type.value == "BEARER_TOKEN":
            headers["Authorization"] = f"Bearer {auth.get('token', '')}"
        elif obj.auth_type.value == "API_KEY" and auth.get("key_location", "header") == "header":
            headers[auth.get("key_name", "X-API-Key")] = auth.get("key_value", "")
        elif obj.auth_type.value == "BASIC_AUTH":
            creds = f"{auth.get('username', '')}:{auth.get('password', '')}"
            headers["Authorization"] = f"Basic {base64.b64encode(creds.encode()).decode()}"
        elif obj.auth_type.value == "JWT_BEARER":
            headers["Authorization"] = f"Bearer {auth.get('token', '')}"
        elif obj.auth_type.value == "OAUTH2":
            token = auth.get("access_token", "")
            token_type = auth.get("token_type", "bearer").lower()
            headers["Authorization"] = f"{token_type.capitalize()} {token}"
        if obj.headers:
            headers.update(obj.headers)
        return headers

    async def connect(self, db: AsyncSession, server_id: int) -> dict:
        """Test connection via MCP session initialize handshake. Returns status and latency_ms."""
        import time

        obj = await self.get(db, server_id)
        start = time.monotonic()
        try:
            headers = self.build_header(obj)
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as async_client:
                async with streamable_http_client(obj.endpoint_url or "", http_client=async_client) as (
                    read_stream, write_stream, _
                ):
                    async with ClientSession(read_stream, write_stream) as mcp_session:
                        await mcp_session.initialize()
            latency_ms = int((time.monotonic() - start) * 1000)
            obj.status = MCPServerStatus.CONNECTED
            obj.last_connected_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)
            return {"status": "CONNECTED", "latency_ms": latency_ms}
        except Exception as e:
            obj.status = MCPServerStatus.ERROR
            obj.updated_at = datetime.now(UTC)
            return {"status": "ERROR", "error": str(e)}

    async def discover_tools(self, db: AsyncSession, server_id: int) -> dict:
        """Discover tools from MCP server and upsert into Tool table."""
        obj = await self.get(db, server_id)
        headers = self.build_header(obj)

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as async_client:
                async with streamable_http_client(obj.endpoint_url or "", http_client=async_client) as (
                    read_stream, write_stream, _
                ):
                    async with ClientSession(read_stream, write_stream) as mcp_session:
                        await mcp_session.initialize()
                        tools_result = await mcp_session.list_tools()
        except Exception as e:
            return {"new_tools": 0, "updated_tools": 0, "error": str(e)}

        new_count = 0
        updated_count = 0
        now = datetime.now(UTC)

        for mcp_tool in tools_result.tools:
            # 用 server_id + mcp_tool_name 定位已有记录（幂等）
            existing = (
                await db.execute(
                    select(Tool).where(
                        Tool.mcp_server_id == obj.id,
                        Tool.mcp_tool_name == mcp_tool.name,
                    )
                )
            ).scalar_one_or_none()

            input_schema: dict = (
                mcp_tool.inputSchema
                if isinstance(mcp_tool.inputSchema, dict)
                else mcp_tool.inputSchema.model_dump()
            )

            if existing:
                existing.display_name = mcp_tool.name
                existing.description = mcp_tool.description or existing.description
                existing.input_schema = input_schema
                existing.updated_at = now
                updated_count += 1
            else:
                # name 保证全局唯一：{server.name}__{tool.name}
                unique_name = f"{obj.name}__{mcp_tool.name}"
                # 防止极端情况下重名
                name_conflict = (
                    await db.execute(select(Tool).where(Tool.name == unique_name))
                ).scalar_one_or_none()
                if name_conflict:
                    unique_name = f"{obj.name}__{mcp_tool.name}__{obj.id}"

                tool = Tool(
                    name=unique_name,
                    display_name=mcp_tool.name,
                    description=mcp_tool.description,
                    protocol=ToolProtocol.MCP,
                    mcp_server_id=obj.id,
                    mcp_tool_name=mcp_tool.name,
                    input_schema=input_schema,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(tool)
                new_count += 1

        # 同步更新 Server 状态
        obj.status = MCPServerStatus.CONNECTED
        obj.last_connected_at = now
        obj.updated_at = now

        return {"new_tools": new_count, "updated_tools": updated_count}
