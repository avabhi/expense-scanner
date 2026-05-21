"""create_receipts

Revision ID: 21bae6a1715d
Revises: 
Create Date: 2026-05-21 12:57:35.817305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '21bae6a1715d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create receipt table
    op.create_table(
        'receipt',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_name', sa.String(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('file_hash', sa.String(), nullable=False),
        sa.Column('s3_object_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipt_file_hash'), 'receipt', ['file_hash'], unique=True)

    # Create lineitem table
    op.create_table(
        'lineitem',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('receipt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['receipt_id'], ['receipt.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lineitem_id'), 'lineitem', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lineitem_id'), table_name='lineitem')
    op.drop_table('lineitem')
    op.drop_index(op.f('ix_receipt_file_hash'), table_name='receipt')
    op.drop_table('receipt')
