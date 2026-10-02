"""Requirement quality analysis: score a user story before generating tests.

Catches the problems that make generated tests weak — vague language,
missing actors, untestable criteria — and tells the author how to fix them.
"""

import re

# Words that cannot be tested and should carry numbers instead.
VAGUE_WORDS = [
    "fast", "quick", "quickly", "slow", "user-friendly", "user friendly",
    "intuitive", "easy", "easily", "simple", "robust", "efficient",
    "efficiently", "seamless", "seamlessly", "adequate", "appropriate",
    "relevant", "timely", "timely manner", "nice", "good", "great",
    "large", "small", "many", "several", "various", "etc", "asap",
    "performant", "scalable", "reliable", "securely-ish",
]

# Phrases that hide missing requirements.
WEASEL_PHRASES = [
    "etc.", "and so on", "as needed", "if necessary", "where appropriate",
    "tbd", "to be determined", "should work", "must work properly",
]

# Compound criteria that should be split into separate testable statements.
COMPOUND_RE = re.compile(r",.*\band\b.*\.", re.IGNORECASE)


def _find_hits(text, words):
    low = text.lower()
    return sorted({w for w in words if w.lower() in low})


def analyze_quality(parsed) -> dict:
    """Score a parsed story 0-100 and list actionable findings.

    `parsed` is the dict returned by rule_engine.parse_story.
    """
    findings = []
    score = 100

    def penalize(points, code, message, suggestion):
        nonlocal score
        score -= points
        findings.append({"code": code, "severity": "high" if points >= 15 else "medium",
                         "message": message, "suggestion": suggestion})

    # --- structural checks -------------------------------------------------
    if not parsed.get("role") or parsed["role"] == "user":
        penalize(10, "missing_actor",
                 "No explicit actor found; defaulted to a generic 'user'.",
                 "Start the story with 'As a <specific role>, ...' (e.g. 'As a checkout customer').")
    if not parsed.get("goal"):
        penalize(15, "missing_goal",
                 "No clear goal ('I want ...') found.",
                 "Add 'I want <capability>' so the intent is explicit.")
    if not parsed.get("benefit"):
        penalize(5, "missing_benefit",
                 "No 'So that ...' benefit statement.",
                 "Add the business value: 'So that <outcome>'.")
    criteria = parsed.get("criteria", [])
    if not criteria:
        penalize(20, "no_criteria",
                 "No acceptance criteria found — nothing concrete to generate tests from.",
                 "Add an 'Acceptance Criteria:' section with one bullet per expected behavior.")
    elif len(criteria) < 3:
        penalize(5, "few_criteria",
                 f"Only {len(criteria)} acceptance criterion/criteria — edge cases are likely uncovered.",
                 "Aim for 3+ criteria covering happy path, validation, and errors.")

    # --- language checks ---------------------------------------------------
    story_text = " ".join([parsed.get("role", ""), parsed.get("goal", ""),
                           parsed.get("benefit", "")] + criteria)
    vague = _find_hits(story_text, VAGUE_WORDS)
    if vague:
        penalize(min(20, 5 * len(vague)), "vague_language",
                 f"Untestable adjectives/adverbs: {', '.join(vague)}.",
                 "Replace each with a number ('within 2 seconds', 'at least 8 characters').")
    weasels = _find_hits(story_text, WEASEL_PHRASES)
    if weasels:
        penalize(10, "weasel_phrases",
                 f"Hand-wavy phrases: {', '.join(weasels)}.",
                 "Spell out the exact expected behavior instead.")
    compound = [c for c in criteria if COMPOUND_RE.search(c)]
    if compound:
        penalize(min(15, 5 * len(compound)), "compound_criteria",
                 f"{len(compound)} criteria bundle multiple behaviors into one sentence.",
                 "Split each into one testable statement per bullet.")

    # criteria without an observable outcome (no When/Then, no observable verb)
    observable = re.compile(r"\b(display|show|send|return|redirect|save|create|update|delete|email|expire|block|allow|deny)\w*\b", re.I)
    unobservable = [c for c in criteria
                    if not re.match(r"(?is)^when\s+.+then\s+", c) and not observable.search(c)]
    if unobservable:
        penalize(min(15, 5 * len(unobservable)), "unobservable_outcome",
                 f"{len(unobservable)} criteria describe no observable outcome.",
                 "Phrase as 'When <action>, then <observable result>'.")

    score = max(0, score)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    return {"score": score, "grade": grade, "findings": findings,
            "summary": f"{score}/100 (grade {grade}) — {len(findings)} findings"}
