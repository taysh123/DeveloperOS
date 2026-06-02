"""Configuration and data-location resolution for DeveloperOS.

Resolution order for the data directory:
1. ``DEVOS_HOME`` environment variable (explicit override).
2. ``%APPDATA%\\DeveloperOS`` on Windows.
3. ``$XDG_DATA_HOME/devos`` or ``~/.local/share/devos`` on POSIX.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "DeveloperOS"
DB_FILENAME = "devos.db"


def default_data_dir() -> Path:
    """Return the platform-appropriate data directory (not created here)."""
    override = os.environ.get("DEVOS_HOME")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR_NAME

    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return base / "devos"


@dataclass(frozen=True)
class Config:
    """Resolved runtime configuration."""

    data_dir: Path
    ai_provider: str
    ai_enabled: bool = True

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILENAME

    def ensure_data_dir(self) -> Path:
        """Create the data directory if needed and return it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def is_initialized(self) -> bool:
        return self.db_path.exists()


def load_config() -> Config:
    """Build a Config from the environment + persisted settings, with sensible defaults.

    AI-provider resolution order: ``DEVOS_AI_PROVIDER`` env var (explicit override) →
    the persisted ``settings.json`` choice → ``"mock"``. The persisted store also carries
    the AI-enabled toggle. Settings are non-secret; keys never live here (see settings.py).
    """
    from devos import settings  # local import avoids an import cycle at module load

    data_dir = default_data_dir()
    stored = settings.load(data_dir)
    provider = os.environ.get("DEVOS_AI_PROVIDER") or stored.ai_provider
    return Config(data_dir=data_dir, ai_provider=provider, ai_enabled=stored.ai_enabled)
