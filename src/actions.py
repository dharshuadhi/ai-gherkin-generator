"""Action compiler: from generated Gherkin steps to typed browser actions.

The rule engine understands the *structure* of a criterion (When X, then Y).
This module compiles that structure into executable browser actions
(goto / fill / click / expect_*) against a target app config — the bridge
between "generated spec" and "running test".
"""

import re
from dataclasses import dataclass, field


@dataclass
class Action:
    type: str                    # goto | fill | click | expect_url | expect_text | expect_visible
    selector: str = ""
    value: str = ""
    text: str = ""
    url: str = ""
    description: str = ""        # human-readable origin step


@dataclass
class CompiledScenario:
    name: str
    actions: list = field(default_factory=list)
    skipped: str = ""            # reason, if the scenario couldn't be compiled


DEMO_TARGET = {
    "name": "demo-login-app",
    "base_url": "http://127.0.0.1:5050",
    "test_data": {
        "valid_email": "user@example.com",
        "valid_password": "correct-horse",
        "invalid_email": "not-an-email",
        "wrong_password": "wrong",
        "unknown_email": "nobody@example.com",
    },
    "selectors": {
        "email": "#email", "password": "#password",
        "login_button": "#login-btn", "logout_link": "#logout-link",
        "reset_link": "#reset-link", "reset_email": "#reset-email",
        "reset_button": "#reset-btn", "error": "#error",
        "welcome": "#welcome", "reset_sent": "#sent",
    },
    "pages": {"login": "/", "dashboard": "/dashboard", "reset": "/reset"},
    # XPath locators + CONSTANT names for Page Object generation (src/pom.py).
    "xpath": {
        "email": "//input[@id='email']",
        "password": "//input[@id='password']",
        "login_button": "//button[@id='login-btn']",
        "logout_link": "//a[@id='logout-link']",
        "reset_link": "//a[@id='reset-link']",
        "reset_email": "//input[@id='reset-email']",
        "reset_button": "//button[@id='reset-btn']",
        "error": "//p[@id='error']",
        "welcome": "//h1[@id='welcome']",
        "reset_sent": "//p[@id='sent']",
    },
    "const": {
        "email": "EMAIL_INPUT", "password": "PASSWORD_INPUT",
        "login_button": "LOGIN_BUTTON", "logout_link": "LOGOUT_LINK",
        "reset_link": "RESET_LINK", "reset_email": "RESET_EMAIL_INPUT",
        "reset_button": "RESET_BUTTON", "error": "ERROR_MESSAGE",
        "welcome": "WELCOME_HEADING", "reset_sent": "RESET_CONFIRMATION",
    },
    # Page Object layout: class name -> url path + element keys it owns.
    "page_objects": {
        "LoginPage": {"path": "/", "elements": ["email", "password", "login_button", "reset_link", "error"]},
        "ResetPage": {"path": "/reset", "elements": ["reset_email", "reset_button", "reset_sent"]},
        "DashboardPage": {"path": "/dashboard", "elements": ["welcome", "logout_link"]},
    },
}


def _sel(target, *names):
    sels = target["selectors"]
    for n in names:
        if n in sels:
            return sels[n]
    return ""


def _compile_login_flow(text, target, actions):
    """Recognize credential-submission phrasing; returns True if handled."""
    td = target["test_data"]
    low = text.lower()
    if "valid credentials" in low or "correct password" in low:
        actions.append(Action("fill", _sel(target, "email"), td["valid_email"], description="fill valid email"))
        actions.append(Action("fill", _sel(target, "password"), td["valid_password"], description="fill valid password"))
        actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
        return True
    if "invalid email" in low and "format" in low or "malformed email" in low:
        actions.append(Action("fill", _sel(target, "email"), td["invalid_email"], description="fill malformed email"))
        actions.append(Action("fill", _sel(target, "password"), td["valid_password"], description="fill password"))
        actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
        return True
    if "invalid" in low and ("password" in low or "credentials" in low):
        actions.append(Action("fill", _sel(target, "email"), td["valid_email"], description="fill valid email"))
        actions.append(Action("fill", _sel(target, "password"), td["wrong_password"], description="fill wrong password"))
        actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
        if "3 times" in low or "three times" in low:
            for i in (2, 3):
                actions.append(Action("fill", _sel(target, "password"), td["wrong_password"],
                                      description=f"fill wrong password (attempt {i})"))
                actions.append(Action("click", _sel(target, "login_button"),
                                      description=f"click log in (attempt {i})"))
        return True
    if "unregistered" in low or "unknown" in low:
        actions.append(Action("fill", _sel(target, "email"), td["unknown_email"], description="fill unknown email"))
        actions.append(Action("fill", _sel(target, "password"), td["valid_password"], description="fill password"))
        actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
        return True
    return False


def _compile_reset_flow(text, target, actions):
    low = text.lower()
    if "reset" not in low:
        return False
    td = target["test_data"]
    actions.append(Action("goto", url=target["pages"]["reset"], description="go to password reset page"))
    if "registered" in low:
        actions.append(Action("fill", _sel(target, "reset_email"), td["valid_email"], description="fill registered email"))
    else:
        actions.append(Action("fill", _sel(target, "reset_email"), td["unknown_email"], description="fill email"))
    actions.append(Action("click", _sel(target, "reset_button"), description="click send reset link"))
    return True


def compile_when(when_text, target, context="") -> list:
    """Compile a When step into browser actions.

    `context` is the full criterion/scenario text — used when the When step
    itself is generic ("tries to log in") but the criterion names the case.
    """
    actions = []
    low = when_text.lower()
    ctx = context.lower()
    if _compile_reset_flow(when_text, target, actions):
        return actions
    if _compile_login_flow(when_text, target, actions):
        return actions
    # generic When + specific context -> infer the flow from the context
    if "log in" in low or "login" in low or "submit" in low:
        if "email format" in ctx and "invalid" in ctx:
            td = target["test_data"]
            actions.append(Action("fill", _sel(target, "email"), td["invalid_email"],
                                  description="fill malformed email (from criterion)"))
            actions.append(Action("fill", _sel(target, "password"), td["valid_password"],
                                  description="fill password"))
            actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
            return actions
        if "invalid" in ctx and "input" in ctx:
            td = target["test_data"]
            actions.append(Action("fill", _sel(target, "email"), td["invalid_email"],
                                  description="fill invalid input"))
            actions.append(Action("click", _sel(target, "login_button"), description="click log in"))
            return actions
    if "log out" in low or "logs out" in low or "clicks logout" in low:
        actions.append(Action("click", _sel(target, "logout_link"), description="click log out"))
        return actions
    m = re.search(r"navigates? to (?:the )?(\w+)", low)
    if m and m.group(1) in target["pages"]:
        actions.append(Action("goto", url=target["pages"][m.group(1)], description=f"go to {m.group(1)}"))
        return actions
    return actions


def compile_then(then_text, target) -> list:
    """Compile a Then step into assertion actions."""
    actions = []
    low = then_text.lower()
    if "dashboard" in low or "welcome" in low:
        actions.append(Action("expect_url", url="/dashboard", description="expect dashboard url"))
        actions.append(Action("expect_visible", _sel(target, "welcome"), description="expect welcome visible"))
    elif "error" in low or "invalid" in low or "locked" in low:
        actions.append(Action("expect_visible", _sel(target, "error"), description="expect error visible"))
    elif "reset" in low and ("emailed" in low or "sent" in low):
        actions.append(Action("expect_visible", _sel(target, "reset_sent"), description="expect reset confirmation"))
    elif "login" in low and ("page" in low or "redirect" in low):
        actions.append(Action("expect_url", url="/", description="expect back at login"))
    return actions


def compile_scenario(name, steps, target) -> CompiledScenario:
    """Compile a scenario's When/Then steps into an executable action list."""
    actions = [Action("goto", url=target["pages"]["login"], description="open login page")]
    for kw, text in steps:
        kwl = kw.lower()
        if kwl == "when":
            actions.extend(compile_when(text, target, context=name))
        elif kwl == "then":
            actions.extend(compile_then(text, target))
    # a scenario is only runnable if it has at least one real interaction + one assertion
    has_action = any(a.type in ("fill", "click", "goto") for a in actions[1:])
    has_assert = any(a.type.startswith("expect") for a in actions)
    if not (has_action and has_assert):
        return CompiledScenario(name, [], skipped="no compilable browser actions for target app")
    return CompiledScenario(name, actions)


def compile_feature(feature, target=DEMO_TARGET) -> list:
    """Compile every scenario in a Feature into CompiledScenarios."""
    out = []
    for sc in feature.scenarios:
        if sc.examples:  # outlines: compile once with the first example row
            steps = [(kw, _fill_example(t, sc.examples)) for kw, t in sc.steps]
            out.append(compile_scenario(sc.name + " [example 1]", steps, target))
        else:
            out.append(compile_scenario(sc.name, sc.steps, target))
    return out


def _fill_example(text, examples):
    for header, row in zip(examples["headers"], examples["rows"]):
        text = text.replace(f"<{header}>", row[0])
    return text
