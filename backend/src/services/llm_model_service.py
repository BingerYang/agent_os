import base64
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.exceptions import ResourceConflict, ResourceNotFound
from src.models.llm_model import LLMModel


def _get_cipher() -> AESGCM:
    settings = get_settings()
    key = settings.llm_encryption_key
    if not key:
        key = base64.b64encode(b"dev-key-insecure-32bytes!!!!!!!!").decode()
    raw = base64.b64decode(key.encode() + b"==")[:32]
    return AESGCM(raw.ljust(32, b"\x00"))


def encrypt_api_key(plain: str) -> str:
    nonce = os.urandom(12)
    ct = _get_cipher().encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_api_key(encrypted: str) -> str:
    raw = base64.b64decode(encrypted.encode())
    nonce, ct = raw[:12], raw[12:]
    return _get_cipher().decrypt(nonce, ct, None).decode()


def mask_api_key(encrypted: str, supplier: str) -> str:
    try:
        plain = decrypt_api_key(encrypted)
        suffix = plain[-4:] if len(plain) >= 4 else plain
        return f"{supplier[:4]}-***-{suffix}"
    except Exception:
        return "***"


class LLMModelService:
    async def list(
        self,
        db: AsyncSession,
        supplier: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[LLMModel], int]:
        q = select(LLMModel)
        if supplier:
            q = q.where(LLMModel.supplier == supplier)
        if enabled is not None:
            q = q.where(LLMModel.enabled == enabled)
        if keyword:
            q = q.where(LLMModel.name.contains(keyword) | LLMModel.supplier.contains(keyword))
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, model_id: int) -> LLMModel:
        obj = await db.get(LLMModel, model_id)
        if not obj:
            raise ResourceNotFound(f"模型 {model_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> LLMModel:
        exists = (await db.execute(select(LLMModel).where(LLMModel.model_id == data["model_id"]))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("模型 API 标识已存在")
        api_key_plain = data.pop("api_key")
        obj = LLMModel(**data, api_key=encrypt_api_key(api_key_plain))
        db.add(obj)
        await db.flush()
        return obj

    async def update(self, db: AsyncSession, model_id: int, data: dict[str, Any]) -> LLMModel:
        obj = await self.get(db, model_id)
        if "api_key" in data:
            data["api_key"] = encrypt_api_key(data["api_key"])
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(UTC)
        return obj

    async def delete(self, db: AsyncSession, model_id: int) -> None:
        obj = await self.get(db, model_id)
        await db.delete(obj)
