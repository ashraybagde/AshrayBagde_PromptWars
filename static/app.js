const $ = (id) => document.getElementById(id);
const EXAMPLE = {
  decision: "I am deciding on a 6-month internship.",
  options_being_considered: "Take the internship, or continue full-time studies.",
  main_reasons: "Good stipend, close to home, gaining industry experience.",
  context_constraints: "I am a student; the internship overlaps with the semester.",
  reversibility: "",
};
let input = null, analysis = null;
const STATUS = ["Verified", "Unsure", "Just a guess"];

function fill(list, items) { list.textContent = ""; items.forEach((t) => { const li = document.createElement("li"); li.textContent = t; list.append(li); }); }
function setBusy(msg) { $("status").textContent = msg; $("error").textContent = ""; }
async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(r.status === 422 ? "Please check your inputs." : r.status === 429 ? "Too many requests; please wait a moment." : "Something went wrong. Please try again.");
  return r.json();
}
function updateMeter() {
  const sel = [...document.querySelectorAll("#assumptions select")];
  const bad = sel.filter((s) => s.value !== "Verified").length;
  $("pct").textContent = (sel.length ? Math.round((100 * bad) / sel.length) : 0) + "%";
}
function showTake(qs) { $("takeaway").hidden = false; fill($("take"), qs); }

$("example").onclick = () => { for (const k in EXAMPLE) $(k).value = EXAMPLE[k]; };

$("form").onsubmit = async (e) => {
  e.preventDefault();
  input = Object.fromEntries(new FormData($("form")));
  if (!input.decision.trim()) { $("decision-e").textContent = "Decision is required."; $("decision").focus(); return; }
  $("decision-e").textContent = "";
  setBusy("Analyzing your reasoning…");
  try { analysis = await post("/api/analyze", input); } catch (err) { $("status").textContent = ""; $("error").textContent = err.message; return; }
  $("status").textContent = "Analysis ready.";
  $("results").hidden = false;
  $("summary").textContent = analysis.reasoning_summary;
  renderRadar($("radar1"), [{ name: "Before", scores: analysis.coverage }]);
  const box = $("assumptions"); box.textContent = "";
  analysis.hidden_assumptions.forEach((a, i) => {
    const d = document.createElement("div"), p = document.createElement("p"), lab = document.createElement("label"), sel = document.createElement("select");
    p.textContent = `${a.assumption} Why it matters: ${a.why_it_matters} How to test: ${a.how_to_test}`;
    sel.id = "as" + i; lab.htmlFor = sel.id; lab.textContent = "Status";
    STATUS.forEach((s) => sel.add(new Option(s, s))); sel.value = "Unsure"; sel.onchange = updateMeter;
    d.append(p, lab, sel); box.append(d);
  });
  updateMeter();
  fill($("factors"), analysis.overlooked_factors.map((f) => `${f.factor} (${f.dimension}): ${f.why_it_matters}`));
  fill($("conflicts"), analysis.internal_conflicts);
  const q = $("questions"); q.textContent = "";
  analysis.probing_questions.forEach((t, i) => {
    const l = document.createElement("label"), a = document.createElement("textarea");
    a.id = "q" + i; l.htmlFor = a.id; l.textContent = t; q.append(l, a);
  });
  showTake(analysis.probing_questions);
  $("results").scrollIntoView();
};

$("reflect").onclick = async () => {
  const answers = [...document.querySelectorAll("#questions textarea")].map((a) => a.value.trim()).filter(Boolean).slice(0, 3);
  if (answers.length < 1) { $("error").textContent = "Answer at least one question to reflect."; return; }
  setBusy("Reflecting…");
  const statuses = [...document.querySelectorAll("#assumptions select")].map((s) => s.value);
  try {
    const r = await post("/api/reflect", { input, analysis, answers, assumption_statuses: statuses });
    $("status").textContent = "Reflection ready.";
    $("round2").hidden = false; $("shifted").textContent = r.what_shifted;
    fill($("newspots"), r.newly_surfaced_blind_spots);
    renderRadar($("radar2"), [{ name: "Before", scores: analysis.coverage, dash: "6 4" }, { name: "After", scores: r.updated_coverage_scores }]);
    showTake(r.remaining_open_questions);
  } catch (err) { $("status").textContent = ""; $("error").textContent = err.message; }
};

$("copy").onclick = async () => {
  const text = [...$("take").children].map((li, i) => `${i + 1}. ${li.textContent}`).join("\n");
  await navigator.clipboard.writeText(text); $("status").textContent = "Copied to clipboard.";
};
$("print").onclick = () => window.print();
