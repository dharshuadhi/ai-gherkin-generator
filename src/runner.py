"""Headless Playwright runner: execute compiled actions for real.

Runs each compiled scenario in Chromium, records per-step timing and
pass/fail, captures a screenshot on failure, and returns a structured
report. This is where generated specs meet reality.
"""

import os
import re
import time
from dataclasses import dataclass, field


@dataclass
class StepResult:
    description: str
    action: str
    ok: bool
    error: str = ""
    duration_ms: int = 0


@dataclass
class ScenarioReport:
    name: str
    passed: bool
    steps: list = field(default_factory=list)
    screenshot: str = ""
    duration_ms: int = 0
    skipped: str = ""


def _reset_target(target):
    """Best-effort: ask the target app to clear test-run state (lockouts, etc.)."""
    try:
        import urllib.request
        req = urllib.request.Request(target["base_url"] + "/__reset", data=b"",
                                     method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:  # noqa: BLE001 - reset hook is optional
        pass


def _run_action(page, expect, a: "Action", base_url: str):
    if a.type == "goto":
        url = a.url if a.url.startswith("http") else base_url + a.url
        page.goto(url)
    elif a.type == "fill":
        page.fill(a.selector, a.value)
    elif a.type == "click":
        page.click(a.selector)
    elif a.type == "expect_url":
        expect(page).to_have_url(re.compile(rf".*{re.escape(a.url)}$"), timeout=5000)
    elif a.type == "expect_visible":
        expect(page.locator(a.selector)).to_be_visible(timeout=5000)
    elif a.type == "expect_text":
        expect(page.locator(a.selector)).to_contain_text(a.text, timeout=5000)
    else:
        raise ValueError(f"unsupported action: {a.type}")


def run_compiled(compiled, target, screenshot_dir="screenshots", headless=True) -> list:
    """Execute compiled scenarios headlessly. Returns [ScenarioReport]."""
    from playwright.sync_api import expect, sync_playwright

    _reset_target(target)  # isolate runs: clear server-side state like lockout counters
    os.makedirs(screenshot_dir, exist_ok=True)
    reports = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        for cs in compiled:
            if cs.skipped:
                reports.append(ScenarioReport(cs.name, True, skipped=cs.skipped))
                continue
            page = browser.new_page()
            steps, t0 = [], time.time()
            failed = None
            for a in cs.actions:
                s0 = time.time()
                try:
                    _run_action(page, expect, a, target["base_url"])
                    steps.append(StepResult(a.description or a.type, a.type, True,
                                            duration_ms=int((time.time() - s0) * 1000)))
                except Exception as exc:  # noqa: BLE001 - record real browser errors
                    steps.append(StepResult(a.description or a.type, a.type, False,
                                            error=str(exc)[:300],
                                            duration_ms=int((time.time() - s0) * 1000)))
                    failed = exc
                    break
            shot = ""
            if failed:
                shot = os.path.join(screenshot_dir,
                                    re.sub(r"[^a-z0-9]+", "_", cs.name.lower())[:50] + ".png")
                page.screenshot(path=shot)
            page.close()
            reports.append(ScenarioReport(
                cs.name, failed is None, steps, shot,
                duration_ms=int((time.time() - t0) * 1000)))
        browser.close()
    return reports


def render_run_report(reports) -> str:
    ran = [r for r in reports if not r.skipped]
    passed = sum(1 for r in ran if r.passed)
    lines = [f"Execution: {passed}/{len(ran)} scenarios passed "
             f"({sum(r.duration_ms for r in ran)}ms total)", ""]
    for r in reports:
        if r.skipped:
            lines.append(f"  SKIP {r.name} ({r.skipped})")
            continue
        icon = "✅" if r.passed else "❌"
        lines.append(f"  {icon} {r.name} [{r.duration_ms}ms]")
        for s in r.steps:
            mark = "✓" if s.ok else "✗"
            extra = f" — {s.error}" if s.error else ""
            lines.append(f"      {mark} {s.description} ({s.duration_ms}ms){extra}")
        if r.screenshot:
            lines.append(f"      📸 {r.screenshot}")
    return "\n".join(lines)
