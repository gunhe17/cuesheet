// #
// cuesheet — 눈금 축 + 미니맵. 2초 폴링으로 전체를 다시 그린다

import * as api from "../core/api.js";
import * as session from "../core/session.js";
import * as route from "../shell/route.js";
import { layout, isMine, hhmm, clock } from "../core/schedule.js";

const SETTLE_MS = 900;
const POLL_MS = 2000;
const FAIL_LIMIT = 3;

let poll = null;
let settle = null;
let fails = 0;
let snapshot = null;


// #
// lifecycle

export function wire() {
  document.getElementById("btn-timeline-close").addEventListener("click", leave);
  document.getElementById("btn-start").addEventListener("click", () => command("/run"));
  document.getElementById("btn-advance").addEventListener("click", () => command("/run/advance", expected()));
  document.getElementById("btn-rewind").addEventListener("click", () => command("/run/rewind", expected()));
  rail();
}

export function enter() {
  stop();
  connection(true);
  fetchOnce();
  poll = setInterval(fetchOnce, POLL_MS);
}

export function stop() {
  clearInterval(poll);
  poll = null;
  fails = 0;
  snapshot = null;
}

function leave() {
  stop();
  session.write({ ...session.read(), cuesheet_id: null });
  route.go(route.path.home());
}


// #
// fetch

function id() {
  return session.read()?.cuesheet_id;
}

async function fetchOnce() {
  try {
    snapshot = await api.get(`/cuesheets/${id()}`);
    fails = 0;
    connection(true);
    render(snapshot);
  } catch {
    // 화면은 마지막 응답 그대로 둔다 — 진행 중에 비면 자기 순서를 놓친다
    fails += 1;
    if (fails >= FAIL_LIMIT || !snapshot) connection(false);
  }
}

function expected() {
  return { expected_cue_id: snapshot?.cuesheet.current_cue_id };
}

async function command(suffix, body) {
  const buttons = document.querySelectorAll("#manager button");
  for (const button of buttons) button.disabled = true;
  try {
    snapshot = await api.post(`/cuesheets/${id()}${suffix}`, body ?? {});
    render(snapshot);
  } finally {
    for (const button of buttons) button.disabled = false;
  }
}


// #
// render

const STATE = { ready: "준비중", running: "진행중", ended: "종료" };

function render(data) {
  const { cuesheet, cues, me } = data;
  const shown = cues.filter((cue) => cue.eta);

  document.getElementById("timeline-title").textContent = cuesheet.title;

  const state = document.getElementById("run-state");
  state.textContent = STATE[cuesheet.state];
  state.dataset.state = cuesheet.state;

  const delay = document.getElementById("now-delay");
  delay.hidden = !cuesheet.delay_sec;
  delay.textContent = `＋${clock(cuesheet.delay_sec)} 지연`;

  const folded = document.getElementById("timeline-folded");
  folded.hidden = cues.length === shown.length;
  folded.textContent = `지난 큐 ${cues.length - shown.length}개`;

  axis(cuesheet, shown, me);
  segments(cues, me);
  manager(cuesheet, me);
}

function manager(cuesheet, me) {
  document.getElementById("manager").hidden = !me?.can_advance || cuesheet.state === "ended";
  document.getElementById("btn-start").hidden = cuesheet.state !== "ready";
  document.getElementById("btn-advance").hidden = cuesheet.state !== "running";
  document.getElementById("btn-rewind").hidden = cuesheet.state !== "running";
}

function connection(alive) {
  const node = document.getElementById("conn");
  node.textContent = alive ? "연결됨" : "연결 끊김";
  node.dataset.state = alive ? "running" : "ended";
}


// #
// axis — 좌표는 core/schedule.js 가 계산한다. 여기는 그리기만

function axis(cuesheet, cues, me) {
  const track = document.getElementById("timeline-track");
  track.replaceChildren();
  if (cues.length === 0) { track.style.height = "0px"; return; }

  const placed = layout(cues);
  const total = placed[placed.length - 1].top + placed[placed.length - 1].height;
  track.style.height = `${total}px`;

  for (const { cue, top, height, stretched } of placed) {
    const label = document.createElement("span");
    label.className = "e-tick";
    label.style.top = `${top}px`;
    label.textContent = hhmm(new Date(cue.eta));
    track.append(label);

    const node = document.getElementById("tpl-axis-cue").content.cloneNode(true);
    const block = node.querySelector(".b-axis-cue");
    block.style.top = `${top}px`;
    block.style.height = `${height - 1}px`;
    block.dataset.mine = String(isMine(cue, me));
    block.dataset.color = cue.color || "slate";
    block.dataset.stretched = String(stretched);
    if (cue.id === cuesheet.current_cue_id) block.dataset.state = "current";
    node.querySelector("b").textContent = cue.title;
    node.querySelector("span").textContent = clock(cue.planned_sec);
    track.append(node);
  }

  now(placed, total, track);
}

// 현재 시각은 늘어난 블록 때문에 시간축과 어긋나므로, 진행 중인 큐 안에서 비례로 찍는다
function now(placed, total, track) {
  const at = Date.now();
  const inside = placed.find(({ cue, height }) => {
    const start = new Date(cue.eta).getTime();
    return at >= start && at < start + cue.planned_sec * 1000 && height > 0;
  });
  if (!inside) return;

  const start = new Date(inside.cue.eta).getTime();
  const ratio = (at - start) / (inside.cue.planned_sec * 1000);

  const marker = document.createElement("div");
  marker.className = "now";
  marker.style.top = `${inside.top + inside.height * ratio}px`;
  marker.innerHTML = "<b></b><i></i>";
  marker.querySelector("b").textContent = hhmm(new Date());
  track.append(marker);
}


// #
// rail — 전체 큐시트를 화면 높이에 압축. 여기는 비율을 깨지 않는다

function segments(cues, me) {
  const track = document.getElementById("rail-track");
  track.replaceChildren();

  for (const cue of cues) {
    const seg = document.createElement("i");
    seg.className = "seg";
    seg.style.flex = `${cue.planned_sec} 0 0`;
    seg.dataset.color = cue.color || "slate";
    seg.dataset.mine = String(isMine(cue, me));
    track.append(seg);
  }
  sync();
}

function rail() {
  const pane = document.getElementById("timeline-axis");
  const hit = document.getElementById("rail-hit");

  pane.addEventListener("scroll", () => { sync(); wake(); }, { passive: true });

  let dragging = false;
  hit.addEventListener("pointerdown", (event) => {
    dragging = true;
    hit.setPointerCapture(event.pointerId);
    jump(event.clientY);
    wake();
    event.preventDefault();
  });
  hit.addEventListener("pointermove", (event) => { if (dragging) { jump(event.clientY); wake(); } });
  hit.addEventListener("pointerup", () => { dragging = false; });
  hit.addEventListener("pointercancel", () => { dragging = false; });
}

function sync() {
  const pane = document.getElementById("timeline-axis");
  const bar = document.getElementById("rail");
  const thumb = document.getElementById("rail-thumb");

  const visible = pane.clientHeight;
  const content = pane.scrollHeight;
  const height = bar.clientHeight;
  if (!content || !height) return;

  const size = Math.max(24, height * (visible / content));
  const range = content - visible;
  const ratio = range > 0 ? pane.scrollTop / range : 0;

  thumb.style.height = `${size}px`;
  thumb.style.top = `${(height - size) * ratio}px`;
}

function jump(clientY) {
  const pane = document.getElementById("timeline-axis");
  const bar = document.getElementById("rail");
  const thumb = document.getElementById("rail-thumb");

  const box = bar.getBoundingClientRect();
  const size = thumb.offsetHeight;
  const ratio = Math.min(1, Math.max(0, (clientY - box.top - size / 2) / Math.max(1, bar.clientHeight - size)));
  pane.scrollTop = ratio * (pane.scrollHeight - pane.clientHeight);
}

function wake() {
  const bar = document.getElementById("rail");
  bar.classList.add("live");
  clearTimeout(settle);
  settle = setTimeout(() => bar.classList.remove("live"), SETTLE_MS);
}
