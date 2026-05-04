"""add pipeline uid

Revision ID: add_pipeline_uid_001
Revises: 492862c9a96f
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = 'add_pipeline_uid_001'
down_revision = '492862c9a96f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("pipelines")}

    if 'uid' not in columns:
        op.add_column('pipelines', sa.Column('uid', sa.String(36), nullable=True))

    pipelines = connection.execute(
        sa.text("SELECT id FROM pipelines WHERE uid IS NULL OR uid = ''")
    ).fetchall()
    for row in pipelines:
        connection.execute(
            sa.text("UPDATE pipelines SET uid = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": row[0]}
        )

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("pipelines")}
    with op.batch_alter_table('pipelines', recreate='always') as batch_op:
        batch_op.alter_column('uid', existing_type=sa.String(36), nullable=False)
        if 'uq_pipeline_uid' not in unique_constraints:
            batch_op.create_unique_constraint('uq_pipeline_uid', ['uid'])


def downgrade() -> None:
    op.drop_constraint('uq_pipeline_uid', 'pipelines', type_='unique')
    op.drop_column('pipelines', 'uid')
