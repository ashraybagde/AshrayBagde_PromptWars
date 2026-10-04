/* Hand-written inline SVG radar + accessible data table. No libraries. */
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text) e.textContent = text;
  return e;
}
function pt(i, n, r, c) {
  const a = (2 * Math.PI * i) / n - Math.PI / 2;
  return [c + r * Math.cos(a), c + r * Math.sin(a)];
}
/** series: [{name, scores:[{dimension,score}], dash}] */
function renderRadar(container, series) {
  container.textContent = "";
  const dims = series[0].scores.map((s) => s.dimension), n = dims.length, C = 160, R = 100;
  const svg = el("svg", { viewBox: "0 0 320 320", role: "img", "aria-label": "Coverage radar. Full data in the table below." });
  [2, 4, 6, 8, 10].forEach((l) => svg.append(el("polygon", { points: dims.map((_, i) => pt(i, n, (R * l) / 10, C).join(",")).join(" "), fill: "none", stroke: "currentColor", "stroke-opacity": ".25" })));
  dims.forEach((d, i) => {
    const [x, y] = pt(i, n, R + 18, C);
    svg.append(el("text", { x, y, "text-anchor": "middle", "font-size": "9", fill: "currentColor" }, `${d} ${series[series.length - 1].scores[i].score}`));
  });
  series.forEach((s, k) => {
    const pts = s.scores.map((v, i) => pt(i, n, (R * v.score) / 10, C).join(",")).join(" ");
    svg.append(el("polygon", { points: pts, fill: "currentColor", "fill-opacity": k ? ".15" : ".05", stroke: "currentColor", "stroke-width": "2", "stroke-dasharray": s.dash || "0" }));
  });
  container.append(svg);
  const t = document.createElement("table");
  const cap = document.createElement("caption"); cap.textContent = "Coverage scores (0 to 10; low scores are possible blind spots)";
  t.append(cap);
  const head = t.insertRow();
  ["Dimension", ...series.map((s) => s.name)].forEach((h) => { const th = document.createElement("th"); th.scope = "col"; th.textContent = h; head.append(th); });
  dims.forEach((d, i) => { const r = t.insertRow(); r.insertCell().textContent = d; series.forEach((s) => (r.insertCell().textContent = `${s.scores[i].score}/10`)); });
  container.append(t);
}
