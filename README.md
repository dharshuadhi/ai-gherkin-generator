# AI Test Case & Gherkin Generator

Turn product requirements and user stories into ready-to-run **Gherkin feature files** —
through a CLI or a web UI — with an AI engine (Azure OpenAI) and an offline rule-based
engine that works with no API key.

## How it works

```mermaid
flowchart LR
    A[📝 Requirement<br/>story + acceptance criteria] --> B{Engine?}
    B -->|Azure OpenAI configured| C[🤖 AI engine<br/>QA prompt → feature file]
    B -->|offline / --engine rule| D[⚙️ Rule engine<br/>parse → scenarios → outlines]
    C --> E[📄 Feature model]
    D --> E
    E --> F[📦 Export<br/>gherkin · json · markdown]
    E --> G[📊 Coverage report]
    E --> H[🔍 Gherkin lint]
```

**Step by step:**

1. **Write your requirement** — a markdown file with a `As a / I want / So that` story
   plus `Acceptance Criteria` bullets (or paste it into the web UI).
2. **Pick an engine** — `auto` uses Azure OpenAI when your key is configured,
   otherwise the offline rule engine. Override with `--engine ai|rule`.
3. **Generate** — each criterion becomes a `Scenario`; `When ... then ...` lines are
   split into steps; value lists like `(admin, user, guest)` become
   `Scenario Outlines` with `Examples` tables; negative scenarios
   (validation, unauthorized access, not found) are added automatically.
4. **Export** — Gherkin `.feature`, JSON test catalog, or Markdown test plan.
5. **Verify** — `--report` shows scenario coverage per requirement,
   `--lint` catches structural problems (missing Given/When/Then, duplicates).

## Web UI

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 — paste a story, choose engine and format, and get the
generated file in the browser with coverage and lint results, plus a download button.

## CLI

```bash
# Auto engine, Gherkin output
python -m src.cli -i examples/login_story.md -o login.feature

# Score the requirement first, then generate with coverage + lint
python -m src.cli -i examples/login_story.md --engine rule --quality --report --lint -o login.feature

# Detect near-duplicate scenarios and generate pytest-bdd stubs
python -m src.cli -i examples/login_story.md --dedup --stubs test_login_steps.py -o login.feature

# Offline rule engine, JSON catalog
python -m src.cli -i examples/login_story.md --engine rule --format json -o login.json

# Markdown test plan
python -m src.cli -i examples/login_story.md --format markdown -o plan.md

# Batch: convert a folder of stories
python -m src.cli -i stories/ -o features/

# Pipe via stdin
cat mystory.md | python -m src.cli --engine rule
```

Input format:

```markdown
# Password reset

As a registered user, I want to reset my password,
so that I can regain access to my account.

Acceptance Criteria:
- When the user submits a registered email, then a reset link is emailed
- An error is shown for unregistered email addresses
- Reset links expire after 60 minutes
```

See [`examples/login.feature`](examples/login.feature) for generated output.

## Features

### Generation
- 🤖 **AI engine** — Azure OpenAI with a QA-engineer system prompt
- ⚙️ **Offline rule engine** — zero dependencies, zero network calls
- 🧬 **Scenario Outlines** — parenthesized value lists become `Examples` tables
- 🛡️ **Negative scenarios** — validation, auth, and not-found cases auto-added

### Quality engineering
- 🎯 **Requirement quality scoring** — grades the story 0–100 (A–F) before generating:
  detects vague untestable language ("fast", "user-friendly"), missing actors/goals,
  compound criteria, and criteria with no observable outcome — each finding ships with a fix suggestion
- 🔍 **Near-duplicate detection** — TF-IDF + cosine similarity flags copy-paste scenarios
  so they can be merged into Scenario Outlines
- 📊 **Coverage reports** — positive/negative/outline counts per requirement
- ✅ **Gherkin lint** — missing steps, duplicates, empty scenarios

### From spec to executable suite
- 🧪 **pytest-bdd stub generation** (`--stubs`) — turns the feature file into runnable
  step-definition skeletons: shared steps deduped, `<placeholders>` become regex parsers
- 📦 **Multi-format export** — Gherkin, JSON catalog, Markdown test plan
- 🌐 **Web UI** — score, generate, preview, and download in the browser
- 📁 **Batch mode** — convert whole folders of stories at once

## Setup

```bash
git clone https://github.com/dharshuadhi/ai-gherkin-generator.git
cd ai-gherkin-generator
pip install -r requirements.txt
cp .env.example .env   # fill in Azure OpenAI values for the AI engine
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project structure

```
app.py            Flask web UI
src/
  cli.py          argument parsing, engine selection, batch mode
  ai_engine.py    Azure OpenAI client + generation
  rule_engine.py  offline parser + structured Feature model + Gherkin renderer
  quality.py      requirement quality scoring (vague language, structure, testability)
  similarity.py   TF-IDF near-duplicate scenario detection
  stubs.py        pytest-bdd step-definition stub generator
  formats.py      JSON catalog + Markdown test plan renderers
  coverage.py     coverage analysis + report
  lint.py         Gherkin structural lint
  prompts.py      system prompt for the AI engine
docs/             browser demo (GitHub Pages): generator + quality scorer in JS
examples/         sample requirement + generated feature file
tests/            unit tests (rule engine, outlines, formats, coverage, lint,
                  quality, similarity, stubs)
```

## License

MIT — see [LICENSE](LICENSE).
