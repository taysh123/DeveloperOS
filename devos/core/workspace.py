"""Workspace context: ties together config, storage, and providers.

This is the object commands operate against. It is created once per CLI invocation
and is the seam the future local API / dashboard will reuse.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from devos.config import Config, load_config
from devos.providers.ai import AIProvider, get_provider
from devos.storage import db


@dataclass
class Workspace:
    config: Config

    @classmethod
    def load(cls) -> "Workspace":
        return cls(config=load_config())

    @property
    def ai(self) -> AIProvider:
        return get_provider(self.config.ai_provider)

    def is_initialized(self) -> bool:
        return self.config.is_initialized()

    def initialize(self) -> sqlite3.Connection:
        """Create the data dir + database and apply the schema (idempotent)."""
        self.config.ensure_data_dir()
        return db.initialize(self.config.db_path)

    def connect(self) -> sqlite3.Connection:
        """Open a connection to an already-initialized database."""
        if not self.is_initialized():
            raise RuntimeError("DeveloperOS is not initialized. Run `devos init` first.")
        return db.connect(self.config.db_path)
