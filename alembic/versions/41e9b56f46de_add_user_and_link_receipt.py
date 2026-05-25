"""add user and link receipt

Revision ID: 41e9b56f46de
Revises: 30d9b56f46dd
Create Date: 2026-05-24 01:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '41e9b56f46de'
down_revision: Union[str, Sequence[str], None] = '30d9b56f46dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user table
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('google_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_google_id'), 'user', ['google_id'], unique=True)
    
    # Add user_id to receipt table
    op.add_column('receipt', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_receipt_user_id'), 'receipt', ['user_id'], unique=False)
    op.create_foreign_key('receipt_user_id_fkey', 'receipt', 'user', ['user_id'], ['id'], ondelete='CASCADE')

    # Change file_hash index from unique to non-unique
    op.drop_index('ix_receipt_file_hash', table_name='receipt')
    op.create_index('ix_receipt_file_hash', 'receipt', ['file_hash'], unique=False)


def downgrade() -> None:
    # Revert file_hash index change
    op.drop_index('ix_receipt_file_hash', table_name='receipt')
    op.create_index('ix_receipt_file_hash', 'receipt', ['file_hash'], unique=True)

    op.drop_constraint('receipt_user_id_fkey', 'receipt', type_='foreignkey')
    op.drop_index(op.f('ix_receipt_user_id'), table_name='receipt')
    op.drop_column('receipt', 'user_id')
    op.drop_index(op.f('ix_user_google_id'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
