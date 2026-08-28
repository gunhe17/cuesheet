// #
// notice — e-notice 요소 하나를 켜고 끈다

export function show(id, message) {
  const element = document.getElementById(id);
  element.textContent = message || "";
  element.hidden = !message;
}
