"""`devos serve` — run the local, read-only dashboard (loopback only)."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace


@register
class ServeCommand(Command):
    name = "serve"
    help = "Run the local dashboard web UI (read-only, 127.0.0.1 only)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--host", default="127.0.0.1",
                            help="Bind address (default 127.0.0.1 - loopback only).")
        parser.add_argument("--port", type=int, default=8765, help="Port (default 8765).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing to show yet - run `devos init` or `devos scan <path>` first.")
            return 0
        from devos.api import server  # local import: only needed when serving

        srv = server.create_server(args.host, args.port)
        host, port = srv.server_address[0], srv.server_address[1]
        print(f"DeveloperOS dashboard: http://{host}:{port}  (read-only; Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
        finally:
            srv.server_close()
        return 0
