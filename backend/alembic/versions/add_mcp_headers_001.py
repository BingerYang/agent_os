"""add_mcp_headers_001

Revision ID: add_mcp_headers_001
Revises: 11347c08a5c7
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_mcp_headers_001"
down_revision: Union[str, None] = "11347c08a5c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORIGINAL_AUTH_TYPES = ("NONE", "API_KEY", "BEARER_TOKEN", "BASIC_AUTH")
_EXTENDED_AUTH_TYPES = _ORIGINAL_AUTH_TYPES + ("JWT_BEARER", "OAUTH2")


def _is_mysql() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "mysql"


def _alter_auth_type_enum(values: tuple[str, ...]) -> None:
    enum_values = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f"ALTER TABLE mcp_servers "
        f"MODIFY COLUMN auth_type ENUM({enum_values}) NOT NULL"
    )


def upgrade() -> None:
    op.add_column("mcp_servers", sa.Column("headers", sa.JSON(), nullable=True))
    if _is_mysql():
        _alter_auth_type_enum(_EXTENDED_AUTH_TYPES)


def downgrade() -> None:
    if _is_mysql():
        _alter_auth_type_enum(_ORIGINAL_AUTH_TYPES)
    op.drop_column("mcp_servers", "headers")
