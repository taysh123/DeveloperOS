"""`devos job <add|list|show|set|rm>` — track job leads (Career Assistant)."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import repo

STATUSES = repo.JOB_STATUSES


def _fmt(j) -> str:
    role = f" - {j['role']}" if j["role"] else ""
    return f"#{j['id']} [{j['status']}] {j['company']}{role}"


@register
class JobCommand(Command):
    name = "job"
    help = "Track job leads (add, list, show, set, rm)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="job_action", metavar="<action>")

        p_add = sub.add_parser("add", help="Add a job lead.")
        p_add.add_argument("company", nargs="+", help="Company name.")
        p_add.add_argument("--role")
        p_add.add_argument("--url")
        p_add.add_argument("--status", choices=STATUSES, default="saved")
        p_add.add_argument("--notes")

        p_list = sub.add_parser("list", help="List job leads.")
        p_list.add_argument("--status", choices=STATUSES)

        p_show = sub.add_parser("show", help="Show one job lead.")
        p_show.add_argument("id", type=int)

        p_set = sub.add_parser("set", help="Update fields of a job lead.")
        p_set.add_argument("id", type=int)
        p_set.add_argument("--company")
        p_set.add_argument("--role")
        p_set.add_argument("--url")
        p_set.add_argument("--status", choices=STATUSES)
        p_set.add_argument("--notes")

        p_rm = sub.add_parser("rm", help="Delete a job lead.")
        p_rm.add_argument("id", type=int)

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` first.")
            return 0
        action = getattr(args, "job_action", None)
        conn = ws.connect()
        try:
            if action == "add":
                jid = repo.create_job(conn, " ".join(args.company), role=args.role,
                                      url=args.url, status=args.status, notes=args.notes)
                print(f"Added job lead #{jid}.")
                return 0
            if action == "show":
                j = repo.get_job(conn, args.id)
                if j is None:
                    print(f"No job lead #{args.id}."); return 1
                print(_fmt(j))
                if j["url"]:
                    print(f"  url: {j['url']}")
                if j["notes"]:
                    print(f"  notes: {j['notes']}")
                print(f"  created {j['created_at']} - updated {j['updated_at']}")
                return 0
            if action == "set":
                if repo.get_job(conn, args.id) is None:
                    print(f"No job lead #{args.id}."); return 1
                repo.update_job(conn, args.id, company=args.company, role=args.role,
                                url=args.url, status=args.status, notes=args.notes)
                print(_fmt(repo.get_job(conn, args.id)))
                return 0
            if action == "rm":
                if repo.delete_job(conn, args.id):
                    print(f"Deleted job lead #{args.id}.")
                    return 0
                print(f"No job lead #{args.id}."); return 1
            # default / list
            jobs = repo.list_jobs(conn, status=getattr(args, "status", None))
            if not jobs:
                print("No job leads. Add one with `devos job add \"<company>\"`.")
                return 0
            print(f"Job leads ({len(jobs)}):")
            for j in jobs:
                print(f"  {_fmt(j)}")
            return 0
        finally:
            conn.close()
