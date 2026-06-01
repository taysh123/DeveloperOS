"""`devos grade <path|topic> --answer ...` — evaluate a learner's answer, grounded in code."""
from __future__ import annotations

import argparse

from devos.commands.ask_cmd import print_answer
from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import learning


@register
class GradeCommand(Command):
    name = "grade"
    help = "Evaluate your answer about a file/topic against the code (feedback + strengths/weaknesses)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target", nargs="+", help="A file path or a topic the answer is about.")
        parser.add_argument("--answer", help="Your answer text.")
        parser.add_argument("--answer-file", help="Read your answer from this file.")
        parser.add_argument("--question", help="The question your answer responds to.")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=learning.qa.DEFAULT_RETRIEVAL,
                            help="Max chunks to retrieve in topic mode.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        answer = args.answer
        if not answer and args.answer_file:
            try:
                answer = open(args.answer_file, "r", encoding="utf-8", errors="ignore").read()
            except OSError as exc:
                print(f"error: cannot read --answer-file: {exc}")
                return 1
        if not answer or not answer.strip():
            print("error: provide your answer via --answer or --answer-file.")
            return 1

        target = " ".join(args.target)
        conn = ws.connect()
        try:
            grade = learning.grade(conn, target, answer=answer, provider=ws.ai,
                                   question=args.question, project=args.project, limit=args.limit)
        finally:
            conn.close()
        print_answer(grade)
        return 0
