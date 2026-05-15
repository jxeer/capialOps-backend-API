"""Hash MFA codes and password reset tokens

Revision ID: hash_mfa_codes_and_reset_tokens
Revises:
Create Date: 2026-05-15

Security migration: stores MFA codes and password reset tokens as SHA-256 hashes
instead of plaintext. The plaintext is returned from generate_code() / generate_token()
for email delivery only — never persisted.

Changes:
- mfa_codes.code → mfa_codes.code_hash (VARCHAR(64), SHA-256 hex digest)
- Add index ix_mfa_codes_user_used_expires on (user_id, used, expires_at)
- password_reset_tokens.token → password_reset_tokens.token_hash (VARCHAR(64), SHA-256 hex digest)
"""
from alembic import op
import sqlalchemy as sa

revision = 'hash_mfa_codes_and_reset_tokens'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('mfa_codes', 'code', new_column_name='code_hash', type_=sa.String(64), nullable=False)
    op.create_index(
        'ix_mfa_codes_user_used_expires',
        'mfa_codes',
        ['user_id', 'used', 'expires_at'],
        unique=False
    )
    op.alter_column('password_reset_tokens', 'token', new_column_name='token_hash', type_=sa.String(64), nullable=False)


def downgrade():
    op.drop_index('ix_mfa_codes_user_used_expires', 'mfa_codes')
    op.alter_column('mfa_codes', 'code_hash', new_column_name='code', type_=sa.String(6), nullable=False)
    op.alter_column('password_reset_tokens', 'token_hash', new_column_name='token', type_=sa.String(64), nullable=False)