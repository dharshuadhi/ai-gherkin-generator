"""CLI: generate Gherkin feature files from requirements.

Usage:
    python -m src.cli -i examples/login_story.md -o login.feature
    python -m src.cli -i story.md --engine ai --format json -o out.json
    python -m src.cli -i stories/ -o features/            # batch mode
    cat story.md | python -m src.cli --engine rule --report --lint
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_engine import generate_with_ai  # noqa: E402
from src.coverage import analyze, render_report  # noqa: E402
from src.formats import render_json, render_markdown  # noqa: E402
from src.lint import lint_gherkin  # noqa: E402
from src.quality import analyze_quality  # noqa: E402
from src.rule_engine import build_feature, generate_from_text, parse_story, render_gherkin  # noqa: E402
from src.similarity import find_duplicates, render_dedup_report  # noqa: E402
from src.stubs import generate_stubs  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be exported manually

FORMATTERS = {
    "gherkin": render_gherkin,
    "json": render_json,
    "markdown": render_markdown,
}
EXT = {"gherkin": ".feature", "json": ".json", "markdown": ".md"}


def _read_input(path: str | None) -> str:
    if path:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    if sys.stdin.isatty():
        raise SystemExit("No input: pass -i <file> or pipe requirement text via stdin.")
    return sys.stdin.read()


def _ai_configured() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"))


def _generate(story: str, engine: str, fmt: str) -> tuple[str, object | None]:
    """Generate output; returns (text, feature model or None for AI engine)."""
    if engine == "ai":
        return generate_with_ai(story), None
    feature = build_feature(parse_story(story))
    return FORMATTERS[fmt](feature), feature


def _post_process(text: str, feature: object | None, args, story: str = "") -> None:
    if args.quality and feature is not None:
        q = analyze_quality(parse_story(story))
        print(f"Quality: {q['summary']}", file=sys.stderr)
        for f in q["findings"]:
            print(f"  [{f['severity']}] {f['message']}", file=sys.stderr)
            print(f"    -> {f['suggestion']}", file=sys.stderr)
    if args.dedup and feature is not None:
        pairs = find_duplicates(feature.scenarios)
        print(render_dedup_report(feature.scenarios, pairs), file=sys.stderr)
    if args.stubs and feature is not None:
        path = args.stubs if isinstance(args.stubs, str) else "test_stubs.py"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(generate_stubs(feature, (args.output or "generated.feature")))
        print(f"Wrote {path} [pytest-bdd stubs]", file=sys.stderr)
    if (args.execute or args.codegen or args.pom) and feature is not None:
        from src.actions import DEMO_TARGET, compile_feature
        from src.codegen import generate_playwright
        target = DEMO_TARGET  # --target demo is the bundled login app
        compiled = compile_feature(feature, target)
        runnable = sum(1 for c in compiled if not c.skipped)
        print(f"Compiled {runnable}/{len(compiled)} scenarios to browser actions "
              f"[{target['name']}]", file=sys.stderr)
        if args.codegen:
            with open(args.codegen, "w", encoding="utf-8") as fh:
                fh.write(generate_playwright(compiled, target, feature.title))
            print(f"Wrote {args.codegen} [runnable Playwright module]", file=sys.stderr)
        if args.pom:
            from src.pom import write_pom_suite
            written = write_pom_suite(compiled, target, feature.title, args.pom)
            print(f"Wrote {len(written)} files -> {args.pom}/ [Page Object suite]", file=sys.stderr)
            for w in written:
                print(f"  {w}", file=sys.stderr)
        if args.execute:
            from src.runner import render_run_report, run_compiled
            try:
                reports = run_compiled(compiled, target)
            except Exception as exc:  # noqa: BLE001 - e.g. target app not running
                print(f"Execution failed: {exc}", file=sys.stderr)
                print(f"Start the demo app first: python demo-app/app.py", file=sys.stderr)
                return
            print(render_run_report(reports), file=sys.stderr)
    if args.lint:
        issues = lint_gherkin(text)
        print("Lint: " + ("clean ✓" if not issues else f"{len(issues)} issue(s)"), file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
    if args.report:
        if feature is None:
            print("Coverage report needs the rule engine.", file=sys.stderr)
        else:
            print(render_report(analyze(feature)), file=sys.stderr)


def _single(args, engine: str) -> None:
    story = _read_input(args.input)
    if not story.strip():
        raise SystemExit("Empty input.")
    text, feature = _generate(story, engine, args.format)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {args.output} [{engine} engine, {args.format}]")
    else:
        print(text, end="")
    _post_process(text, feature, args, story)


def _batch(args, engine: str) -> None:
    src_dir = args.input
    out_dir = args.output or "features"
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.endswith((".md", ".txt")))
    if not files:
        raise SystemExit(f"No .md/.txt files in {src_dir}")
    for fname in files:
        story = _read_input(os.path.join(src_dir, fname))
        if not story.strip():
            continue
        text, feature = _generate(story, engine, args.format)
        out_path = os.path.join(out_dir, os.path.splitext(fname)[0] + EXT[args.format])
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {out_path}")
        _post_process(text, feature, args, story)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gherkin feature files from requirements (AI or offline rule-based)."
    )
    parser.add_argument("-i", "--input", help="Requirement file, directory (batch), or stdin")
    parser.add_argument("-o", "--output", help="Output file or directory (batch)")
    parser.add_argument(
        "--engine",
        choices=["auto", "ai", "rule"],
        default="auto",
        help="auto: AI when Azure OpenAI is configured, else rule-based (default: auto)",
    )
    parser.add_argument(
        "--format",
        choices=["gherkin", "json", "markdown"],
        default="gherkin",
        help="Output format (default: gherkin)",
    )
    parser.add_argument("--report", action="store_true", help="Print a coverage report")
    parser.add_argument("--lint", action="store_true", help="Lint the generated output")
    parser.add_argument("--quality", action="store_true",
                        help="Score the requirement quality before generating")
    parser.add_argument("--dedup", action="store_true",
                        help="Detect near-duplicate scenarios (TF-IDF similarity)")
    parser.add_argument("--stubs", nargs="?", const="test_stubs.py", metavar="FILE",
                        help="Generate pytest-bdd step-definition stubs")
    parser.add_argument("--execute", action="store_true",
                        help="Compile to browser actions and run headless with Playwright")
    parser.add_argument("--codegen", metavar="FILE",
                        help="Write a standalone runnable Playwright test module")
    parser.add_argument("--pom", metavar="DIR",
                        help="Generate a Page Object Model suite (XPath locators + page classes) into DIR")
    parser.add_argument("--target", default="demo",
                        help="Execution target app config (default: demo login app)")
    args = parser.parse_args()

    engine = args.engine
    if engine == "auto":
        engine = "ai" if _ai_configured() else "rule"

    if args.input and os.path.isdir(args.input):
        _batch(args, engine)
    else:
        _single(args, engine)


if __name__ == "__main__":
    main()
