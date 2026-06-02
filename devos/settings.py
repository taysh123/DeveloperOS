"""User-controllable settings (non-secret) + AI-provider catalog/resolution.

Dashboard slice 5 (Settings & AI Management). Two design rules drive this module:

1. **No secrets here, ever.** Only non-secret preferences (`ai_enabled`, `ai_provider`)
   are persisted, to ``<data_dir>/settings.json``. API keys come from environment
   variables / an OS keychain (see docs/SECURITY.md sec. 2) — never SQLite, never this
   file, never the frontend. We only ever report whether a key is *present* as a boolean.
2. **Reuse the single provider registry.** Provider *selection* is a stored preference,
   but the *effective* provider is resolved through ``providers.ai.available_providers()``
   so an unavailable (not-yet-implemented) or disabled choice falls back safely to the
   offline ``mock`` — no external calls, no key required.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from devos.providers.ai import available_providers

SETTINGS_FILENAME = "settings.json"
DEFAULT_PROVIDER = "mock"

# Ordered provider catalog. Metadata here drives the dashboard's privacy ("local" vs
# "cloud") and cost ("free" vs paid) messaging so a non-technical user understands the
# implications before switching. `key_env` names the environment variable a future real
# provider would read its key from — the value is never read into the catalog.
PROVIDERS = [
    {"id": "mock", "label": "Offline (Mock)", "kind": "local", "free": True,
     "requires_key": False, "key_env": None, "endpoint_hint": None,
     "blurb": "Runs entirely on your machine. No internet, no cost. This is the default."},
    {"id": "ollama", "label": "Ollama (local models)", "kind": "local", "free": True,
     "requires_key": False, "key_env": None, "endpoint_hint": "http://localhost:11434",
     "blurb": "Local models served by Ollama on your own machine. Private and free — "
              "nothing leaves your computer."},
    {"id": "claude", "label": "Claude (Anthropic)", "kind": "cloud", "free": False,
     "requires_key": True, "key_env": "ANTHROPIC_API_KEY", "endpoint_hint": None,
     "blurb": "Cloud AI from Anthropic. Sends your prompts over the internet and needs an "
              "API key. Usage may cost money."},
    {"id": "openai", "label": "OpenAI", "kind": "cloud", "free": False,
     "requires_key": True, "key_env": "OPENAI_API_KEY", "endpoint_hint": None,
     "blurb": "Cloud AI from OpenAI. Sends your prompts over the internet and needs an "
              "API key. Usage may cost money."},
]
PROVIDER_IDS = [p["id"] for p in PROVIDERS]


@dataclass(frozen=True)
class Settings:
    """Resolved, non-secret user preferences."""

    ai_enabled: bool = True
    ai_provider: str = DEFAULT_PROVIDER


def _path(data_dir) -> Path:
    return Path(data_dir) / SETTINGS_FILENAME


def load(data_dir) -> Settings:
    """Read settings from ``<data_dir>/settings.json``; fall back to safe defaults.

    Missing, unreadable, corrupt, or unexpected content never raises — it yields the
    defaults (AI enabled, offline ``mock``). Unknown providers are coerced to ``mock``.
    """
    try:
        raw = json.loads(_path(data_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    enabled = raw.get("ai_enabled", True)
    if not isinstance(enabled, bool):
        enabled = True
    provider = raw.get("ai_provider", DEFAULT_PROVIDER)
    if provider not in PROVIDER_IDS:
        provider = DEFAULT_PROVIDER
    return Settings(ai_enabled=enabled, ai_provider=provider)


def save(data_dir, *, ai_enabled: bool | None = None,
         ai_provider: str | None = None) -> Settings:
    """Persist the two non-secret preferences (atomically). Returns the new Settings.

    Only ``ai_enabled`` and ``ai_provider`` are accepted — the keyword-only signature
    makes it impossible to smuggle a secret (e.g. ``api_key``) onto disk. Unknown
    providers raise ``ValueError``. A ``None`` argument leaves that field unchanged.
    """
    current = load(data_dir)
    enabled = current.ai_enabled if ai_enabled is None else bool(ai_enabled)
    provider = current.ai_provider if ai_provider is None else ai_provider
    if provider not in PROVIDER_IDS:
        raise ValueError(
            f"Unknown provider {provider!r}. Choose one of: {', '.join(PROVIDER_IDS)}.")
    payload = {"ai_enabled": enabled, "ai_provider": provider}  # whitelist — never secrets
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    tmp = _path(data_dir).with_name(SETTINGS_FILENAME + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(_path(data_dir))
    return Settings(ai_enabled=enabled, ai_provider=provider)


def provider_meta(provider_id: str) -> dict | None:
    return next((p for p in PROVIDERS if p["id"] == provider_id), None)


def effective_provider_name(preferred: str, enabled: bool) -> str:
    """Resolve the provider actually used: disabled or unavailable → offline ``mock``."""
    if not enabled:
        return DEFAULT_PROVIDER
    return preferred if preferred in available_providers() else DEFAULT_PROVIDER


def key_present(provider_id: str) -> bool:
    """Whether the provider's API-key env var is set. Returns only a boolean — never the value."""
    meta = provider_meta(provider_id)
    if not meta or not meta.get("key_env"):
        return False
    return bool(os.environ.get(meta["key_env"]))
