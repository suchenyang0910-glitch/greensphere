"""Compatibility layer.

Historically the repo used multiple database modules. The canonical database
implementation is `app.core.database` which defaults to SQLite for local dev.
"""

from app.core.database import engine, SessionLocal, get_db  # noqa: F401
