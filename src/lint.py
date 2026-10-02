"""Basic Gherkin lint: catch structural problems in generated files."""

import re


def lint_gherkin(text: str) -> list[str]:
    """Return a list of issues found in a Gherkin feature file."""
    issues: list[str] = []
    lines = text.splitlines()

    if not any(ln.startswith("Feature:") for ln in lines):
        issues.append("Missing 'Feature:' line")

    current: str | None = None
    seen = {"Given": False, "When": False, "Then": False}
    section: str | None = None
    scenario_names: list[str] = []

    def close_scenario():
        if current is None:
            return
        for kw in ("Given", "When", "Then"):
            if not seen[kw]:
                issues.append(f"Scenario '{current}' is missing a {kw} step")

    for ln in lines:
        s = ln.strip()
        m = re.match(r"^(Scenario(?: Outline)?):\s*(.*)$", s)
        if m:
            close_scenario()
            current = m.group(2).strip() or "<unnamed>"
            scenario_names.append(current)
            seen = {"Given": False, "When": False, "Then": False}
            section = None
            if not m.group(2).strip():
                issues.append("Found a scenario with an empty name")
            continue
        km = re.match(r"^(Given|When|Then|And|But)\b(.*)$", s)
        if km and current is not None:
            kw, rest = km.group(1), km.group(2).strip()
            if kw in ("Given", "When", "Then"):
                section = kw
                seen[kw] = True
            elif section is None:
                issues.append(f"Scenario '{current}': '{kw}' step with no preceding Given/When/Then")
            if not rest:
                issues.append(f"Scenario '{current}': empty '{kw}' step")
    close_scenario()

    dupes = {n for n in scenario_names if scenario_names.count(n) > 1}
    for d in sorted(dupes):
        issues.append(f"Duplicate scenario name: '{d}'")

    if not scenario_names:
        issues.append("No scenarios found")
    return issues
