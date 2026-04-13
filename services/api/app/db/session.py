"""
SQLAlchemy async-compatible session factory.

When DATABASE_URL is set, Postgres is used.
Otherwise falls back to the local JSON file store (for dev / no-Postgres mode).
"""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None and DATABASE_URL:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db() -> Generator[Session | None, None, None]:
    """FastAPI dependency: yield a DB session or None (JSON fallback)."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
