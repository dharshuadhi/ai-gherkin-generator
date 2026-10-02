/* Page Object Model preview — browser port of src/pom.py (simplified).
   Generates Python page-object classes with XPath locators + thin tests. */

const POM_TARGET = {
  baseUrl: "http://127.0.0.1:5050",
  xpath: {
    email: "//input[@id='email']", password: "//input[@id='password']",
    login_button: "//button[@id='login-btn']", logout_link: "//a[@id='logout-link']",
    reset_link: "//a[@id='reset-link']", reset_email: "//input[@id='reset-email']",
    reset_button: "//button[@id='reset-btn']", error: "//p[@id='error']",
    welcome: "//h1[@id='welcome']", reset_sent: "//p[@id='sent']",
  },
  const: {
    email: "EMAIL_INPUT", password: "PASSWORD_INPUT", login_button: "LOGIN_BUTTON",
    logout_link: "LOGOUT_LINK", reset_link: "RESET_LINK", reset_email: "RESET_EMAIL_INPUT",
    reset_button: "RESET_BUTTON", error: "ERROR_MESSAGE", welcome: "WELCOME_HEADING",
    reset_sent: "RESET_CONFIRMATION",
  },
  pages: {
    LoginPage: { path: "/", elements: ["email", "password", "login_button", "reset_link", "error"] },
    ResetPage: { path: "/reset", elements: ["reset_email", "reset_button", "reset_sent"] },
    DashboardPage: { path: "/dashboard", elements: ["welcome", "logout_link"] },
  },
};

const TD = { valid_email: "user@example.com", valid_password: "correct-horse",
             invalid_email: "not-an-email", wrong_password: "wrong", unknown_email: "nobody@example.com" };

function _acts() { return []; }

function compileLite(whenText, thenText, context) {
  const acts = [{ type: "goto", url: "/", description: "open login page" }];
  const low = (whenText + " " + context).toLowerCase();
  const A = (type, key, extra = {}) => ({ type, key, ...extra });
  if (/reset/.test(low)) {
    acts.push({ type: "goto", url: "/reset", description: "go to password reset page" });
    const em = /registered/.test(low) ? TD.valid_email : TD.unknown_email;
    acts.push(A("fill", "reset_email", { value: em, description: "fill email" }));
    acts.push(A("click", "reset_button", { description: "click send reset link" }));
  } else if (/valid credentials/.test(low)) {
    acts.push(A("fill", "email", { value: TD.valid_email, description: "fill valid email" }));
    acts.push(A("fill", "password", { value: TD.valid_password, description: "fill valid password" }));
    acts.push(A("click", "login_button", { description: "click log in" }));
  } else if (/invalid.*password/.test(low) || (/invalid/.test(low) && /credentials/.test(low))) {
    acts.push(A("fill", "email", { value: TD.valid_email, description: "fill valid email" }));
    const n = /3 times|three times/.test(low) ? 3 : 1;
    for (let i = 0; i < n; i++) {
      acts.push(A("fill", "password", { value: TD.wrong_password, description: "fill wrong password" }));
      acts.push(A("click", "login_button", { description: "click log in" }));
    }
  } else if (/email format.*invalid|invalid.*email/.test(low)) {
    acts.push(A("fill", "email", { value: TD.invalid_email, description: "fill malformed email" }));
    acts.push(A("fill", "password", { value: TD.valid_password, description: "fill password" }));
    acts.push(A("click", "login_button", { description: "click log in" }));
  } else if (/unregistered|unknown/.test(low)) {
    acts.push(A("fill", "email", { value: TD.unknown_email, description: "fill unknown email" }));
    acts.push(A("fill", "password", { value: TD.valid_password, description: "fill password" }));
    acts.push(A("click", "login_button", { description: "click log in" }));
  } else if (/log ?out/.test(low)) {
    acts.push(A("click", "logout_link", { description: "click log out" }));
  }
  const tl = thenText.toLowerCase();
  if (/dashboard|welcome/.test(tl)) {
    acts.push({ type: "expect_url", url: "/dashboard", description: "expect dashboard url" });
    acts.push(A("expect_visible", "welcome", { description: "expect welcome visible" }));
  } else if (/error|invalid|locked/.test(tl)) {
    acts.push(A("expect_visible", "error", { description: "expect error visible" }));
  } else if (/reset/.test(tl) && /email|sent/.test(tl)) {
    acts.push(A("expect_visible", "reset_sent", { description: "expect reset confirmation" }));
  }
  return acts;
}

const METHOD_BODIES = {
  open: { params: "self", doc: "Open this page.",
          body: ["self.page.goto(self.base_url + self.URL_PATH)", "return self"] },
  login: { params: "self, email: str, password: str", doc: "Log in with the given credentials.",
           body: ["self.page.locator(self.EMAIL_INPUT).fill(email)",
                  "self.page.locator(self.PASSWORD_INPUT).fill(password)",
                  "self.page.locator(self.LOGIN_BUTTON).click()"] },
  is_error_visible: { params: "self", doc: "Whether a validation error is shown.",
                      body: ["return self.page.locator(self.ERROR_MESSAGE).is_visible()"] },
  get_error_message: { params: "self", doc: "Text of the validation error.",
                       body: ["return self.page.locator(self.ERROR_MESSAGE).inner_text()"] },
  request_reset: { params: "self, email: str", doc: "Request a password-reset link.",
                   body: ["self.page.locator(self.RESET_EMAIL_INPUT).fill(email)",
                          "self.page.locator(self.RESET_BUTTON).click()"] },
  is_confirmation_visible: { params: "self", doc: "Whether the reset confirmation is shown.",
                              body: ["return self.page.locator(self.RESET_CONFIRMATION).is_visible()"] },
  is_loaded: { params: "self", doc: "Whether the dashboard loaded.",
               body: ["return self.page.locator(self.WELCOME_HEADING).is_visible()"] },
  logout: { params: "self", doc: "Log out.",
            body: ["self.page.locator(self.LOGOUT_LINK).click()"] },
};

function pageClassCode(cls, methods) {
  const spec = POM_TARGET.pages[cls];
  const L = [`"""Page object for ${spec.path} — generated by ai-gherkin-generator."""`,
    "from playwright.sync_api import Page", "", "", `class ${cls}:`,
    `    """Page object for \`${spec.path}\`."""`, "", `    URL_PATH = "${spec.path}"`, ""];
  spec.elements.forEach(k => L.push(`    ${POM_TARGET.const[k]} = "${POM_TARGET.xpath[k]}"`));
  L.push("", "    def __init__(self, page: Page, base_url: str):",
         "        self.page = page", "        self.base_url = base_url", "");
  ["open", ...methods.filter(m => m !== "open").sort()].forEach(m => {
    const b = METHOD_BODIES[m];
    L.push(`    def ${m}(${b.params}):`, `        """${b.doc}"""`);
    b.body.forEach(l => L.push("        " + l));
    L.push("");
  });
  return L.join("\n").trimEnd() + "\n";
}

function generatePOMPreview(feature) {
  // compile each scenario, collect touched pages + methods
  const keyToPage = {};
  Object.entries(POM_TARGET.pages).forEach(([cls, spec]) =>
    spec.elements.forEach(k => keyToPage[k] = cls));
  const used = {}; // cls -> Set(methods)
  const compiled = feature.scenarios.map(sc => {
    const whens = sc.steps.filter(s => s[0] === "When").map(s => s[1]);
    const thens = sc.steps.filter(s => s[0] === "Then").map(s => s[1]);
    const acts = compileLite(whens.join(" "), thens.join(" "), sc.name);
    acts.forEach(a => {
      const cls = a.url ? Object.keys(POM_TARGET.pages).find(c => POM_TARGET.pages[c].path === a.url)
                        : keyToPage[a.key];
      if (!cls) return;
      const set = used[cls] || (used[cls] = new Set(["open"]));
      if (a.type === "fill" && /email|password/.test(a.key) ||
          (a.type === "click" && /login_button|reset_button/.test(a.key))) {
        if (cls === "LoginPage" && /login_button/.test(a.key || "")) set.add("login");
        if (cls === "ResetPage" && /reset_button/.test(a.key || "")) set.add("request_reset");
      }
      if (a.type === "click" && a.key === "logout_link") set.add("logout");
      if (a.type === "expect_visible" && a.key === "error") { set.add("is_error_visible"); set.add("get_error_message"); }
      if (a.type === "expect_visible" && a.key === "welcome") set.add("is_loaded");
      if (a.type === "expect_visible" && a.key === "reset_sent") set.add("is_confirmation_visible");
    });
    return { name: sc.name, acts };
  });

  let out = "";
  Object.keys(used).forEach(cls => {
    out += `# ── pages/${cls.replace(/([A-Z])/g, "_$1").toLowerCase().slice(1)}.py ──\n`;
    out += pageClassCode(cls, [...used[cls]]) + "\n";
  });
  // thin tests
  const modName = m => m;
  out += `# ── test_${feature.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "suite"}.py ──\n`;
  out += `"""Tests generated from '${feature.title}' — Page Object style."""\n`;
  Object.keys(used).forEach(cls =>
    out += `from pages.${cls.replace(/([A-Z])/g, "_$1").toLowerCase().slice(1)} import ${cls}\n`);
  out += `\nBASE_URL = "${POM_TARGET.baseUrl}"\n\n`;
  const varOf = cls => cls.replace(/([A-Z])/g, "_$1").toLowerCase().slice(1);
  compiled.forEach(cs => {
    const tname = "test_" + cs.name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 60);
    out += `def ${tname}(page):\n`;
    const made = new Set();
    const ensure = (cls, openIt = true) => {
      if (!made.has(cls)) {
        out += `    ${varOf(cls)} = ${cls}(page, BASE_URL)${openIt ? ".open()" : ""}\n`;
        made.add(cls);
      }
    };
    let lastEmail = "";
    cs.acts.forEach(a => {
      const cls = a.url ? Object.keys(POM_TARGET.pages).find(c => POM_TARGET.pages[c].path === a.url)
                        : keyToPage[a.key];
      if (a.type === "goto" && cls) { ensure(cls); return; }
      if (a.type === "fill" && cls === "LoginPage" && a.key === "email") lastEmail = a.value;
      if (a.type === "click" && a.key === "login_button" && cls === "LoginPage") {
        ensure("LoginPage");
        const em = cs.acts.find(x => x.type === "fill" && x.key === "email");
        const pw = [...cs.acts].reverse().find(x => x.type === "fill" && x.key === "password");
        out += `    ${varOf("LoginPage")}.login(${JSON.stringify(em ? em.value : lastEmail)}, ${JSON.stringify(pw ? pw.value : "")})\n`;
        return;
      }
      if (a.type === "click" && a.key === "reset_button") {
        ensure("ResetPage");
        const em = cs.acts.find(x => x.type === "fill" && x.key === "reset_email");
        out += `    ${varOf("ResetPage")}.request_reset(${JSON.stringify(em ? em.value : "")})\n`;
        return;
      }
      if (a.type === "click" && a.key === "logout_link") { ensure("DashboardPage"); out += `    ${varOf("DashboardPage")}.logout()\n`; return; }
      if (a.type === "expect_visible" && a.key === "error") { ensure("LoginPage", false); out += `    assert ${varOf("LoginPage")}.is_error_visible()\n`; return; }
      if (a.type === "expect_visible" && a.key === "welcome") { ensure("DashboardPage", false); out += `    assert ${varOf("DashboardPage")}.is_loaded()\n`; return; }
      if (a.type === "expect_visible" && a.key === "reset_sent") { ensure("ResetPage", false); out += `    assert ${varOf("ResetPage")}.is_confirmation_visible()\n`; return; }
    });
    out += "\n";
  });
  return { code: out, pages: Object.keys(used).length,
           tests: compiled.filter(c => c.acts.some(a => a.type !== "goto")).length };
}

if (typeof module !== "undefined") module.exports = { generatePOMPreview, POM_TARGET };
