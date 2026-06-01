"""`devos search <query>` — ranked keyword search over the index."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import index as index_mod


@register
class SearchCommand(Command):
    name = "search"
    help = "Search indexed code/docs by keyword (ranked, with file:line references)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("query", nargs="+", help="Search terms (implicit AND).")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=10, help="Max results (default 10).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        query = " ".join(args.query)
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        conn = ws.connect()
        try:
            hits = index_mod.search(conn, query, project=args.project, limit=args.limit)
        finally:
            conn.close()

        if not hits:
            print(f"No matches for '{query}'.")
            return 0

        print(f"{len(hits)} result(s) for '{query}':")
        for i, h in enumerate(hits, 1):
            snippet = " ".join(h.snippet.split())
            print(f"  {i}. {h.location}  [{h.project}]")
            print(f"     {snippet}")
        return 0
