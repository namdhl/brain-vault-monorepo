"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="api"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("original_url", sa.Text, nullable=True),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note_path", sa.Text, nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("canonical_hash", sa.String(64), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("failed_stage", sa.String(64), nullable=True),
    )
    op.create_index("ix_items_status", "items", ["status"])
    op.create_index("ix_items_type", "items", ["type"])
    op.create_index("ix_items_source", "items", ["source"])
    op.create_index("ix_items_created_at", "items", ["created_at"])
    op.create_index("ix_items_canonical_hash", "items", ["canonical_hash"])

    op.create_table(
        "assets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("item_id", sa.String(64), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="original"),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assets_item_id", "assets", ["item_id"])

    op.create_table(
        "jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("item_id", sa.String(64), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.String(64), nullable=True),
        sa.Column("stage", sa.String(64), nullable=False, server_default="raw_persisted"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retried_from", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_jobs_item_id", "jobs", ["item_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "upload_sessions",
        sa.Column("upload_id", sa.String(64), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("item_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("upload_sessions")
    op.drop_table("jobs")
    op.drop_table("assets")
    op.drop_table("items")
