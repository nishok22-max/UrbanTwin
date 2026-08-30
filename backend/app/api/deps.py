"""Shared FastAPI dependencies (DB session, services, config)."""
from __future__ import annotations

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.services.consequence.engine import ConsequenceEngine, get_engine


def get_current_settings() -> Settings:
    return get_settings()


def get_consequence_engine() -> ConsequenceEngine:
    return get_engine()
