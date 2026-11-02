"use strict";

const $ = (id) => document.getElementById(id);
const PAIRS = ["#087e8b", "#c34c62", "#8051b2", "#855300", "#287b55", "#426abf"];
const state = { defaultGrammar: "", last: null, intent: null, selectedTree: 0, busy: false };

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));

async function api(path, body) {
  const response = await fetch(path, body === undefined ? { headers: { Accept: "application/json" } } : {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({ error: "The server returned an unreadable response." }));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}

function toast(message) {
  const region = $("toast-region");
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  region.appendChild(el);
  window.setTimeout(() => el.remove(), 2600);
}

function setStatus(kind, label) {
  const el = $("backend-status");
  el.className = `status-pill status-${kind}`;
  el.querySelector("span").textContent = label;
}

function showAlert(message) {
  const box = $("alert-area");
  box.textContent = message;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function clearAlert() { $("alert-area").textContent = ""; }

function setBusy(busy) {
  state.busy = busy;
  const button = $("analyze");
  button.disabled = busy;
  button.innerHTML = busy ? '<span class="loading-dot" aria-hidden="true"></span> Analyzing…' : 'Analyze grammar <span aria-hidden="true">↗</span>';
}

function buildTreeLayout(root) {
  const leafGap = 13;
  const rowHeight = 72;
  let cursor = 24;
  let maxDepth = 0;
  const measure = (node, depth) => {
    node._depth = depth;
    maxDepth = Math.max(maxDepth, depth);
    node._width = Math.max(node.terminal ? 38 : 50, String(node.label || "").length * (node.terminal ? 7 : 7.2) + 22);
    const children = Array.isArray(node.children) ? node.children : [];
    if (!children.length) {
      node._x = cursor + node._width / 2;
      cursor += node._width + leafGap;
      return;
    }
    children.forEach((child) => measure(child, depth + 1));
    node._x = (children[0]._x + children[children.length - 1]._x) / 2;
  };
  measure(root, 0);
  return { width: Math.max(260, cursor + 8), height: (maxDepth + 1) * rowHeight + 36, rowHeight };
}

function treeSvg(tree, bindings) {
  if (!tree) return "";
  const pairForToken = new Map();
  (bindings || []).forEach((binding, index) => {
    const pair = index % PAIRS.length;
    pairForToken.set(Number(binding.if), pair);
    pairForToken.set(Number(binding.else), pair);
  });
  const pairForElse = new Map((bindings || []).map((binding, index) => [Number(binding.else), index % PAIRS.length]));
  const dims = buildTreeLayout(tree);
  const edges = [];
  const nodes = [];
  const nodeY = (node) => 24 + node._depth * dims.rowHeight;
  const draw = (node) => {
    const y = nodeY(node);
    const children = Array.isArray(node.children) ? node.children : [];
    children.forEach((child) => {
      const cy = nodeY(child);
      const startY = y + 17;
      const endY = cy - 17;
      const bend = (startY + endY) / 2;
      edges.push(`<path class="edge" d="M ${node._x} ${startY} C ${node._x} ${bend}, ${child._x} ${bend}, ${child._x} ${endY}"/>`);
      draw(child);
    });
    const x = node._x - node._width / 2;
    const label = escapeHtml(node.label || "?");
    if (node.terminal) {
      const pair = pairForToken.get(Number(node.pos));
      const color = pair === undefined ? null : PAIRS[pair];
      const style = color ? `style="--pair-color:${color};fill:${color};stroke:${color}"` : "";
      const klass = color ? "leaf paired" : "leaf";
      const title = `Token ${Number(node.pos) + 1}: ${node.label}`;
      nodes.push(`<g class="${klass}" ${style}><title>${escapeHtml(title)}</title><rect x="${x}" y="${y - 15}" width="${node._width}" height="30" rx="7"/><text x="${node._x}" y="${y + 4}" text-anchor="middle">${label}</text></g>`);
    } else {
      const pair = node.else_pos === undefined ? undefined : pairForElse.get(Number(node.else_pos));
      const style = pair === undefined ? "" : `style="--pair-color:${PAIRS[pair]};stroke:${PAIRS[pair]}"`;
      nodes.push(`<g class="nt ${pair === undefined ? "" : "owner"}" ${style}><title>Non-terminal ${escapeHtml(node.label)}</title><rect x="${x}" y="${y - 16}" width="${node._width}" height="32" rx="10"/><text x="${node._x}" y="${y + 4}" text-anchor="middle">${label}</text></g>`);
    }
  };
  draw(tree);
  const width = Math.ceil(dims.width);
  const height = Math.ceil(dims.height);
  const pairCss = PAIRS.map((c, i) => `.pair-${i}{fill:${c};}`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" class="tree-svg" role="img" aria-label="Parse tree" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>Parse tree for ${escapeHtml(tree.label || "statement")}</title><desc>Top-down syntax tree showing non-terminals and terminal tokens.</desc><style>.edge{fill:none;stroke:#aeb9ca;stroke-width:1.5}.nt rect{fill:#fff;stroke:#5576be;stroke-width:1.4}.nt text{fill:#172033;font:600 11px monospace}.leaf rect{fill:#e9edf4;stroke:#cbd4e2;stroke-width:1}.leaf text{fill:#172033;font:500 10px monospace}.leaf.paired rect{stroke:var(--pair-color);stroke-width:1.8}.leaf.paired text{fill:#fff;font-weight:700}.owner rect{stroke-width:2.5}${pairCss}</style>${edges.join("")}${nodes.join("")}</svg>`;
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function downloadText(filename, text, type = "text/plain") { downloadBlob(filename, new Blob([text], { type })); }
function currentTreeSvg(container) { return container.querySelector("svg.tree-svg"); }
async function downloadPng(container, filename) {
  const svg = currentTreeSvg(container);
  if (!svg) return;
  const clone = svg.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const markup = new XMLSerializer().serializeToString(clone);
  const url = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }));
  const image = new Image();
  image.onload = () => {
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = image.width * scale; canvas.height = image.height * scale;
    const context = canvas.getContext("2d");
    context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface-soft").trim() || "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => { if (blob) downloadBlob(filename, blob); else toast("Could not export PNG."); }, "image/png");
    URL.revokeObjectURL(url);
  };
  image.onerror = () => { URL.revokeObjectURL(url); toast("Could not export this tree as PNG."); };
  image.src = url;
}

function tokensMarkup(result) {
  const pairMap = new Map();
  (result.rule_bindings || []).forEach((binding, index) => {
    const color = PAIRS[index % PAIRS.length];
    pairMap.set(binding.if, { color, label: `if #${binding.if_no}` });
    pairMap.set(binding.else, { color, label: `else for if #${binding.if_no}` });
  });
  const chips = (result.tokens || []).map((token) => {
    const pair = pairMap.get(token.pos);
    return `<span class="token-chip ${pair ? "paired" : ""}" ${pair ? `style="--pair-color:${pair.color}" title="${pair.label}"` : ""}><b>${escapeHtml(token.text)}</b><small>${token.pos + 1}</small></span>`;
  }).join("");
  return `<section class="result-panel"><div class="result-panel-header"><div><h3>Token stream</h3><p>Lexical units identified in the input statement.</p></div><span class="count-badge">${(result.tokens || []).length} TOKENS</span></div><div class="token-list">${chips || '<span class="section-copy">No tokens to display.</span>'}</div><p class="token-legend">Matching colours identify each <code>if</code> and the <code>else</code> attached to it by the nearest-unmatched-if rule.</p></section>`;
}

function grammarCard(title, text, subtitle) {
  if (!text) return `<section class="grammar-card"><div class="grammar-card-header"><strong>${title}</strong><span>${subtitle}</span></div><pre>Not available for this grammar.</pre></section>`;
  return `<section class="grammar-card"><div class="grammar-card-header"><strong>${title}</strong><span>${subtitle}</span></div><pre>${escapeHtml(text)}</pre></section>`;
}

function treePanel({ id, title, subtitle, count, trees, selected, after = false }) {
  if (!trees || !trees.length) {
    return `<section class="tree-panel"><div class="tree-panel-head"><div><h3>${title}</h3><p>${subtitle}</p></div></div><p class="section-copy">No parse tree is available for this input.</p></section>`;
  }
  const treeEntry = trees[selected] || trees[0];
  const countBadge = `<span class="count-badge ${count > 1 ? "warn" : "good"}">${count} ${count === 1 ? "PARSE" : "PARSES"}</span>`;
  const tabs = after ? "" : `<div class="tree-tabs" role="tablist" aria-label="Original parse alternatives">${trees.map((tree, i) => `<button type="button" role="tab" aria-selected="${i === selected}" aria-label="Parse tree ${i + 1}" data-tree-index="${i}">${i + 1}</button>`).join("")}</div>`;
  const stateBadge = treeEntry.matches_rule === null || treeEntry.matches_rule === undefined ? "" : `<span class="rule-badge ${treeEntry.matches_rule ? "follows" : "alternative"}">${treeEntry.matches_rule ? "Follows rule" : "Alternative reading"}</span>`;
  const stateText = treeEntry.matches_rule === null || treeEntry.matches_rule === undefined ? "" : treeEntry.matches_rule ? "This interpretation attaches each else to the nearest unmatched if." : "This is a valid reading of the original grammar, but it does not follow the conventional nearest-unmatched-if rule.";
  const more = !after && count > trees.length ? `<p class="tree-footnote">Showing ${trees.length} of ${count} parse trees returned by the parser.</p>` : "";
  return `<section class="tree-panel" id="${id}"><div class="tree-panel-head"><div><h3>${title}</h3><p>${subtitle}</p></div>${countBadge}</div>${tabs}<div class="tree-state">${stateBadge}<span>${escapeHtml(stateText)}</span></div><div class="tree-viewport">${treeSvg(treeEntry.tree, treeEntry.bindings || [])}</div><div class="tree-actions"><button type="button" data-action="dot">Download .dot</button><button type="button" data-action="svg">Download SVG</button><button type="button" data-action="png">Download PNG</button></div>${more}</section>`;
}

function bindingMarkup(result) {
  const bindings = result.rule_bindings || [];
  if (!bindings.length) return `<section class="result-panel"><div class="result-panel-header"><div><h3>Which if receives each else?</h3><p>No else clause needs to be attached in this example.</p></div></div><p class="section-copy">The statement contains no dangling else attachment to resolve.</p></section>`;
  const ifPositions = (result.tokens || []).filter((token) => token.text === "if").map((token) => token.pos);
  const numberOf = (position) => ifPositions.indexOf(position) + 1;
  const beforeTrees = result.before?.trees || [];
  const rows = bindings.map((binding, index) => {
    const color = PAIRS[index % PAIRS.length];
    const token = result.tokens?.[binding.if + 1]?.text || "condition";
    const otherReadings = [...new Set(beforeTrees.flatMap((tree) => (tree.bindings || []).filter((item) => item.else === binding.else && item.if !== binding.if).map((item) => `if #${numberOf(item.if)}`)))].join(", ") || "None";
    const level = binding.if_no;
    return `<tr><td><span class="pair-label" style="--pair-color:${color}"><i class="pair-dot"></i>Else ${index + 1}</span></td><td>Token ${binding.else + 1}</td><td><strong>if #${binding.if_no}</strong><span class="binding-explanation">Token ${binding.if + 1} · condition ${escapeHtml(token)}</span></td><td>${level}</td><td>${escapeHtml(otherReadings)}</td></tr>`;
  }).join("");
  return `<section class="result-panel"><div class="result-panel-header"><div><h3>Which if receives each else?</h3><p>The nearest-unmatched-if rule pairs each else with the most recent open if.</p></div></div><div class="binding-table-wrap"><table><thead><tr><th>Else</th><th>Token position</th><th>Attached to</th><th>If order</th><th>Other valid readings</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}

function stepsMarkup(result) {
  const steps = result.steps || [];
  const items = steps.map((step, index) => `<details ${index === 0 ? "open" : ""}><summary><span class="step-number">${String(index + 1).padStart(2, "0")}</span><span>${escapeHtml(step.title)}</span><span class="step-chevron">⌄</span></summary><div class="step-body">${escapeHtml(step.text)}</div></details>`).join("");
  const trace = (result.rule_trace || []).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  return `<section class="result-panel"><div class="result-panel-header"><div><h3>Step-by-step explanation</h3><p>Follow the analysis from tokenization to grammar transformation.</p></div></div><div class="steps-list">${items || '<p class="section-copy">No explanation steps are available.</p>'}</div><div class="rule-callout" style="margin-top:12px"><strong>Nearest-unmatched-if rule</strong>An <code>else</code> attaches to the closest preceding <code>if</code> that does not already have an <code>else</code>. This is why the transformed grammar separates fully matched statements from unmatched statements.</div>${trace ? `<details class="trace-details"><summary>View parser stack trace</summary><ol class="rule-trace">${trace}</ol></details>` : ""}</section>`;
}

function renderResult(result) {
  state.last = result;
  state.selectedTree = 0;
  const valid = Boolean(result.valid);
  $("stat-before").textContent = valid ? String(result.parse_count) : "0";
  $("stat-after").textContent = valid && result.after ? String(result.after.count) : valid ? "N/A" : "0";
  $("stat-verdict").textContent = !valid ? "Invalid input" : result.ambiguous ? "Ambiguous" : "Unambiguous";

  if (!valid) {
    $("analysis-output").innerHTML = `<section class="verdict-banner invalid"><span class="verdict-icon">!</span><div><strong>Input could not be parsed</strong><p>${escapeHtml(result.error || "The input is not valid under the supplied grammar.")}</p></div></section>${tokensMarkup(result)}${stepsMarkup(result)}`;
    return;
  }

  const ambiguous = Boolean(result.ambiguous);
  const headline = ambiguous ? `Ambiguous input · ${result.parse_count} valid parse trees` : "No dangling-else ambiguity in this input";
  const explanation = ambiguous ? "The same token sequence can be derived in more than one way under the original grammar." : "Only one parse tree is generated by the original grammar for this statement.";
  const beforeTrees = result.before?.trees || [];
  const afterTree = result.after?.tree ? [result.after.tree] : [];
  const afterCount = result.after?.count ?? 0;
  const beforeTreePanel = treePanel({ id: "before-tree-panel", title: "Before · Original grammar", subtitle: "All valid interpretations under the ambiguous CFG.", count: result.before?.count ?? result.parse_count, trees: beforeTrees, selected: 0 });
  const afterPanel = treePanel({ id: "after-tree-panel", title: "After · Matched / unmatched", subtitle: "The transformed grammar selects one interpretation.", count: afterCount, trees: afterTree, selected: 0, after: true });
  const grammarBefore = result.grammar_before?.text || "";
  const grammarAfter = result.grammar_after?.text || "";
  const grammarArea = `<section class="result-panel" id="grammar-comparison"><div class="result-panel-header"><div><h3>Grammar transformation</h3><p>Compare the original ambiguous productions with the matched/unmatched rewrite.</p></div></div><div class="grammar-comparison">${grammarCard("Original grammar · ambiguous", grammarBefore, "BEFORE")}${grammarCard("Transformed grammar · unambiguous", grammarAfter, "AFTER")}</div></section>`;
  const intentPanel = state.intent ? intentMarkup(result) : "";
  $("analysis-output").innerHTML = `
    <section class="verdict-banner ${ambiguous ? "ambiguous" : "clear"}"><span class="verdict-icon">${ambiguous ? "!" : "✓"}</span><div><strong>${headline}</strong><p>${explanation}</p></div></section>
    <div class="result-metrics"><div class="metric-card"><span>PARSES BEFORE</span><strong>${result.parse_count}</strong><small>Original grammar</small></div><div class="metric-card"><span>PARSES AFTER</span><strong>${afterCount || "N/A"}</strong><small>Transformed grammar</small></div><div class="metric-card"><span>IF NESTING DEPTH</span><strong>${(result.tokens || []).filter((token) => token.text === "if").length}</strong><small>Conditional statements</small></div></div>
    ${tokensMarkup(result)}
    ${intentPanel}
    <section id="tree-comparison" class="result-panel"><div class="result-panel-header"><div><h3>Parse tree comparison</h3><p>Each node represents a grammar symbol. Coloured terminals show the if/else bindings.</p></div><span class="count-badge">BEFORE → AFTER</span></div><div class="tree-comparison">${beforeTreePanel}${afterPanel}</div></section>
    ${bindingMarkup(result)}
    ${grammarArea}
    ${stepsMarkup(result)}`;
  attachTreeEvents("before-tree-panel", false);
  attachTreeEvents("after-tree-panel", true);
}

function intentMarkup(result) {
  const actual = result.rule_bindings || [];
  const mismatches = state.intent.filter((intended) => !actual.some((binding) => binding.if === intended.if && binding.else === intended.else));
  const copy = mismatches.length ? mismatches.map((item) => {
    const actualBinding = actual.find((binding) => binding.else === item.else);
    return `<li>Else at token ${item.else + 1}: intended for if #${item.level}, attached by the grammar to ${actualBinding ? `if #${actualBinding.if_no}` : "no if"}.</li>`;
  }).join("") : "<li>Every else attaches to the if level selected in the builder.</li>";
  return `<section class="result-panel"><div class="result-panel-header"><div><h3>Builder intention vs grammar rule</h3><p>The parser follows grammar structure, not the author's intended indentation.</p></div></div><ul class="rule-trace">${copy}</ul></section>`;
}

function attachTreeEvents(panelId, isAfter) {
  const panel = $(panelId);
  if (!panel) return;
  panel.querySelectorAll('[role="tab"][data-tree-index]').forEach((button) => button.addEventListener("click", () => {
    state.selectedTree = Number(button.dataset.treeIndex);
    const entry = state.last?.before?.trees?.[state.selectedTree];
    if (!entry) return;
    const treeContainer = panel.querySelector(".tree-viewport");
    treeContainer.innerHTML = treeSvg(entry.tree, entry.bindings || []);
    panel.querySelectorAll("[data-tree-index]").forEach((tab) => tab.setAttribute("aria-selected", String(tab === button)));
    const stateNode = panel.querySelector(".tree-state");
    const follows = entry.matches_rule;
    stateNode.innerHTML = `${follows === null ? "" : `<span class="rule-badge ${follows ? "follows" : "alternative"}">${follows ? "Follows rule" : "Alternative reading"}</span>`}<span>${follows === null ? "" : follows ? "This interpretation follows the nearest-unmatched-if rule." : "This is a valid alternative reading of the original grammar."}</span>`;
  }));
  panel.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", async () => {
    const entry = isAfter ? state.last?.after?.tree : state.last?.before?.trees?.[state.selectedTree];
    if (!entry) return;
    const action = button.dataset.action;
    if (action === "dot") downloadText(isAfter ? "grammar-fix-after.dot" : `grammar-fix-before-${state.selectedTree + 1}.dot`, entry.dot || "");
    if (action === "svg") {
      const svg = panel.querySelector(".tree-viewport svg");
      if (svg) downloadText(isAfter ? "grammar-fix-after.svg" : `grammar-fix-before-${state.selectedTree + 1}.svg`, new XMLSerializer().serializeToString(svg), "image/svg+xml");
    }
    if (action === "png") await downloadPng(panel.querySelector(".tree-viewport"), isAfter ? "grammar-fix-after.png" : `grammar-fix-before-${state.selectedTree + 1}.png`);
  }));
}

function updateBuilder() {
  const depth = Number($("depth").value);
  $("depth-out").textContent = String(depth);
  const checks = Array.from({ length: depth }, (_, index) => `<label><input type="checkbox" value="${index + 1}" ${index === 0 ? "checked" : ""}><span>Else for if #${index + 1}</span></label>`).join("");
  $("levels").innerHTML = checks;
  updateBuilderPreview();
}
function updateBuilderPreview() {
  const depth = Number($("depth").value);
  const levels = [...$("levels").querySelectorAll("input:checked")].map((node) => Number(node.value));
  let source = "s";
  for (let level = depth; level >= 1; level--) {
    source = `if e${level} then ${source}${levels.includes(level) ? ` else s${level}` : ""}`;
  }
  $("builder-preview-text").textContent = source;
}

async function analyze() {
  if (state.busy) return;
  clearAlert();
  setBusy(true);
  try {
    const result = await api("/api/analyze", { input: $("input").value, grammar: $("grammar").value });
    renderResult(result);
  } catch (error) {
    showAlert(error.message);
  } finally { setBusy(false); }
}

async function runTests() {
  const button = $("run-tests");
  button.disabled = true;
  button.textContent = "Running tests…";
  try {
    const data = await api("/api/tests");
    $("test-summary").textContent = `${data.passed} / ${data.total} passed`;
    $("test-summary").className = `test-summary ${data.passed === data.total ? "passed" : "failed"}`;
    const rows = (data.results || []).map((item, index) => `<tr class="test-row" data-test-index="${index}" tabindex="0" title="Load this test case into the editor"><td><strong>${escapeHtml(item.name)}</strong></td><td class="mono">${escapeHtml(item.input)}</td><td>${item.actual_before} <span class="muted-inline">/ ${item.expected_before}</span></td><td>${item.actual_after} <span class="muted-inline">/ ${item.expected_after}</span></td><td>${item.rule_ok ? "Yes" : "No"}</td><td><span class="test-status ${item.passed ? "pass" : "fail"}">${item.passed ? "PASS" : "FAIL"}</span></td></tr>`).join("");
    $("test-results").innerHTML = `<div class="test-table-wrap"><table><thead><tr><th>Test case</th><th>Input</th><th>Before</th><th>After</th><th>Rule</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div><p class="section-copy">Select any row to load that case into the source editor and inspect its parse trees.</p>`;
    $("test-results").querySelectorAll("[data-test-index]").forEach((row) => {
      const load = () => { $("input").value = data.results[Number(row.dataset.testIndex)].input; state.intent = null; updateCharCount(); analyze(); window.scrollTo({ top: 0, behavior: "smooth" }); };
      row.addEventListener("click", load);
      row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); load(); } });
    });
    toast(`${data.passed} of ${data.total} test cases passed.`);
  } catch (error) { showAlert(error.message); }
  finally { button.disabled = false; button.innerHTML = 'Run built-in tests <span aria-hidden="true">→</span>'; }
}

function updateCharCount() { $("char-count").textContent = `${$("input").value.length} characters`; }

async function initialize() {
  updateCharCount();
  updateBuilder();
  try {
    const data = await api("/api/default");
    state.defaultGrammar = data.grammar || "";
    $("grammar").value = state.defaultGrammar;
    setStatus("online", "Backend online");
    $("examples").innerHTML = (data.examples || []).map((example, index) => `<button class="example-chip" type="button" data-example="${index}">${escapeHtml(example.name)}</button>`).join("");
    $("examples").querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", () => {
      const example = data.examples[Number(button.dataset.example)];
      $("input").value = example.input; state.intent = null; updateCharCount(); analyze();
    }));
    await analyze();
  } catch (error) {
    setStatus("offline", "Backend offline");
    showAlert("Cannot connect to the Grammar Fix backend. Start it with: python backend/app.py");
  }
}

$("analyze").addEventListener("click", () => { state.intent = null; analyze(); });
$("empty-analyze").addEventListener("click", () => analyze());
$("input").addEventListener("input", updateCharCount);
$("input").addEventListener("keydown", (event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); state.intent = null; analyze(); } });
$("depth").addEventListener("input", updateBuilder);
$("levels").addEventListener("change", updateBuilderPreview);
$("build").addEventListener("click", async () => {
  try {
    const levels = [...$("levels").querySelectorAll("input:checked")].map((node) => Number(node.value));
    const result = await api("/api/generate", { depth: Number($("depth").value), else_levels: levels });
    $("input").value = result.input; state.intent = result.intended || []; updateCharCount(); await analyze();
  } catch (error) { showAlert(error.message); }
});
$("witness").addEventListener("click", async () => {
  const button = $("witness"); button.disabled = true; button.textContent = "Searching…";
  try {
    const result = await api("/api/witness", { grammar: $("grammar").value, max_len: 11 });
    if (!result.witnesses?.length) { $("witness-out").textContent = `No ambiguous string found up to ${result.searched_up_to} tokens.`; return; }
    $("witness-out").innerHTML = result.witnesses.map((item, index) => `<button type="button" class="witness-chip" data-witness="${index}">${escapeHtml(item.string)} · ${item.parses} parses</button>`).join("");
    $("witness-out").querySelectorAll("[data-witness]").forEach((chip) => chip.addEventListener("click", () => {
      $("input").value = result.witnesses[Number(chip.dataset.witness)].string; state.intent = null; updateCharCount(); analyze();
    }));
  } catch (error) { showAlert(error.message); }
  finally { button.disabled = false; button.textContent = "Find an ambiguous string"; }
});
$("reset-grammar").addEventListener("click", () => { $("grammar").value = state.defaultGrammar; toast("Default grammar restored."); });
$("run-tests").addEventListener("click", runTests);

function applyTheme(theme, persist = false) {
  document.documentElement.dataset.theme = theme;
  const button = $("theme-toggle");
  button.setAttribute("aria-pressed", String(theme === "dark"));
  button.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
  document.querySelector('meta[name="theme-color"]').content = theme === "dark" ? "#111827" : "#f3f5f9";
  if (persist) { try { localStorage.setItem("grammarfix-theme-v2", theme); } catch (_) {} }
}
$("theme-toggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true));

document.addEventListener("keydown", (event) => {
  if ((event.key === "t" || event.key === "T") && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) && !event.metaKey && !event.ctrlKey && !event.altKey) {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true);
  }
  if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
    const panel = $("before-tree-panel");
    if (!panel || !panel.contains(document.activeElement)) return;
    const tabs = [...panel.querySelectorAll("[data-tree-index]")];
    const current = tabs.indexOf(document.activeElement);
    if (current < 0 || !tabs.length) return;
    event.preventDefault();
    tabs[(current + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length].focus();
    tabs[(current + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length].click();
  }
});

initialize();
