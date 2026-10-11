"""Synchronous SQLAlchemy 2 engine/session factory.

Creating the engine does NOT open a connection (lazy), so importing this
module is safe without a running database.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session and always closing it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
