"""`devos ask <question>` — grounded Q&A over the indexed project(s)."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import qa


def print_answer(ans) -> None:
    print(ans.text)
    if ans.sources:
        print("\nSources:")
        seen = set()
        for s in ans.sources:
            if s.location in seen:
                continue
            seen.add(s.location)
            print(f"  - {s.location}  [{s.project}]")


@register
class AskCommand(Command):
    name = "ask"
    help = "Ask a question about your indexed project(s); answers cite file:line sources."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("question", nargs="+", help="The question to ask.")
        parser.add_argument("--project", help="Limit retrieval to a project by name.")
        parser.add_argument("--limit", type=int, default=qa.DEFAULT_RETRIEVAL,
                            help=f"Max chunks to retrieve (default {qa.DEFAULT_RETRIEVAL}).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        question = " ".join(args.question)
        conn = ws.connect()
        try:
            ans = qa.answer(conn, question, provider=ws.ai, project=args.project, limit=args.limit)
        finally:
            conn.close()
        print_answer(ans)
        return 0
