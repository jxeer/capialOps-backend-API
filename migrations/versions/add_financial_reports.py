"""Add financial_reports table

Revision ID: add_financial_reports
Revises:
Create Date: 2026-05-12

This migration creates the financial_reports table for sharing
project and deal financial summaries between users.
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_financial_reports'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'financial_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('project_id IS NOT NULL OR deal_id IS NOT NULL', name='check_financial_report_project_or_deal')
    )


def downgrade():
    op.drop_table('financial_reports')