"""PyInstaller entry point — DeveloperOS.exe runs the `devos app` launcher (D-0030/D-0031).

Extra command-line arguments pass straight through, so
``DeveloperOS.exe --port 8770 --no-browser`` works like ``devos app --port 8770 --no-browser``.
"""
import sys

from devos.cli import main

if __name__ == "__main__":
    sys.exit(main(["app"] + sys.argv[1:]))
