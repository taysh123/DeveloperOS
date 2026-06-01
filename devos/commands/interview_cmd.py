"""`devos interview <job-id> [--n N]` — grounded interview prep from a job lead's notes."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import career


@register
class InterviewCommand(Command):
    name = "interview"
    help = "Generate interview-prep questions grounded in a tracked job lead's notes."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("job_id", type=int, help="The job lead id (see `devos job list`).")
        parser.add_argument("--n", type=int, default=5,
                            help=f"Number of questions (default 5, max {career.MAX_INTERVIEW_QUESTIONS}).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` first.")
            return 0
        conn = ws.connect()
        try:
            prep = career.interview_prep(conn, args.job_id, provider=ws.ai, n=args.n)
        finally:
            conn.close()

        print(prep.text)
        if prep.sources:
            print("\nSource:")
            for s in prep.sources:
                print(f"  - job #{s['job_id']} {s['company']} - {s['role']}")
        return 0
