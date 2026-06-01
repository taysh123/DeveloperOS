"""`devos task <add|list|show|set|rm>` — manage tasks/bugs/features."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.storage import repo

KINDS = ("task", "bug", "feature")
STATUSES = ("todo", "in_progress", "blocked", "done")
PRIORITIES = ("low", "medium", "high")


def _resolve_pid(conn, project: str | None) -> "int | None | bool":
    """Return project id, None for global, or False if a named project is unknown."""
    if not project:
        return None
    pid = repo.project_id_by_name(conn, project)
    return pid if pid is not None else False


def _fmt(t) -> str:
    ms = f" ~{t['milestone']}" if t["milestone"] else ""
    return f"#{t['id']} [{t['status']}/{t['priority']}] ({t['kind']}) {t['title']}{ms}"


@register
class TaskCommand(Command):
    name = "task"
    help = "Manage tasks/bugs/features (add, list, show, set, rm)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="task_action", metavar="<action>")

        p_add = sub.add_parser("add", help="Add a task.")
        p_add.add_argument("title", nargs="+", help="Task title.")
        p_add.add_argument("--kind", choices=KINDS, default="task")
        p_add.add_argument("--priority", choices=PRIORITIES, default="medium")
        p_add.add_argument("--status", choices=STATUSES, default="todo")
        p_add.add_argument("--milestone")
        p_add.add_argument("--notes")
        p_add.add_argument("--project")

        p_list = sub.add_parser("list", help="List tasks.")
        p_list.add_argument("--status", choices=STATUSES)
        p_list.add_argument("--kind", choices=KINDS)
        p_list.add_argument("--milestone")
        p_list.add_argument("--project")

        p_show = sub.add_parser("show", help="Show one task.")
        p_show.add_argument("id", type=int)

        p_set = sub.add_parser("set", help="Update fields of a task.")
        p_set.add_argument("id", type=int)
        p_set.add_argument("--title")
        p_set.add_argument("--kind", choices=KINDS)
        p_set.add_argument("--status", choices=STATUSES)
        p_set.add_argument("--priority", choices=PRIORITIES)
        p_set.add_argument("--milestone")
        p_set.add_argument("--notes")

        p_rm = sub.add_parser("rm", help="Delete a task.")
        p_rm.add_argument("id", type=int)

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` or `devos scan <path>` first.")
            return 0
        action = getattr(args, "task_action", None)
        conn = ws.connect()
        try:
            if action == "add":
                pid = _resolve_pid(conn, args.project)
                if pid is False:
                    print(f"error: unknown project '{args.project}'."); return 1
                tid = repo.create_task(conn, pid, " ".join(args.title), kind=args.kind,
                                       status=args.status, priority=args.priority,
                                       milestone=args.milestone, notes=args.notes)
                print(f"Created task #{tid}.")
                return 0
            if action == "show":
                t = repo.get_task(conn, args.id)
                if t is None:
                    print(f"No task #{args.id}."); return 1
                print(_fmt(t))
                if t["notes"]:
                    print(f"  notes: {t['notes']}")
                print(f"  created {t['created_at']} - updated {t['updated_at']}")
                return 0
            if action == "set":
                if repo.get_task(conn, args.id) is None:
                    print(f"No task #{args.id}."); return 1
                repo.update_task(conn, args.id, title=args.title, kind=args.kind,
                                 status=args.status, priority=args.priority,
                                 milestone=args.milestone, notes=args.notes)
                print(_fmt(repo.get_task(conn, args.id)))
                return 0
            if action == "rm":
                if repo.delete_task(conn, args.id):
                    print(f"Deleted task #{args.id}.")
                    return 0
                print(f"No task #{args.id}."); return 1
            # default / "list"
            pid = _resolve_pid(conn, getattr(args, "project", None))
            if pid is False:
                print(f"error: unknown project '{args.project}'."); return 1
            tasks = repo.list_tasks(conn, project_id=pid,
                                    status=getattr(args, "status", None),
                                    kind=getattr(args, "kind", None),
                                    milestone=getattr(args, "milestone", None))
            if not tasks:
                print("No tasks. Add one with `devos task add \"<title>\"`.")
                return 0
            print(f"Tasks ({len(tasks)}):")
            for t in tasks:
                print(f"  {_fmt(t)}")
            return 0
        finally:
            conn.close()
