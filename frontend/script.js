"use strict";

const API = { start: "/api/v1/simulation/start", dashboard: "/api/v1/dashboard", health: "/api/v1/health" };
const MIN = 10_000, MAX = 10_000_000, LOCALE = "en-IN", POLL_MS = 1000, MAX_FAILS = 3;

const $ = (id) => document.getElementById(id);
const miss = (v) => v === null || v === undefined;
const fN = (v) => (miss(v) ? "—" : Number(v).toLocaleString(LOCALE, { maximumFractionDigits: 2 }));
const fS = (v) => (miss(v) ? "—" : `${Number(v).toFixed(4)} s`);
const fU = (ns) => (miss(ns) ? "—" : `${(Number(ns) / 1000).toFixed(2)} µs`); // API sends ns
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------- dashboard definition ---------- */
const GROUPS = [
  { cls: "cards", item: "card", items: [
    ["ORDERS PROCESSED", (m) => m.orders_processed, fN, "Matching engine"],
    ["THROUGHPUT", (m) => m.steady_throughput, fN, "Orders / second"],
    ["P99 LATENCY", (m) => m.latency?.p99, fU, "Microseconds"],
    ["MEAN LATENCY", (m) => m.latency?.mean, fU, "Microseconds"],
    ["TRADES EXECUTED", (m) => m.trades_executed, fN, "Successful matches"],
    ["STEADY STATE", (m) => m.timings?.steady_state_seconds, fS, "Seconds"],
  ]},
  { title: "LATENCY DISTRIBUTION", cls: "strip", item: "cell", items: [
    ["P50", (m) => m.latency?.median, fU], ["P95", (m) => m.latency?.p95, fU],
    ["P99", (m) => m.latency?.p99, fU], ["MAXIMUM", (m) => m.latency?.max, fU],
  ]},
  { title: "EXECUTION VERIFICATION", cls: "strip", item: "cell", items: [
    ["GENERATED", (m) => m.simulator?.generated, fN], ["ACCEPTED", (m) => m.simulator?.accepted, fN],
    ["PUBLISHED", (m) => m.published, fN], ["RECEIVED", (m) => m.orders_received, fN],
    ["UNIQUE IDS", (m) => m.unique_order_ids, fN], ["DUPLICATES", (m) => m.duplicate_order_ids, fN],
  ]},
];

const STAGES = {
  pipeline_wall_seconds: "Pipeline wall time", steady_state_seconds: "Steady-state time",
  workload_build_seconds: "Workload construction", simulator_run_seconds: "Simulator run",
  producer_queue_wait_seconds: "Producer queue wait", producer_publish_seconds: "Producer publishing",
  consumer_receive_seconds: "Consumer receiving", consumer_timeout_seconds: "Consumer timeout",
  matching_seconds: "Matching engine", trade_materialization_seconds: "Trade materialization",
  depth_seconds: "Order book depth", adapter_drain_seconds: "Adapter drain",
  consumer_join_seconds: "Consumer join", ring_cleanup_seconds: "Ring cleanup",
};

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function renderResults(metrics) {
  const root = $("groups");
  root.replaceChildren();
  let i = 0;

  GROUPS.forEach((g) => {
    if (g.title) root.append(el("h3", "group-title", g.title));
    const wrap = el("div", g.cls);
    g.items.forEach(([label, get, fmt, unit]) => {
      const node = el("div", g.item);
      node.style.setProperty("--i", i++);
      node.append(el("span", "k", label), el("span", "v", fmt(get(metrics))));
      if (unit) node.append(el("span", "u", unit));
      wrap.append(node);
    });
    root.append(wrap);
  });

  const timings = metrics.timings || {};
  $("stage-timings").replaceChildren(
    ...Object.entries(STAGES).map(([key, label]) => {
      const tr = el("tr");
      tr.append(el("td", "", label), el("td", "", fS(timings[key])));
      return tr;
    })
  );
}

/* ---------- UI state ---------- */
const setPhase = (p) => { document.body.dataset.phase = p; };

function setBusy(busy, label = "START SIMULATION") {
  $("start-button").disabled = busy;
  $("order-count").disabled = busy;
  $("start-button").setAttribute("aria-busy", String(busy));
  $("button-text").textContent = label;
}

function setStatus(status, msg) {
  $("simulation-status").textContent = status.toUpperCase();
  $("simulation-message").textContent = msg;
  $("simulation-dot").className = "dot " + (status === "queued" ? "running" : status);
}

function showError(msg) { const e = $("error-message"); e.textContent = msg; e.classList.remove("hidden"); }
function clearError() { const e = $("error-message"); e.textContent = ""; e.classList.add("hidden"); }

function setConnection(online) {
  $("connection-status").textContent = online ? "SYSTEM ONLINE" : "BACKEND OFFLINE";
  $("conn-dot").className = "dot " + (online ? "online" : "failed");
}

/* ---------- animated stage: simulated trading terminal (illustrative only) ---------- */
const stage = (() => {
  const cv = $("stage-canvas"), ctx = cv.getContext("2d");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const G = "0,214,154", R = "255,92,101";
  const MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";
  const TICK = 0.05, P0 = 2450, LV = 8, MAXC = 70, CANDLE_S = 0.9;
  let W = 0, H = 0, raf = 0, last = 0, acc = 0, ct = 0, flash = 0, live = false;
  let candles = [], cur = null, price = P0, open0 = P0, vol = 0, nOrders = 0, nTrades = 0;
  let bids = [], asks = [], lo = 0, hi = 0;

  const rnd = (a, b) => a + Math.random() * (b - a);
  const snap = (p) => Math.round(p / TICK) * TICK;
  const fp = (p) => p.toLocaleString(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const walk = (p) => snap(p + rnd(-0.9, 0.9) + (P0 - p) * 0.01);

  function resize() {
    const d = devicePixelRatio || 1;
    W = cv.clientWidth; H = cv.clientHeight;
    cv.width = W * d; cv.height = H * d;
    ctx.setTransform(d, 0, 0, d, 0, 0);
  }

  function seed() {
    candles = []; let p = P0 + rnd(-15, 15);
    for (let i = 0; i < 50; i++) {
      const c = { o: p, h: p, l: p, c: p, v: 0 };
      for (let j = 0; j < 12; j++) { p = walk(p); c.h = Math.max(c.h, p); c.l = Math.min(c.l, p); c.v += rnd(20, 300); }
      c.c = p; candles.push(c);
    }
    price = p; open0 = candles[0].o; cur = null; lo = hi = 0;
    bids = Array.from({ length: LV }, () => ({ q: rnd(100, 600) }));
    asks = Array.from({ length: LV }, () => ({ q: rnd(100, 600) }));
  }

  function tick() {
    const prev = price; price = walk(price);
    const buy = price !== prev ? price > prev : Math.random() < 0.5;
    const q = Math.round(rnd(1, 400));
    cur.c = price; cur.h = Math.max(cur.h, price); cur.l = Math.min(cur.l, price); cur.v += q;
    vol += q; nTrades++; nOrders += Math.floor(rnd(2, 7)); flash = 1;
    (buy ? asks : bids)[0].q *= 0.4; // aggressor eats the best level
    for (let i = 0; i < LV; i++)
      for (const s of [bids, asks]) s[i].q += (rnd(80, 600) * (1 + i * 0.12) - s[i].q) * 0.5;

    const li = el("li", buy ? "buy" : "sell");
    li.append(el("span", "", new Date().toLocaleTimeString(LOCALE)),
              el("span", "", `${buy ? "▲" : "▼"} ${fp(price)}`), el("span", "", fN(q)));
    $("tape").prepend(li);
    while ($("tape").children.length > 6) $("tape").lastElementChild.remove();

    const chg = ((price - open0) / open0) * 100;
    $("v-orders").textContent = fN(nOrders);
    $("v-trades").textContent = fN(nTrades);
    $("v-vol").textContent = fN(vol);
    $("v-price").textContent = fp(price); $("v-price").className = buy ? "up" : "down";
    $("v-chg").textContent = `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%`; $("v-chg").className = chg >= 0 ? "up" : "down";
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const bw = W < 560 ? 0 : Math.min(250, W * 0.3), cw = W - bw, ax = 64, top = 36;
    const volH = Math.round(H * 0.15), ch = H - top - volH - 10;

    ctx.textAlign = "left"; ctx.font = `700 12px ${MONO}`; ctx.fillStyle = "#e7edf0";
    ctx.fillText("CHRN / USD", 14, 22);
    ctx.font = `10px ${MONO}`; ctx.fillStyle = live ? `rgb(${G})` : "#8a969e";
    ctx.fillText((live ? "● LIVE · " : "○ IDLE · ") + "CHRONOS MATCHING ENGINE", 100, 22);

    // price range (smoothed so the scale glides)
    const vis = candles.slice(-MAXC);
    let mn = Infinity, mx = -Infinity, vm = 1;
    vis.forEach((c) => { mn = Math.min(mn, c.l); mx = Math.max(mx, c.h); vm = Math.max(vm, c.v); });
    const pad = (mx - mn) * 0.15 + 0.2, tl = mn - pad, th = mx + pad;
    lo = lo ? lo + (tl - lo) * 0.15 : tl; hi = hi ? hi + (th - hi) * 0.15 : th;
    const y = (p) => top + ch * (1 - (p - lo) / (hi - lo));

    ctx.globalAlpha = live ? 1 : 0.5;
    ctx.lineWidth = 1; ctx.font = `10px ${MONO}`; ctx.textAlign = "right";
    for (let i = 0; i <= 4; i++) {
      const p = lo + ((hi - lo) * i) / 4, yy = Math.round(y(p)) + 0.5;
      ctx.strokeStyle = "rgba(255,255,255,.06)";
      ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(cw - ax, yy); ctx.stroke();
      ctx.fillStyle = "#8a969e"; ctx.fillText(fp(p), cw - 8, yy + 3);
    }

    const step = (cw - ax - 12) / MAXC, bwid = Math.max(2, step * 0.62);
    vis.forEach((c, i) => {
      const x = 6 + (MAXC - vis.length + i) * step + step / 2, col = c.c >= c.o ? G : R;
      ctx.strokeStyle = ctx.fillStyle = `rgb(${col})`;
      ctx.beginPath(); ctx.moveTo(x, y(c.h)); ctx.lineTo(x, y(c.l)); ctx.stroke();
      ctx.fillRect(x - bwid / 2, y(Math.max(c.o, c.c)), bwid, Math.max(1, Math.abs(y(c.o) - y(c.c))));
      const vh = (c.v / vm) * volH;
      ctx.fillStyle = `rgba(${col},.35)`; ctx.fillRect(x - bwid / 2, H - 10 - vh, bwid, vh);
    });

    const up = !cur || price >= cur.o, lc = up ? G : R, ly = y(price);
    ctx.setLineDash([4, 4]); ctx.strokeStyle = `rgba(${lc},.8)`;
    ctx.beginPath(); ctx.moveTo(0, ly); ctx.lineTo(cw - ax, ly); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = `rgb(${lc})`; ctx.fillRect(cw - ax, ly - 9, ax - 2, 18);
    ctx.fillStyle = "#001b13"; ctx.textAlign = "center"; ctx.font = `700 10px ${MONO}`;
    ctx.fillText(fp(price), cw - ax / 2 - 1, ly + 3.5);
    ctx.globalAlpha = 1;

    if (!live) {
      ctx.fillStyle = "#e7edf0"; ctx.font = "600 13px system-ui"; ctx.textAlign = "center";
      ctx.fillText("MARKET IDLE — start a simulation to open trading", cw / 2, top + ch / 2);
    }

    if (bw) { // order book
      const x0 = cw + 10, w = bw - 18, midH = 34, rh = (H - 10 - 30 - midH) / (LV * 2);
      ctx.strokeStyle = "rgba(255,255,255,.08)";
      ctx.beginPath(); ctx.moveTo(cw, 8); ctx.lineTo(cw, H - 8); ctx.stroke();
      ctx.font = `10px ${MONO}`; ctx.fillStyle = "#8a969e";
      ctx.textAlign = "left"; ctx.fillText("ORDER BOOK", x0, 22);
      ctx.textAlign = "right"; ctx.fillText("SIZE", x0 + w - 4, 22);

      const cum = (s) => { let a = 0; return s.map((l) => (a += l.q)); };
      const ca = cum(asks), cb = cum(bids), mc = Math.max(ca[LV - 1], cb[LV - 1]);
      const row = (yy, p, q, cq, col) => {
        ctx.fillStyle = `rgba(${col},.16)`; const b = (cq / mc) * w; ctx.fillRect(x0 + w - b, yy + 1, b, rh - 2);
        ctx.fillStyle = `rgb(${col})`; ctx.textAlign = "left"; ctx.fillText(fp(p), x0 + 4, yy + rh / 2 + 3.5);
        ctx.fillStyle = "#c9d3d8"; ctx.textAlign = "right"; ctx.fillText(fN(Math.round(q)), x0 + w - 4, yy + rh / 2 + 3.5);
      };

      let yy = 30;
      for (let i = LV - 1; i >= 0; i--, yy += rh) row(yy, snap(price + TICK * (i + 1)), asks[i].q, ca[i], R);
      ctx.fillStyle = `rgba(${lc},${0.08 + flash * 0.2})`; ctx.fillRect(x0, yy, w, midH);
      ctx.fillStyle = `rgb(${lc})`; ctx.font = `700 15px ${MONO}`; ctx.textAlign = "left";
      ctx.fillText(`${up ? "▲" : "▼"} ${fp(price)}`, x0 + 4, yy + 15);
      ctx.fillStyle = "#8a969e"; ctx.font = `10px ${MONO}`;
      ctx.fillText(`SPREAD ${fp(TICK * 2)}`, x0 + 4, yy + 28);
      yy += midH;
      for (let i = 0; i < LV; i++, yy += rh) row(yy, snap(price - TICK * (i + 1)), bids[i].q, cb[i], G);
    }
  }

  function frame(now) {
    const dt = Math.min((now - last) / 1000, 0.05); last = now;
    flash = Math.max(0, flash - dt * 4);
    acc += dt; ct += dt;
    const every = reduce ? 0.5 : 0.12;
    while (acc > every) { acc -= every; tick(); }
    if (ct > CANDLE_S) {
      ct = 0; cur = { o: price, h: price, l: price, c: price, v: 0 };
      candles.push(cur); if (candles.length > MAXC + 10) candles.shift();
    }
    draw(); raf = requestAnimationFrame(frame);
  }

  addEventListener("resize", () => { resize(); if (!raf) { if (!candles.length) seed(); draw(); } });

  return {
    idle() { resize(); if (!candles.length) seed(); draw(); },
    start() {
      if (raf) return;
      seed(); open0 = price; vol = nOrders = nTrades = 0; flash = acc = ct = 0;
      cur = { o: price, h: price, l: price, c: price, v: 0 }; candles.push(cur); live = true;
      $("tape").replaceChildren();
      ["v-orders", "v-trades", "v-vol"].forEach((id) => ($(id).textContent = "0"));
      $("v-price").textContent = "--"; $("v-chg").textContent = "0.00%";
      resize(); last = performance.now(); raf = requestAnimationFrame(frame);
    },
    stop() { cancelAnimationFrame(raf); raf = 0; live = false; },
  };
})();

/* ---------- backend ---------- */
const readJson = (r) => r.json().catch(() => null);
const jobIdOf = (j) => j?.job_id ?? j?.id ?? null;
let polling = false;

function finish(status, msg, phase) {
  stage.stop();
  setStatus(status, msg);
  setPhase(phase);
  setBusy(false);
  if (phase !== "done") stage.idle();
}

async function poll(expectedId = null) {
  if (polling) return;
  polling = true;
  let fails = 0;

  try {
    while (true) {
      let data;
      try {
        const r = await fetch(API.dashboard);
        if (!r.ok) throw new Error(`Could not retrieve dashboard data (HTTP ${r.status}).`);
        data = await r.json(); fails = 0; setConnection(true);
      } catch (err) {
        if (++fails >= MAX_FAILS) throw err;
        await sleep(POLL_MS); continue;
      }

      const job = data.job;
      if (!job) return finish("idle", "Waiting for simulation command", "idle");

      const stale = expectedId && jobIdOf(job) && jobIdOf(job) !== expectedId;

      if (stale || job.status === "queued" || job.status === "running") {
        setBusy(true, "SIMULATION RUNNING");
        setStatus("running", `Processing ${fN(job.total_orders)} orders`);
        setPhase("running"); stage.start();
        await sleep(POLL_MS); continue;
      }

      if (job.status === "completed" && job.metrics) {
        renderResults(job.metrics);
        return finish("completed", "Simulation completed successfully", "done");
      }

      if (job.status === "failed") {
        showError(job.error || "Unknown simulation error");
        return finish("failed", "Simulation failed", "idle");
      }

      return finish("failed", `Unexpected job status: ${job.status}`, "idle");
    }
  } catch (err) {
    setConnection(false);
    showError(err.message);
    finish("failed", "Unable to retrieve simulation status", "idle");
  } finally {
    polling = false;
  }
}

$("simulation-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if ($("start-button").disabled) return;
  clearError();

  const total = Number($("order-count").value);
  if (!Number.isSafeInteger(total) || total < MIN || total > MAX) {
    showError(`Order count must be a whole number between ${fN(MIN)} and ${fN(MAX)}.`);
    return $("order-count").focus();
  }

  setBusy(true, "STARTING...");
  setStatus("queued", "Submitting simulation request");
  setPhase("running"); stage.start();

  try {
    const r = await fetch(API.start, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ total_orders: total }),
    });
    const data = await readJson(r);
    if (!r.ok) throw new Error(data?.detail || `Could not start simulation (HTTP ${r.status}).`);

    setStatus("running", `Job ID: ${data?.job_id ?? "unknown"}`);
    await poll(data?.job_id ?? null);
  } catch (err) {
    showError(err.message);
    finish("failed", "Could not start simulation", "idle");
  }
});

async function init() {
  stage.idle();
  try {
    const r = await fetch(API.health);
    if (!r.ok) throw new Error();
    setConnection(true);
    await poll(); // resumes UI if a job is already running or finished
  } catch {
    setConnection(false);
    showError("Cannot connect to ChronosMatch backend.");
  }
}

init();