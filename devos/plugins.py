"""Plugin / extension discovery and loading (Phase 9, slice 5).

Plugins extend DeveloperOS by registering commands (`commands.base.register`) and/or AI
providers (`providers.ai.register_provider`) — no parallel machinery. Two sources:

1. **Entry points** in group ``devos.plugins`` (installed packages the user chose to install).
   Each entry point resolves to a zero-arg callable that performs registration.
2. **Local files** ``<data_dir>/plugins/*.py`` — loaded ONLY when ``DEVOS_ENABLE_LOCAL_PLUGINS=1``
   (opt-in; default off, since loading them executes arbitrary code — see docs/SECURITY.md).

Loading is fail-safe: a broken plugin is recorded in ``ERRORS`` and skipped; the CLI keeps
working. ``LOADED`` holds the names that loaded successfully.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from devos.config import default_data_dir

LOADED: list[str] = []
ERRORS: list[tuple[str, str]] = []

ENTRY_POINT_GROUP = "devos.plugins"
LOCAL_ENABLE_ENV = "DEVOS_ENABLE_LOCAL_PLUGINS"


def local_plugins_dir() -> Path:
    return default_data_dir() / "plugins"


def _record(name: str, ok: bool, error: str = "") -> None:
    if ok:
        if name not in LOADED:
            LOADED.append(name)
    else:
        ERRORS.append((name, error))


def _entry_points():
    """Return entry points in our group (stdlib importlib.metadata)."""
    from importlib import metadata
    try:
        eps = metadata.entry_points()
    except Exception:
        return []
    # Python 3.10+: selectable API; older returns a dict.
    try:
        return list(eps.select(group=ENTRY_POINT_GROUP))
    except AttributeError:
        return list(eps.get(ENTRY_POINT_GROUP, []))  # pragma: no cover


def load_entry_point_plugins(eps=None) -> list[str]:
    """Load plugins from entry points (group ``devos.plugins``).

    ``eps`` may be injected (iterable of objects with ``.name`` and ``.load()``) for testing;
    otherwise discovered from installed distributions. Each loaded object is called with no args.
    """
    if eps is None:
        eps = _entry_points()
    loaded: list[str] = []
    for ep in eps:
        name = getattr(ep, "name", str(ep))
        try:
            target = ep.load()
            target()  # the plugin registers its commands/providers
        except Exception as exc:  # isolate broken plugins
            _record(name, False, f"{type(exc).__name__}: {exc}")
            continue
        _record(name, True)
        loaded.append(name)
    return loaded


def load_local_plugins(plugins_dir: Path) -> list[str]:
    """Import every ``*.py`` in ``plugins_dir`` (their import performs registration)."""
    plugins_dir = Path(plugins_dir)
    if not plugins_dir.is_dir():
        return []
    loaded: list[str] = []
    for path in sorted(plugins_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod_name = f"devos_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:
            _record(path.stem, False, f"{type(exc).__name__}: {exc}")
            continue
        _record(path.stem, True)
        loaded.append(path.stem)
    return loaded


_loaded_once = False


def ensure_loaded() -> None:
    """Load installed plugins exactly once per process (called at CLI startup)."""
    global _loaded_once
    if _loaded_once:
        return
    _loaded_once = True
    load_installed()


def load_installed() -> list[str]:
    """Load all available plugins (entry points always; local dir only if opted in). Guarded."""
    loaded: list[str] = []
    try:
        loaded += load_entry_point_plugins()
    except Exception as exc:  # never let discovery crash the CLI
        ERRORS.append(("<entry-points>", f"{type(exc).__name__}: {exc}"))
    if os.environ.get(LOCAL_ENABLE_ENV) == "1":
        try:
            loaded += load_local_plugins(local_plugins_dir())
        except Exception as exc:
            ERRORS.append(("<local-plugins>", f"{type(exc).__name__}: {exc}"))
    return loaded
