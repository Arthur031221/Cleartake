import { LANGUAGES, pickLanguage, setLanguage, t } from "./i18n.js";
import { ABPlayer } from "./player.js";
import { drawSpectrogram, drawWaveform } from "./spectro.js";

const $ = (id) => document.getElementById(id);
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const lufs = (n) => `${n.toFixed(1)}`;

const state = { files: [], jobs: [], demo: false, player: null, report: null, options: null };
const ACTIVE = ["pending", "uploading", "queued", "running"];

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

let resizing = 0;
window.addEventListener("resize", () => {
  clearTimeout(resizing);
  resizing = setTimeout(() => { if (state.player && !$("result").hidden) drawStage(state.player); }, 150);
});

function updateEngineHint() {
  const engine = document.querySelector("input[name=engine]:checked").value;
  $("engine-hint").textContent = t(`engine.${engine}.hint`);
}

function bindSetup() {
  const drop = $("drop"), input = $("file");
  const choose = (files) => {
    state.files = [...files];
    const name = state.files.length > 1 ? t("drop.count", { n: state.files.length }) : state.files[0]?.name || "";
    $("file-name").hidden = !state.files.length;
    $("file-name").textContent = name;
    drop.classList.toggle("has-file", state.files.length > 0);
    $("go").disabled = !state.files.length;
  };
  input.addEventListener("change", () => choose(input.files));
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  for (const name of ["dragenter", "dragover"]) drop.addEventListener(name, (e) => { e.preventDefault(); drop.classList.add("over"); });
  for (const name of ["dragleave", "drop"]) drop.addEventListener(name, () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer.files.length) choose(e.dataTransfer.files); });
  document.querySelectorAll("input[name=engine]").forEach((r) => r.addEventListener("change", updateEngineHint));
  $("strength").addEventListener("input", () => { $("strength-out").textContent = `${$("strength").value}%`; });
  $("go").addEventListener("click", submit);
  $("again").addEventListener("click", reset);
  $("retry").addEventListener("click", reset);
  $("back").addEventListener("click", backToFiles);
  $("cancel").addEventListener("click", () => cancelJob(state.jobs[0]));
  $("files").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-act]");
    if (!button) return;
    const job = state.jobs[Number(button.dataset.index)];
    if (button.dataset.act === "cancel") cancelJob(job);
    else if (button.dataset.act === "review") openResult(job);
  });
  document.addEventListener("languagechange", () => { if (state.jobs.length) renderProgress(); });
}

function show(...ids) {
  for (const id of ["intro", "setup", "progress", "result"]) $(id).hidden = !ids.includes(id);
}

function reset() {
  for (const job of state.jobs) if (ACTIVE.includes(job.status)) cancelJob(job);
  state.jobs = [];
  disposePlayer(); state.report = null;
  $("error").hidden = true; $("retry").hidden = true;
  show("intro", "setup");
}

function disposePlayer() {
  state.player?.dispose();
  state.player = null;
}

function showError(message) {
  show("progress");
  $("progress-title").textContent = "";
  $("stages").innerHTML = "";
  $("files").innerHTML = "";
  $("queue").textContent = "";
  $("cancel").hidden = true;
  $("error").textContent = t("err.generic", { message });
  $("error").hidden = false;
  $("retry").hidden = false;
}

const jobUrl = (job, tail = "") => `api/jobs/${job.id}${tail}`;

function submit() {
  state.options = {
    engine: document.querySelector("input[name=engine]:checked").value,
    strength: String($("strength").value / 100),
    preset: $("preset").value,
    check: String($("check").checked),
  };
  state.jobs = state.files.map((file) => ({ file, id: null, status: "pending", pct: 0, stage: "", position: 0, error: "", report: null }));
  $("go").disabled = true;
  $("error").hidden = true; $("retry").hidden = true;
  show("progress");
  renderProgress();
  const jobs = state.jobs;
  (async () => {
    for (const job of jobs) {
      if (job.status !== "pending" || jobs !== state.jobs) continue;
      job.status = "uploading";
      renderProgress();
      try {
        job.id = await upload(job);
        job.status = "queued";
      } catch (err) {
        job.status = err instanceof Cancel ? "cancelled" : "error";
        job.error = err.message;
      }
      renderProgress();
      if (job.id && jobs === state.jobs) startPolling();
    }
  })();
}

class Cancel extends Error {}

function upload(job) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", job.file);
    for (const [key, value] of Object.entries(state.options)) form.append(key, value);
    const xhr = new XMLHttpRequest();
    job.xhr = xhr;
    xhr.open("POST", "api/jobs");
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      job.pct = Math.round((e.loaded / e.total) * 100);
      renderProgress();
    };
    xhr.onload = () => {
      let body = {};
      try { body = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status === 202) resolve(body.id);
      else reject(new Error(body.detail || xhr.statusText || String(xhr.status)));
    };
    xhr.onerror = () => reject(new Error(t("err.lost")));
    xhr.onabort = () => reject(new Cancel());
    xhr.send(form);
  });
}

async function cancelJob(job) {
  if (!job || !ACTIVE.includes(job.status)) return;
  if (job.status === "pending") job.status = "cancelled";
  else if (job.status === "uploading") job.xhr.abort();
  else {
    try {
      const answer = await (await fetch(jobUrl(job), { method: "DELETE" })).json();
      job.status = answer.cancelling ? "cancelling" : "cancelled";
    } catch {
      job.status = "error"; job.error = t("err.lost");
    }
  }
  renderProgress();
}

function rowStatus(job) {
  switch (job.status) {
    case "pending": return t("file.waiting");
    case "uploading": return t("file.uploading", { pct: job.pct });
    case "queued": return job.position ? t("queue.wait", { n: job.position }) : t("stage.queued");
    case "running": return t(`stage.${job.stage || "decode"}`);
    case "cancelling": return t("file.cancelling");
    case "done": return t("file.done");
    case "cancelled": return t("file.cancelled");
    default: return t("err.generic", { message: job.error });
  }
}

function renderProgress() {
  const jobs = state.jobs;
  if (!jobs.length) return;
  const single = jobs.length === 1, job = jobs[0];
  $("stages").hidden = !single;
  $("files").hidden = single;
  $("cancel").hidden = !(single && ACTIVE.includes(job.status));
  $("error").hidden = true;
  const finished = jobs.every((j) => !ACTIVE.includes(j.status) && j.status !== "cancelling");
  $("retry").hidden = !finished;
  $("retry").textContent = t(single ? "download.another" : "batch.again");
  if (single) {
    $("progress-title").textContent = ["uploading", "pending"].includes(job.status)
      ? t("file.uploading", { pct: job.pct }) : rowStatus(job);
    renderStages(job);
    if (job.status === "error") { $("error").textContent = t("err.generic", { message: job.error }); $("error").hidden = false; }
    return;
  }
  $("progress-title").textContent = t("batch.title", { done: jobs.filter((j) => j.status === "done").length, n: jobs.length });
  $("queue").textContent = "";
  $("files").innerHTML = "";
  jobs.forEach((j, i) => {
    const li = document.createElement("li");
    li.dataset.status = j.status;
    const name = document.createElement("span");
    name.className = "file-label"; name.textContent = j.file.name;
    const status = document.createElement("span");
    status.className = "file-status"; status.textContent = rowStatus(j);
    li.append(name, status);
    const add = (act, text, aria) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost small"; b.dataset.act = act; b.dataset.index = i;
      b.textContent = text; if (aria) b.setAttribute("aria-label", `${aria}: ${j.file.name}`);
      li.append(b);
    };
    if (j.status === "done") {
      add("review", t("file.review"));
      const a = document.createElement("a");
      a.className = "ghost small btn"; a.href = jobUrl(j, "/download"); a.textContent = t("file.download"); a.setAttribute("download", "");
      li.append(a);
    } else if (ACTIVE.includes(j.status)) add("cancel", "\u00d7", t("file.cancel"));
    $("files").append(li);
  });
}

function renderStages(job) {
  const stages = ["decode", "enhance", "finish", "check", "write"].filter((name) => name !== "check" || state.options.check === "true");
  const at = stages.indexOf(job.stage);
  const waiting = job.status !== "running" && job.status !== "done";
  $("stages").innerHTML = "";
  stages.forEach((name, i) => {
    const li = document.createElement("li");
    li.className = waiting ? "" : i < at || job.status === "done" ? "done" : i === at ? "active" : "";
    li.innerHTML = `<i class="dot"></i><span>${t(`stage.${name}`)}</span>`;
    $("stages").append(li);
  });
  $("queue").textContent = job.status === "queued" && job.position ? t("queue.wait", { n: job.position }) : "";
}

let polledJobs = null;
async function startPolling() {
  const jobs = state.jobs;
  if (polledJobs === jobs) return;
  polledJobs = jobs;
  let failures = 0;
  while (jobs === state.jobs) {
    const live = jobs.filter((j) => j.id && ["queued", "running", "cancelling"].includes(j.status));
    if (!live.length && jobs.every((j) => !ACTIVE.includes(j.status))) break;
    try {
      await Promise.all(live.map((j) => refresh(j)));
      failures = 0;
    } catch {
      if (++failures >= 5) for (const j of live) { j.status = "error"; j.error = t("err.lost"); }
    }
    if (jobs === state.jobs) renderProgress();
    if (jobs.length === 1 && jobs[0].status === "done" && jobs === state.jobs) openResult(jobs[0]);
    await new Promise((resolve) => setTimeout(resolve, 600));
  }
  if (polledJobs === jobs) polledJobs = null;
}

async function refresh(job) {
  const response = await fetch(jobUrl(job));
  if (response.status === 404) { job.status = "error"; job.error = t("err.gone"); return; }
  if (!response.ok) throw new Error(response.statusText);
  const data = await response.json();
  job.stage = data.stage; job.position = data.queue_position;
  if (data.state === "error") { job.status = "error"; job.error = data.error; }
  else if (data.state === "cancelled") job.status = "cancelled";
  else if (data.state === "done") { job.status = "done"; job.report = data.report; }
  else if (job.status !== "cancelling") job.status = data.state;
}

function openResult(job) {
  $("dl-audio").href = jobUrl(job, "/download");
  $("dl-report").href = jobUrl(job, "/report.json");
  $("back").hidden = state.jobs.length < 2;
  $("again").hidden = state.jobs.length > 1;
  showResult(jobUrl(job, "/original.wav"), jobUrl(job, "/enhanced.wav"), job.report).catch((err) => {
    if (state.jobs.length < 2) return showError(err.message);
    job.status = "error"; job.error = err.message;
    backToFiles();
  });
}

function backToFiles() {
  state.player?.stop();
  show("progress");
  renderProgress();
}

async function loadSample() {
  $("back").hidden = true;
  $("again").hidden = false;
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
  const buffers = await decodePair(originalUrl, enhancedUrl);
  disposePlayer();
  const player = new ABPlayer(...buffers);
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
  $("play").setAttribute("aria-label", t(p.playing ? "player.pause" : "player.play"));
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
    const tag = document.activeElement.tagName;
    if ($("result").hidden || e.ctrlKey || e.metaKey || e.altKey) return;
    if (/INPUT|SELECT|TEXTAREA/.test(tag) || (e.key === " " && /BUTTON|A/.test(tag)) || document.activeElement.getAttribute("role") === "button") return;
    if (e.key === " ") { e.preventDefault(); toggle(); }
    else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      if (document.activeElement !== stage) return;
      e.preventDefault();
      state.player.seek(state.player.position + (e.key === "ArrowRight" ? 5 : -5));
    }
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
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    const play = () => { state.player.seek(start); state.player.play(start); };
    el.addEventListener("click", play);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); play(); } });
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
