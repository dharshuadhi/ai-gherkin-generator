"""Tests for quality analysis, dedup detection and stub generation."""

import unittest

from src.quality import analyze_quality
from src.rule_engine import build_feature, parse_story
from src.similarity import find_duplicates
from src.stubs import generate_stubs

VAGUE_STORY = """# Thing

I want the thing to work.

Acceptance Criteria:
- The page should load fast and be user-friendly, etc.
"""

GOOD_STORY = """# Password reset

As a registered user, I want to reset my password,
so that I can regain access to my account.

Acceptance Criteria:
- When the user submits a registered email, then a reset link is emailed within 60 seconds
- When the user submits an unregistered email, then an error is displayed
- Reset links expire after 60 minutes
"""


class TestQuality(unittest.TestCase):
    def test_vague_story_scores_low(self):
        q = analyze_quality(parse_story(VAGUE_STORY))
        self.assertLess(q["score"], 60)
        codes = {f["code"] for f in q["findings"]}
        self.assertIn("vague_language", codes)

    def test_good_story_scores_high(self):
        q = analyze_quality(parse_story(GOOD_STORY))
        self.assertGreaterEqual(q["score"], 75)
        self.assertEqual(q["grade"], "A")

    def test_findings_have_suggestions(self):
        q = analyze_quality(parse_story(VAGUE_STORY))
        self.assertTrue(all(f["suggestion"] for f in q["findings"]))


class TestSimilarity(unittest.TestCase):
    def test_detects_near_duplicates(self):
        feature = build_feature(parse_story(GOOD_STORY))
        # clone a scenario with nearly identical wording
        feature.scenarios.append(feature.scenarios[0])
        pairs = find_duplicates(feature.scenarios)
        self.assertTrue(pairs)
        self.assertGreaterEqual(pairs[0][2], 0.9)

    def test_no_false_positives(self):
        feature = build_feature(parse_story(GOOD_STORY))
        pairs = find_duplicates(feature.scenarios, threshold=0.95)
        # distinct criteria should not be near-identical
        self.assertEqual(pairs, [])


class TestStubs(unittest.TestCase):
    def test_generates_runnable_skeleton(self):
        feature = build_feature(parse_story(GOOD_STORY))
        code = generate_stubs(feature, "reset.feature")
        self.assertIn('scenarios("reset.feature")', code)
        self.assertIn("@given", code)
        self.assertIn("@when", code)
        self.assertIn("@then", code)
        self.assertIn("raise NotImplementedError", code)
        compile(code, "stubs.py", "exec")  # must be valid Python

    def test_dedupes_shared_steps(self):
        feature = build_feature(parse_story(GOOD_STORY))
        code = generate_stubs(feature)
        # background Given step appears once despite many scenarios
        self.assertEqual(code.count('a "registered user" is using the system'), 1)


if __name__ == "__main__":
    unittest.main()
