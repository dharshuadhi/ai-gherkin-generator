"""Tests for outlines, formats, coverage and lint."""

import json
import unittest

from src.coverage import analyze
from src.formats import render_json, render_markdown
from src.lint import lint_gherkin
from src.rule_engine import build_feature, parse_story, render_gherkin

STORY = """# Discounts

As a shopper, I want discount codes to apply,
so that I pay less at checkout.

Acceptance Criteria:
- Discount applies for (gold, silver, bronze) members
- An error is shown for expired codes
"""


class TestOutlines(unittest.TestCase):
    def test_enumeration_becomes_outline(self):
        feature = build_feature(parse_story(STORY))
        outlines = [s for s in feature.scenarios if s.examples]
        self.assertEqual(len(outlines), 1)
        self.assertEqual(outlines[0].examples["rows"], [["gold"], ["silver"], ["bronze"]])

    def test_outline_renders_examples_table(self):
        out = render_gherkin(build_feature(parse_story(STORY)))
        self.assertIn("Scenario Outline:", out)
        self.assertIn("Examples:", out)
        self.assertIn("| gold |", out)
        self.assertIn("<value>", out)


class TestFormats(unittest.TestCase):
    def test_json_is_valid(self):
        data = json.loads(render_json(build_feature(parse_story(STORY))))
        self.assertEqual(data["feature"], "Discounts")
        self.assertTrue(any(s["type"] == "outline" for s in data["scenarios"]))
        self.assertIn("steps", data["scenarios"][0])

    def test_markdown_structure(self):
        md = render_markdown(build_feature(parse_story(STORY)))
        self.assertIn("# Test Plan: Discounts", md)
        self.assertIn("## Scenarios", md)


class TestCoverage(unittest.TestCase):
    def test_counts(self):
        analysis = analyze(build_feature(parse_story(STORY)))
        self.assertEqual(analysis["outlines"], 1)
        self.assertGreaterEqual(analysis["negative"], 1)
        self.assertEqual(analysis["total_scenarios"],
                         analysis["positive"] + analysis["negative"])


class TestLint(unittest.TestCase):
    def test_clean_feature(self):
        out = render_gherkin(build_feature(parse_story(STORY)))
        self.assertEqual(lint_gherkin(out), [])

    def test_catches_missing_parts(self):
        issues = lint_gherkin("Feature: X\n\n  Scenario: broken\n    When nothing\n")
        self.assertTrue(any("Given" in i for i in issues))
        self.assertTrue(any("Then" in i for i in issues))

    def test_catches_no_feature(self):
        self.assertTrue(any("Feature" in i for i in lint_gherkin("hello")))


if __name__ == "__main__":
    unittest.main()
