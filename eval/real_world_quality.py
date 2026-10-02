"""Real-world evaluation: score live GitHub feature requests.

Fetches open feature requests from any public repo (no auth needed) and runs
the requirement quality scorer over them. Reproduces the numbers in the README.

Usage:
    python eval/real_world_quality.py microsoft/vscode feature-request 30
"""

import json
import re
import sys
import urllib.request

sys.path.insert(0, ".")
from src.quality import analyze_quality


def fetch_issues(repo, label, n):
    url = (f"https://api.github.com/repos/{repo}/issues"
           f"?state=open&labels={label}&per_page={n}")
    req = urllib.request.Request(url, headers={"User-Agent": "ai-gherkin-generator-eval"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return [i for i in data if not i.get("pull_request")]


def issue_to_parsed(issue):
    body = issue.get("body") or ""
    criteria = [b.strip("-* ").strip() for b in body.split("\n")
                if re.match(r"^\s*[-*]\s+\S", b)][:8]
    return {"title": issue["title"][:60], "role": "user",
            "goal": issue["title"], "benefit": "", "criteria": criteria}


def main(repo="microsoft/vscode", label="feature-request", n=30):
    issues = fetch_issues(repo, label, n)
    scores, grades, vague_n, no_crit = [], {}, 0, 0
    for issue in issues:
        q = analyze_quality(issue_to_parsed(issue))
        scores.append(q["score"])
        grades[q["grade"]] = grades.get(q["grade"], 0) + 1
        codes = {f["code"] for f in q["findings"]}
        vague_n += "vague_language" in codes
        no_crit += "no_criteria" in codes
    print(f"n={len(scores)} open '{label}' issues from {repo}")
    print(f"avg quality score: {sum(scores) / len(scores):.0f}/100")
    print(f"grade distribution: {dict(sorted(grades.items()))}")
    print(f"with vague/untestable language: {vague_n}/{len(scores)}")
    print(f"with no testable criteria: {no_crit}/{len(scores)}")


if __name__ == "__main__":
    main(*sys.argv[1:]) if len(sys.argv) > 1 else main()
