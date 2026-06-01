"""`devos learn <path|topic>` — a grounded, leveled explanation of your code."""
from __future__ import annotations

import argparse

from devos.commands.ask_cmd import print_answer
from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import learning


@register
class LearnCommand(Command):
    name = "learn"
    help = "Explain a file or topic from your indexed code at a chosen level (cites file:line)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target", nargs="+", help="A file path or a topic to learn about.")
        parser.add_argument("--level", choices=tuple(learning.LEVELS), default="intermediate",
                            help="Explanation depth (default: intermediate).")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=learning.qa.DEFAULT_RETRIEVAL,
                            help="Max chunks to retrieve in topic mode.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        target = " ".join(args.target)
        conn = ws.connect()
        try:
            lesson = learning.learn(conn, target, provider=ws.ai, level=args.level,
                                    project=args.project, limit=args.limit)
        finally:
            conn.close()
        print_answer(lesson)  # Lesson exposes .text and .sources (file:line)
        return 0
