// #
// form — 제출 · 검증 · 버튼 잠금 · 오류 표시

import * as notice from "./notice.js";

export function bind(formId, noticeId, submit) {
  const form = document.getElementById(formId);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    notice.show(noticeId, "");

    if (!form.reportValidity()) return;

    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await submit(Object.fromEntries(new FormData(form).entries()));
    } catch (error) {
      notice.show(noticeId, error.message);
    } finally {
      button.disabled = false;
    }
  });
}

export function reset(formId) {
  document.getElementById(formId).reset();
}
