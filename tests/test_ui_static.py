"""Slice 10 — design-system / accessibility contract tests (TDD, stdlib unittest).

The dashboard is a no-build React+htm app, so there is no DOM runtime available
to a stdlib test suite. These tests pin the *source-level* design-token and
accessibility contract (D-0027) so regressions fail fast; runtime behavior is
covered by the live socket smoke and a manual keyboard pass per slice.
"""
from __future__ import annotations

import re
import unittest

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


if __name__ == "__main__":
    unittest.main()
