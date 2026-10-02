"""CLI: generate Gherkin feature files from requirements.

Usage:
    python -m src.cli -i examples/login_story.md -o login.feature
    python -m src.cli -i story.md --engine ai -o out.feature
    cat story.md | python -m src.cli --engine rule
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_engine import generate_with_ai  # noqa: E402
from src.rule_engine import generate_from_text  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be exported manually


def _read_input(path: str | None) -> str:
    if path:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    if sys.stdin.isatty():
        raise SystemExit("No input: pass -i <file> or pipe requirement text via stdin.")
    return sys.stdin.read()


def _ai_configured() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gherkin feature files from requirements (AI or offline rule-based)."
    )
    parser.add_argument("-i", "--input", help="Requirement text/markdown file (default: stdin)")
    parser.add_argument("-o", "--output", help="Write .feature to file (default: stdout)")
    parser.add_argument(
        "--engine",
        choices=["auto", "ai", "rule"],
        default="auto",
        help="auto: use AI when Azure OpenAI is configured, else rule-based (default: auto)",
    )
    args = parser.parse_args()

    story = _read_input(args.input)
    if not story.strip():
        raise SystemExit("Empty input.")

    engine = args.engine
    if engine == "auto":
        engine = "ai" if _ai_configured() else "rule"

    if engine == "ai":
        feature = generate_with_ai(story)
    else:
        feature = generate_from_text(story)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(feature)
        print(f"Wrote {args.output} [{engine} engine]")
    else:
        print(feature, end="")


if __name__ == "__main__":
    main()
