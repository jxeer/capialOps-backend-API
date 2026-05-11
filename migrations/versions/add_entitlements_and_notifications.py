"""Add entitlement_records, permit_events, field_media, notifications tables

Revision ID: add_entitlements_and_notifications
Revises:
Create Date: 2026-05-11

This migration creates four new tables:
- entitlement_records: Permit/entitlement applications tied to projects
- permit_events: Status changes on entitlement records
- field_media: Photos/videos uploaded for projects or work orders
- notifications: Alerts sent to users
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_entitlements_and_notifications'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'entitlement_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('parcel_number', sa.String(length=100), nullable=False),
        sa.Column('agency', sa.String(length=200), nullable=False),
        sa.Column('application_number', sa.String(length=100), nullable=False),
        sa.Column('entitlement_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('submitted_date', sa.Date(), nullable=False),
        sa.Column('hearing_date', sa.Date(), nullable=True),
        sa.Column('approved_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'permit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entitlement_record_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('previous_value', sa.String(length=200), nullable=True),
        sa.Column('new_value', sa.String(length=200), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['entitlement_record_id'], ['entitlement_records.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'field_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('work_order_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(length=20), nullable=False),
        sa.Column('s3_key', sa.String(length=500), nullable=False),
        sa.Column('s3_bucket', sa.String(length=200), nullable=False),
        sa.Column('filename', sa.String(length=300), nullable=False),
        sa.Column('caption', sa.String(length=500), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id']),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('project_id IS NOT NULL OR work_order_id IS NOT NULL', name='check_field_media_project_or_work_order')
    )

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('related_entity_type', sa.String(length=50), nullable=True),
        sa.Column('related_entity_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('notifications')
    op.drop_table('field_media')
    op.drop_table('permit_events')
    op.drop_table('entitlement_records')