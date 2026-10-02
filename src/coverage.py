"""Coverage analysis: how well do the scenarios cover the requirement?"""

import re

from .rule_engine import Feature

_NEGATIVE_RE = re.compile(r"invalid|unauthorized|denied|not.?found|rejected|error|expired|locked", re.I)


def analyze(feature: Feature) -> dict:
    """Compute coverage stats for a generated Feature."""
    scenarios = feature.scenarios
    outlines = [s for s in scenarios if s.examples]
    negatives = [s for s in scenarios if _NEGATIVE_RE.search(s.name)]
    positives = [s for s in scenarios if s not in negatives]

    ac_scenarios = [s for s in scenarios if s.name.startswith("AC")]
    warnings: list[str] = []
    if not negatives:
        warnings.append("No negative scenarios — add validation/error criteria for stronger coverage.")
    if not outlines:
        warnings.append("No Scenario Outlines — enumerate values like (admin, user, guest) to get data-driven cases.")
    if len(ac_scenarios) < len(feature.scenarios) and not ac_scenarios:
        warnings.append("No acceptance-criteria scenarios found.")

    return {
        "feature": feature.title,
        "total_scenarios": len(scenarios),
        "positive": len(positives),
        "negative": len(negatives),
        "outlines": len(outlines),
        "ac_scenarios": len(ac_scenarios),
        "warnings": warnings,
    }


def render_report(analysis: dict) -> str:
    """Render a human-readable coverage report."""
    lines = [
        f"Coverage report: {analysis['feature']}",
        f"  Scenarios : {analysis['total_scenarios']} "
        f"({analysis['positive']} positive, {analysis['negative']} negative, "
        f"{analysis['outlines']} outlines)",
        f"  AC-mapped : {analysis['ac_scenarios']}",
    ]
    if analysis["warnings"]:
        lines.append("  Warnings  :")
        lines += [f"    - {w}" for w in analysis["warnings"]]
    else:
        lines.append("  Warnings  : none — solid coverage")
    return "\n".join(lines)
