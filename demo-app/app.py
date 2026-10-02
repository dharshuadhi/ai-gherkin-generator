"""Demo target app for the generate->execute loop.

A tiny but REAL web app (login, dashboard, logout, password reset) that the
generated Playwright tests drive headlessly. This is test infrastructure —
a stand-in for any real product under test.
"""

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = "demo-only-not-for-prod"

USERS = {"user@example.com": "correct-horse"}
ATTEMPTS = {}  # email -> failed attempt count (demo lockout)

LOGIN = """
<!doctype html><html><body style="font-family:sans-serif;max-width:400px;margin:4rem auto">
<h1>Sign in</h1>
{% if error %}<p id="error" style="color:red">{{ error }}</p>{% endif %}
<form method="post">
  <label>Email <input id="email" name="email" type="text"></label><br><br>
  <label>Password <input id="password" name="password" type="password"></label><br><br>
  <button id="login-btn" type="submit">Log in</button>
</form>
<p><a id="reset-link" href="/reset">Forgot password?</a></p>
</body></html>
"""

DASHBOARD = """
<!doctype html><html><body style="font-family:sans-serif;max-width:400px;margin:4rem auto">
<h1 id="welcome">Welcome, {{ email }}!</h1>
<p>You are on the dashboard.</p>
<a id="logout-link" href="/logout">Log out</a>
</body></html>
"""

RESET = """
<!doctype html><html><body style="font-family:sans-serif;max-width:400px;margin:4rem auto">
<h1>Reset password</h1>
{% if sent %}<p id="sent">Reset link emailed to {{ sent }}</p>
{% else %}<form method="post">
  <label>Email <input id="reset-email" name="email" type="text"></label><br><br>
  <button id="reset-btn" type="submit">Send reset link</button>
</form>{% endif %}
</body></html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if ATTEMPTS.get(email, 0) >= 3:
            error = "Account temporarily locked after too many failed attempts."
        elif "@" not in email:
            error = "Enter a valid email address."
        elif USERS.get(email) != password:
            ATTEMPTS[email] = ATTEMPTS.get(email, 0) + 1
            if ATTEMPTS[email] >= 3:
                error = "Account temporarily locked after too many failed attempts."
            else:
                error = "Invalid email or password."
        else:
            ATTEMPTS.pop(email, None)
            session["user"] = email
            return redirect(url_for("dashboard"))
    return render_template_string(LOGIN, error=error)


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template_string(DASHBOARD, email=session["user"])


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/reset", methods=["GET", "POST"])
def reset():
    sent = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if email in USERS:
            sent = email
    return render_template_string(RESET, sent=sent)


@app.route("/__reset", methods=["POST"])
def reset_demo():
    """Test hook: clear lockout counters between runs."""
    ATTEMPTS.clear()
    return {"ok": True}


if __name__ == "__main__":
    app.run(port=5050)
