/* Requirement quality analysis — browser port of src/quality.py. */
const VAGUE_WORDS = [
  "fast",
  "quick",
  "quickly",
  "slow",
  "user-friendly",
  "user friendly",
  "intuitive",
  "easy",
  "easily",
  "simple",
  "robust",
  "efficient",
  "efficiently",
  "seamless",
  "seamlessly",
  "adequate",
  "appropriate",
  "relevant",
  "timely",
  "timely manner",
  "nice",
  "good",
  "great",
  "large",
  "small",
  "many",
  "several",
  "various",
  "etc",
  "asap",
  "performant",
  "scalable",
  "reliable",
  "securely-ish"
];
const WEASEL_PHRASES = [
  "etc.",
  "and so on",
  "as needed",
  "if necessary",
  "where appropriate",
  "tbd",
  "to be determined",
  "should work",
  "must work properly"
];

function analyzeQuality(parsed) {
  const findings = [];
  let score = 100;
  const penalize = (pts, code, message, suggestion) => {
    score -= pts;
    findings.push({ code, severity: pts >= 15 ? "high" : "medium", message, suggestion });
  };
  const hits = (text, words) => {
    const low = text.toLowerCase();
    return [...new Set(words.filter(w => low.includes(w.toLowerCase())))];
  };
  if (!parsed.role || parsed.role === "user") penalize(10, "missing_actor",
    "No explicit actor found; defaulted to a generic 'user'.",
    "Start with 'As a <specific role>, ...'.");
  if (!parsed.goal) penalize(15, "missing_goal", "No clear goal ('I want ...') found.",
    "Add 'I want <capability>' so the intent is explicit.");
  if (!parsed.benefit) penalize(5, "missing_benefit", "No 'So that ...' benefit statement.",
    "Add the business value: 'So that <outcome>'.");
  const criteria = parsed.criteria || [];
  if (!criteria.length) penalize(20, "no_criteria",
    "No acceptance criteria found — nothing concrete to generate tests from.",
    "Add an 'Acceptance Criteria:' section with one bullet per expected behavior.");
  else if (criteria.length < 3) penalize(5, "few_criteria",
    `Only ${criteria.length} acceptance criterion/criteria — edge cases are likely uncovered.`,
    "Aim for 3+ criteria covering happy path, validation, and errors.");
  const storyText = [parsed.role, parsed.goal, parsed.benefit, ...criteria].join(" ");
  const vague = hits(storyText, VAGUE_WORDS);
  if (vague.length) penalize(Math.min(20, 5 * vague.length), "vague_language",
    `Untestable adjectives/adverbs: ${vague.join(", ")}.`,
    "Replace each with a number ('within 2 seconds', 'at least 8 characters').");
  const weasels = hits(storyText, WEASEL_PHRASES);
  if (weasels.length) penalize(10, "weasel_phrases",
    `Hand-wavy phrases: ${weasels.join(", ")}.`,
    "Spell out the exact expected behavior instead.");
  score = Math.max(0, score);
  const grade = score >= 90 ? "A" : score >= 75 ? "B" : score >= 60 ? "C" : score >= 40 ? "D" : "F";
  return { score, grade, findings, summary: `${score}/100 (grade ${grade}) — ${findings.length} findings` };
}

// minimal story parser for the demo (mirrors rule_engine parsing)
function parseStoryLite(text) {
  const lines = text.trim().split("\n").map(l => l.replace(/\s+$/, ""));
  const title = (lines[0] || "").replace(/^#+\s*/, "").trim() || "Generated Feature";
  const m = text.match(/as an?\s+([^,]+?),\s*i want\s+(.+?)(?:,?\s*so that\s+(.+))?\s*$/im);
  const criteria = [];
  let inAc = false;
  for (const line of lines) {
    const s = line.trim();
    if (/^#{0,3}\s*acceptance criteria\b/i.test(s)) { inAc = true; continue; }
    if (!inAc) continue;
    const bm = s.match(/^(?:[-*•]\s+|\d+[.)]\s+)(.+)$/);
    if (bm) criteria.push(bm[1].trim());
  }
  return { title, role: (m && m[1].trim()) || "user", goal: (m && m[2].trim()) || "",
           benefit: (m && m[3] || "").trim(), criteria };
}

if (typeof module !== "undefined") module.exports = { analyzeQuality, parseStoryLite, VAGUE_WORDS, WEASEL_PHRASES };
