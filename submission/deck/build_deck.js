// Build submission/deck/Solution_Presentation.pptx (16:9, 10" x 5.625")
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/47e94113-deee-4c3b-b676-a75959829b91_d0e1b3df-c4b4-4040-9b02-75e2b4b4f2f0/pptx/scripts/apply_theme.js");

const REPO = "/home/user/adb-ivan";
const OUT = path.join(REPO, "submission/deck/Solution_Presentation.pptx");
const SCALING = fs.existsSync(path.join(REPO, "docs/SCALING.md")) && fs.existsSync(path.join(REPO, "results/scaling.png"));

const THEME = {
  name: "Joint Tail",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A2230", lt1: "FFFFFF", dk2: "1F3247", lt2: "EEF2F5",
    accent1: "C8611A", accent2: "2F7F8A", accent3: "8C97A8", accent4: "F4E3D3",
    accent5: "D9E8EA", accent6: "5A6B7D", hlink: "2F7F8A", folHlink: "6A5A8C",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Importance-Weighted Amplitude Estimation for the Rare Joint Tail";
pres.subject = "ADB Quantum Innovation Challenge 2026, Phase 1";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const FOOT = "ADB Quantum Innovation Challenge 2026  ·  Phase 1";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: THEME.colors.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.0, w: 5.5, h: 2.15, fontSize: 30, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 3.35, w: 5.5, h: 0.5, fontSize: 16, color: C.accent5, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75, fontSize: 28, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.5, y: 5.2, w: 6.5, h: 0.25, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.25, fontSize: 10, color: THEME.colors.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: THEME.colors.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.45, w: 8.8, h: 0.8, fontSize: 30, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
  ],
});

// ---------------------------------------------------------------- helpers
const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, color: C.text1, fontSize: 16, valign: "top" }, o));
function card(s, x, y, w, h, name, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name });
}
function stat(s, x, y, w, big, label, name, bigSize) {
  T(s, big, { x, y, w, h: 0.75, fontSize: bigSize || 36, bold: true, color: C.accent1, fontFace: THEME.headFontFace, valign: "bottom", objectName: name + " value" });
  T(s, label, { x, y: y + 0.8, w, h: 0.75, fontSize: 14, color: C.text1, objectName: name + " label" });
}
function bullets(s, items, o) {
  const arr = items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: 8 } }));
  return s.addText(arr, Object.assign({ isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top" }, o));
}
function dot(s, x, y, d, label, name, fill) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill || C.accent2 }, line: { color: fill || C.accent2, width: 0 }, objectName: name });
  T(s, label, { x, y, w: d, h: d, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", objectName: name + " number" });
}
function rings(s, cx, cy, r, name) { // motif: two overlapping hazard footprints
  s.addShape(pres.shapes.OVAL, { x: cx - r * 1.55, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: C.accent2, transparency: 35 }, line: { color: C.accent5, width: 1 }, objectName: name + " ring A" });
  s.addShape(pres.shapes.OVAL, { x: cx - r * 0.45, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: C.accent1, transparency: 35 }, line: { color: C.accent4, width: 1 }, objectName: name + " ring B" });
}

// ---------------------------------------------------------------- 1 title
pres.addSection({ title: "Proposal" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Proposal" });
s.addText("Importance-Weighted Amplitude Estimation for the Rare Joint Tail of Disaster Relief Bonds", { placeholder: "title" });
s.addText("ADB Quantum Innovation Challenge 2026  ·  Phase 1", { placeholder: "body" });
T(s, "Qubit Happens", { x: 0.6, y: 4.15, w: 5.5, h: 0.4, fontSize: 18, bold: true, color: C.accent4, objectName: "team name" });
T(s, "Team ID 6746", { x: 0.6, y: 4.6, w: 5.5, h: 0.4, fontSize: 14, color: C.accent5, objectName: "team id" });
rings(s, 8.1, 2.75, 1.1, "title motif");
T(s, "joint tail", { x: 7.5, y: 2.55, w: 1.0, h: 0.4, fontSize: 14, italic: true, color: C.background1, align: "center", valign: "middle", objectName: "motif label" });
s.addNotes("Title. Two overlapping footprints: the Kyrgyz Republic and Tajikistan bonds. The overlap, where both are hit, is the joint tail we estimate.");

// ---------------------------------------------------------------- 2 problem
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Proposal" });
s.addText("Pooling and triggers hinge on the joint tail", { placeholder: "title" });
bullets(s, [
  "ADB's US$160m Disaster Relief Bonds cover the Kyrgyz Republic and Tajikistan (2026)",
  "Shared fault lines: one seismic episode can hit both bonds",
  "Whether pooling saves money, and whether triggers pay when damage occurs, depends on how extremes co-move",
  "History is too short to estimate this tail, so it must be simulated",
], { x: 0.5, y: 1.35, w: 5.1, h: 3.6, objectName: "problem bullets" });
card(s, 6.0, 1.35, 3.5, 3.55, "tail stat card");
stat(s, 6.3, 1.55, 2.95, "3 in 100,000", "chance that both bonds are exhausted within one 3-year term (exact 3.2 × 10⁻⁵)", "tail stat", 30);
stat(s, 6.3, 3.25, 2.95, "69%", "relative error of plain Monte Carlo after 65,000 simulated terms", "mc stat", 30);
s.addNotes("The brief locates the bottleneck exactly here: accuracy on the rare joint tail at a fixed budget, getting worse as portfolios grow.");

// ---------------------------------------------------------------- 3 benchmark
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Proposal" });
s.addText("An exact reference and six classical baselines", { placeholder: "title" });
card(s, 0.5, 1.35, 3.9, 3.55, "reference card", C.accent5);
T(s, "Exact reference model", { x: 0.75, y: 1.55, w: 3.4, h: 0.4, fontSize: 18, bold: true, color: C.text2, objectName: "reference heading" });
bullets(s, [
  "Reproduces all 25 values of the brief's Table 5",
  "100 annual states, 10⁶ three-year paths",
  "Ground truth for every error we report",
], { x: 0.75, y: 2.1, w: 3.45, h: 2.6, objectName: "reference bullets" });
const base = [["Monte Carlo", "brief"], ["Scrambled Sobol", "brief"], ["Stratified", "brief"], ["Importance sampling", "brief"], ["Importance, loss² tilt", "added"], ["Stratified IS", "added"]];
base.forEach(([name, tag], i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = 4.75 + col * 2.4, y = 1.35 + row * 1.05;
  card(s, x, y, 2.25, 0.9, "baseline " + name, tag === "added" ? C.accent4 : C.background2);
  T(s, name, { x: x + 0.15, y: y + 0.12, w: 1.95, h: 0.4, fontSize: 16, bold: true, color: C.text1, objectName: "baseline name " + i });
  T(s, tag === "added" ? "added: stronger" : "from the brief", { x: x + 0.15, y: y + 0.52, w: 1.95, h: 0.3, fontSize: 12, color: C.accent6, objectName: "baseline tag " + i });
});
s.addNotes("We added two classical baselines that beat the brief's four on several targets, so the quantum method is compared against the strongest classical method per target.");

// ---------------------------------------------------------------- 4 method
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Proposal" });
s.addText("Amplitude estimation: error falls as 1/M, not 1/√M", { placeholder: "title" });
const steps = [
  ["Load", "Encode the 3-year joint loss law p(x) in amplitudes (8 qubits per year)"],
  ["Compute", "Reversible adders, caps and flags set one objective qubit to the payoff"],
  ["Estimate", "Iterative QAE reads the amplitude with a confidence interval"],
];
steps.forEach(([h, d], i) => {
  const x = 0.5 + i * 3.05;
  dot(s, x, 1.45, 0.55, String(i + 1), "step " + (i + 1));
  T(s, h, { x: x + 0.7, y: 1.5, w: 2.1, h: 0.45, fontSize: 20, bold: true, color: C.text2, valign: "middle", objectName: "step heading " + i });
  T(s, d, { x, y: 2.15, w: 2.8, h: 1.3, fontSize: 16, color: C.text1, objectName: "step text " + i });
  if (i < 2) T(s, "→", { x: x + 2.75, y: 1.45, w: 0.3, h: 0.55, fontSize: 22, color: C.accent3, align: "center", valign: "middle", objectName: "arrow " + i });
});
card(s, 0.5, 3.7, 9.0, 1.2, "iqae card", C.accent5);
T(s, [
  { text: "Iterative QAE replaces the prototype's fixed-schedule MLAE. ", options: { bold: true } },
  { text: "The 15% error plateau on the rare tail disappears, and confidence intervals hold in 95–100% of runs." },
], { x: 0.75, y: 3.85, w: 8.5, h: 0.9, fontSize: 16, valign: "middle", objectName: "iqae text" });
s.addNotes("Classical sampling error shrinks as one over the square root of the samples; amplitude estimation as one over the number of oracle calls.");

// ---------------------------------------------------------------- 5 contribution
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Proposal" });
s.addText("Our contribution: importance-weighted QAE", { placeholder: "title" });
bullets(s, [
  "Load a proposal q tilted toward heavy-loss years; rotate the objective qubit by the path weight p/q",
  "The encoded amplitude grows from a to a/W, so relative error per query falls by √(1/W)",
  "Grid-snapped proposal: weights are exact in a 6-qubit register, so the estimate is unbiased",
], { x: 0.5, y: 1.35, w: 5.4, h: 2.6, objectName: "contribution bullets" });
card(s, 6.25, 1.35, 3.25, 2.55, "gain card");
stat(s, 6.5, 1.5, 2.8, "2.6–4×", "lower error per query on tail targets, before any extra hardware", "gain stat", 40);
T(s, [
  { text: "Tested and rejected: ", options: { bold: true } },
  { text: "stratifying by payout years (≈1× for QAE) and per-year weights (≤0.5×). QAE pays for the worst-case weight, not the average." },
], { x: 0.5, y: 4.15, w: 9.0, h: 0.8, fontSize: 14, color: C.accent6, objectName: "negative results" });
s.addNotes("The gain is computed exactly: sqrt(1/W) is 2.6 with the brief's proposal and 4.0 with a loss-squared tilt on the both-exhausted target.");

// ---------------------------------------------------------------- 6 results
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
s.addText("Rare joint tail: 4–9× more accurate at equal budget", { placeholder: "title" });
const hdr = { bold: true, color: "FFFFFF", fill: { color: "1F3247" }, fontSize: 14 };
const rows = [
  [{ text: "Scenario", options: hdr }, { text: "Budget", options: Object.assign({}, hdr, { align: "right" }) }, { text: "IW-IQAE", options: Object.assign({}, hdr, { align: "right" }) }, { text: "Best classical", options: Object.assign({}, hdr, { align: "right" }) }],
  ["base", "58k", "1.8%", "11.7%"],
  ["independent", "223k", "1.7%", "14.9%"],
  ["common shock", "65k", "1.3%", "11.7%"],
  ["rain stress", "65k", "1.5%", "7.2%"],
  ["rain cover", "56k", "1.8%", "14.2%"],
].map((r, i) => i === 0 ? r : r.map((c, j) => ({ text: c, options: { fontSize: 14, color: j === 2 ? "C8611A" : "1A2230", bold: j === 2, align: j === 0 ? "left" : "right" } })));
s.addTable(rows, { x: 0.5, y: 1.35, w: 4.4, colW: [1.45, 0.85, 0.95, 1.15], rowH: 0.42, border: { type: "solid", pt: 0.75, color: "D5DCE3" }, fill: { color: "FFFFFF" }, margin: [0, 0.08, 0, 0.08], valign: "middle", objectName: "equal budget table" });
T(s, "Relative RMSE on both-bonds-exhausted. Best classical is importance sampling in every scenario.", { x: 0.5, y: 4.0, w: 4.4, h: 0.8, fontSize: 12, color: C.accent6, objectName: "table caption" });
s.addImage({ path: path.join(REPO, "submission/deck/assets/rare_tail.png"), x: 5.15, y: 1.3, w: 4.35, h: 3.1, altText: "Relative error versus budget for the both-bonds-exhausted target", objectName: "rare tail chart" });
T(s, "adb-base: quantum = exact statistics of ideal circuits", { x: 5.15, y: 4.45, w: 4.35, h: 0.3, fontSize: 12, color: C.accent6, objectName: "chart caption" });
s.addNotes("Every method gets the same mean budget: classical paths versus oracle calls. Quantum numbers are emulated from the verified measurement law, not hardware.");

// ---------------------------------------------------------------- 7 honesty
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
s.addText("Where classical methods still win", { placeholder: "title" });
s.addChart(pres.charts.BAR, [
  { name: "IW-IQAE (ours)", labels: ["Both exhausted", "Pr(L > 80m)", "Stop-loss", "Both pay", "Expected loss"], values: [1.8, 1.7, 1.9, 2.2, 2.2] },
  { name: "Best classical", labels: ["Both exhausted", "Pr(L > 80m)", "Stop-loss", "Both pay", "Expected loss"], values: [11.7, 4.5, 3.9, 2.8, 0.5] },
], { x: 0.5, y: 1.3, w: 5.75, h: 3.4, barDir: "bar", barGrouping: "clustered", barGapWidthPct: 60,
  chartColors: ["C8611A", "8C97A8"], showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: "1A2230",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt", dataLabelColor: "1A2230", dataLabelFormatCode: "0.0\"%\"",
  catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: "1A2230", catAxisOrientation: "maxMin",
  valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
  showTitle: true, title: "Relative RMSE at equal budget, adb-base (lower is better)", titleFontSize: 12, titleFontFace: "+mn-lt", titleColor: "5A6B7D",
  objectName: "equal budget chart" });
bullets(s, [
  "Expected loss: stratified importance sampling 0.5% vs our 2.2% at the same budget",
  "Both countries pay (4.4%): close, 2.2% vs 2.8%",
  "The quantum gain concentrates in the rare tail, where the brief locates the bottleneck",
], { x: 6.55, y: 1.35, w: 2.95, h: 3.6, fontSize: 16, objectName: "honesty bullets" });
s.addNotes("We report where we lose. Smooth, common targets are well served by stratified importance sampling and Sobol points.");

// ---------------------------------------------------------------- 8 resources
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
s.addText("Resource estimate: built, verified, costed", { placeholder: "title" });
const R = [
  ["39 qubits", "850 two-qubit gates for one plain oracle"],
  ["6,494", "two-qubit gates in one Grover step"],
  ["52 qubits", "importance-weighted oracle"],
  ["63k vs 204k", "queries to ~2% error: weighted vs plain"],
  ["334 vs 1,331", "longest Grover power: weighted vs plain"],
  ["4.1 vs 4.2 bn", "T gates: weighted (QROM, projected) vs plain"],
];
R.forEach(([b, l], i) => {
  const col = i % 3, row = Math.floor(i / 3);
  const x = 0.5 + col * 3.05, y = 1.3 + row * 1.42;
  card(s, x, y, 2.85, 1.27, "resource card " + i);
  T(s, b, { x: x + 0.18, y: y + 0.1, w: 2.5, h: 0.55, fontSize: 24, bold: true, color: C.accent1, fontFace: THEME.headFontFace, valign: "bottom", objectName: "resource value " + i });
  T(s, l, { x: x + 0.18, y: y + 0.7, w: 2.55, h: 0.5, fontSize: 13, color: C.text1, objectName: "resource label " + i });
});
T(s, [
  { text: "Verified: ", options: { bold: true } },
  { text: "arithmetic bit-simulated on all 10⁶ paths. Not feasible on today's NISQ devices; fault-tolerant target. Trapped-ion preferred near term (heavy-hex routing adds 2.7× gates)." },
], { x: 0.5, y: 4.2, w: 9.0, h: 0.8, fontSize: 14, color: C.text1, objectName: "resource note" });
s.addNotes("Counts from Qiskit 2.6.2 transpilation to CX plus single-qubit gates, all-to-all connectivity. T-counts use Ross-Selinger synthesis; the QROM line is a projection, not built.");

// ---------------------------------------------------------------- 9 scaling
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
s.addText("Scaling to larger portfolios", { placeholder: "title" });
if (SCALING) {
  s.addImage({ path: path.join(REPO, "results/scaling.png"), x: 0.5, y: 1.3, w: 5.4, h: 3.4, altText: "Scaling results", objectName: "scaling chart" });
}
const scaleItems = [
  ["Linear oracle", "4n + 7 qubits, ~70 CX per country (built and verified)"],
  ["Rarer tail", "P(all exhausted): 3.2e-5 at n\u00a0=\u00a02, 3.2e-10 at n\u00a0=\u00a020"],
  ["Cost at n\u00a0=\u00a020", "10% error: 3.1e11 MC samples vs 8.5e6 QAE calls"],
];
scaleItems.forEach(([h, d], i) => {
  const x0 = SCALING ? 6.2 : 0.5, w0 = SCALING ? 3.3 : 9.0;
  const y = 1.35 + i * 1.12;
  dot(s, x0, y, 0.5, String(i + 1), "scale step " + i, C.accent2);
  T(s, [{ text: h + ": ", options: { bold: true, color: C.text2 } }, { text: d }], { x: x0 + 0.65, y: y - 0.02, w: w0 - 0.65, h: 1.0, fontSize: 16, objectName: "scale text " + i });
});
if (!SCALING) T(s, "Numbers and the n-country model are in the technical proposal.", { x: 0.5, y: 4.75, w: 9.0, h: 0.3, fontSize: 12, italic: true, color: C.accent6, objectName: "scaling note" });
s.addNotes("Evaluation criterion two. The model generalises exactly to n countries given one regional shock factor (matches Table 5 at n = 2 to 5e-14). The oracle grows linearly: 4n + 7 qubits and about 70 CX per country. The all-exhausted tail falls from 3.2e-5 to 3.2e-10 by n = 20, where Monte Carlo needs about 37,000 times more samples than QAE needs oracle calls. Honest boundary: for one factor, classical conditional calculation is also exact; quantum matters for many-factor or data-driven dependence.");

// ---------------------------------------------------------------- 10 phase 2
pres.addSection({ title: "Plan and impact" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Plan and impact" });
s.addText("Phase 2: eight weeks to a tested prototype", { placeholder: "title" });
const plan = [
  ["Weeks 1–2", "Unary-iteration QROM and ancilla-assisted reflection; full fault-tolerant estimate"],
  ["Weeks 3–4", "n-country generator and tensor-network references for n ≥ 5; GPU classical baselines"],
  ["Weeks 5–6", "Noisy simulation on QAI GPU credits; small-k hardware demo with error mitigation"],
  ["Weeks 7–8", "Official benchmark incl. World Bank loss tables; final report, docs and demo"],
];
s.addShape(pres.shapes.LINE, { x: 0.8, y: 1.9, w: 8.4, h: 0, line: { color: C.accent3, width: 1.5 }, objectName: "timeline axis" });
plan.forEach(([w, d], i) => {
  const x = 0.5 + i * 2.3;
  dot(s, x + 0.05, 1.62, 0.55, String(i + 1), "milestone " + (i + 1), C.accent1);
  T(s, w, { x, y: 2.35, w: 2.1, h: 0.4, fontSize: 18, bold: true, color: C.text2, objectName: "milestone weeks " + i });
  T(s, d, { x, y: 2.8, w: 2.1, h: 2.1, fontSize: 15, color: C.text1, objectName: "milestone text " + i });
});
s.addNotes("Each milestone closes a gap we list in the proposal: lookup cost, reflection cost, scaling evidence, hardware evidence and coverage of the official benchmark.");

// ---------------------------------------------------------------- 11 impact
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Plan and impact" });
s.addText("Who uses it and why it matters", { placeholder: "title" });
const cols = [
  ["Users", ["MDB treasuries pricing disaster bonds (ADB, World Bank)", "Regional pools: CCRIF, ARC, PCRIC, SEADRIF", "Reinsurers, ILS funds, cat-model vendors"]],
  ["Impact", ["OP3 climate and disaster resilience; OP7 regional cooperation", "Better-priced pooled cover and triggers that pay when damage occurs", "Same engine for credit, systemic and operational tail risk"]],
];
cols.forEach(([h, items], i) => {
  const x = 0.5 + i * 4.6;
  card(s, x, 1.35, 4.4, 3.6, "impact card " + i, i === 0 ? C.background2 : C.accent5);
  T(s, h, { x: x + 0.25, y: 1.5, w: 3.9, h: 0.45, fontSize: 20, bold: true, color: C.text2, objectName: "impact heading " + i });
  bullets(s, items, { x: x + 0.25, y: 2.05, w: 3.9, h: 2.8, fontSize: 16, objectName: "impact bullets " + i });
});
s.addNotes("Commercial path: a risk-analytics engine and benchmark that plugs into existing catastrophe-model outputs, licensed to issuers, pools and reinsurers.");

// ---------------------------------------------------------------- 12 team
s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Plan and impact" });
s.addText("Team and prototype", { placeholder: "title" });
T(s, "Qubit Happens  ·  Team ID 6746", { x: 0.6, y: 1.45, w: 5.2, h: 0.45, fontSize: 20, bold: true, color: C.accent4, objectName: "closing team name" });
T(s, [{ text: "Ivan Cheong", options: { breakLine: true } }, { text: "Tan Boon Xuan", options: { breakLine: true } }, { text: "Loh Shi Lynn" }], { x: 0.6, y: 1.95, w: 5.2, h: 1.0, fontSize: 16, color: C.background1, objectName: "closing team members" });
T(s, "Reproducible prototype", { x: 0.6, y: 3.15, w: 5.2, h: 0.35, fontSize: 16, bold: true, color: C.accent5, objectName: "repo heading" });
T(s, "github.com/legaxy6-repo/adb-ivan", { x: 0.6, y: 3.53, w: 5.2, h: 0.35, fontSize: 16, color: C.background1, hyperlink: { url: "https://github.com/legaxy6-repo/adb-ivan" }, objectName: "repo url" });
T(s, "AI use: code, benchmarks and documents were drafted with assistance from Claude (Anthropic). The authors are responsible for reviewing and verifying them.", { x: 0.6, y: 4.2, w: 8.8, h: 0.7, fontSize: 12, color: C.accent5, objectName: "ai disclosure" });
rings(s, 8.1, 2.35, 0.95, "closing motif");
s.addNotes("All results reproduce with run_benchmarks_v2.py, make_plots_v2.py and resources/build_circuits.py; seed 2026.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT, "scaling:", SCALING);
})();
