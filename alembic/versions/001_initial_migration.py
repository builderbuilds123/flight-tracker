"""Initial migration - create alerts and price_history tables

Revision ID: 001
Revises: 
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('origin', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=False),
        sa.Column('departure_date', sa.DateTime(), nullable=True),
        sa.Column('return_date', sa.DateTime(), nullable=True),
        sa.Column('max_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), default='USD'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('check_frequency_hours', sa.Integer(), default=6),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('last_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for alerts table
    op.create_index('ix_alerts_id', 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_user_id', 'alerts', ['user_id'], unique=False)
    
    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), default='USD'),
        sa.Column('flight_data', sa.JSON(), nullable=True),
        sa.Column('found_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for price_history table
    op.create_index('ix_price_history_id', 'price_history', ['id'], unique=False)
    op.create_index('ix_price_history_alert_id', 'price_history', ['alert_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_price_history_alert_id', table_name='price_history')
    op.drop_index('ix_price_history_id', table_name='price_history')
    op.drop_table('price_history')
    
    op.drop_index('ix_alerts_user_id', table_name='alerts')
    op.drop_index('ix_alerts_id', table_name='alerts')
    op.drop_table('alerts')
