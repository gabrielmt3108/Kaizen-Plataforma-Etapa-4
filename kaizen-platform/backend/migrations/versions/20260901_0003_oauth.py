"""OAuth Google e códigos de troca de uso único.

Revision ID: 20260901_0003
Revises: 20260831_0002
Create Date: 2026-09-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260901_0003"
down_revision: str | None = "20260831_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
    )
    op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"])

    op.create_table(
        "oauth_login_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("return_to", sa.String(length=1000), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_oauth_login_attempts_state_hash", "oauth_login_attempts", ["state_hash"], unique=True
    )
    op.create_index(
        "ix_oauth_login_attempts_expires_at", "oauth_login_attempts", ["expires_at"]
    )

    op.create_table(
        "oauth_exchange_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_oauth_exchange_codes_token_hash", "oauth_exchange_codes", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_oauth_exchange_codes_expires_at", "oauth_exchange_codes", ["expires_at"]
    )
    op.create_index("ix_oauth_exchange_codes_user_id", "oauth_exchange_codes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_oauth_exchange_codes_user_id", table_name="oauth_exchange_codes")
    op.drop_index("ix_oauth_exchange_codes_expires_at", table_name="oauth_exchange_codes")
    op.drop_index("ix_oauth_exchange_codes_token_hash", table_name="oauth_exchange_codes")
    op.drop_table("oauth_exchange_codes")
    op.drop_index("ix_oauth_login_attempts_expires_at", table_name="oauth_login_attempts")
    op.drop_index("ix_oauth_login_attempts_state_hash", table_name="oauth_login_attempts")
    op.drop_table("oauth_login_attempts")
    op.drop_index("ix_oauth_identities_user_id", table_name="oauth_identities")
    op.drop_table("oauth_identities")
