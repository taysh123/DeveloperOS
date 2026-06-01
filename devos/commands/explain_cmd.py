"""`devos explain [path]` — explain a file or the whole project, with citations."""
from __future__ import annotations

import argparse

from devos.commands.ask_cmd import print_answer
from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import qa


@register
class ExplainCommand(Command):
    name = "explain"
    help = "Explain a file (devos explain <path>) or the project overview (devos explain)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", help="File to explain (omit for a project overview).")
        parser.add_argument("--project", help="Project name (for the overview when ambiguous).")
        parser.add_argument("--limit", type=int, default=qa.DEFAULT_RETRIEVAL,
                            help=f"Max files/chunks to include (default {qa.DEFAULT_RETRIEVAL}).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        conn = ws.connect()
        try:
            ans = qa.explain(conn, args.path, provider=ws.ai, project=args.project, limit=args.limit)
        finally:
            conn.close()
        print_answer(ans)
        return 0
