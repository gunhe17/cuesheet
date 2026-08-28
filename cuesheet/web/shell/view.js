// #
// shell — 뷰 전환만. 스타일을 만지지 않는다

const VIEWS = ["login", "register", "pick", "cuesheet"];

export function show(name) {
  for (const view of VIEWS) {
    document.getElementById(`view-${view}`).hidden = view !== name;
  }
  document.getElementById(`view-${name}`).querySelector("input")?.focus();
}

export function wire() {
  for (const button of document.querySelectorAll("[data-goto]")) {
    button.addEventListener("click", () => show(button.dataset.goto));
  }
}
