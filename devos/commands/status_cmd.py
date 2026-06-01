"""`devos status` — report where DeveloperOS stands."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import db


@register
class StatusCommand(Command):
    name = "status"
    help = "Show data location, schema version, AI provider, and stored counts."

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        print("DeveloperOS status")
        print(f"  data dir : {ws.config.data_dir}")
        print(f"  database : {ws.config.db_path}")
        print(f"  ai       : {ws.config.ai_provider}")

        if not ws.is_initialized():
            print("  state    : NOT initialized - run `devos init` to get started.")
            return 0

        conn = ws.connect()
        try:
            version = db.schema_version(conn)
            counts = db.table_counts(conn)
        finally:
            conn.close()

        print(f"  schema   : v{version}")
        print("  stored   :")
        for table, count in counts.items():
            print(f"    - {table:<9}: {count}")
        return 0
