"""`devos quiz <path|topic>` — generate grounded review questions about your code."""
from __future__ import annotations

import argparse

from devos.commands.ask_cmd import print_answer
from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import learning


@register
class QuizCommand(Command):
    name = "quiz"
    help = "Generate grounded review questions about a file or topic from your indexed code."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target", nargs="+", help="A file path or a topic to quiz on.")
        parser.add_argument("--n", type=int, default=5,
                            help=f"Number of questions (default 5, max {learning.MAX_QUIZ_QUESTIONS}).")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=learning.qa.DEFAULT_RETRIEVAL,
                            help="Max chunks to retrieve in topic mode.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        if args.n < 1:
            print("error: --n must be >= 1.")
            return 1
        target = " ".join(args.target)
        conn = ws.connect()
        try:
            quiz = learning.quiz(conn, target, provider=ws.ai, n=args.n,
                                 project=args.project, limit=args.limit)
        finally:
            conn.close()
        print_answer(quiz)  # Quiz exposes .text and .sources (file:line)
        return 0
