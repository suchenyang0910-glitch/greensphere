"""Compatibility re-export.

Some modules import get_db/SessionLocal/Base from `app.database`.
The canonical implementation lives in `app.core.database`.
"""

from app.core.database import Base, SessionLocal, engine, get_db  # noqa: F401
