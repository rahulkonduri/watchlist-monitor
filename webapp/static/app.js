// Watchlist Monitor — vanilla JS SPA
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

const fmt = {
  price: (v, sym = "$") => (v == null ? "—" : sym + Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })),
  money: (v) => fmt.price(v, "$"),
  pct: (v) => (v == null ? "—" : (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%"),
  num: (v, d = 1) => (v == null ? "—" : Number(v).toFixed(d)),
  cls: (v) => (v == null ? "" : v >= 0 ? "pos" : "neg"),
};

// ── Tab switching ────────────────────────────────────────────────────────────
$$("#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$("#tabs button").forEach((b) => b.classList.remove("active"));
    $$(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $("#" + btn.dataset.tab).classList.add("active");
    loaders[btn.dataset.tab]?.();
  });
});

// ── Dashboard ────────────────────────────────────────────────────────────────
async function loadDashboard(refresh = false) {
  const status = $("#dash-status");
  status.textContent = "Loading market data…";
  try {
    const data = await api(`/api/dashboard?refresh=${refresh ? 1 : 0}`);
    const tbody = $("#dash-table tbody");
    tbody.innerHTML = "";
    for (const r of data.rows) {
      const a = r.assessment || {};
      const badgeCls = { "Technically strong": "strong", "Technically weak": "weak", "Looks stretched": "stretched" }[a.label] || "neutral";
      const tr = document.createElement("tr");
      if (r.error) {
        tr.innerHTML = `<td><strong>${r.ticker}</strong></td><td colspan="7" class="neg">Error: ${r.error}</td>`;
      } else {
        const alerts = r.alerts?.length
          ? `<ul class="alerts">${r.alerts.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
          : '<span class="muted">—</span>';
        const factors = a.factors?.length ? `<ul class="factors">${a.factors.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : "";
        tr.innerHTML = `
          <td><strong>${r.ticker}</strong>${r.held ? '<span class="held-dot" title="In your portfolio">●</span>' : ""}</td>
          <td>${fmt.money(r.price)}</td>
          <td class="${fmt.cls(r.change_pct)}">${fmt.pct(r.change_pct)}</td>
          <td>${fmt.num(r.rsi)}</td>
          <td>${r.ma_cross ? `<span class="badge ${r.ma_cross === "golden" ? "strong" : "weak"}">${r.ma_cross}</span>` : '<span class="muted">—</span>'}</td>
          <td>${alerts}</td>
          <td class="assess"><span class="badge ${badgeCls}">${esc(a.label || "—")}</span><div class="rationale">${esc(a.rationale || "")}</div>${factors}</td>
          <td class="ai-note">${r.ai_note ? esc(r.ai_note) : '<span class="muted">—</span>'}</td>`;
      }
      tbody.appendChild(tr);
    }
    const aiMsg = data.ai_enabled ? (data.ai_active ? "AI context: on" : "AI context: enabled but inactive (set OPENAI_API_KEY)") : "AI context: off";
    $("#dash-meta").textContent = `As of ${data.as_of} · ${data.counts.tickers} tickers · ${data.counts.alerts} alerts · ${aiMsg}`;
    status.textContent = data.rows.length ? "" : "No tickers yet — add interests or holdings.";
  } catch (e) {
    status.textContent = "Error: " + e.message;
  }
}
$("#dash-refresh").addEventListener("click", () => loadDashboard(true));

// ── Daily Ideas (screener) ───────────────────────────────────────────────────
function badgeClass(label) {
  return { "Technically strong": "strong", "Technically weak": "weak", "Looks stretched": "stretched" }[label] || "neutral";
}

function ideaCard(it, sym = "$") {
  const a = it.assessment || {};
  const reasons = (it.reasons || []).map((r) => `<li>${esc(r)}</li>`).join("");
  const ai = it.ai_note ? `<div class="idea-ai">🧠 ${esc(it.ai_note)}</div>` : "";
  return `
    <div class="idea-card">
      <div class="idea-head">
        <span class="idea-ticker">${esc(it.ticker)}</span>
        <span class="badge ${badgeClass(a.label)}">${esc(a.label || "—")}</span>
      </div>
      <div class="idea-stats">
        ${fmt.price(it.price, sym)} ·
        <span class="${fmt.cls(it.change_pct)}">${fmt.pct(it.change_pct)}</span> ·
        RSI ${fmt.num(it.rsi)}${it.ma_cross ? " · " + esc(it.ma_cross) + " cross" : ""}
      </div>
      <div class="idea-why">Flagged because:</div>
      <ul class="idea-reasons">${reasons || "<li>—</li>"}</ul>
      <div class="rationale">${esc(a.rationale || "")}</div>
      ${ai}
    </div>`;
}

function renderIdeaGroups(container, groups, sym) {
  container.innerHTML = groups
    .map((g) => {
      const more = g.total && g.total > g.items.length ? ` <span class="muted">(showing ${g.items.length} of ${g.total})</span>` : ` <span class="muted">(${g.items.length})</span>`;
      const body = g.items.length
        ? `<div class="ideas-cards">${g.items.map((it) => ideaCard(it, sym)).join("")}</div>`
        : '<p class="muted">None today.</p>';
      return `<div class="idea-group"><h4>${esc(g.title)}${more}</h4><p class="hint">${esc(g.blurb)}</p>${body}</div>`;
    })
    .join("");
}

// ── Market Scan (top US / India indexes) ──────────────────────────────────────
async function loadMarketUniverse() {
  const sel = $("#market-index");
  if (sel.dataset.filled) return;
  const data = await api("/api/universe");
  sel.innerHTML = data.indexes
    .map((i) => `<option value="${i.key}">${esc(i.name)} · ${i.count} stocks</option>`)
    .join("");
  sel.dataset.filled = "1";
}

async function scanMarket() {
  const sel = $("#market-index");
  const status = $("#market-status");
  const key = sel.value;
  status.textContent = `Scanning ${sel.options[sel.selectedIndex].text}… (this can take 10–30s)`;
  try {
    const data = await api(`/api/market-scan?index=${encodeURIComponent(key)}&refresh=1`);
    const sym = data.index.symbol || "$";
    $("#market-meta").textContent = `${data.index.name} · ${data.counts.flagged} of ${data.counts.universe} flagged · ${data.as_of}`;
    $("#market-top").innerHTML = data.top.length
      ? data.top.map((it) => ideaCard(it, sym)).join("")
      : '<p class="muted">Nothing in this index meets your screening conditions right now.</p>';
    renderIdeaGroups($("#market-groups"), data.groups, sym);
    status.textContent = "";
  } catch (e) {
    status.textContent = "Error: " + e.message;
  }
}
async function loadMarket() {
  try { await loadMarketUniverse(); } catch (e) { $("#market-status").textContent = "Error: " + e.message; }
}
$("#market-scan-btn").addEventListener("click", scanMarket);

async function loadIdeas(refresh = false) {
  const status = $("#ideas-status");
  status.textContent = "Scanning your universe…";
  try {
    const data = await api(`/api/ideas?refresh=${refresh ? 1 : 0}`);
    $("#ideas-meta").textContent = `As of ${data.as_of} · ${data.counts.flagged} of ${data.counts.universe} tickers flagged`;

    $("#ideas-top").innerHTML = data.top.length
      ? data.top.map((it) => ideaCard(it, "$")).join("")
      : '<p class="muted">Nothing in your universe is flagged today. That\'s a normal, quiet market day.</p>';

    renderIdeaGroups($("#ideas-groups"), data.groups, "$");
    status.textContent = "";
  } catch (e) {
    status.textContent = "Error: " + e.message;
  }
}
$("#ideas-refresh").addEventListener("click", () => loadIdeas(true));

// ── Portfolio ────────────────────────────────────────────────────────────────
async function loadPortfolio(refresh = false) {
  const status = $("#pf-status");
  status.textContent = "Loading…";
  try {
    const data = await api(`/api/portfolio?refresh=${refresh ? 1 : 0}`);
    const s = data.summary;
    $("#pf-summary").innerHTML = `
      <div class="card"><div class="label">Total cost</div><div class="value">${fmt.money(s.total_cost)}</div></div>
      <div class="card"><div class="label">Market value</div><div class="value">${fmt.money(s.total_value)}</div></div>
      <div class="card"><div class="label">Unrealized P&L</div><div class="value ${fmt.cls(s.total_pl)}">${fmt.money(s.total_pl)}</div></div>
      <div class="card"><div class="label">Return</div><div class="value ${fmt.cls(s.total_pl_pct)}">${fmt.pct(s.total_pl_pct)}</div></div>`;
    const tbody = $("#pf-table tbody");
    tbody.innerHTML = "";
    for (const p of data.positions) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${p.ticker}</strong></td>
        <td>${p.shares}</td>
        <td>${fmt.money(p.cost_basis)}</td>
        <td>${fmt.money(p.cost_total)}</td>
        <td>${fmt.money(p.current_price)}</td>
        <td>${fmt.money(p.market_value)}</td>
        <td class="${fmt.cls(p.unrealized_pl)}">${fmt.money(p.unrealized_pl)}</td>
        <td class="${fmt.cls(p.unrealized_pl_pct)}">${fmt.pct(p.unrealized_pl_pct)}</td>
        <td><button class="del-btn" data-id="${p.id}">Delete</button></td>`;
      tbody.appendChild(tr);
    }
    $$("#pf-table .del-btn").forEach((b) =>
      b.addEventListener("click", async () => {
        await api(`/api/holdings/${b.dataset.id}`, { method: "DELETE" });
        loadPortfolio(false);
      })
    );
    status.textContent = data.positions.length ? "" : "No holdings yet — add one above.";
  } catch (e) {
    status.textContent = "Error: " + e.message;
  }
}
$("#pf-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api("/api/holdings", {
      method: "POST",
      body: JSON.stringify({
        ticker: f.ticker.value,
        shares: parseFloat(f.shares.value),
        cost_basis: parseFloat(f.cost_basis.value),
        purchased_on: f.purchased_on.value || null,
      }),
    });
    f.reset();
    loadPortfolio(false);
  } catch (err) {
    $("#pf-status").textContent = "Error: " + err.message;
  }
});

// ── Interests ────────────────────────────────────────────────────────────────
async function loadInterests() {
  const status = $("#int-status");
  try {
    const data = await api("/api/interests");
    const sel = $("#theme-select");
    if (!sel.dataset.filled) {
      sel.innerHTML = data.available_themes.map((t) => `<option value="${t}">${t}</option>`).join("");
      sel.dataset.filled = "1";
    }
    const list = $("#int-list");
    list.innerHTML = "";
    for (const it of data.interests) {
      const li = document.createElement("li");
      if (it.kind === "theme") li.className = "theme";
      li.innerHTML = `<span>${it.kind === "theme" ? "🏷️ " : ""}${esc(it.value)}</span><span class="x" data-id="${it.id}">✕</span>`;
      list.appendChild(li);
    }
    $$("#int-list .x").forEach((x) =>
      x.addEventListener("click", async () => {
        await api(`/api/interests/${x.dataset.id}`, { method: "DELETE" });
        loadInterests();
      })
    );
    status.textContent = data.interests.length ? "" : "No interests yet.";
  } catch (e) {
    status.textContent = "Error: " + e.message;
  }
}
$("#int-ticker-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/interests", { method: "POST", body: JSON.stringify({ kind: "ticker", value: e.target.value.value }) });
  e.target.reset();
  loadInterests();
});
$("#int-theme-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/interests", { method: "POST", body: JSON.stringify({ kind: "theme", value: e.target.value.value }) });
  loadInterests();
});

// ── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
  const s = await api("/api/settings");
  const f = $("#settings-form");
  f.daily_move_pct.value = s.triggers.daily_move_pct;
  f.rsi_oversold.value = s.triggers.rsi_oversold;
  f.rsi_overbought.value = s.triggers.rsi_overbought;
  f.ma_short.value = s.triggers.ma_short;
  f.ma_long.value = s.triggers.ma_long;
  f.ai_enabled.checked = !!s.ai_analysis.enabled;
  f.ai_question.value = s.ai_analysis.question || "";
  f.always_send_summary.checked = !!s.always_send_summary;
  f.schedule_enabled.checked = !!s.schedule.enabled;
  f.schedule_hour.value = s.schedule.hour;
  f.schedule_minute.value = s.schedule.minute;
  $("#ai-env").textContent = s._env.openai_key_set
    ? "OPENAI_API_KEY detected — AI context will run when enabled."
    : "OPENAI_API_KEY not set — AI context stays inactive even if enabled.";
  $("#smtp-env").textContent = s._env.smtp_configured
    ? "SMTP configured — emails will send."
    : "SMTP env vars not set — emails print to the server console (dry run).";
}
$("#settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const patch = {
    triggers: {
      daily_move_pct: parseFloat(f.daily_move_pct.value),
      rsi_oversold: parseFloat(f.rsi_oversold.value),
      rsi_overbought: parseFloat(f.rsi_overbought.value),
      ma_short: parseInt(f.ma_short.value, 10),
      ma_long: parseInt(f.ma_long.value, 10),
    },
    ai_analysis: { enabled: f.ai_enabled.checked, question: f.ai_question.value },
    always_send_summary: f.always_send_summary.checked,
    schedule: { enabled: f.schedule_enabled.checked, hour: parseInt(f.schedule_hour.value, 10), minute: parseInt(f.schedule_minute.value, 10) },
  };
  try {
    await api("/api/settings", { method: "PUT", body: JSON.stringify(patch) });
    $("#settings-status").textContent = "Saved ✓";
    setTimeout(() => ($("#settings-status").textContent = ""), 2000);
  } catch (err) {
    $("#settings-status").textContent = "Error: " + err.message;
  }
});
$("#btn-preview").addEventListener("click", async () => {
  $("#settings-status").textContent = "Building preview…";
  try {
    const { html } = await api("/api/email/preview", { method: "POST" });
    const pane = $("#preview-pane");
    pane.innerHTML = "<iframe></iframe>";
    pane.querySelector("iframe").srcdoc = html;
    $("#settings-status").textContent = "";
  } catch (e) {
    $("#settings-status").textContent = "Error: " + e.message;
  }
});
$("#btn-send").addEventListener("click", async () => {
  $("#settings-status").textContent = "Sending…";
  try {
    const r = await api("/api/email/send", { method: "POST" });
    $("#settings-status").textContent = r.status;
  } catch (e) {
    $("#settings-status").textContent = "Error: " + e.message;
  }
});
$("#btn-export").addEventListener("click", async () => {
  try {
    const r = await api("/api/export-config", { method: "POST" });
    $("#settings-status").textContent = "Exported to " + r.path;
  } catch (e) {
    $("#settings-status").textContent = "Error: " + e.message;
  }
});

// ── utils ────────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ── Ticker Inspector ─────────────────────────────────────────────────────────
let _priceChart = null, _rsiChart = null;

function destroyCharts() {
  if (_priceChart) { _priceChart.destroy(); _priceChart = null; }
  if (_rsiChart)   { _rsiChart.destroy();   _rsiChart = null; }
}

async function runInspector(symbol, refresh = false) {
  if (!symbol) return;
  const status = $("#insp-status");
  status.textContent = `Loading ${symbol.toUpperCase()}…`;
  $("#insp-body").style.display = "none";
  destroyCharts();
  try {
    const d = await api(`/api/ticker/${encodeURIComponent(symbol.toUpperCase())}?refresh=${refresh ? 1 : 0}`);
    const s = d.snapshot;
    const a = d.assessment;
    const ch = d.chart;
    const sym = s.ticker.endsWith(".NS") || s.ticker.endsWith(".BO") ? "₹" : "$";

    $("#insp-meta").textContent = `${d.symbol} · as of ${d.as_of}`;
    $("#insp-refresh").style.display = "";
    $("#insp-refresh").onclick = () => runInspector(d.symbol, true);

    // Cards
    $("#insp-cards").innerHTML = `
      <div class="card"><div class="label">Price</div><div class="value">${fmt.price(s.price, sym)}</div></div>
      <div class="card"><div class="label">Daily change</div><div class="value ${fmt.cls(s.change_pct)}">${fmt.pct(s.change_pct)}</div></div>
      <div class="card"><div class="label">RSI (14)</div><div class="value">${fmt.num(s.rsi)}</div></div>
      <div class="card"><div class="label">50-day SMA</div><div class="value">${fmt.price(d.current.sma50, sym)}</div></div>
      <div class="card"><div class="label">200-day SMA</div><div class="value">${fmt.price(d.current.sma200, sym)}</div></div>
      <div class="card"><div class="label">MA Cross</div><div class="value">${s.ma_cross ? `<span class="badge ${s.ma_cross === "golden" ? "strong" : "weak"}">${s.ma_cross}</span>` : "—"}</div></div>`;

    // Assessment
    const bc = badgeClass(a.label);
    const factors = a.factors?.length ? `<ul class="factors">${a.factors.map(f => `<li>${esc(f)}</li>`).join("")}</ul>` : "";
    $("#insp-assessment").innerHTML = `
      <span class="badge ${bc}" style="font-size:1rem;padding:4px 14px">${esc(a.label)}</span>
      <div class="rationale" style="margin-top:8px">${esc(a.rationale)}</div>${factors}`;

    // SMA relationship
    $("#insp-sma-rel").textContent = d.sma_relationship || "";
    $("#insp-sma-rel").style.display = d.sma_relationship ? "" : "none";

    // Price + SMA chart
    _priceChart = new Chart($("#insp-price-chart"), {
      type: "line",
      data: {
        labels: ch.dates,
        datasets: [
          { label: d.symbol, data: ch.prices, borderColor: "#2f81f7", borderWidth: 2, pointRadius: 0, tension: 0.2, fill: false },
          { label: "SMA 50",  data: ch.sma50,  borderColor: "#d29922", borderWidth: 1.5, pointRadius: 0, tension: 0.2, fill: false, borderDash: [4,2] },
          { label: "SMA 200", data: ch.sma200, borderColor: "#f85149", borderWidth: 1.5, pointRadius: 0, tension: 0.2, fill: false, borderDash: [8,4] },
        ],
      },
      options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: "#8b98a5" } } }, scales: { x: { ticks: { color: "#8b98a5", maxTicksLimit: 8 }, grid: { color: "#30363d" } }, y: { ticks: { color: "#8b98a5" }, grid: { color: "#30363d" } } } },
    });

    // RSI chart with 30/70 bands
    const rsiLen = ch.rsi.length;
    _rsiChart = new Chart($("#insp-rsi-chart"), {
      type: "line",
      data: {
        labels: ch.dates.slice(-rsiLen),
        datasets: [
          { label: "RSI (14)", data: ch.rsi, borderColor: "#3fb950", borderWidth: 2, pointRadius: 0, tension: 0.2, fill: false },
          { label: "Overbought (70)", data: Array(rsiLen).fill(70), borderColor: "#f85149", borderWidth: 1, pointRadius: 0, borderDash: [6,3], fill: false },
          { label: "Oversold (30)",   data: Array(rsiLen).fill(30), borderColor: "#d29922", borderWidth: 1, pointRadius: 0, borderDash: [6,3], fill: false },
        ],
      },
      options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: "#8b98a5" } } }, scales: { x: { ticks: { color: "#8b98a5", maxTicksLimit: 8 }, grid: { color: "#30363d" } }, y: { min: 0, max: 100, ticks: { color: "#8b98a5" }, grid: { color: "#30363d" } } } },
    });

    // Alerts
    const alerts = s.alerts || [];
    $("#insp-alerts").innerHTML = alerts.length
      ? `<ul class="alerts" style="list-style:disc;padding-left:20px">${alerts.map(a => `<li>${esc(a)}</li>`).join("")}</ul>`
      : `<p class="insp-alerts-empty">No alerts fired today with current thresholds.</p>`;

    // AI note
    $("#insp-ai").innerHTML = d.ai_note
      ? `<div class="insp-section"><strong>🧠 AI context note</strong><div style="margin-top:6px;font-size:0.88rem">${esc(d.ai_note)}</div></div>`
      : "";

    $("#insp-body").style.display = "";
    status.textContent = "";
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
}

$("#insp-form").addEventListener("submit", (e) => {
  e.preventDefault();
  runInspector($("#insp-input").value.trim());
});

function loadInspector() {} // tab entered — nothing to auto-load

const loaders = { dashboard: loadDashboard, ideas: loadIdeas, market: loadMarket, inspector: loadInspector, portfolio: loadPortfolio, interests: loadInterests, settings: loadSettings };

// initial load
loadDashboard(false);
