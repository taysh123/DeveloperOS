"""`devos remember <title> [--body ...]` — store a long-term memory entry."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import repo

MEMORY_KINDS = ("decision", "summary", "preference", "note")


@register
class RememberCommand(Command):
    name = "remember"
    help = "Store a long-term memory entry (decision, summary, preference, or note)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("title", nargs="+", help="Short title of the memory.")
        parser.add_argument("--body", default="", help="Full detail (defaults to the title).")
        parser.add_argument("--kind", choices=MEMORY_KINDS, default="note")
        parser.add_argument("--tags", help="Comma-separated tags.")
        parser.add_argument("--project", help="Attach to a project by name (default: global).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        ws.initialize().close()
        title = " ".join(args.title)
        body = args.body or title
        conn = ws.connect()
        try:
            project_id = None
            if args.project:
                project_id = repo.project_id_by_name(conn, args.project)
                if project_id is None:
                    print(f"error: unknown project '{args.project}'.")
                    return 1
            mid = repo.create_memory(conn, project_id, kind=args.kind,
                                     title=title, body=body, tags=args.tags)
        finally:
            conn.close()
        print(f"Remembered #{mid} ({args.kind}): {title}")
        return 0
