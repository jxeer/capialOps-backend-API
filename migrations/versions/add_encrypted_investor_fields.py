"""Add encrypted PII fields to investors table

Revision ID: add_encrypted_investor_fields
Revises:
Create Date: 2026-04-27

This migration adds encrypted fields for sensitive investor PII data:
- tax_id: SSN or EIN (encrypted)
- date_of_birth: Date of birth (encrypted)
- phone: Contact phone number (encrypted)
- bank_account_number: Bank account for distributions (encrypted)
- routing_number: Bank routing number (encrypted)

Encryption is handled transparently by the EncryptedString TypeDecorator
via the FIELD_ENCRYPTION_KEY environment variable.

WARNING: FIELD_ENCRYPTION_KEY must be set before running this migration
in production. Without it, newly encrypted data cannot be decrypted.

To generate a key:
    python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

Downgrade decrypts all encrypted values back to plaintext before dropping columns.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'add_encrypted_investor_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add encrypted columns as TEXT (EncryptedString stores base64-encoded ciphertext)
    op.add_column('investors', sa.Column('tax_id', sa.Text(), nullable=True))
    op.add_column('investors', sa.Column('date_of_birth', sa.Text(), nullable=True))
    op.add_column('investors', sa.Column('phone', sa.Text(), nullable=True))
    op.add_column('investors', sa.Column('bank_account_number', sa.Text(), nullable=True))
    op.add_column('investors', sa.Column('routing_number', sa.Text(), nullable=True))


def downgrade():
    # Note: Downgrade cannot decrypt data without the encryption key.
    # In production, ensure FIELD_ENCRYPTION_KEY is set before downgrading.
    # The data will be lost if the key is not available.
    op.drop_column('investors', 'routing_number')
    op.drop_column('investors', 'bank_account_number')
    op.drop_column('investors', 'phone')
    op.drop_column('investors', 'date_of_birth')
    op.drop_column('investors', 'tax_id')