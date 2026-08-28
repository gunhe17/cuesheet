// #
// pick — 내가 참여 중인 큐시트 목록

import * as api from "../core/api.js";
import * as notice from "../core/notice.js";
import * as session from "../core/session.js";
import * as view from "../shell/view.js";
import * as route from "../shell/route.js";

export function wire() {
  for (const button of document.querySelectorAll("[data-logout]")) {
    button.addEventListener("click", () => {
      session.clear();
      route.go(route.path.home(), { replace: true });
      view.show("login");
    });
  }
}

export async function enter() {
  const current = session.read();
  document.getElementById("pick-greeting").textContent =
    current?.name ? `${current.name} 님` : "";

  notice.show("pick-notice", "");

  try {
    render(await api.get("/cuesheets"));
  } catch (error) {
    notice.show("pick-notice", error.message);
  }
}


// #
// render

function render(cuesheets) {
  const list = document.getElementById("pick-list");
  list.replaceChildren();

  document.getElementById("pick-empty").hidden = cuesheets.length > 0;

  for (const cuesheet of cuesheets) {
    list.appendChild(entry(cuesheet));
  }
}

const STATE = {
  ready: "준비중",
  running: "진행중",
  ended: "종료",
};

function entry(cuesheet) {
  const node = document.getElementById("tpl-cuesheet").content.cloneNode(true);

  node.querySelector("[data-title]").textContent = cuesheet.title;

  const state = node.querySelector("[data-state]");
  state.textContent = STATE[cuesheet.state];
  state.dataset.state = cuesheet.state;

  node.querySelector("[data-when]").textContent =
    `${when(cuesheet.scheduled_at)}${cuesheet.can_advance ? " · 총괄" : ""}`;

  node.querySelector("button").addEventListener("click", () => open(cuesheet.id));

  return node;
}

function when(iso) {
  const at = new Date(iso);
  return at.toLocaleString("ko-KR", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}


// #
// open

function open(id) {
  route.go(route.path.cuesheet(id));
}
