"""`devos recall <query>` — search across memory, tasks, and project code."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import recall as recall_mod


@register
class RecallCommand(Command):
    name = "recall"
    help = "Recall across memory, tasks, and indexed code (retrieval-only, offline)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("query", nargs="*", help="Search terms (omit to list recent).")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=recall_mod.qa.DEFAULT_RETRIEVAL,
                            help="Max results per group.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` or `devos scan <path>` first.")
            return 0
        query = " ".join(args.query)
        conn = ws.connect()
        try:
            result = recall_mod.recall(conn, query, project=args.project, limit=args.limit)
        finally:
            conn.close()

        if result.empty:
            print(f"Nothing found for '{query}'." if query.strip() else "Nothing recorded yet.")
            return 0

        if result.memories:
            print(f"Memory ({len(result.memories)}):")
            for m in result.memories:
                print(f"  - #{m['id']} ({m['kind']}) {m['title']}")
        if result.tasks:
            print(f"Tasks ({len(result.tasks)}):")
            for t in result.tasks:
                print(f"  - #{t['id']} [{t['status']}/{t['priority']}] {t['title']}")
        if result.code:
            print(f"Code ({len(result.code)}):")
            for c in result.code:
                print(f"  - {c.location}  [{c.project}]")
        return 0
