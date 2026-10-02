"""Tests for the offline rule-based Gherkin generator."""

import unittest

from src.rule_engine import generate_from_text, parse_story

STORY = """# Password reset

As a registered user, I want to reset my password,
so that I can regain access to my account.

Acceptance Criteria:
- When the user submits a registered email, then a reset link is emailed
- An error is shown for unregistered email addresses
- Reset links expire after 60 minutes
"""


class TestParseStory(unittest.TestCase):
    def test_parses_role_goal_benefit(self):
        parsed = parse_story(STORY)
        self.assertEqual(parsed["title"], "Password reset")
        self.assertEqual(parsed["role"], "registered user")
        self.assertIn("reset my password", parsed["goal"])
        self.assertIn("regain access", parsed["benefit"])

    def test_parses_criteria(self):
        parsed = parse_story(STORY)
        self.assertEqual(len(parsed["criteria"]), 3)
        self.assertTrue(parsed["criteria"][0].startswith("When the user submits"))


class TestGenerate(unittest.TestCase):
    def test_feature_structure(self):
        out = generate_from_text(STORY)
        self.assertIn("Feature: Password reset", out)
        self.assertIn("Background:", out)
        self.assertIn("Scenario: AC1", out)
        self.assertIn("Scenario: AC2", out)
        self.assertIn("Scenario: AC3", out)

    def test_when_then_split(self):
        out = generate_from_text(STORY)
        self.assertIn("When the user submits a registered email", out)
        self.assertIn("Then a reset link is emailed", out)

    def test_negative_scenarios_added(self):
        out = generate_from_text(STORY)
        self.assertIn("Scenario: Validation - invalid input is rejected", out)

    def test_no_criteria_still_generates(self):
        out = generate_from_text("# Simple\nAs a user, I want to log out.")
        self.assertIn("Feature: Simple", out)
        self.assertIn("Scenario:", out)


if __name__ == "__main__":
    unittest.main()
