"""Slice 10 — design-system / accessibility contract tests (TDD, stdlib unittest).

The dashboard is a no-build React+htm app, so there is no DOM runtime available
to a stdlib test suite. These tests pin the *source-level* design-token and
accessibility contract (D-0027) so regressions fail fast; runtime behavior is
covered by the live socket smoke and a manual keyboard pass per slice.
"""
from __future__ import annotations

import json
import re
import struct
import unittest
from pathlib import Path

from devos.api.app import STATIC_DIR

CSS = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")
JS = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")


class TestDesignTokens(unittest.TestCase):
    def test_spacing_radius_and_motion_tokens_defined(self) -> None:
        for token in ("--space-2", "--space-4", "--radius-m", "--dur-fast", "--focus-ring"):
            self.assertIn(token, CSS, f"styles.css must define the {token} token")

    def test_semantic_color_tokens_defined(self) -> None:
        for token in ("--danger", "--success"):
            self.assertIn(token, CSS, f"styles.css must define the {token} token")

    def test_reduced_motion_respected(self) -> None:
        self.assertIn("prefers-reduced-motion", CSS)

    def test_focus_visible_styles_present(self) -> None:
        self.assertIn(":focus-visible", CSS)

    def test_no_text_below_12px(self) -> None:
        sizes = [int(m) for m in re.findall(r"font(?:-size)?:\s*(\d+)px", CSS)]
        self.assertTrue(sizes, "expected font sizes in styles.css")
        self.assertGreaterEqual(min(sizes), 12, f"text below 12px found: {sorted(set(sizes))}")


class TestA11yContract(unittest.TestCase):
    def test_error_messages_use_alert_role(self) -> None:
        match = re.search(r"function Msg\([\s\S]{0,400}?\"alert\"", JS)
        self.assertIsNotNone(match, "Msg must emit role=alert for errors")

    def test_tabs_follow_wai_aria_pattern(self) -> None:
        for marker in ('role="tablist"', 'role="tab"', 'role="tabpanel"',
                       "aria-controls", "onKeyDown"):
            self.assertIn(marker, JS, f"tabs must implement {marker}")

    def test_skip_link_present(self) -> None:
        self.assertIn("skip-link", JS)
        self.assertIn(".skip-link", CSS)

    def test_loading_primitive_announces_politely(self) -> None:
        match = re.search(r"function Loading\([\s\S]{0,300}?role=\"status\"", JS)
        self.assertIsNotNone(match, "shared Loading primitive with role=status required")

    def test_index_html_basics(self) -> None:
        self.assertIn('lang="en"', HTML)
        self.assertIn('name="viewport"', HTML)

    def test_no_string_style_props(self) -> None:
        # React requires the style prop to be an object; a string style throws at
        # render time and unmounts the whole SPA (this crashed the Meeting tab —
        # found by the screenshot automation). Use CSS classes instead.
        self.assertNotIn('style="', JS, "string style prop crashes React at render")

    def test_readme_screenshots_exist(self) -> None:
        # Every screenshot the README references must be committed (D-0034) —
        # the gallery is real captures, never broken links or fabrications.
        root = STATIC_DIR.parents[2]
        readme = (root / "README.md").read_text(encoding="utf-8")
        # Refs may live in subfolders (github/portfolio/store), so allow "/".
        refs = re.findall(r"docs/screenshots/([\w./-]+\.png)", readme)
        self.assertTrue(refs, "README should reference the screenshot gallery")
        for name in refs:
            self.assertTrue((root / "docs" / "screenshots" / Path(name)).is_file(),
                            f"README references missing screenshot {name}")


class TestOnboardingContract(unittest.TestCase):
    """Slice 11 (D-0028): welcome + live get-started checklist on Home."""

    def test_welcome_guide_component_exists(self) -> None:
        self.assertIn("function WelcomeGuide(", JS)

    def test_state_persisted_in_local_storage(self) -> None:
        self.assertIn("devos.onboarding", JS)

    def test_plain_language_and_privacy_up_front(self) -> None:
        self.assertIn("Get started", JS)
        self.assertIn("stays on your computer", JS)

    def test_checklist_markup_present(self) -> None:
        self.assertIn('class="checklist"', JS)

    def test_welcome_region_labelled(self) -> None:
        match = re.search(r"aria-labelledby=\"welcome-h\"[\s\S]{0,300}?id=\"welcome-h\"", JS)
        self.assertIsNotNone(match, "welcome section must be labelled by its heading")

    def test_welcome_styles_defined(self) -> None:
        self.assertIn(".welcome", CSS)
        self.assertIn(".checklist", CSS)


def _png_size(path) -> tuple[int, int]:
    """Width/height from a PNG's IHDR (validates the signature too)."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path.name} is not a PNG")
    return struct.unpack(">II", data[16:24])


class TestPwaContract(unittest.TestCase):
    """Slice 12 (D-0029): PWA foundation — manifest + icon system + installability."""

    def setUp(self) -> None:
        self.manifest_path = STATIC_DIR / "manifest.webmanifest"

    def test_manifest_exists_with_install_criteria(self) -> None:
        self.assertTrue(self.manifest_path.is_file(), "manifest.webmanifest required")
        m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(m["name"], "DeveloperOS")
        self.assertEqual(m["short_name"], "DevOS")
        self.assertEqual(m["start_url"], "/")
        self.assertEqual(m["scope"], "/")
        self.assertEqual(m["display"], "standalone")
        self.assertEqual(m["theme_color"], "#0f1117")
        self.assertEqual(m["background_color"], "#0f1117")

    def test_manifest_icons_cover_192_and_512_plus_maskable(self) -> None:
        m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        sizes = {i["sizes"] for i in m["icons"]}
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)
        self.assertTrue(any(i.get("purpose") == "maskable" for i in m["icons"]),
                        "a maskable icon is required for good Android/desktop masking")

    def test_icon_files_are_real_pngs_with_declared_sizes(self) -> None:
        m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for icon in m["icons"]:
            rel = icon["src"].replace("/static/", "", 1)
            path = STATIC_DIR / rel
            self.assertTrue(path.is_file(), f"{icon['src']} missing")
            w, h = _png_size(path)
            self.assertEqual(f"{w}x{h}", icon["sizes"], f"{path.name} size mismatch")

    def test_index_html_wires_pwa_head_links(self) -> None:
        self.assertIn('rel="manifest"', HTML)
        self.assertIn('name="theme-color"', HTML)
        self.assertIn("favicon.svg", HTML)
        self.assertIn('rel="apple-touch-icon"', HTML)

    def test_content_types_cover_pwa_assets(self) -> None:
        from devos.api.app import _CONTENT_TYPES
        self.assertEqual(_CONTENT_TYPES.get(".png"), "image/png")
        self.assertEqual(_CONTENT_TYPES.get(".webmanifest"),
                         "application/manifest+json")

    def test_favicon_svg_exists(self) -> None:
        self.assertTrue((STATIC_DIR / "icons" / "favicon.svg").is_file())


if __name__ == "__main__":
    unittest.main()
