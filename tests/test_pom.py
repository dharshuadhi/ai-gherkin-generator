"""Tests for the Page Object Model generator."""

import os
import tempfile
import unittest

from src.actions import DEMO_TARGET, compile_feature
from src.pom import _used_pages, render_page_object, write_pom_suite
from src.rule_engine import build_feature, parse_story

STORY = open("examples/login_story.md").read()


class TestPOM(unittest.TestCase):
    def setUp(self):
        feature = build_feature(parse_story(STORY))
        self.compiled = compile_feature(feature, DEMO_TARGET)
        self.used = _used_pages(self.compiled, DEMO_TARGET)

    def test_detects_login_and_dashboard_pages(self):
        self.assertIn("LoginPage", self.used)
        self.assertIn("DashboardPage", self.used)

    def test_login_page_has_login_method(self):
        self.assertIn("login", self.used["LoginPage"]["methods"])

    def test_page_object_uses_xpath_constants(self):
        code = render_page_object(
            "LoginPage", DEMO_TARGET["page_objects"]["LoginPage"],
            {"open", "login", "is_error_visible"}, DEMO_TARGET)
        compile(code, "login_page.py", "exec")  # valid Python
        self.assertIn('EMAIL_INPUT = "//input[@id=\'email\']"', code)
        self.assertIn("def login(self, email: str, password: str):", code)
        self.assertIn("def is_error_visible(self):", code)
        self.assertNotIn("#email", code.split('"""', 2)[-1].replace("URL_PATH", ""))

    def test_suite_writes_runnable_files(self):
        with tempfile.TemporaryDirectory() as d:
            written = write_pom_suite(self.compiled, DEMO_TARGET, "User login", d)
            self.assertTrue(any(p.endswith("login_page.py") for p in written))
            self.assertTrue(any(p.endswith("conftest.py") for p in written))
            for path in written:
                if path.endswith(".py") and "__init__" not in path:
                    compile(open(path).read(), path, "exec")

    def test_no_css_selectors_leak_into_page_objects(self):
        with tempfile.TemporaryDirectory() as d:
            written = write_pom_suite(self.compiled, DEMO_TARGET, "User login", d)
            for path in written:
                if "/pages/" in path and path.endswith(".py"):
                    code = open(path).read()
                    self.assertNotIn('"#email"', code)
                    self.assertNotIn('"#login-btn"', code)


if __name__ == "__main__":
    unittest.main()
