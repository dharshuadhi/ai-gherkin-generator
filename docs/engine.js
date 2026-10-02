/* Rule-based Gherkin generator — browser port of src/rule_engine.py.
   Zero dependencies. Also used by index.html for the live demo. */

function clean(t) {
  return (t || "").replace(/\s+/g, " ").trim().replace(/[.]+$/, "");
}
function lowerFirst(t) {
  t = (t || "").trim();
  return t ? t[0].toLowerCase() + t.slice(1) : t;
}

const ROLE_RE = /as an?\s+([^,]+?),\s*i want\s+(.+?)(?:,?\s*so that\s+(.+))?\s*$/i;
const WHEN_THEN_RE = /^when\s+(.+?)[,;]?\s+then\s+(.+)$/is;
const BULLET_RE = /^(?:[-*\u2022\u2013\u2014]\s+(.*)|(\d+)[.)]\s+(.*))$/;
const AC_HEADER_RE = /^#{0,3}\s*acceptance criteria\b/i;
const HEADER_RE = /^#{1,3}\s+\S/;
const ENUM_RE = /\(([^()]{2,60})\)/;

function parseStory(text) {
  const lines = text.trim().split("\n").map(l => l.replace(/\s+$/, ""));
  const title = lines.length ? clean(lines[0].replace(/^#+\s*/, "")) || "Generated Feature" : "Generated Feature";

  const storyLines = [];
  let started = false;
  for (const line of lines.slice(1)) {
    const s = line.trim();
    if (!s) { if (started) break; continue; }
    if (AC_HEADER_RE.test(s)) break;
    started = true;
    storyLines.push(s);
  }
  const storyText = storyLines.join(" ");

  let role = "user", goal = "", benefit = "";
  const m = storyText.match(ROLE_RE);
  if (m) {
    role = clean(m[1]) || role;
    goal = clean(m[2]);
    benefit = clean(m[3]);
  }

  const criteria = [];
  let inAc = false;
  for (const line of lines) {
    const s = line.trim();
    if (AC_HEADER_RE.test(s)) { inAc = true; continue; }
    if (!inAc) continue;
    if (HEADER_RE.test(s)) break;
    const bm = s.match(BULLET_RE);
    if (bm) {
      const c = clean(bm[1] || bm[3] || "");
      if (c) criteria.push(c);
    } else if (s === "" || s.startsWith(">")) {
      continue;
    } else if (criteria.length) {
      break;
    }
  }
  return { title, role, goal, benefit, criteria };
}

function scenarioName(criterion) {
  return clean(criterion).replace(/^(when|then|and|given)\s+/i, "").slice(0, 90);
}

function detectEnumeration(criterion) {
  const m = criterion.match(ENUM_RE);
  if (!m) return null;
  const items = m[1].split(/,|\band\b|\bor\b|\//).map(i => i.trim().replace(/^["']|["']$/g, "")).filter(i => i && i.length <= 25);
  if (items.length >= 2 && items.length <= 6) return { full: m[0], items };
  return null;
}

function stepsFor(role, goal, criterion) {
  const given = `a "${role}" is using the system`;
  const wt = criterion.trim().match(WHEN_THEN_RE);
  if (wt) return [given, lowerFirst(clean(wt[1])), lowerFirst(clean(wt[2]))];
  let action = lowerFirst(goal) || "performs the action";
  action = action.replace(/^to\s+/, "").replace(/\bmy\b/g, "their");
  return [given, `the ${role} tries to ${action}`, lowerFirst(clean(criterion))];
}

function negativeScenarios(role, criteria) {
  const out = [];
  const text = criteria.join(" ").toLowerCase();
  const has = (...ks) => ks.some(k => text.includes(k));
  if (has("valid", "invalid", "error", "required", "format", "empty")) {
    out.push({ name: "Validation - invalid input is rejected", steps: [
      ["Given", `a "${role}" is using the system`],
      ["When", "the user submits invalid input"],
      ["Then", "a clear validation error is displayed"],
      ["And", "no data is saved"],
    ]});
  }
  if (has("login", "auth", "permission", "role", "access", "token")) {
    out.push({ name: "Security - unauthorized access is denied", steps: [
      ["Given", `a "${role}" is using the system`],
      ["When", "the user attempts the action without valid credentials"],
      ["Then", "access is denied"],
      ["And", "a 401 or 403 response is returned"],
    ]});
  }
  if (has("not found", "missing", "deleted", "unknown")) {
    out.push({ name: "Not found - missing resource is handled", steps: [
      ["Given", `a "${role}" is using the system`],
      ["When", "the user requests a resource that does not exist"],
      ["Then", "a not-found message is displayed"],
    ]});
  }
  return out;
}

function buildFeature(parsed) {
  const role = parsed.role || "user";
  const goal = parsed.goal || "";
  const benefit = parsed.benefit || "";
  const criteria = parsed.criteria || [];
  const storyLines = [`As a ${role}`];
  if (goal) storyLines.push(`I want ${goal}`);
  if (benefit) storyLines.push(`So that ${benefit}`);
  const feature = {
    title: parsed.title || "Generated Feature",
    storyLines,
    background: [["Given", `a "${role}" is using the system`]],
    scenarios: [],
  };
  if (!criteria.length && goal) {
    let action = lowerFirst(goal).replace(/^to\s+/, "").replace(/\bmy\b/g, "their");
    feature.scenarios.push({ name: `Happy path - ${action}`, steps: [
      ["Given", `a "${role}" is using the system`],
      ["When", `the ${role} tries to ${action}`],
      ["Then", "the expected outcome is achieved"],
    ]});
  }
  criteria.forEach((criterion, idx) => {
    const [given, when, then] = stepsFor(role, goal, criterion);
    const steps = [["Given", given], ["When", when], ["Then", then]];
    const en = detectEnumeration(criterion);
    if (en) {
      const name = scenarioName(criterion.replace(en.full, "<value>"));
      feature.scenarios.push({
        name: `AC${idx + 1} - ${name}`,
        steps: steps.map(([kw, t]) => [kw, t.split(en.full).join("<value>")]),
        examples: { headers: ["value"], rows: en.items.map(i => [i]) },
      });
    } else {
      feature.scenarios.push({ name: `AC${idx + 1} - ${scenarioName(criterion)}`, steps });
    }
  });
  feature.scenarios.push(...negativeScenarios(role, criteria));
  return feature;
}

function renderGherkin(feature) {
  const lines = [`Feature: ${feature.title}`];
  feature.storyLines.forEach(s => lines.push(`  ${s}`));
  lines.push("", "  Background:");
  feature.background.forEach(([kw, t]) => lines.push(`    ${kw} ${t}`));
  lines.push("");
  for (const sc of feature.scenarios) {
    lines.push(`  ${sc.examples ? "Scenario Outline" : "Scenario"}: ${sc.name}`);
    sc.steps.forEach(([kw, t]) => lines.push(`    ${kw} ${t}`));
    if (sc.examples) {
      lines.push("", "    Examples:");
      lines.push("      | " + sc.examples.headers.join(" | ") + " |");
      sc.examples.rows.forEach(r => lines.push("      | " + r.join(" | ") + " |"));
    }
    lines.push("");
  }
  return lines.join("\n").replace(/\s+$/, "") + "\n";
}

function renderJson(feature) {
  return JSON.stringify({
    feature: feature.title,
    story: feature.storyLines,
    background: feature.background.map(([keyword, text]) => ({ keyword, text })),
    scenarios: feature.scenarios.map(s => ({
      name: s.name,
      type: s.examples ? "outline" : "scenario",
      steps: s.steps.map(([keyword, text]) => ({ keyword, text })),
      ...(s.examples ? { examples: s.examples } : {}),
    })),
  }, null, 2) + "\n";
}

function renderMarkdown(feature) {
  const lines = [`# Test Plan: ${feature.title}`, ""];
  if (feature.storyLines.length) {
    lines.push("## User Story", "");
    feature.storyLines.forEach(s => lines.push(`> ${s}`));
    lines.push("");
  }
  lines.push("## Background", "");
  feature.background.forEach(([kw, t]) => lines.push(`- **${kw}** ${t}`));
  lines.push("", "## Scenarios", "");
  feature.scenarios.forEach((s, i) => {
    lines.push(`### ${i + 1}. ${s.examples ? "Scenario Outline" : "Scenario"}: ${s.name}`, "");
    s.steps.forEach(([kw, t]) => lines.push(`- **${kw}** ${t}`));
    if (s.examples) {
      lines.push("", "| " + s.examples.headers.join(" | ") + " |",
        "|" + s.examples.headers.map(() => "---").join("|") + "|");
      s.examples.rows.forEach(r => lines.push("| " + r.join(" | ") + " |"));
    }
    lines.push("");
  });
  return lines.join("\n").replace(/\s+$/, "") + "\n";
}

function analyzeCoverage(feature) {
  const negRe = /invalid|unauthorized|denied|not.?found|rejected|error|expired|locked/i;
  const negatives = feature.scenarios.filter(s => negRe.test(s.name));
  const outlines = feature.scenarios.filter(s => s.examples);
  const warnings = [];
  if (!negatives.length) warnings.push("No negative scenarios — add validation/error criteria for stronger coverage.");
  if (!outlines.length) warnings.push("No Scenario Outlines — enumerate values like (admin, user, guest) to get data-driven cases.");
  return {
    total: feature.scenarios.length,
    positive: feature.scenarios.length - negatives.length,
    negative: negatives.length,
    outlines: outlines.length,
    warnings,
  };
}

function lintGherkin(text) {
  const issues = [];
  const lines = text.split("\n");
  if (!lines.some(l => l.startsWith("Feature:"))) issues.push("Missing 'Feature:' line");
  let current = null, seen = null, section = null;
  const names = [];
  const close = () => {
    if (!current) return;
    ["Given", "When", "Then"].forEach(kw => {
      if (!seen[kw]) issues.push(`Scenario '${current}' is missing a ${kw} step`);
    });
  };
  for (const ln of lines) {
    const s = ln.trim();
    const m = s.match(/^(Scenario(?: Outline)?):\s*(.*)$/);
    if (m) {
      close();
      current = m[2].trim() || "<unnamed>";
      names.push(current);
      seen = { Given: false, When: false, Then: false };
      section = null;
      if (!m[2].trim()) issues.push("Found a scenario with an empty name");
      continue;
    }
    const km = s.match(/^(Given|When|Then|And|But)\b(.*)$/);
    if (km && current) {
      const kw = km[1], rest = km[2].trim();
      if (kw === "Given" || kw === "When" || kw === "Then") { section = kw; seen[kw] = true; }
      else if (!section) issues.push(`Scenario '${current}': '${kw}' step with no preceding Given/When/Then`);
      if (!rest) issues.push(`Scenario '${current}': empty '${kw}' step`);
    }
  }
  close();
  [...new Set(names)].forEach(n => {
    if (names.filter(x => x === n).length > 1) issues.push(`Duplicate scenario name: '${n}'`);
  });
  if (!names.length) issues.push("No scenarios found");
  return issues;
}

function generateFromText(text, fmt) {
  const feature = buildFeature(parseStory(text));
  const out = fmt === "json" ? renderJson(feature) : fmt === "markdown" ? renderMarkdown(feature) : renderGherkin(feature);
  return { out, feature };
}

if (typeof module !== "undefined") module.exports = { parseStory, buildFeature, renderGherkin, renderJson, renderMarkdown, analyzeCoverage, lintGherkin, generateFromText };
