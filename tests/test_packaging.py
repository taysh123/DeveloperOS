"""Desktop ladder step C — packaging foundation tests (TDD, stdlib unittest).

Pins the D-0031 packaging contract: a committed multi-size Windows icon, a
PyInstaller spec that bundles every runtime data file (static dashboard assets
+ storage/schema.sql), and an entry script that routes into `devos app`.
The actual exe build is a dev-time step (packaging/README.md), not a test.
"""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

PACKAGING = Path(__file__).resolve().parents[1] / "packaging"

PNG_SIG = b"\x89PNG\r\n\x1a\n"


class TestIcoFile(unittest.TestCase):
    def setUp(self) -> None:
        self.path = PACKAGING / "devos.ico"

    def test_ico_exists(self) -> None:
        self.assertTrue(self.path.is_file(), "packaging/devos.ico required")

    def test_ico_structure_and_sizes(self) -> None:
        data = self.path.read_bytes()
        reserved, ico_type, count = struct.unpack("<HHH", data[:6])
        self.assertEqual(reserved, 0)
        self.assertEqual(ico_type, 1, "type 1 = icon")
        self.assertGreaterEqual(count, 4)
        sizes = set()
        for i in range(count):
            entry = data[6 + i * 16: 6 + (i + 1) * 16]
            width, height = entry[0], entry[1]
            size, offset = struct.unpack("<II", entry[8:16])
            sizes.add(256 if width == 0 else width)
            self.assertEqual(width, height, "square icons only")
            self.assertEqual(data[offset:offset + 8], PNG_SIG,
                             "entries must be PNG-format images (Vista+ ICO)")
            self.assertLessEqual(offset + size, len(data))
        self.assertTrue({16, 32, 48, 256}.issubset(sizes), f"sizes found: {sizes}")


class TestSpecAndEntry(unittest.TestCase):
    def test_spec_bundles_runtime_data(self) -> None:
        spec = (PACKAGING / "devos.spec").read_text(encoding="utf-8")
        self.assertIn("devos/api/static", spec, "dashboard assets must be bundled")
        self.assertIn("schema.sql", spec, "storage schema must be bundled")
        self.assertIn("devos.ico", spec)
        self.assertIn('name="DeveloperOS"', spec.replace("'", '"'))

    def test_entry_script_routes_into_devos_app(self) -> None:
        entry = (PACKAGING / "launch_devos.py").read_text(encoding="utf-8")
        self.assertIn('"app"', entry, "the exe wraps `devos app` (D-0030 launcher)")
        self.assertIn("devos.cli", entry)


if __name__ == "__main__":
    unittest.main()
