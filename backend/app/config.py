"""Pydantic Settings — env-driven config. Keys: DATABASE_URL, LLM_API_KEY, CORS_ORIGINS, CITY_ID, RANDOM_SEED."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://urbantwin:urbantwin@localhost:5432/urbantwin"
    llm_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    city_id: str = "tnagar"
    random_seed: int = 42

    # Paths (resolved at runtime relative to repo root)
    data_dir: str = str(Path(__file__).parent.parent.parent / "data" / "prepared")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def nodes_geojson(self) -> Path:
        return Path(self.data_dir) / "tnagar_nodes.geojson"

    @property
    def edges_geojson(self) -> Path:
        return Path(self.data_dir) / "tnagar_edges.geojson"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
