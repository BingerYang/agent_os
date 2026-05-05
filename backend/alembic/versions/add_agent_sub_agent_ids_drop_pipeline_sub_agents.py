"""add sub_agent_ids to agents, drop pipeline_sub_agents

Revision ID: add_sub_agent_ids_001
Revises: add_pipeline_uid_001
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_sub_agent_ids_001'
down_revision = 'add_pipeline_uid_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. agents 表新增 sub_agent_ids JSON 列
    op.add_column(
        'agents',
        sa.Column('sub_agent_ids', sa.JSON(), nullable=True, server_default='[]')
    )

    # 2. 删除 pipeline_sub_agents 表
    op.drop_table('pipeline_sub_agents')


def downgrade() -> None:
    # 1. 重建 pipeline_sub_agents 表
    op.create_table(
        'pipeline_sub_agents',
        sa.Column('pipeline_id', sa.BigInteger(), nullable=False),
        sa.Column('agent_id', sa.BigInteger(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('pipeline_id', 'agent_id'),
    )

    # 2. 删除 sub_agent_ids 列
    op.drop_column('agents', 'sub_agent_ids')
