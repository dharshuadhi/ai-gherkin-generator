"""Near-duplicate scenario detection with TF-IDF + cosine similarity.

Catches the copy-paste scenarios that bloat a suite — e.g. two criteria
that generate almost-identical steps — before they become maintenance debt.
No external dependencies; pure Python.
"""

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z]{2,}")
STOPWORDS = frozenset("""
a an the and or of to in on for with is are was were be been being by at as it its
this that these those then than when where which who whom whose what how all any
each every both either neither not no nor so such into out up down over under
""".split())


def _tokens(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _scenario_text(scenario) -> str:
    parts = [scenario.name] + [text for _kw, text in scenario.steps]
    return " ".join(parts)


def find_duplicates(scenarios, threshold=0.75) -> list:
    """Return [(i, j, similarity)] for scenario pairs above threshold."""
    docs = [_tokens(_scenario_text(s)) for s in scenarios]
    if len(docs) < 2:
        return []
    # document frequency
    df = Counter()
    for tokens in docs:
        df.update(set(tokens))
    n = len(docs)
    idf = {t: math.log(n / (1 + df[t])) for t in df}
    # tf-idf vectors
    vectors = []
    for tokens in docs:
        tf = Counter(tokens)
        vectors.append({t: (1 + math.log(c)) * idf[t] for t, c in tf.items()})
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = _cosine(vectors[i], vectors[j])
            if sim >= threshold:
                pairs.append((i, j, round(sim, 3)))
    return sorted(pairs, key=lambda p: -p[2])


def _cosine(a, b) -> float:
    dot = sum(a[t] * b[t] for t in a if t in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def render_dedup_report(scenarios, pairs) -> str:
    if not pairs:
        return f"Dedup: {len(scenarios)} scenarios, no near-duplicates found."
    lines = [f"Dedup: {len(pairs)} near-duplicate pair(s) above threshold:"]
    for i, j, sim in pairs:
        lines.append(f"  - {sim:.0%} similar: '{scenarios[i].name}' <-> '{scenarios[j].name}'")
        lines.append("    Consider merging these into one Scenario Outline.")
    return "\n".join(lines)
