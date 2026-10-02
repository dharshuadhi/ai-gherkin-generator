"""Page Object Model generator: compiled actions -> page classes + tests.

Produces the structure real SDET teams maintain — not flat scripts:

    pom_suite/
        conftest.py            # browser / page fixtures
        pages/
            __init__.py
            login_page.py      # XPath locators as class constants + methods
            reset_page.py
            dashboard_page.py
        test_login.py          # thin tests calling page-object methods

Locators are XPath (//input[@id='email']) stored as class constants;
interactions live in named methods (login(), request_reset(), logout());
tests only orchestrate pages and assert outcomes.
"""

import os
import re


def _test_name(name):
    n = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60].rstrip("_")
    return f"test_{n or 'scenario'}"


def _module_name(class_name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()


def _var_name(class_name):
    return _module_name(class_name)


def _key_of(target, selector):
    for key, css in target["selectors"].items():
        if css == selector:
            return key
    return ""


def _lit(value):
    return repr(value)


# Method vocabularies: action-sequence patterns -> page methods.
# Each entry: (method_name, [(action_type, element_key), ...], call_template, page_class)
# {email_ctx} = most recently used email (for retry sequences that only refill the password).
METHOD_PATTERNS = [
    ("login", [("fill", "email"), ("fill", "password"), ("click", "login_button")],
     'login({email}, {password})', "LoginPage"),
    ("login", [("fill", "password"), ("click", "login_button")],
     'login({email_ctx}, {password})', "LoginPage"),
    ("login", [("fill", "email"), ("click", "login_button")],
     'login({email}, "")', "LoginPage"),
    ("open_password_reset", [("click", "reset_link")],
     'open_password_reset()', "LoginPage"),
    ("request_reset", [("fill", "reset_email"), ("click", "reset_button")],
     'request_reset({email})', "ResetPage"),
    ("logout", [("click", "logout_link")],
     'logout()', "DashboardPage"),
]

ASSERTION_METHODS = {
    # (action_type, element_key) -> (method_name, page_class)
    ("expect_visible", "error"): ("is_error_visible", "LoginPage"),
    ("expect_visible", "welcome"): ("is_loaded", "DashboardPage"),
    ("expect_visible", "reset_sent"): ("is_confirmation_visible", "ResetPage"),
}

# Page-object method bodies (method_name -> (params, docstring, body_lines)).
METHOD_BODIES = {
    "open": (["self"], "Open this page.",
             ["self.page.goto(self.base_url + self.URL_PATH)", "return self"]),
    "login": (["self", "email: str", "password: str"], "Log in with the given credentials.",
              ["self.page.locator(self.EMAIL_INPUT).fill(email)",
               "self.page.locator(self.PASSWORD_INPUT).fill(password)",
               "self.page.locator(self.LOGIN_BUTTON).click()"]),
    "open_password_reset": (["self"], "Go to the password-reset page.",
                            ["self.page.locator(self.RESET_LINK).click()"]),
    "is_error_visible": (["self"], "Whether a validation error is shown.",
                         ["return self.page.locator(self.ERROR_MESSAGE).is_visible()"]),
    "get_error_message": (["self"], "Text of the validation error.",
                          ["return self.page.locator(self.ERROR_MESSAGE).inner_text()"]),
    "request_reset": (["self", "email: str"], "Request a password-reset link.",
                      ["self.page.locator(self.RESET_EMAIL_INPUT).fill(email)",
                       "self.page.locator(self.RESET_BUTTON).click()"]),
    "is_confirmation_visible": (["self"], "Whether the reset confirmation is shown.",
                                 ["return self.page.locator(self.RESET_CONFIRMATION).is_visible()"]),
    "is_loaded": (["self"], "Whether the dashboard loaded (welcome banner visible).",
                  ["return self.page.locator(self.WELCOME_HEADING).is_visible()"]),
    "get_welcome_text": (["self"], "Welcome banner text.",
                         ["return self.page.locator(self.WELCOME_HEADING).inner_text()"]),
    "logout": (["self"], "Log out.",
               ["self.page.locator(self.LOGOUT_LINK).click()"]),
}


def _used_pages(compiled, target):
    """Which page-object classes the scenarios touch, and which methods."""
    key_to_page = {}
    for cls, spec in target["page_objects"].items():
        for key in spec["elements"]:
            key_to_page[key] = cls
    path_to_page = {spec["path"]: cls for cls, spec in target["page_objects"].items()}

    used = {}  # cls -> {"methods": set, "assertions": set}
    for cs in compiled:
        if cs.skipped:
            continue
        for a in cs.actions:
            if a.type == "goto":
                cls = path_to_page.get(a.url)
                if cls:
                    used.setdefault(cls, {"methods": set(), "assertions": set()})["methods"].add("open")
                continue
            key = _key_of(target, a.selector)
            cls = key_to_page.get(key)
            if not cls:
                continue
            entry = used.setdefault(cls, {"methods": set(), "assertions": set()})
            if (a.type, key) in ASSERTION_METHODS:
                entry["assertions"].add(ASSERTION_METHODS[(a.type, key)][0])
            else:
                # record candidate interaction methods by matching patterns later
                entry["methods"].add(key)
    # resolve interaction methods from patterns
    for cs in compiled:
        if cs.skipped:
            continue
        seq = [(a.type, _key_of(target, a.selector)) for a in cs.actions]
        for i in range(len(seq)):
            for mname, pattern, _tmpl, cls in METHOD_PATTERNS:
                if seq[i:i + len(pattern)] == pattern:
                    used.setdefault(cls, {"methods": set(), "assertions": set()})["methods"].add(mname)
    # drop raw element keys, keep real method names
    for cls, entry in used.items():
        entry["methods"] = {m for m in entry["methods"] if m in METHOD_BODIES}
        entry["methods"].add("open")
        # always include useful readers for asserted pages
        if "is_error_visible" in entry["assertions"]:
            entry["methods"].add("get_error_message")
        if "is_loaded" in entry["assertions"]:
            entry["methods"].add("get_welcome_text")
    return {k: v for k, v in used.items() if v["methods"] or v["assertions"]}


def render_page_object(cls, spec, methods, target) -> str:
    """Render one page-object class with XPath locators + methods."""
    lines = [f'"""Page object for {spec["path"]} — generated by ai-gherkin-generator."""',
             "from playwright.sync_api import Page", "", "",
             f"class {cls}:", f'    """Page object for `{spec["path"]}`."""', "",
             f'    URL_PATH = "{spec["path"]}"', ""]
    for key in spec["elements"]:
        const = target["const"][key]
        lines.append(f'    {const} = "{target["xpath"][key]}"')
    lines += ["", "    def __init__(self, page: Page, base_url: str):",
              "        self.page = page", "        self.base_url = base_url", ""]
    ordered = ["open"] + sorted(m for m in methods if m != "open")
    for mname in ordered:
        params, doc, body = METHOD_BODIES[mname]
        lines.append(f"    def {mname}({', '.join(params)}):")
        lines.append(f'        """{doc}"""')
        lines.extend(f"        {b}" for b in body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _match_method(seq, i, target, ctx):
    """Try to match a METHOD_PATTERN at position i.

    Returns (method_name, page_class, length, call) or None.
    ctx carries 'last_email' for retry sequences that only refill the password.
    """
    for mname, pattern, tmpl, cls in METHOD_PATTERNS:
        chunk = seq[i:i + len(pattern)]
        if len(chunk) != len(pattern):
            continue
        if all((a.type, _key_of(target, a.selector)) == p for a, p in zip(chunk, pattern)):
            values = {}
            for a, (t, key) in zip(chunk, pattern):
                if a.type == "fill":
                    values["email" if "email" in key else "password"] = a.value
            if "email" in values:
                ctx["last_email"] = values["email"]
            fmt = {"email": _lit(values.get("email", "")),
                   "password": _lit(values.get("password", "")),
                   "email_ctx": _lit(ctx.get("last_email", ""))}
            return mname, cls, len(pattern), tmpl.format(**fmt)
    return None


def render_test_module(compiled, target, feature_title, used_pages) -> str:
    """Render thin tests that orchestrate page objects."""
    path_to_page = {spec["path"]: cls for cls, spec in target["page_objects"].items()}
    imports = sorted(used_pages)
    lines = [f'"""Tests generated from \'{feature_title}\' — Page Object style.',
             "",
             "Run:  pytest",
             '"""',
             ""]
    for cls in imports:
        lines.append(f"from pages.{_module_name(cls)} import {cls}")
    lines += ["", "", f'BASE_URL = "{target["base_url"]}"', "", ""]
    for cs in compiled:
        if cs.skipped:
            lines.append(f"# SKIPPED: {cs.name} ({cs.skipped})")
            lines.append("")
            continue
        lines.append(f"def {_test_name(cs.name)}(page):")
        made = set()
        ctx = {"last_email": ""}
        seq = cs.actions
        i = 0
        while i < len(seq):
            a = seq[i]
            matched = _match_method(seq, i, target, ctx)
            if matched:
                mname, cls, length, call = matched
                var = _var_name(cls)
                if var not in made:
                    lines.append(f"    {var} = {cls}(page, BASE_URL)")
                    made.add(var)
                lines.append(f"    {var}.{call}")
                i += length
                continue
            if a.type == "goto":
                cls = path_to_page.get(a.url)
                if cls and cls in used_pages:
                    var = _var_name(cls)
                    if var not in made:
                        lines.append(f"    {var} = {cls}(page, BASE_URL).open()")
                        made.add(var)
                    else:
                        lines.append(f"    {var}.open()")
                i += 1
                continue
            key = _key_of(target, a.selector)
            if (a.type, key) in ASSERTION_METHODS:
                mname, cls = ASSERTION_METHODS[(a.type, key)]
                var = _var_name(cls)
                if var not in made:
                    lines.append(f"    {var} = {cls}(page, BASE_URL)")
                    made.add(var)
                lines.append(f"    assert {var}.{mname}(), \"expected: {a.description}\"")
            elif a.type == "expect_url":
                lines.append(f"    assert \"{a.url}\" in page.url  # {a.description}")
            else:
                lines.append(f"    # TODO (unmapped): {a.type} {a.description}")
            i += 1
        lines += ["", ""]
    return "\n".join(lines).rstrip() + "\n"


CONFTEST = '''"""Shared Playwright fixtures for the generated POM suite."""
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5050"


@pytest.fixture(scope="session", autouse=True)
def _reset_target_state():
    """Isolate runs: clear server-side state (e.g. lockout counters)."""
    try:
        req = urllib.request.Request(BASE_URL + "/__reset", data=b"", method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    p = browser.new_page()
    yield p
    p.close()
'''


def write_pom_suite(compiled, target, feature_title, out_dir) -> list:
    """Write the full POM suite. Returns list of written file paths."""
    used = _used_pages(compiled, target)
    written = []
    pages_dir = os.path.join(out_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    for cls, entry in used.items():
        spec = target["page_objects"][cls]
        code = render_page_object(cls, spec, entry["methods"] | entry["assertions"], target)
        path = os.path.join(pages_dir, _module_name(cls) + ".py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        written.append(path)
    with open(os.path.join(pages_dir, "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write("")
    fname = "test_" + re.sub(r"[^a-z0-9]+", "_", feature_title.lower()).strip("_")[:40] + ".py"
    test_code = render_test_module(compiled, target, feature_title, used)
    tpath = os.path.join(out_dir, fname or "test_suite.py")
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(test_code)
    written.append(tpath)
    cpath = os.path.join(out_dir, "conftest.py")
    with open(cpath, "w", encoding="utf-8") as fh:
        fh.write(CONFTEST)
    written.append(cpath)
    return written
