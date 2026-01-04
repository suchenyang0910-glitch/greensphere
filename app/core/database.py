"""Database configuration and FastAPI dependency.

This repo initially had multiple database modules and a hard-coded MySQL DSN.
To make the project runnable for local development, we default to SQLite.

Set DATABASE_URL in .env to use MySQL/Postgres in production.
Examples:
  SQLite:  sqlite:///./data/greensphere.db
  MySQL:   mysql+pymysql://user:pass@host:3306/greensphere
  Postgres:postgresql+psycopg://user:pass@host:5432/greensphere
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _default_sqlite_url() -> str:
    # Create a local data directory for the sqlite file
    data_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'greensphere.db').as_posix()}"


DATABASE_URL = os.getenv("DATABASE_URL") or _default_sqlite_url()


connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # Needed for SQLite when used in multithreaded ASGI servers
    connect_args = {"check_same_thread": False}


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
