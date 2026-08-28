// #
// session — localStorage. 저장 실패해도 이번 세션은 동작한다

const KEY = "cuesheet.session";

export function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch {
    return null;
  }
}

export function write(session) {
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // 시크릿 모드 등 저장 불가
  }
}

export function clear() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // 위와 같다
  }
}
