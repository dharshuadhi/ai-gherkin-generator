"""Additional output formats: JSON test catalog and Markdown test plan."""

import json

from .rule_engine import Feature


def render_json(feature: Feature) -> str:
    """Render a Feature as a structured JSON test catalog."""
    data = {
        "feature": feature.title,
        "story": feature.story_lines,
        "background": [{"keyword": kw, "text": text} for kw, text in feature.background],
        "scenarios": [
            {
                "name": s.name,
                "type": "outline" if s.examples else "scenario",
                "steps": [{"keyword": kw, "text": text} for kw, text in s.steps],
                **({"examples": s.examples} if s.examples else {}),
            }
            for s in feature.scenarios
        ],
    }
    return json.dumps(data, indent=2) + "\n"


def render_markdown(feature: Feature) -> str:
    """Render a Feature as a human-readable Markdown test plan."""
    lines = [f"# Test Plan: {feature.title}", ""]
    if feature.story_lines:
        lines += ["## User Story", ""]
        lines += [f"> {s}" for s in feature.story_lines]
        lines.append("")
    lines += ["## Background", ""]
    lines += [f"- **{kw}** {text}" for kw, text in feature.background]
    lines += ["", "## Scenarios", ""]
    for i, s in enumerate(feature.scenarios, 1):
        kind = "Scenario Outline" if s.examples else "Scenario"
        lines.append(f"### {i}. {kind}: {s.name}")
        lines.append("")
        for kw, text in s.steps:
            lines.append(f"- **{kw}** {text}")
        if s.examples:
            lines.append("")
            headers = s.examples["headers"]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            for row in s.examples["rows"]:
                lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
