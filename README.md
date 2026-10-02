# AI Test Case & Gherkin Generator

Turn product requirements and user stories into ready-to-run **Gherkin feature files** — with an
AI engine (Azure OpenAI) and an offline rule-based engine that works with no API key.

## How it works

```
requirement.md  ──►  cli.py  ──►  AI engine (Azure OpenAI)  ──►  feature file
                              └─►  Rule engine (offline)    ──►  feature file
```

- **AI engine** (`src/ai_engine.py`) — sends the requirement to Azure OpenAI with a
  QA-engineer system prompt; returns a clean `.feature` file (happy path, edge cases,
  negative scenarios, Scenario Outlines with Examples).
- **Rule engine** (`src/rule_engine.py`) — parses `As a / I want / So that` stories plus
  `Acceptance Criteria` bullets and generates structured scenarios, including
  `When ... then ...` splitting and heuristic negative scenarios (validation,
  unauthorized access, not found). Zero dependencies, zero network calls.

## Setup

```bash
git clone https://github.com/dharshuadhi/ai-gherkin-generator.git
cd ai-gherkin-generator
pip install -r requirements.txt
```

For the AI engine, copy `.env.example` to `.env` and fill in your Azure OpenAI values:

```bash
cp .env.example .env
```

## Usage

```bash
# Auto: AI when configured, otherwise the offline rule engine
python -m src.cli -i examples/login_story.md -o login.feature

# Force the offline engine (no API key needed)
python -m src.cli -i examples/login_story.md --engine rule -o login.feature

# Pipe a requirement via stdin
cat mystory.md | python -m src.cli --engine rule
```

Input format (markdown):

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

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project structure

```
src/
  cli.py          argument parsing, engine selection, I/O
  ai_engine.py    Azure OpenAI client + generation
  rule_engine.py  offline parser + Gherkin renderer
  prompts.py      system prompt for the AI engine
examples/         sample requirement + generated feature file
tests/            unit tests for the rule engine
```

## License

MIT — see [LICENSE](LICENSE).
