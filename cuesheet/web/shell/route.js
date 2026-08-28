// #
// route — 해시 라우팅. 서버에 catch-all 이 없어도 새로고침·뒤로가기·링크 공유가 된다

const ROUTES = [
  { pattern: /^\/?$/,             name: "home" },
  { pattern: /^\/join\/([^/]+)$/, name: "join",     keys: ["token"] },
  { pattern: /^\/c\/([^/]+)$/,    name: "cuesheet", keys: ["cuesheet_id"] },
];

export function current() {
  const path = location.hash.replace(/^#/, "") || "/";
  for (const route of ROUTES) {
    const match = path.match(route.pattern);
    if (!match) continue;
    const params = {};
    (route.keys || []).forEach((key, index) => { params[key] = match[index + 1]; });
    return { name: route.name, params };
  }
  return { name: "home", params: {} };
}

export function go(path, { replace = false } = {}) {
  const next = `#${path}`;
  if (location.hash === next) return;
  if (replace) location.replace(next);
  else location.hash = next;
}

export function onChange(handler) {
  window.addEventListener("hashchange", handler);
}

export const path = {
  home: () => "/",
  cuesheet: (id) => `/c/${id}`,
  join: (token) => `/join/${token}`,
};
