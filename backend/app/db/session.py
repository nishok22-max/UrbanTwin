"""Database engine and session setup (PostgreSQL + PostGIS).

Note: For M2, the in-memory NetworkX graph is the primary high-speed read-model.
This DB session is used for optional persistence of scenarios, results, and audit logs.
"""
from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionFactory = None


def get_db_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        try:
            _engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
        except Exception as e:
            logger.warning("Could not initialize DB engine (%s). Running with in-memory store.", e)
            _engine = None
    return _engine


def get_db() -> Generator[Session | None, None, None]:
    """Dependency that yields a DB session or None if DB is unreachable."""
    global _SessionFactory
    engine = get_db_engine()
    if engine is None:
        yield None
        return

    if _SessionFactory is None:
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = _SessionFactory()
    try:
        yield db
    except Exception as e:
        logger.warning("DB session error: %s", e)
        yield None
    finally:
        db.close()
