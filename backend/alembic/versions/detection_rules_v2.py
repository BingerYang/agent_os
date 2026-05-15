"""detection_rules_v2: add strategy/action fields, new binding/event/audit tables

Revision ID: detection_rules_v2
Revises: add_tool_headers_001
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "detection_rules_v2"
down_revision: Union[str, None] = "add_tool_headers_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend detection_rules table
    op.add_column("detection_rules", sa.Column("strategy_type", sa.String(32), nullable=False, server_default="content_filter"))
    op.add_column("detection_rules", sa.Column("action_type", sa.String(32), nullable=False, server_default="block"))
    op.add_column("detection_rules", sa.Column("max_retry_count", sa.Integer(), nullable=False, server_default="3"))

    # 2. Create agent_detection_bindings
    op.create_table(
        "agent_detection_bindings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("config_override", sa.JSON(), nullable=True),
        sa.Column("action_override", sa.String(32), nullable=True),
        sa.Column("priority_override", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["detection_rules.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", "rule_id", name="uq_agent_rule"),
    )
    op.create_index("idx_adb_agent_id", "agent_detection_bindings", ["agent_id"])
    op.create_index("idx_adb_rule_id", "agent_detection_bindings", ["rule_id"])

    # 3. Create detection_events
    op.create_table(
        "detection_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("stage", sa.String(8), nullable=False),
        sa.Column("strategy_type", sa.String(32), nullable=False),
        sa.Column("action_taken", sa.String(32), nullable=False),
        sa.Column("hit_detail", sa.JSON(), nullable=True),
        sa.Column("input_snapshot", sa.Text(), nullable=True),
        sa.Column("output_snapshot", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="LOGGED"),
        sa.Column("reviewer_id", sa.String(64), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["detection_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_de_agent_id", "detection_events", ["agent_id"])
    op.create_index("idx_de_rule_id", "detection_events", ["rule_id"])
    op.create_index("idx_de_status", "detection_events", ["status"])
    op.create_index("idx_de_created_at", "detection_events", ["created_at"])
    op.create_index("idx_de_strategy_type", "detection_events", ["strategy_type"])

    # 4. Create policy_config_audits
    op.create_table(
        "policy_config_audits",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operator_id", sa.String(64), nullable=False),
        sa.Column("agent_id", sa.BigInteger(), nullable=True),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("before_value", sa.JSON(), nullable=True),
        sa.Column("after_value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pca_rule_id", "policy_config_audits", ["rule_id"])
    op.create_index("idx_pca_agent_id", "policy_config_audits", ["agent_id"])
    op.create_index("idx_pca_created_at", "policy_config_audits", ["created_at"])


def downgrade() -> None:
    op.drop_table("policy_config_audits")
    op.drop_table("detection_events")
    op.drop_table("agent_detection_bindings")
    op.drop_column("detection_rules", "max_retry_count")
    op.drop_column("detection_rules", "action_type")
    op.drop_column("detection_rules", "strategy_type")
