"""`devos plugins` — list loaded plugins and any load errors."""
from __future__ import annotations

import argparse

from devos import plugins
from devos.commands.base import Command, register
from devos.core.workspace import Workspace


@register
class PluginsCommand(Command):
    name = "plugins"
    help = "List loaded plugins (entry-point + opt-in local) and any load errors."

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if plugins.LOADED:
            print(f"Loaded plugins ({len(plugins.LOADED)}):")
            for name in plugins.LOADED:
                print(f"  - {name}")
        else:
            print("No plugins loaded.")
            print(f"  (install a `{plugins.ENTRY_POINT_GROUP}` package, or set "
                  f"{plugins.LOCAL_ENABLE_ENV}=1 and drop *.py in {plugins.local_plugins_dir()})")

        if plugins.ERRORS:
            print(f"Errors ({len(plugins.ERRORS)}):")
            for name, msg in plugins.ERRORS:
                print(f"  - {name}: {msg}")
        return 0
