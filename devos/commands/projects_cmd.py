"""`devos projects` — list registered projects."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import repo


@register
class ProjectsCommand(Command):
    name = "projects"
    help = "List registered projects and their file counts."

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("No projects yet - run `devos scan <path>` to add one.")
            return 0

        conn = ws.connect()
        try:
            projects = repo.list_projects(conn)
        finally:
            conn.close()

        if not projects:
            print("No projects yet - run `devos scan <path>` to add one.")
            return 0

        print(f"Projects ({len(projects)}):")
        for p in projects:
            scanned = p["last_scanned_at"] or "never"
            print(f"  - {p['name']}  [{p['file_count']} files, scanned {scanned}]")
            print(f"      {p['root_path']}")
        return 0
