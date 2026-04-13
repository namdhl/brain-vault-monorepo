"""
SQLAlchemy ORM models for Brain Vault.

These mirror the Pydantic schemas in schemas.py but target Postgres.
Local JSON files remain the fallback when DATABASE_URL is not set.
"""
from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id = Column(String(64), primary_key=True)
    type = Column(String(32), nullable=False)
    source = Column(String(32), nullable=False, default="api")
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    original_url = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    note_path = Column(Text, nullable=True)
    language = Column(String(16), nullable=True)
    canonical_hash = Column(String(64), nullable=True)
    summary = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    failed_stage = Column(String(64), nullable=True)

    assets = relationship("Asset", back_populates="item", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="item", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(64), primary_key=True)
    item_id = Column(String(64), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False, default="original")
    storage_path = Column(Text, nullable=False)
    mime_type = Column(String(128), nullable=False)
    filename = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("Item", back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String(64), primary_key=True)
    item_id = Column(String(64), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=True)
    stage = Column(String(64), nullable=False, default="raw_persisted")
    status = Column(String(32), nullable=False, default="queued")
    attempt = Column(Integer, nullable=False, default=0)
    retried_from = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    error = Column(Text, nullable=True)

    item = relationship("Item", back_populates="jobs")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    upload_id = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    item_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
