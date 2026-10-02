"""Tests for the action compiler and Playwright codegen."""

import unittest

from src.actions import DEMO_TARGET, compile_feature, compile_scenario
from src.codegen import generate_playwright
from src.rule_engine import build_feature, parse_story

STORY = open("examples/login_story.md").read()


class TestActions(unittest.TestCase):
    def setUp(self):
        self.feature = build_feature(parse_story(STORY))

    def test_compiles_happy_path(self):
        compiled = compile_feature(self.feature, DEMO_TARGET)
        runnable = [c for c in compiled if not c.skipped]
        self.assertGreaterEqual(len(runnable), 3)
        first = runnable[0]
        types = [a.type for a in first.actions]
        self.assertIn("goto", types)
        self.assertIn("fill", types)
        self.assertIn("click", types)
        self.assertTrue(any(t.startswith("expect") for t in types))

    def test_lockout_repeats_attempts(self):
        compiled = compile_feature(self.feature, DEMO_TARGET)
        lockout = next(c for c in compiled if "locked" in c.name)
        clicks = [a for a in lockout.actions if a.type == "click"]
        self.assertEqual(len(clicks), 3)

    def test_uncompilable_scenario_skipped_honestly(self):
        compiled = compile_feature(self.feature, DEMO_TARGET)
        skipped = [c for c in compiled if c.skipped]
        self.assertTrue(any("Sessions expire" in c.name for c in skipped))

    def test_outline_uses_first_example(self):
        feature = build_feature(parse_story(
            "# T\nAs a user, I want X.\n\nAcceptance Criteria:\n"
            "- When the user submits valid credentials for (admin, guest), then they are taken to the dashboard\n"))
        compiled = compile_feature(feature, DEMO_TARGET)
        self.assertFalse(compiled[0].skipped)


class TestCodegen(unittest.TestCase):
    def test_generates_valid_playwright_module(self):
        feature = build_feature(parse_story(STORY))
        compiled = compile_feature(feature, DEMO_TARGET)
        code = generate_playwright(compiled, DEMO_TARGET, feature.title)
        compile(code, "test_generated.py", "exec")  # must be valid Python
        self.assertIn("sync_playwright", code)
        self.assertIn('page.fill("#email"', code)
        self.assertIn("to_be_visible", code)


class TestRunner(unittest.TestCase):
    def test_live_execution_against_demo_app(self):
        import urllib.request
        try:
            urllib.request.urlopen("http://127.0.0.1:5050/", timeout=3)
        except Exception:
            self.skipTest("demo app not running (python demo-app/app.py)")
        try:
            from src.runner import render_run_report, run_compiled
        except ImportError:
            self.skipTest("playwright not installed")
        feature = build_feature(parse_story(STORY))
        compiled = compile_feature(feature, DEMO_TARGET)
        reports = run_compiled(compiled, DEMO_TARGET, screenshot_dir="/tmp/shots")
        ran = [r for r in reports if not r.skipped]
        self.assertTrue(ran)
        self.assertTrue(all(r.passed for r in ran),
                        render_run_report(reports))


if __name__ == "__main__":
    unittest.main()
