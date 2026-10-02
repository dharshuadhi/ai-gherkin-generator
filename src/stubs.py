"""Generate runnable test stubs from a Feature model.

Turns generated Gherkin into pytest-bdd step-definition skeletons so the
feature file becomes an executable suite with one command — the step every
SDET does by hand, automated.
"""

import re

HEADER = '''"""Step definitions generated from {feature_file}.

Run:  pytest --gherkin-terminal-reporter
Fill in each step body, then delete the NotImplementedError.
"""
import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("{feature_file}")
'''


def _func_name(text):
    name = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (name[:60] or "step").rstrip("_")


def _is_param(text):
    return "<" in text and ">" in text


def _parser_expr(text):
    """Return a valid Python expression matching the step text.

    Plain steps become string literals (via repr, so quotes are safe);
    steps with <placeholders> become named-group regex parsers.
    """
    if not _is_param(text):
        return repr(text)
    parts = re.split(r"(<[^>]+>)", text)
    out = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            out.append(f"(?P<{part[1:-1]}>.+)")
        else:
            out.append(re.escape(part))
    pattern = "".join(out).replace('"', '\\"')
    return f'parsers.re(r"{pattern}")'


def generate_stubs(feature, feature_file="generated.feature") -> str:
    """Return a pytest-bdd step-definition module for the feature."""
    seen = set()
    chunks = [HEADER.format(feature_file=feature_file)]
    # background steps first
    ordered = [("Background", kw, text) for kw, text in feature.background]
    for sc in feature.scenarios:
        for kw, text in sc.steps:
            ordered.append((sc.name, kw, text))
    for origin, kw, text in ordered:
        key = (kw.lower(), text)
        if key in seen:
            continue
        seen.add(key)
        deco = {"given": "given", "when": "when", "then": "then"}.get(kw.lower(), "then")
        fname = _func_name(f"{deco}_{text}")
        params = ""
        body_params = ""
        if _is_param(text):
            names = re.findall(r"<([^>]+)>", text)
            params = ", " + ", ".join(names)
            body_params = f"  # params: {', '.join(names)}\n"
        chunks.append(
            f"@{deco}({_parser_expr(text)})\n"
            f"def {fname}(){params}:\n"
            f'    """From: {origin}."""\n'
            f"{body_params}"
            f"    raise NotImplementedError\n\n"
        )
    stats = (f"# {len(feature.scenarios)} scenarios, "
             f"{len(seen)} unique steps generated from '{feature.title}'\n")
    return stats + "\n" + "".join(chunks)
