"""Web UI for the AI Gherkin Generator.

Run:
    python app.py
then open http://127.0.0.1:5000

Paste a requirement, pick an engine and format, and get the
generated test artifacts in the browser — plus coverage and lint.
"""

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, Response, request, render_template_string

from src.coverage import analyze, render_report
from src.formats import render_json, render_markdown
from src.lint import lint_gherkin
from src.rule_engine import build_feature, parse_story, render_gherkin

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

EXAMPLE = """# User login

As a registered user, I want to log in with my email and password,
so that I can access my account securely.

Acceptance Criteria:
- When the user submits valid credentials, then they are taken to the dashboard
- An error is shown when the email format is invalid (admin, user, guest)
"""

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Gherkin Generator</title>
<style>
body{background:#14121f;color:#d6d0ea;font-family:ui-monospace,Menlo,Consolas,monospace;max-width:900px;margin:2rem auto;padding:0 1rem}
h1{color:#a78bfa}h2{color:#f5c86e}
textarea{width:100%;height:220px;background:#1e1a33;color:#d6d0ea;border:1px solid #3b3355;border-radius:8px;padding:.75rem;font:inherit}
select,button{background:#1e1a33;color:#d6d0ea;border:1px solid #3b3355;border-radius:8px;padding:.5rem .8rem;font:inherit}
button{background:#a78bfa;color:#14121f;font-weight:bold;cursor:pointer}
button:hover{background:#c4b5fd}
pre{background:#1e1a33;border:1px solid #3b3355;border-radius:8px;padding:1rem;overflow:auto;white-space:pre-wrap}
label{margin-right:1rem}.row{margin:.75rem 0}.err{color:#ff7b72}.ok{color:#7ee787}
a{color:#a78bfa}
</style></head><body>
<h1>🤖 AI Gherkin Generator</h1>
<p>Requirement in, <b>.feature</b> file out — via Azure OpenAI or the offline rule engine.</p>
<form method="post" action="/generate">
<div class="row"><textarea name="story" placeholder="Paste your user story here...">{{ story }}</textarea></div>
<div class="row">
<label>Engine <select name="engine"><option value="auto">auto</option><option value="rule">rule (offline)</option><option value="ai">ai (Azure OpenAI)</option></select></label>
<label>Format <select name="fmt"><option value="gherkin">gherkin</option><option value="json">json</option><option value="markdown">markdown</option></select></label>
<label><input type="checkbox" name="report" checked> coverage</label>
<label><input type="checkbox" name="lint" checked> lint</label>
</div>
<div class="row"><button type="submit">Generate ✨</button></div>
</form>
{{ result }}
</body></html>"""

RESULT = """
<h2>Output</h2>
<pre>{{ output }}</pre>
<form method="post" action="/download">
<input type="hidden" name="story" value="{{ story_attr }}">
<input type="hidden" name="engine" value="{{ engine }}">
<input type="hidden" name="fmt" value="{{ fmt }}">
<button type="submit">⬇ Download file</button>
</form>
{% if report %}<h2>Coverage</h2><pre>{{ report }}</pre>{% endif %}
{% if lint %}<h2>Lint</h2><pre class="{{ 'ok' if lint_ok else 'err' }}">{{ lint }}</pre>{% endif %}
"""


def _generate(story: str, engine: str, fmt: str):
    """Returns (text, feature-or-None, error-or-None)."""
    if engine == "auto":
        engine = (
            "ai"
            if os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY")
            else "rule"
        )
    if engine == "ai":
        try:
            from src.ai_engine import generate_with_ai
        except RuntimeError as exc:
            return None, None, str(exc)
        try:
            return generate_with_ai(story), None, None
        except Exception as exc:  # noqa: BLE001 - show provider errors in UI
            return None, None, f"AI engine error: {exc}"
    feature = build_feature(parse_story(story))
    if fmt == "json":
        return render_json(feature), feature, None
    if fmt == "markdown":
        return render_markdown(feature), feature, None
    return render_gherkin(feature), feature, None


@app.route("/", methods=["GET"])
def index():
    return render_template_string(PAGE, story=EXAMPLE, result="")


@app.route("/generate", methods=["POST"])
def generate():
    story = request.form.get("story", "")
    engine = request.form.get("engine", "auto")
    fmt = request.form.get("fmt", "gherkin")
    if not story.strip():
        result = '<p class="err">Paste a requirement first.</p>'
        return render_template_string(PAGE, story=story, result=result)

    text, feature, error = _generate(story, engine, fmt)
    if error:
        result = f'<p class="err">{html.escape(error)}</p>'
        return render_template_string(PAGE, story=story, result=result)

    report = render_report(analyze(feature)) if request.form.get("report") and feature else ""
    issues = lint_gherkin(text) if request.form.get("lint") else []
    lint_html = "clean ✓" if not issues else "\n".join(f"- {i}" for i in issues)
    result = render_template_string(
        RESULT,
        output=text,
        story_attr=story,
        engine=engine,
        fmt=fmt,
        report=report,
        lint=lint_html,
        lint_ok=not issues,
    )
    return render_template_string(PAGE, story=story, result=result)


@app.route("/download", methods=["POST"])
def download():
    story = request.form.get("story", "")
    engine = request.form.get("engine", "auto")
    fmt = request.form.get("fmt", "gherkin")
    text, _, error = _generate(story, engine, fmt)
    if error:
        return error, 400
    ext = {"gherkin": "feature", "json": "json", "markdown": "md"}[fmt]
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=generated.{ext}"},
    )


if __name__ == "__main__":
    app.run(debug=True)
