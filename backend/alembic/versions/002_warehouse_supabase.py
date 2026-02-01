"""Update warehouse_connections for Supabase

Revision ID: 002
Revises: 001
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename MotherDuck columns to Supabase columns
    op.alter_column('warehouse_connections', 'database_name',
                    new_column_name='supabase_url',
                    type_=sa.String(500))

    op.alter_column('warehouse_connections', 'access_token_encrypted',
                    new_column_name='supabase_key_encrypted')

    # Add schema_name column
    op.add_column('warehouse_connections',
                  sa.Column('schema_name', sa.String(100), nullable=False, server_default='public'))


def downgrade() -> None:
    # Remove schema_name column
    op.drop_column('warehouse_connections', 'schema_name')

    # Rename back to MotherDuck columns
    op.alter_column('warehouse_connections', 'supabase_url',
                    new_column_name='database_name',
                    type_=sa.String(255))

    op.alter_column('warehouse_connections', 'supabase_key_encrypted',
                    new_column_name='access_token_encrypted')
