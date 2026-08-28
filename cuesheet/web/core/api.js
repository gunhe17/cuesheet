// #
// api — 도메인 무지. 경로와 본문만 안다

import * as session from "./session.js";

export function get(path) {
  return call("GET", path);
}

export function post(path, body) {
  return call("POST", path, body);
}


// #
// call

async function call(method, path, body) {
  const headers = {};
  if (body !== undefined) headers["content-type"] = "application/json";

  const current = session.read();
  if (current?.token) headers["authorization"] = `Bearer ${current.token}`;

  const response = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // 응답 본문이 JSON 이 아닌 경우
  }

  // 토큰이 죽으면 화면이 조용히 비어버린다 — 세션을 버리고 로그인으로 돌린다
  if (response.status === 401) {
    session.clear();
    location.hash = "#/";
    throw new Error("다시 로그인해 주세요");
  }

  if (!response.ok) {
    throw new Error(payload?.message || "잠시 후 다시 시도해 주세요");
  }
  return payload.data;
}
