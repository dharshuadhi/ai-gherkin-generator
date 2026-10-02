"""Offline rule-based Gherkin generator (no API key needed).

Understands a simple, common requirement format:

    # Password reset
    As a registered user, I want to reset my password,
    so that I can regain access to my account.

    Acceptance Criteria:
    - When the user submits a valid email, then a reset link is sent
    - An error is shown for unregistered email addresses
    - Reset links expire after 60 minutes

Each acceptance criterion becomes a Scenario; "When ... then ..."
criteria are split into When/Then steps automatically. Negative
scenarios (validation, unauthorized access) are added heuristically.
"""

import re

_ROLE_RE = re.compile(
    r"as an?\s+([^,]+?),\s*i want\s+(.+?)(?:,?\s*so that\s+(.+))?\s*$",
    re.IGNORECASE,
)
_WHEN_THEN_RE = re.compile(r"^when\s+(.+?)[,;]?\s+then\s+(.+)$", re.IGNORECASE | re.DOTALL)
_BULLET_RE = re.compile(r"^[-*•\u2013\u2014]\s+(.*)$|^(\d+)[.)]\s+(.*)$")
_AC_HEADER_RE = re.compile(r"^#{0,3}\s*acceptance criteria\b", re.IGNORECASE)
_HEADER_RE = re.compile(r"^#{1,3}\s+\S")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().rstrip(".")


def _lower_first(text: str) -> str:
    text = text.strip()
    return text[:1].lower() + text[1:] if text else text


def parse_story(text: str) -> dict:
    """Parse a requirement into title, role, goal, benefit and criteria."""
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    title = lines[0].lstrip("# ").strip() if lines else "Generated Feature"

    # The user-story block: skip blanks after the title, then read until
    # the next blank line or the Acceptance Criteria header, so
    # "so that ..." never swallows the criteria section.
    story_lines: list[str] = []
    started = False
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if _AC_HEADER_RE.match(stripped):
            break
        started = True
        story_lines.append(stripped)
    story_text = " ".join(story_lines)

    role, goal, benefit = "user", "", ""
    m = _ROLE_RE.search(story_text)
    if m:
        role = _clean(m.group(1)) or role
        goal = _clean(m.group(2))
        benefit = _clean(m.group(3))

    criteria: list[str] = []
    in_ac = False
    for line in lines:
        stripped = line.strip()
        if _AC_HEADER_RE.match(stripped):
            in_ac = True
            continue
        if not in_ac:
            continue
        if _HEADER_RE.match(stripped):
            break
        bm = _BULLET_RE.match(stripped)
        if bm:
            criterion = next((g for g in bm.groups() if g), "").strip()
            if criterion:
                criteria.append(_clean(criterion))
        elif stripped == "" or stripped.startswith(">"):
            continue
        elif criteria:
            break  # non-bullet line ends the criteria section

    return {
        "title": _clean(title) or "Generated Feature",
        "role": role,
        "goal": goal,
        "benefit": benefit,
        "criteria": criteria,
    }


def _scenario_name(criterion: str) -> str:
    name = _clean(criterion)
    name = re.sub(r"^(when|then|and|given)\s+", "", name, flags=re.IGNORECASE)
    return name[:90]


def _steps_for(role: str, goal: str, criterion: str) -> tuple[str, str, str]:
    """Build (Given, When, Then) steps for one acceptance criterion."""
    given = f'a "{role}" is using the system'
    wt = _WHEN_THEN_RE.match(criterion.strip())
    if wt:
        when = _lower_first(_clean(wt.group(1)))
        then = _lower_first(_clean(wt.group(2)))
        return given, when, then
    # Outcome-style criterion ("An error is shown for ...")
    action = _lower_first(goal) or "performs the action"
    action = re.sub(r"^to\s+", "", action)
    action = re.sub(r"\bmy\b", "their", action)
    when = f"the {role} tries to {action}"
    then = _lower_first(_clean(criterion))
    return given, when, then


def _negative_scenarios(role: str, criteria: list[str]) -> list[str]:
    out: list[str] = []
    text = " ".join(criteria).lower()

    if any(k in text for k in ("valid", "invalid", "error", "required", "format", "empty")):
        out += [
            "  Scenario: Validation - invalid input is rejected",
            f'    Given a "{role}" is using the system',
            "    When the user submits invalid input",
            "    Then a clear validation error is displayed",
            "    And no data is saved",
            "",
        ]
    if any(k in text for k in ("login", "auth", "permission", "role", "access", "token")):
        out += [
            "  Scenario: Security - unauthorized access is denied",
            f'    Given a "{role}" is using the system',
            "    When the user attempts the action without valid credentials",
            "    Then access is denied",
            "    And a 401 or 403 response is returned",
            "",
        ]
    if any(k in text for k in ("not found", "missing", "deleted", "unknown")):
        out += [
            "  Scenario: Not found - missing resource is handled",
            f'    Given a "{role}" is using the system',
            "    When the user requests a resource that does not exist",
            "    Then a not-found message is displayed",
            "",
        ]
    return out


def generate(parsed: dict) -> str:
    """Render parsed requirement as a Gherkin feature file."""
    role = parsed.get("role") or "user"
    goal = parsed.get("goal") or ""
    benefit = parsed.get("benefit") or ""
    criteria = parsed.get("criteria") or []

    lines = [f"Feature: {parsed.get('title') or 'Generated Feature'}"]
    lines.append(f"  As a {role}")
    if goal:
        lines.append(f"  I want {goal}")
    if benefit:
        lines.append(f"  So that {benefit}")
    lines += ["", "  Background:", f'    Given a "{role}" is using the system', ""]

    if not criteria and goal:
        action = re.sub(r"^to\s+", "", _lower_first(goal))
        lines += [
            f"  Scenario: Happy path - {action}",
            f'    Given a "{role}" is using the system',
            f"    When the {role} tries to {action}",
            "    Then the expected outcome is achieved",
            "",
        ]

    for i, criterion in enumerate(criteria, 1):
        given, when, then = _steps_for(role, goal, criterion)
        lines += [
            f"  Scenario: AC{i} - {_scenario_name(criterion)}",
            f"    Given {given}",
            f"    When {when}",
            f"    Then {then}",
            "",
        ]

    lines += _negative_scenarios(role, criteria)
    return "\n".join(lines).rstrip() + "\n"


def generate_from_text(text: str) -> str:
    """Parse requirement text and return a Gherkin feature file."""
    return generate(parse_story(text))
