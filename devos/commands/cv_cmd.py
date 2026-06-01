"""`devos cv <file> [--job ID]` — keyword-match a local CV against job notes (offline)."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import career
from devos.storage import repo


@register
class CvCommand(Command):
    name = "cv"
    help = "Analyze a local CV/resume file against tracked job notes (offline keyword match)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file", help="Path to your CV/resume text file.")
        parser.add_argument("--job", type=int, help="Compare against this job lead's notes (else all).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` first.")
            return 0
        try:
            cv_text = open(args.file, "r", encoding="utf-8", errors="ignore").read()
        except OSError as exc:
            print(f"error: cannot read CV file: {exc}")
            return 1

        conn = ws.connect()
        try:
            if args.job is not None:
                job = repo.get_job(conn, args.job)
                if job is None:
                    print(f"No job lead #{args.job}."); return 1
                target = " ".join(filter(None, [job["role"], job["company"], job["notes"]]))
                label = f"job #{job['id']} ({job['company']})"
            else:
                jobs = repo.list_jobs(conn)
                if not jobs:
                    print("No job leads to compare against. Add one with `devos job add`.")
                    return 0
                target = " ".join(filter(None, (j["notes"] for j in jobs)))
                label = f"all {len(jobs)} tracked job(s)"
        finally:
            conn.close()

        analysis = career.analyze_cv(cv_text, target, target_label=label)
        if not analysis.target_keywords:
            print(f"No keywords found in {label} to match against (add job notes).")
            return 0

        print(f"CV vs {label}")
        print(f"  Coverage : {analysis.coverage * 100:.0f}%  "
              f"({len(analysis.matched)}/{len(analysis.target_keywords)} keywords)")
        print(f"  Matched  : {', '.join(sorted(analysis.matched)) or '(none)'}")
        print(f"  Missing  : {', '.join(sorted(analysis.missing)) or '(none)'}")
        return 0
