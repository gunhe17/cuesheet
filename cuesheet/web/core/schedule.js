// #
// schedule — eta·planned_sec 를 화면 좌표와 표시 문자열로 옮긴다.
// 축과 랩이 같은 산술을 쓴다 — 두 곳에서 따로 계산하면 어긋난다

const PX_PER_SEC = 46 / 60;      // 1분 = 46px
const MIN_HEIGHT = 34;           // 제목과 길이가 들어가는 최소 높이


// #
// layout — 위치는 eta, 높이는 planned_sec.
// 다만 최소 높이보다 짧은 큐는 늘리고, 그만큼 뒤를 밀어 겹침을 막는다

export function layout(cues) {
  const origin = new Date(cues[0].eta).getTime();
  let cursor = 0;
  return cues.map((cue) => {
    const exact = cue.planned_sec * PX_PER_SEC;
    const height = Math.max(MIN_HEIGHT, exact);
    const at = { cue, top: cursor, height, stretched: height > exact + 0.5, origin };
    cursor += height;
    return at;
  });
}


// #
// derive

export function isMine(cue, me) {
  const roles = me?.role_ids || [];
  return cue.tasks.some((task) => roles.includes(task.role_id));
}

export function hhmm(at) {
  return at.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
}

export function hhmmss(at) {
  return at.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
}

// 남은 시간은 음수가 될 수 있다 — 초과분을 부호로 드러낸다
export function clock(sec) {
  const abs = Math.abs(sec);
  return `${sec < 0 ? "-" : ""}${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, "0")}`;
}
