// #
// lab — 목업 여섯 안을 web/ 컴포넌트로 그린다. 서버 대신 fixture 를 읽는다

import * as fixture from "./fixture.js";
import { layout, isMine, hhmm, hhmmss, clock } from "../core/schedule.js";

const CASES = [
  { key: "A", label: "조밀 리스트", body: dense,
    note: "한 줄에 순번·시각·제목·길이만. 전체 흐름이 제일 빨리 읽힌다" },
  { key: "B", label: "지금 & 다음", body: nowNext, foot: manager,
    note: "화면 절반을 진행 중인 큐 하나에 쓴다. 카운트다운은 로컬 시계" },
  { key: "C", label: "시간 비례 타임라인", body: axis,
    note: "블록 높이 = 소요시간. v-timeline 이 이미 쓰는 s-axis·b-axis-cue 그대로" },
  { key: "D", label: "접히는 행", body: expand,
    note: "탭하면 그 자리에서 task 가 펼쳐진다. details 만으로 동작" },
  { key: "E", label: "가로 스크롤 표", body: table,
    note: "시각 열만 고정하고 나머지를 민다. 한 손 조작에는 맞지 않는다" },
  { key: "F", label: "코너별 묶기", body: segments,
    note: "코너 헤더에 누계. 코너는 도메인에 없는 필드다" },
];

// 애플의 에셋은 가져올 수 없다 — 묶음 목록의 얼개와 치수만 옮겼다
const BORROWED = [
  { key: "S1", label: "설정", body: settings,
    note: "그룹이 카드, 구분선은 라벨에 맞춰 들어간다. 값은 오른쪽, 꺾쇠는 그 뒤" },
  { key: "S2", label: "큐 편집", body: editor,
    note: "같은 패턴을 큐 상세에 얹은 것. D 안이 펼치던 내용이 한 화면이 된다" },
];

let state = "running";
let data = null;
let ticker = null;


// #
// render

function render() {
  data = fixture.snapshot(state);

  document.getElementById("deck").replaceChildren(...CASES.map(build));
  document.getElementById("borrowed").replaceChildren(...BORROWED.map(build));

  restartTicker();
  requestAnimationFrame(sync);
}

function build(spec) {
  const node = document.getElementById("tpl-lab-case").content.cloneNode(true);
  const { cuesheet } = data;

  node.querySelector("[data-key]").textContent = spec.key;
  node.querySelector("[data-label]").textContent = spec.label;
  node.querySelector("[data-note]").textContent = spec.note;
  node.querySelector("[data-title]").textContent = cuesheet.title;

  const badge = node.querySelector("[data-run-state]");
  badge.textContent = fixture.STATE_LABEL[cuesheet.state];
  badge.dataset.state = cuesheet.state;

  const delay = node.querySelector("[data-delay]");
  delay.hidden = !cuesheet.delay_sec;
  delay.textContent = `＋${clock(cuesheet.delay_sec)} 지연`;

  const phone = node.querySelector(".s-phone");
  phone.append(spec.body());
  if (spec.foot) phone.append(spec.foot());

  return node;
}

function screen(...children) {
  const node = document.createElement("div");
  node.className = "screen";
  node.append(...children);
  return node;
}

function row(cue) {
  const node = document.getElementById("tpl-lab-row").content.cloneNode(true);
  const block = node.querySelector(".b-row");

  block.dataset.color = cue.color || "slate";
  block.dataset.mine = String(isMine(cue, data.me));
  if (cue.id === data.cuesheet.current_cue_id) block.dataset.state = "current";
  else if (!cue.eta) block.dataset.state = "done";

  node.querySelector("[data-seq]").textContent = cue.seq;
  node.querySelector("[data-eta]").textContent = cue.eta ? hhmmss(new Date(cue.eta)) : "—";
  node.querySelector("[data-title]").textContent = cue.title;
  node.querySelector("[data-length]").textContent = clock(cue.planned_sec);

  return node;
}

function text(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
}


// #
// A — 조밀 리스트

function dense() {
  return screen(...data.cues.map(row));
}


// #
// B — 지금 & 다음. 카운트다운은 eta + planned_sec 을 로컬 시계로 센다

function nowNext() {
  const { cues, cuesheet } = data;
  const current = cues.find((cue) => cue.id === cuesheet.current_cue_id) || cues[0];
  const rest = cues.slice(cues.indexOf(current) + 1);

  const hero = document.createElement("section");
  hero.className = "s-hero";
  hero.append(
    text("p", "e-label", `${running() ? "진행 중" : fixture.STATE_LABEL[cuesheet.state]} · ${current.seq}/${cues.length}`),
    count(current),
    text("p", "e-heading", current.title),
    text("p", "e-caption", instruction(current)),
    progress(current),
  );

  const next = rest[0];
  return screen(
    hero,
    text("p", "e-label", next ? "다음" : "마지막 큐입니다"),
    ...(next ? [row(next)] : []),
    ...rest.slice(1).map(row),
  );
}

function count(cue) {
  const node = text("p", "e-count", clock(cue.planned_sec));
  node.dataset.countdown = cue.eta ? String(new Date(cue.eta).getTime() + cue.planned_sec * 1000) : "";
  return node;
}

function progress(cue) {
  const node = document.createElement("div");
  node.className = "b-progress";
  node.dataset.elapsed = cue.eta || "";
  node.dataset.planned = cue.planned_sec;
  node.append(document.createElement("i"));
  return node;
}

function instruction(cue) {
  return cue.tasks
    .filter((task) => data.me.role_ids.includes(task.role_id))
    .map((task) => `${fixture.ROLE_NAME[task.role_id]} · ${task.instruction}`)
    .join(" / ") || "담당 없음";
}

function manager() {
  const node = document.createElement("section");
  node.className = "s-manager";
  if (!data.me.can_advance || data.cuesheet.state === "ended") return node;

  const button = text("button", "e-action", running() ? "다음 순서" : "시작");
  button.type = "button";
  node.append(button);
  return node;
}


// #
// C — 시간 비례 타임라인. v-timeline 과 같은 컴포넌트·같은 좌표 변환

function axis() {
  const stage = document.createElement("div");
  stage.className = "stage";

  const pane = document.createElement("div");
  pane.className = "s-axis";
  const track = document.createElement("div");
  track.className = "track";
  pane.append(track);

  const shown = data.cues.filter((cue) => cue.eta);
  if (shown.length) blocks(track, shown);

  stage.append(pane, rail(data.cues));
  pane.addEventListener("scroll", () => sync(), { passive: true });
  return stage;
}

function blocks(track, cues) {
  const placed = layout(cues);
  const total = placed[placed.length - 1].top + placed[placed.length - 1].height;
  track.style.height = `${total}px`;

  for (const { cue, top, height, stretched } of placed) {
    const label = text("span", "e-tick", hhmm(new Date(cue.eta)));
    label.style.top = `${top}px`;
    track.append(label);

    const node = document.getElementById("tpl-lab-axis-cue").content.cloneNode(true);
    const block = node.querySelector(".b-axis-cue");
    block.style.top = `${top}px`;
    block.style.height = `${height - 1}px`;
    block.dataset.mine = String(isMine(cue, data.me));
    block.dataset.color = cue.color || "slate";
    block.dataset.stretched = String(stretched);
    if (cue.id === data.cuesheet.current_cue_id) block.dataset.state = "current";
    node.querySelector("b").textContent = cue.title;
    node.querySelector("span").textContent = clock(cue.planned_sec);
    track.append(node);
  }

  marker(placed, track);
}

// 현재 시각은 늘어난 블록 때문에 시간축과 어긋나므로, 진행 중인 큐 안에서 비례로 찍는다
function marker(placed, track) {
  const at = Date.now();
  const inside = placed.find(({ cue }) => {
    const start = new Date(cue.eta).getTime();
    return at >= start && at < start + cue.planned_sec * 1000;
  });
  if (!inside) return;

  const start = new Date(inside.cue.eta).getTime();
  const ratio = (at - start) / (inside.cue.planned_sec * 1000);

  const node = document.createElement("div");
  node.className = "now";
  node.style.top = `${inside.top + inside.height * ratio}px`;
  node.innerHTML = "<b></b><i></i>";
  node.querySelector("b").textContent = hhmm(new Date());
  track.append(node);
}

function rail(cues) {
  const bar = document.createElement("div");
  bar.className = "s-rail live";

  const track = document.createElement("div");
  track.className = "track";
  for (const cue of cues) {
    const seg = document.createElement("i");
    seg.className = "seg";
    seg.style.flex = `${cue.planned_sec} 0 0`;
    seg.dataset.color = cue.color || "slate";
    track.append(seg);
  }

  const thumb = document.createElement("div");
  thumb.className = "e-thumb";
  bar.append(track, thumb);
  return bar;
}

// 랩은 드래그를 붙이지 않는다 — 조작은 v-timeline 의 몫이고 여기는 비율만 본다
function sync() {
  for (const stage of document.querySelectorAll(".s-phone > .stage")) {
    const pane = stage.querySelector(".s-axis");
    const bar = stage.querySelector(".s-rail");
    const thumb = stage.querySelector(".e-thumb");
    if (!pane || !thumb) continue;

    const visible = pane.clientHeight;
    const content = pane.scrollHeight;
    const height = bar.clientHeight;
    if (!content || !height) continue;

    const size = Math.max(24, height * (visible / content));
    const range = content - visible;
    const ratio = range > 0 ? pane.scrollTop / range : 0;

    thumb.style.height = `${size}px`;
    thumb.style.top = `${(height - size) * ratio}px`;
  }
}


// #
// D — 접히는 행. 상세는 task + role 로만 채운다

function expand() {
  const list = document.createElement("div");
  list.className = "s-expand";

  for (const cue of data.cues) {
    const item = document.createElement("details");
    item.open = cue.id === data.cuesheet.current_cue_id;

    const summary = document.createElement("summary");
    summary.append(row(cue));

    item.append(summary, detail(cue), actions());
    list.append(item);
  }
  return screen(list);
}

function detail(cue) {
  const node = document.createElement("dl");
  node.className = "b-detail";

  node.append(text("dt", null, "길이"), text("dd", null, `${clock(cue.planned_sec)} · ${cue.color}`));
  for (const task of cue.tasks) {
    node.append(
      text("dt", null, fixture.ROLE_NAME[task.role_id]),
      text("dd", null, task.note ? `${task.instruction} — ${task.note}` : task.instruction),
    );
  }
  return node;
}

function actions() {
  const node = document.createElement("span");
  node.className = "s-actions-inline";
  for (const label of ["편집", "복제", "위로"]) {
    const button = text("button", "e-action-ghost", label);
    button.type = "button";
    node.append(button);
  }
  return node;
}


// #
// E — 가로 스크롤 표. 담당·지시·비고는 task 를 펼친 것이다

const COLUMNS = ["시각", "제목", "길이", "담당", "지시", "비고"];

function table() {
  const wrap = document.createElement("div");
  wrap.className = "s-table";

  const node = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  COLUMNS.forEach((label, index) => {
    const cell = text("th", null, label);
    if (index === 0) cell.dataset.frozen = "";
    headRow.append(cell);
  });
  head.append(headRow);

  const body = document.createElement("tbody");
  for (const cue of data.cues) {
    const first = cue.tasks[0];
    const line = document.createElement("tr");
    const cells = [
      cue.eta ? hhmmss(new Date(cue.eta)) : "—",
      cue.title,
      clock(cue.planned_sec),
      cue.tasks.map((task) => fixture.ROLE_NAME[task.role_id]).join(", ") || "—",
      first?.instruction || "—",
      first?.note || "—",
    ];
    cells.forEach((value, index) => {
      const cell = text("td", null, value);
      if (index === 0) cell.dataset.frozen = "";
      line.append(cell);
    });
    body.append(line);
  }

  node.append(head, body);
  wrap.append(node);
  return screen(wrap);
}


// #
// F — 코너별 묶기. segment 는 fixture 에만 있는 필드다

function segments() {
  const list = document.createElement("div");
  list.className = "s-segments";

  let current = null;
  for (const cue of data.cues) {
    if (cue.segment !== current) {
      current = cue.segment;
      list.append(header(data.cues, current));
    }
    list.append(row(cue));
  }
  return screen(list);
}

function header(cues, segment) {
  const total = cues
    .filter((cue) => cue.segment === segment)
    .reduce((sum, cue) => sum + cue.planned_sec, 0);

  const node = document.createElement("div");
  node.className = "b-segment";
  node.append(text("b", null, segment), text("span", null, clock(total)));
  return node;
}


// #
// settings — 차용한 묶음 목록. 화면에 쓰는 값은 여기서도 fixture 에서만 나온다

function settings() {
  const { cuesheet, participants, me } = data;

  return screen(
    group("큐시트", null, [
      setting({ label: "제목", value: cuesheet.title, symbol: "tag", tint: "blue" }),
      setting({ label: "시작 시각", value: hhmm(new Date(cuesheet.scheduled_at)), symbol: "clock", tint: "amber" }),
      setting({ label: "참가자", value: `${participants.length}명`, symbol: "person", tint: "teal" }),
    ]),
    group("내 역할", "색은 큐 종류라 역할과 무관합니다. 담당 여부는 진하기로만 드러납니다", [
      setting({ label: "맡은 역할", value: me.role_ids.map((id) => fixture.ROLE_NAME[id]).join(" · ") }),
      setting({ label: "담당 큐만 보기", accessory: toggle(false), tap: false }),
      setting({ label: "진행 권한", value: me.can_advance ? "총괄" : "없음", accessory: null, tap: false }),
    ]),
    group("화면", null, [
      setting({ label: "테마", value: "시스템", symbol: "moon", tint: "violet" }),
      setting({ label: "내 순서 알림", symbol: "bell", tint: "rose", accessory: toggle(true), tap: false }),
    ]),
    group(null, null, [
      setting({ label: "로그아웃", tone: "danger", accessory: null }),
    ]),
  );
}

function editor() {
  const cue = data.cues.find((item) => item.id === data.cuesheet.current_cue_id) || data.cues[0];

  return screen(
    group("큐", null, [
      setting({ label: "제목", value: cue.title, symbol: "tag", tint: "blue" }),
      setting({ label: "길이", value: clock(cue.planned_sec), symbol: "clock", tint: "amber" }),
      setting({ label: "색", value: cue.color, symbol: "swatch", tint: cue.color }),
    ]),
    group("역할별 지시", "task 하나가 행 하나다 — 카메라·자막 열을 새로 만들지 않았다",
      cue.tasks.map((task) => setting({
        label: fixture.ROLE_NAME[task.role_id],
        value: task.instruction,
      })),
    ),
    group("진행", null, [
      setting({ label: "시작 시각 고정", accessory: toggle(false), tap: false }),
      setting({ label: "담당에게 알림", accessory: toggle(true), tap: false }),
    ]),
    group(null, null, [
      setting({ label: "큐 삭제", tone: "danger", accessory: null }),
    ]),
  );
}

function group(head, foot, rows) {
  const node = document.createElement("section");
  node.className = "s-settings";

  const card = document.createElement("div");
  card.className = "group";
  card.append(...rows);

  if (head) node.append(text("p", "e-label", head));
  node.append(card);
  if (foot) node.append(text("p", "e-caption", foot));
  return node;
}

// 액세서리를 넘기지 않으면 꺾쇠가 붙는다 — 설정 목록의 행은 대개 들어가는 행이다
function setting({ label, value, symbol, tint, tone, accessory, tap = true }) {
  const id = tap ? "tpl-lab-setting" : "tpl-lab-setting-static";
  const node = document.getElementById(id).content.cloneNode(true);
  const row = node.querySelector(".b-setting");

  if (tone) row.dataset.tone = tone;
  if (symbol) row.prepend(tile(symbol, tint));
  node.querySelector("[data-label]").textContent = label;
  node.querySelector("[data-value]").textContent = value || "";

  if (accessory !== null) row.append(accessory || chevron());
  return node;
}

function chevron() {
  const node = document.createElement("i");
  node.className = "e-chevron";
  return node;
}

function toggle(on) {
  const node = document.createElement("button");
  node.className = "e-toggle";
  node.type = "button";
  node.setAttribute("role", "switch");
  node.setAttribute("aria-checked", String(on));
  node.append(document.createElement("i"));
  return node;
}


// #
// symbol — SF Symbols 를 쓸 수 없으므로 필요한 다섯 개만 직접 그린다

const SVG_NS = "http://www.w3.org/2000/svg";

const SYMBOLS = {
  tag: ["M4 12V5.5A1.5 1.5 0 015.5 4H12l8 8-6.5 6.5z", "M8.2 8.2h.01"],
  clock: ["M12 21a9 9 0 100-18 9 9 0 000 18z", "M12 7.5V12l3 2"],
  person: ["M12 12a4 4 0 100-8 4 4 0 000 8z", "M5 20c1.4-3.3 3.9-5 7-5s5.6 1.7 7 5"],
  moon: ["M20 14.4A8.5 8.5 0 019.6 4 8.5 8.5 0 1020 14.4z"],
  bell: ["M12 4a5.5 5.5 0 00-5.5 5.5v3.2L5 16h14l-1.5-3.3V9.5A5.5 5.5 0 0012 4z", "M10.2 19a2 2 0 003.6 0"],
};

function tile(name, tint) {
  const node = document.createElement("span");
  node.className = "e-symbol";
  if (tint) node.dataset.tint = tint;

  const paths = SYMBOLS[name];
  if (!paths) return node;

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  for (const shape of paths) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", shape);
    svg.append(path);
  }
  node.append(svg);
  return node;
}


// #
// countdown — 폴링 응답이 아니라 로컬 시계로 센다

function restartTicker() {
  clearInterval(ticker);
  if (!running()) return;
  ticker = setInterval(tick, 1000);
  tick();
}

function tick() {
  const at = Date.now();

  for (const node of document.querySelectorAll("[data-countdown]")) {
    const target = Number(node.dataset.countdown);
    if (!target) continue;
    const left = Math.round((target - at) / 1000);
    node.textContent = clock(left);
    node.dataset.over = String(left < 0);
  }

  for (const node of document.querySelectorAll(".b-progress")) {
    const started = new Date(node.dataset.elapsed).getTime();
    const planned = Number(node.dataset.planned) * 1000;
    const ratio = Math.min(1, Math.max(0, (at - started) / planned));
    node.querySelector("i").style.inlineSize = `${ratio * 100}%`;
  }
}

function running() {
  return data.cuesheet.state === "running";
}


// #
// findings — 목업을 스택 위에 올리며 드러난, 화면이 아니라 도메인·응답의 문제

const FINDINGS = [
  ["지난 큐의 eta 가 null", "진행중이면 서버가 현재 큐부터만 eta 를 채운다. 축(C)은 그래도 되지만 목록형(A·D·E·F)은 지난 시각 자리에 — 만 남는다. 지난 eta 도 내려주거나 화면이 첫 큐부터 누적해야 한다"],
  ["코너(segment) 가 도메인에 없다", "F 안은 Cue 위에 묶음 하나가 더 필요하다. 지금 그 필드는 fixture 에만 있다"],
  ["큐 종류가 색 키뿐이다", "목업의 VCR·LIVE·STAGE·CG·CM 배지는 저장되는 값이 아니다. Cue.color 는 팔레트 키라 종류를 대신 읽으면 색을 바꾸는 순간 뜻이 바뀐다"],
  ["카메라·자막·비고 열이 없다", "E·D 의 상세는 Task.instruction·note 를 펼친 것이다. 열로 고정하려면 Task 를 종류로 가르거나 Cue 에 필드를 늘려야 한다"],
  ["delay_sec 는 현재 큐가 넘겼을 때만 붙는다", "목업은 2:03 남은 상태에서 ＋0:12 지연을 함께 보여준다. 지금 계산으로는 그 조합이 나오지 않는다"],
  ["목록형은 초까지 필요하다", "축은 눈금이 2분 간격이라 시:분이면 되지만, 35초짜리 큐가 줄로 서면 시:분만으로 두 줄이 같은 시각이 된다"],
];

function findings() {
  const list = document.getElementById("findings");
  list.replaceChildren(...FINDINGS.map(([title, why]) => {
    const item = document.createElement("li");
    item.className = "b-demo";
    item.append(text("p", "e-label", title), text("p", "e-caption", why));
    return item;
  }));
}


// #
// controls — 테마와 상태. 컴포넌트는 어느 쪽인지 모른다

const THEMES = [null, "light", "dark"];
const THEME_LABEL = { null: "시스템", light: "라이트", dark: "다크" };
const THEME_KEY = "cuesheet.theme";

function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;

  document.getElementById("theme-label").textContent = THEME_LABEL[theme];
  try {
    if (theme) localStorage.setItem(THEME_KEY, theme);
    else localStorage.removeItem(THEME_KEY);
  } catch {
    // 저장 불가여도 이번 세션은 동작한다
  }
}

function applyState(next) {
  state = next;
  document.getElementById("state-label").textContent = fixture.STATE_LABEL[next];
  render();
}


// #
// run

window.addEventListener("load", () => {
  let stored = null;
  try {
    stored = localStorage.getItem(THEME_KEY);
  } catch {
    // 위와 같다
  }
  applyTheme(THEMES.includes(stored) ? stored : null);

  document.getElementById("theme").addEventListener("click", () => {
    applyTheme(THEMES[(THEMES.indexOf(document.documentElement.dataset.theme || null) + 1) % THEMES.length]);
  });
  document.getElementById("state").addEventListener("click", () => {
    applyState(fixture.STATES[(fixture.STATES.indexOf(state) + 1) % fixture.STATES.length]);
  });

  applyState(state);
  findings();
});

// 스위치는 랩에서도 눌린다 — 켜고 끈 모습을 둘 다 봐야 대비가 판단된다
document.addEventListener("click", (event) => {
  const switched = event.target.closest(".e-toggle");
  if (!switched) return;
  switched.setAttribute("aria-checked", String(switched.getAttribute("aria-checked") !== "true"));
});

window.addEventListener("resize", sync);
