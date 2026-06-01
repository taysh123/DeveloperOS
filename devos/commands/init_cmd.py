"""`devos init` — create the local data dir and initialize the database."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import db


@register
class InitCommand(Command):
    name = "init"
    help = "Create the local data directory and initialize the SQLite database."

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        already = ws.is_initialized()
        conn = ws.initialize()
        try:
            version = db.schema_version(conn)
        finally:
            conn.close()

        state = "already initialized" if already else "initialized"
        print(f"DeveloperOS {state}.")
        print(f"  data dir : {ws.config.data_dir}")
        print(f"  database : {ws.config.db_path}")
        print(f"  schema   : v{version}")
        print(f"  ai       : {ws.config.ai_provider} (mock until a real provider is wired in)")
        return 0
