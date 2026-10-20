import { LANGUAGES, pickLanguage, setLanguage, t } from "./i18n.js";
import { ABPlayer } from "./player.js";
import { drawSpectrogram, drawWaveform } from "./spectro.js";

const $ = (id) => document.getElementById(id);
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const lufs = (n) => `${n.toFixed(1)}`;

const state = { file: null, demo: false, player: null, job: null, report: null, stageNames: [] };

async function init() {
  const select = $("lang");
  for (const [code, name] of Object.entries(LANGUAGES)) select.add(new Option(name, code));
  const lang = await setLanguage(pickLanguage());
  select.value = lang;
  select.addEventListener("change", () => setLanguage(select.value));
  $("theme").addEventListener("click", toggleTheme);

  try {
    const response = await fetch("api/health");
    if (!response.ok) throw new Error("no server");
    const health = await response.json();
    $("version").textContent = `v${health.version}`;
    if (!health.ffmpeg) showError(t("err.ffmpeg"));
  } catch {
    state.demo = true;
  }
  document.documentElement.dataset.mode = state.demo ? "demo" : "app";
  if (state.demo) enterDemo();
  bindSetup();
  document.addEventListener("languagechange", () => { updateEngineHint(); if (state.report) renderStats(state.report); });
  updateEngineHint();
  document.documentElement.dataset.ready = "1";
  if (new URLSearchParams(location.search).has("sample") && state.demo) loadSample();
}

function toggleTheme() {
  const dark = matchMedia("(prefers-color-scheme: dark)").matches;
  const now = document.documentElement.dataset.theme || (dark ? "dark" : "light");
  const next = now === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("cleartake.theme", next);
}

function enterDemo() {
  $("demo-banner").hidden = false;
  document.querySelector(".drop").hidden = true;
  document.querySelector(".options").hidden = true;
  $("go").hidden = true;
  $("sample").hidden = false;
  $("sample").classList.replace("ghost", "primary");
  $("sample").addEventListener("click", loadSample);
}

function updateEngineHint() {
  const engine = document.querySelector("input[name=engine]:checked").value;
  $("engine-hint").textContent = t(`engine.${engine}.hint`);
}

function bindSetup() {
  const drop = $("drop"), input = $("file");
  const choose = (file) => {
    state.file = file;
    $("file-name").hidden = !file;
    $("file-name").textContent = file ? file.name : "";
    drop.classList.toggle("has-file", !!file);
    $("go").disabled = !file;
  };
  input.addEventListener("change", () => choose(input.files[0] || null));
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  for (const name of ["dragenter", "dragover"]) drop.addEventListener(name, (e) => { e.preventDefault(); drop.classList.add("over"); });
  for (const name of ["dragleave", "drop"]) drop.addEventListener(name, () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer.files[0]) choose(e.dataTransfer.files[0]); });
  document.querySelectorAll("input[name=engine]").forEach((r) => r.addEventListener("change", updateEngineHint));
  $("strength").addEventListener("input", () => { $("strength-out").textContent = `${$("strength").value}%`; });
  $("go").addEventListener("click", submit);
  $("again").addEventListener("click", reset);
  $("retry").addEventListener("click", reset);
}

function show(...ids) {
  for (const id of ["intro", "setup", "progress", "result"]) $(id).hidden = !ids.includes(id);
}

function reset() {
  state.player?.stop(); state.player = null; state.report = null;
  $("error").hidden = true; $("retry").hidden = true;
  show("intro", "setup");
}

function showError(message) {
  show("progress");
  $("progress-title").textContent = "";
  $("stages").innerHTML = "";
  $("queue").textContent = "";
  $("error").textContent = t("err.generic", { message });
  $("error").hidden = false;
  $("retry").hidden = false;
}

async function submit() {
  const form = new FormData();
  form.append("file", state.file);
  form.append("engine", document.querySelector("input[name=engine]:checked").value);
  form.append("strength", String($("strength").value / 100));
  form.append("preset", $("preset").value);
  form.append("check", $("check").checked);
  $("go").disabled = true;
  try {
    const response = await fetch("api/jobs", { method: "POST", body: form });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || response.statusText);
    state.job = (await response.json()).id;
  } catch (err) {
    $("go").disabled = false;
    return showError(err.message);
  }
  show("progress");
  $("error").hidden = true; $("retry").hidden = true;
  poll();
}

function renderStages(job) {
  const stages = job.stages.filter((name) => name !== "check" || $("check").checked);
  const at = stages.indexOf(job.stage);
  $("progress-title").textContent = job.state === "queued" ? t("stage.queued") : t(`stage.${job.stage || "decode"}`);
  $("stages").innerHTML = "";
  stages.forEach((name, i) => {
    const li = document.createElement("li");
    li.className = job.state === "queued" ? "" : i < at || job.state === "done" ? "done" : i === at ? "active" : "";
    li.innerHTML = `<i class="dot"></i><span>${t(`stage.${name}`)}</span>`;
    $("stages").append(li);
  });
  $("queue").textContent = job.state === "queued" ? t("queue.wait", { n: job.queue_position }) : "";
}

async function poll() {
  for (;;) {
    const job = await (await fetch(`api/jobs/${state.job}`)).json();
    if (job.state === "error") return showError(job.error);
    renderStages(job);
    if (job.state === "done") {
      const base = `api/jobs/${state.job}`;
      $("dl-audio").href = `${base}/download`;
      $("dl-report").href = `${base}/report.json`;
      return showResult(`${base}/original.wav`, `${base}/enhanced.wav`, job.report);
    }
    await new Promise((resolve) => setTimeout(resolve, 600));
  }
}

async function loadSample() {
  $("dl-audio").href = "demo/enhanced.mp3";
  $("dl-report").href = "demo/report.json";
  try {
    const report = await (await fetch("demo/report.json")).json();
    await showResult("demo/original.mp3", "demo/enhanced.mp3", report);
  } catch (err) {
    showError(err.message);
  }
}

async function showResult(originalUrl, enhancedUrl, report) {
  const player = new ABPlayer(...(await decodePair(originalUrl, enhancedUrl)));
  state.player = player; state.report = report;
  show("result");
  drawStage(player);
  renderStats(report);
  renderDrift(report.drift);
  setMode("enhanced");
  updateTime();
  bindPlayer(player);
}

async function decodePair(a, b) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const load = async (url) => ctx.decodeAudioData(await (await fetch(url)).arrayBuffer());
  const pair = await Promise.all([load(a), load(b)]);
  ctx.close();
  return pair;
}

function drawStage(player) {
  const stage = $("stage");
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.floor(stage.clientWidth * ratio), height = Math.floor(stage.clientHeight * ratio);
  const { original, enhanced } = player.buffers;
  drawSpectrogram($("spec-original"), original.getChannelData(0), original.sampleRate, width, height);
  drawSpectrogram($("spec-enhanced"), enhanced.getChannelData(0), enhanced.sampleRate, width, height);
  drawWaveform($("wave"), enhanced.getChannelData(0), width, Math.floor(height * 0.34));
}

function setMode(mode) {
  state.player?.setMode(mode);
  document.querySelector(".ab").dataset.mode = mode;
  $("ab-a").setAttribute("aria-pressed", mode === "original");
  $("ab-b").setAttribute("aria-pressed", mode === "enhanced");
  $("spec-original").style.opacity = mode === "original" ? 1 : 0;
  $("spec-enhanced").style.opacity = mode === "enhanced" ? 1 : 0;
}

function updateTime() {
  const p = state.player;
  if (!p) return;
  $("time").textContent = `${fmtTime(p.position)} / ${fmtTime(p.duration)}`;
  $("playhead").style.left = `${(p.position / p.duration) * 100}%`;
  $("play-icon").setAttribute("d", p.playing ? "M6 5h4v14H6zm8 0h4v14h-4z" : "M8 5v14l11-7z");
  $("play").setAttribute("aria-label", p.playing ? "Pause" : "Play");
}

let bound = false;
function bindPlayer(player) {
  const tick = () => { if (state.player === player) { updateTime(); requestAnimationFrame(tick); } };
  tick();
  if (bound) return;
  bound = true;
  const stage = $("stage");
  const toggle = () => (state.player.playing ? state.player.pause() : state.player.play());
  $("play").addEventListener("click", toggle);
  $("ab-a").addEventListener("click", () => setMode("original"));
  $("ab-b").addEventListener("click", () => setMode("enhanced"));
  $("loop").addEventListener("change", applyRegion);
  $("clear").addEventListener("click", () => setRegion(null));
  document.addEventListener("keydown", (e) => {
    if ($("result").hidden || /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName) && e.key === " ") return;
    if (e.key === " ") { e.preventDefault(); toggle(); }
    else if (e.key.toLowerCase() === "b") setMode(state.player.mode === "enhanced" ? "original" : "enhanced");
    else if (e.key === "Escape") setRegion(null);
  });
  let drag = null;
  const at = (e) => { const r = stage.getBoundingClientRect(); return Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1); };
  stage.addEventListener("pointerdown", (e) => { drag = { from: at(e), moved: false }; stage.setPointerCapture(e.pointerId); });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const now = at(e);
    if (Math.abs(now - drag.from) * stage.clientWidth > 5) drag.moved = true;
    if (drag.moved) drawRegion(Math.min(drag.from, now), Math.max(drag.from, now));
  });
  stage.addEventListener("pointerup", (e) => {
    if (!drag) return;
    const now = at(e), d = state.player.duration;
    if (drag.moved) setRegion([Math.min(drag.from, now) * d, Math.max(drag.from, now) * d]);
    else state.player.seek(now * d);
    drag = null;
  });
}

function drawRegion(lo, hi) {
  const el = $("region");
  el.hidden = false;
  el.style.left = `${lo * 100}%`;
  el.style.width = `${(hi - lo) * 100}%`;
}

function setRegion(region) {
  const p = state.player;
  $("region").hidden = !region;
  $("clear").hidden = !region;
  if (region) {
    drawRegion(region[0] / p.duration, region[1] / p.duration);
    $("loop").checked = true;
    p.region = region;
    p.setRegion(region, true);
    p.seek(region[0]);
  } else p.setRegion(null, false);
}

function applyRegion() { state.player.setRegion(state.player.region, $("loop").checked); }

function renderStats(report) {
  const { before, after, target } = report.loudness;
  $("stat-lufs").textContent = `${lufs(before.integrated)} → ${lufs(after.integrated)}`;
  $("stat-lufs-sub").textContent = target ? t("stats.target", { n: lufs(target[0]) }) : t("stats.untouched");
  $("stat-peak").textContent = `${lufs(after.true_peak)} dBTP`;
  $("stat-peak-sub").textContent = t("stats.before", { n: lufs(before.true_peak) });
  $("stat-speed").textContent = t("stats.speed.value", { x: report.speed_x_realtime });
  $("stat-device").textContent = `${report.model.name}, ${report.device}`;
}

function renderDrift(drift) {
  const chip = $("drift-chip"), box = $("transcript");
  box.textContent = "";
  $("legend").hidden = true;
  if (!drift) {
    chip.textContent = t("drift.off"); chip.className = "chip";
    $("drift-explain").hidden = true;
    return;
  }
  $("drift-explain").hidden = false;
  const n = drift.changed + drift.dropped + drift.added;
  chip.textContent = n === 0 ? t("drift.clean") : t("drift.some", { n });
  chip.className = `chip ${n === 0 ? "ok" : "warn"}`;
  const marks = drift.changes;
  const pending = marks.filter((c) => c.kind === "dropped");
  const span = (text, cls, start) => {
    const el = document.createElement("span");
    el.textContent = `${text} `;
    if (cls) el.className = cls;
    el.addEventListener("click", () => { state.player.seek(start); state.player.play(start); });
    box.append(el);
  };
  for (const word of drift.transcript_after || []) {
    while (pending.length && pending[0].start <= word.start) span(pending.shift().before, "dropped", word.start);
    const hit = marks.find((c) => c.kind !== "dropped" && word.start >= c.start - 0.01 && word.end <= c.end + 0.01);
    span(word.text, hit ? hit.kind : "", word.start);
  }
  for (const c of pending) span(c.before, "dropped", c.start);
  $("legend").hidden = n === 0;
}

init();
