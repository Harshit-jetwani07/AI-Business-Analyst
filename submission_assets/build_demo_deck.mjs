import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const runtimeRequire = createRequire("C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/pptxgenjs@4.0.1/node_modules/");
const pptxgen = runtimeRequire("pptxgenjs");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "BizVision AI";
pptx.company = "BizVision AI";
pptx.subject = "AI-powered analytics demo";
pptx.title = "BizVision AI Demo";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};

const C = {
  bg: "07070F",
  panel: "12122A",
  panel2: "191933",
  text: "F8FAFC",
  muted: "A6A6C8",
  purple: "7C6AF7",
  green: "10B981",
  red: "EF4444",
  amber: "F59E0B",
  line: "2A2A5A",
};

function addBg(slide) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.08, fill: { color: C.purple }, line: { color: C.purple } });
}

function title(slide, kicker, claim) {
  slide.addText(kicker.toUpperCase(), {
    x: 0.55, y: 0.35, w: 2.2, h: 0.22,
    fontFace: "Aptos", fontSize: 9, bold: true, color: C.purple,
    margin: 0, breakLine: false, fit: "shrink",
  });
  slide.addText(claim, {
    x: 0.55, y: 0.68, w: 11.8, h: 0.65,
    fontFace: "Aptos Display", fontSize: 27, bold: true, color: C.text,
    margin: 0.02, breakLine: false, fit: "shrink",
  });
}

function pill(slide, text, x, y, w, color = C.panel) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.42,
    rectRadius: 0.08,
    fill: { color },
    line: { color: C.line, transparency: 8 },
  });
  slide.addText(text, {
    x: x + 0.12, y: y + 0.105, w: w - 0.24, h: 0.18,
    fontSize: 10.5, color: C.text, bold: true, margin: 0, fit: "shrink",
  });
}

function card(slide, heading, body, x, y, w, h, accent = C.purple) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.08,
    fill: { color: C.panel },
    line: { color: C.line, transparency: 0 },
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.06, h, fill: { color: accent }, line: { color: accent } });
  slide.addText(heading, {
    x: x + 0.22, y: y + 0.22, w: w - 0.42, h: 0.25,
    fontSize: 15, bold: true, color: C.text, margin: 0, fit: "shrink",
  });
  slide.addText(body, {
    x: x + 0.22, y: y + 0.62, w: w - 0.42, h: h - 0.82,
    fontSize: 10.5, color: C.muted, valign: "top",
    breakLine: false, fit: "shrink", margin: 0.02,
  });
}

function footer(slide, n) {
  slide.addText(`BizVision AI demo | ${n}`, {
    x: 10.6, y: 7.08, w: 2.2, h: 0.2,
    fontSize: 8.5, color: C.muted, align: "right", margin: 0,
  });
}

let s = pptx.addSlide();
addBg(s);
s.addText("BizVision AI", { x: 0.65, y: 1.1, w: 8.2, h: 0.62, fontSize: 39, bold: true, color: C.text, margin: 0 });
s.addText("Business performance ko analyze karne wali intelligent vision for AI insights, forecasting, anomaly detection, admin approvals, and PDF reporting.", { x: 0.68, y: 1.95, w: 7.5, h: 0.85, fontSize: 18, color: C.muted, margin: 0.02, fit: "shrink" });
["Streamlit", "Python", "Pandas", "Plotly", "SQLite", "OpenAI / Ollama"].forEach((t, i) => pill(s, t, 0.7 + (i % 3) * 2.15, 3.2 + Math.floor(i / 3) * 0.55, 1.85));
card(s, "Demo Credentials", "Admin: admin / admin123\nUser: demouser / user123", 9.0, 1.0, 3.3, 1.7, C.green);
card(s, "Core Value", "Turns uploaded business data into decision-ready insights, governed by an admin workflow.", 9.0, 3.0, 3.3, 1.7, C.purple);
footer(s, 1);

s = pptx.addSlide();
addBg(s); title(s, "Problem", "Business users need more than static charts.");
card(s, "Manual Analysis Is Slow", "Teams spend time cleaning files, checking quality, building charts, and writing summaries.", 0.75, 1.8, 3.7, 2.0, C.red);
card(s, "Data Quality Is Unclear", "Bad dates, missing values, duplicate rows, and messy headers reduce trust in analysis.", 4.85, 1.8, 3.7, 2.0, C.amber);
card(s, "Governance Is Missing", "Most student dashboards skip user roles, approvals, audit logs, and admin monitoring.", 8.95, 1.8, 3.7, 2.0, C.purple);
card(s, "Solution", "A single AI-assisted workflow: upload, clean, score, visualize, chat, forecast, detect anomalies, report, and approve.", 1.55, 4.55, 10.2, 1.25, C.green);
footer(s, 2);

s = pptx.addSlide();
addBg(s); title(s, "Tech Stack", "The project follows the recommended stack and stays lightweight.");
const rows = [["Frontend", "Streamlit"], ["Backend", "Python"], ["AI", "OpenAI, Gemini, Groq, Ollama-ready"], ["Data", "Pandas, NumPy"], ["Charts", "Plotly"], ["ML", "scikit-learn"], ["Database", "SQLite"]];
rows.forEach((r, i) => {
  const y = 1.55 + i * 0.68;
  s.addShape(pptx.ShapeType.rect, { x: 1.35, y, w: 3.0, h: 0.48, fill: { color: C.panel }, line: { color: C.line } });
  s.addShape(pptx.ShapeType.rect, { x: 4.45, y, w: 7.3, h: 0.48, fill: { color: i % 2 ? C.panel : C.panel2 }, line: { color: C.line } });
  s.addText(r[0], { x: 1.55, y: y + 0.13, w: 2.5, h: 0.18, fontSize: 12, bold: true, color: C.text, margin: 0 });
  s.addText(r[1], { x: 4.65, y: y + 0.13, w: 6.8, h: 0.18, fontSize: 12, color: C.muted, margin: 0 });
});
footer(s, 3);

s = pptx.addSlide();
addBg(s); title(s, "User Workflow", "The user side covers the full analytics journey.");
const flow = ["Login", "Upload CSV/Excel", "Quality Score", "Overview", "Charts", "AI Chat", "Forecast", "Anomalies", "PDF Report"];
flow.forEach((f, i) => {
  const x = 0.55 + (i % 3) * 4.25;
  const y = 1.55 + Math.floor(i / 3) * 1.35;
  card(s, `${i + 1}. ${f}`, i === 1 ? "Smart loader handles messy sheets." : i === 2 ? "Missing, duplicate, date and numeric checks." : i === 5 ? "Natural-language questions over data context." : i === 8 ? "Executive report with AI-backed sections." : "Business-ready workflow step.", x, y, 3.65, 0.95, i % 2 ? C.purple : C.green);
});
footer(s, 4);

s = pptx.addSlide();
addBg(s); title(s, "Feature Depth", "Small details make the demo feel production-aware.");
card(s, "Smart Parser", "Auto header detection, blank row/column removal, horizontal matrix handling, currency/percent cleanup, date/FY parsing.", 0.7, 1.55, 3.8, 1.45, C.green);
card(s, "Quality Engine", "Score out of 100 with Good, Needs Cleaning, or Risky grade plus issue list.", 4.75, 1.55, 3.8, 1.45, C.purple);
card(s, "Safe Charts", "Plotly charts with NumPy trendline to avoid statsmodels dependency issues.", 8.8, 1.55, 3.8, 1.45, C.amber);
card(s, "AI Context Control", "AI receives dataset summary, columns, missing values, numeric stats, and sample rows instead of full raw data.", 0.7, 3.55, 3.8, 1.45, C.purple);
card(s, "Forecasting", "Future projection with MAE, RMSE, and trend direction.", 4.75, 3.55, 3.8, 1.45, C.green);
card(s, "Anomaly Detection", "Isolation Forest highlights unusual numeric business records.", 8.8, 3.55, 3.8, 1.45, C.red);
footer(s, 5);

s = pptx.addSlide();
addBg(s); title(s, "Admin Governance", "Admin panel turns the dashboard into a managed platform.");
card(s, "Identity & Auth", "Create users, validate emails, check password strength, change roles, activate/deactivate, delete users.", 0.75, 1.65, 3.8, 1.65, C.purple);
card(s, "Dataset Review", "Every uploaded dataset starts pending; admin can preview, approve, reject, and add notes.", 4.78, 1.65, 3.8, 1.65, C.green);
card(s, "Report Review", "Reports have an approval queue so generated outputs can be governed.", 8.82, 1.65, 3.8, 1.65, C.amber);
card(s, "Audit & Cost", "Tracks login, upload, AI query, report and approval actions; shows estimated AI usage and top active user.", 2.0, 4.3, 9.35, 1.2, C.green);
footer(s, 6);

s = pptx.addSlide();
addBg(s); title(s, "Architecture", "A simple modular architecture keeps the system explainable.");
const layers = [
  ["Streamlit UI", "Login, dashboard, admin panel"],
  ["Utility Modules", "Analyzer, visualizer, forecaster, AI agent, reports"],
  ["Data Layer", "Pandas dataframes and SQLite records"],
  ["AI Providers", "OpenAI / Gemini / Groq / Ollama endpoint"],
];
layers.forEach((l, i) => {
  const y = 1.5 + i * 1.1;
  card(s, l[0], l[1], 1.2, y, 10.9, 0.72, i % 2 ? C.purple : C.green);
  if (i < layers.length - 1) s.addShape(pptx.ShapeType.downArrow, { x: 6.2, y: y + 0.76, w: 0.45, h: 0.28, fill: { color: C.purple }, line: { color: C.purple } });
});
footer(s, 7);

s = pptx.addSlide();
addBg(s); title(s, "Deployment", "Submission package is ready for GitHub and Streamlit Cloud.");
card(s, "GitHub Repo", "README, deployment guide, demo script, requirements, config, and gitignore are prepared.", 0.85, 1.55, 3.65, 1.6, C.green);
card(s, "Working Demo", "Run locally with streamlit run app.py, then deploy on Streamlit Community Cloud.", 4.85, 1.55, 3.65, 1.6, C.purple);
card(s, "Documentation", "README.md, DEPLOYMENT.md, and DEMO_SCRIPT.md explain setup, features, and demo flow.", 8.85, 1.55, 3.65, 1.6, C.amber);
card(s, "Next Production Upgrades", "Email/SMS OTP, cloud database, object storage, environment secrets, and LangChain/CrewAI orchestration.", 1.5, 4.15, 10.3, 1.25, C.purple);
footer(s, 8);

await pptx.writeFile({ fileName: path.join(__dirname, "BizVision_AI_Demo.pptx") });
console.log("Created BizVision_AI_Demo.pptx");
