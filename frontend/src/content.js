// Everything the site says, in one place. To change a text, a status or a rule,
// edit this file: the components only decide how it looks.

export const LINKS = {
  api: "https://veloce-decision-service.onrender.com/docs",
  code: "https://github.com/saroatov2910/welos-ai",
};

export const NAV = [
  { label: "Product", href: "#promises" },
  { label: "How it works", href: "#how" },
  { label: "Pipeline", href: "#pipeline" },
  { label: "Live API", href: LINKS.api },
];

export const HERO = {
  badge: "On-prem fraud gatekeeper",
  title: "Stop card fraud before the receipt prints.",
  lead: "Veloce AI runs inside the store or bank network and decides on every card transaction in under 15 ms. Card numbers never leave the building.",
};

// status: "live" or "planned". label is the text on the badge.
export const PROMISES = [
  {
    icon: "server",
    title: "Runs on-prem",
    status: "live",
    label: "Live",
    text: "Hardened container, running on Kubernetes (k3s): non-root, read-only filesystem.",
  },
  {
    icon: "bolt",
    title: "Under 15 ms",
    status: "live",
    label: "Live",
    text: "Local rules, no network calls in the decision path.",
  },
  {
    icon: "lock",
    title: "Data stays inside",
    status: "live",
    label: "Live",
    text: "Network policy blocks all outbound traffic. Local audit log, masked card numbers, CVV never stored.",
  },
  {
    icon: "shield",
    title: "AI-reviewed rules",
    status: "planned",
    label: "Planned",
    text: "An AI reviewer reads each rule change and flags critical issues. Built, not yet a pipeline gate.",
  },
  {
    icon: "phone",
    title: "Control from phone",
    status: "live",
    label: "Blocking live",
    text: "Risky cards are blocked automatically; the security manager can block or release a card through the API. Phone alerts are planned.",
  },
];

export const STEPS = [
  { title: "API key", text: "Only registered stores can ask." },
  { title: "Validation", text: "Luhn check, CVV, expiry, amount, timezone." },
  { title: "Blocklist", text: "Blocked cards are rejected at once, matched by an HMAC, never by the number." },
  { title: "Risk score", text: "Rules add points from 0 to 100." },
  { title: "Decision", text: "Accept, review or reject. A score of 90+ blocks the card for 24 hours." },
  { title: "Audit", text: "Written to a local, append-only log." },
];

// Must match calculate_risk_score_and_reasons in services/decision-service/app/services.py.
export const RISK_RULES = [
  { rule: "Extremely high amount", when: "3,000 and above", points: 80 },
  { rule: "High amount", when: "1,000 to 2,999", points: 45 },
  { rule: "Elevated amount", when: "400 to 999", points: 25 },
  { rule: "Night hours", when: "00:00 to 05:00", points: 15 },
  { rule: "Round amount", when: "1,000 and above, no cents", points: 10 },
  { rule: "Rapid attempts", when: "3+ by the same customer in 10 minutes", points: 15 },
  { rule: "Very rapid attempts", when: "5+ by the same customer in 10 minutes", points: 30 },
];

export const DECISIONS = [
  { label: "0-39 accept", color: "var(--accept)" },
  { label: "40-69 review", color: "var(--review)" },
  { label: "70+ reject", color: "var(--reject)" },
];

// done: true = running today, false = on the roadmap.
export const PIPELINE = [
  { label: "Pull request", done: true },
  { label: "GitHub Actions: lint, tests, bandit, pip-audit", done: true },
  { label: "AI rule review gate", done: false },
  { label: "Merge to main", done: true },
  { label: "Jenkins: tests, gitleaks, trivy", done: true },
  { label: "Build and scan image", done: true },
  { label: "Deploy to Kubernetes (k3s)", done: true },
  { label: "Verify + automatic rollback", done: true },
];


export const DEMO_WARNING = "";
