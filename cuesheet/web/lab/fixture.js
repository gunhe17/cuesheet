// #
// fixture — cuesheet_get 응답 하나를 대신한다. 여섯 후보가 같은 데이터를 나눠 쓴다.
// eta 누적은 서버(usecase/cuesheet_get.py 의 _schedule)가 하는 산술이다 — 여기가 그 서버 자리다

const CUESHEET_ID = "cuesheet-lab";

const ROLES = [
  { id: "role-pd", name: "연출" },
  { id: "role-fd", name: "FD" },
  { id: "role-cam", name: "카메라" },
  { id: "role-cg", name: "자막" },
  { id: "role-edit", name: "편집" },
  { id: "role-writer", name: "작가" },
];

const PARTICIPANTS = [
  { id: "participant-me", user_id: "user-me", name: "최유진", can_advance: true, role_ids: ["role-fd", "role-cam"] },
  { id: "participant-cg", user_id: "user-cg", name: "박시우", can_advance: false, role_ids: ["role-cg"] },
  { id: "participant-writer", user_id: "user-writer", name: "한지우", can_advance: false, role_ids: ["role-writer"] },
];

// segment 는 도메인에 없는 필드다 — F 안이 무엇을 더 요구하는지 보이려고 fixture 에만 둔다
const CUES = [
  { title: "오프닝 타이틀 VCR", planned_sec: 35, color: "violet", segment: "오프닝",
    tasks: [["role-edit", "서버 A · OPEN_0828.mxf 송출", "페이드인 15프레임"]] },
  { title: "MC 오프닝", planned_sec: 130, color: "blue", segment: "오프닝",
    tasks: [["role-cam", "1·2번 스탠딩 투샷", null], ["role-cg", "CG-01 프로그램 타이틀", null]] },
  { title: "1위 후보 소개 CG", planned_sec: 50, color: "amber", segment: "오프닝",
    tasks: [["role-cg", "CG-04 후보 5팀 롤", null]] },
  { title: "무대 ① 아티스트 A", planned_sec: 200, color: "rose", segment: "무대 1부",
    tasks: [["role-cam", "4번 지미집 · 6번 크레인", "인트로 8초 후 전환"], ["role-fd", "무대 좌측 대기", null], ["role-cg", "CG-07 아티스트명 / 곡명", null]] },
  { title: "MC 브릿지", planned_sec: 65, color: "blue", segment: "무대 1부",
    tasks: [["role-cam", "1번 원샷", null], ["role-fd", "다음 무대 소개 멘트 큐", null]] },
  { title: "무대 ② 아티스트 B", planned_sec: 225, color: "rose", segment: "무대 1부",
    tasks: [["role-cam", "3·5번", null], ["role-cg", "CG-08 아티스트명 / 곡명", null]] },
  { title: "광고", planned_sec: 90, color: "slate", segment: "광고",
    tasks: [["role-pd", "편성 고정 · 수정 불가", null]] },
  { title: "주간 차트 코너", planned_sec: 240, color: "teal", segment: "주간 차트",
    tasks: [["role-writer", "차트 원고 최종본", null], ["role-cg", "CG-11 차트 순위", null]] },
  { title: "무대 ③ 아티스트 C", planned_sec: 210, color: "rose", segment: "피날레",
    tasks: [["role-cam", "4·6번", null], ["role-cg", "CG-09 아티스트명 / 곡명", null]] },
  { title: "1위 발표", planned_sec: 135, color: "blue", segment: "피날레",
    tasks: [["role-fd", "꽃가루 큐", null], ["role-cam", "1·3번", null], ["role-cg", "CG-12 1위 발표", null]] },
  { title: "엔딩", planned_sec: 60, color: "blue", segment: "피날레",
    tasks: [["role-cam", "크레인 풀샷", null]] },
];

const TOTAL_SEC = CUES.reduce((sum, cue) => sum + cue.planned_sec, 0);
const CURRENT_INDEX = 3;
const ELAPSED_SEC = 117;
const LEAD_SEC = 600;

export const STATES = ["running", "ready", "ended"];
export const STATE_LABEL = { running: "진행중", ready: "준비중", ended: "종료" };
export const ROLE_NAME = Object.fromEntries(ROLES.map((role) => [role.id, role.name]));


// #
// snapshot

export function snapshot(state) {
  const now = Date.now();
  const scheduled = anchor(state, now);
  const startedAt = state === "running" ? scheduled + offset(CURRENT_INDEX) * 1000 : null;
  const delaySec = delay(startedAt, now);

  return {
    cuesheet: {
      id: CUESHEET_ID,
      owner_user_id: "user-me",
      title: "뮤직 스테이지",
      scheduled_at: new Date(scheduled).toISOString(),
      state,
      current_cue_id: state === "running" ? cueId(CURRENT_INDEX) : null,
      prev_cue_id: state === "running" ? cueId(CURRENT_INDEX - 1) : null,
      cue_started_at: startedAt ? new Date(startedAt).toISOString() : null,
      ended_at: state === "ended" ? new Date(now).toISOString() : null,
      delay_sec: delaySec,
    },
    cues: cues(state, scheduled, startedAt, delaySec),
    roles: ROLES,
    participants: PARTICIPANTS,
    me: { participant_id: "participant-me", can_advance: true, role_ids: ["role-fd", "role-cam"] },
  };
}

// 세 상태 모두 지금 시각을 기준으로 잡는다 — 카운트다운과 현재선이 살아 있어야 판단이 된다
function anchor(state, now) {
  if (state === "running") return now - (offset(CURRENT_INDEX) + ELAPSED_SEC) * 1000;
  if (state === "ended") return now - TOTAL_SEC * 1000;
  return now + LEAD_SEC * 1000;
}

function delay(startedAt, now) {
  if (!startedAt) return 0;
  return Math.max(0, Math.floor((now - startedAt) / 1000) - CUES[CURRENT_INDEX].planned_sec);
}


// #
// schedule — 진행중이면 현재 큐부터, 아니면 첫 큐부터 eta 를 채운다. 지난 큐는 null

function cues(state, scheduled, startedAt, delaySec) {
  const first = state === "running" ? CURRENT_INDEX : 0;
  let cursor = state === "running" ? startedAt + delaySec * 1000 : scheduled;

  return CUES.map((cue, index) => {
    const eta = index < first ? null : new Date(cursor).toISOString();
    if (index >= first) cursor += cue.planned_sec * 1000;

    return {
      id: cueId(index),
      cuesheet_id: CUESHEET_ID,
      seq: index + 1,
      title: cue.title,
      planned_sec: cue.planned_sec,
      color: cue.color,
      segment: cue.segment,
      eta,
      tasks: cue.tasks.map(([roleId, instruction, note], order) => ({
        id: `task-${index + 1}-${order + 1}`,
        cuesheet_id: CUESHEET_ID,
        cue_id: cueId(index),
        role_id: roleId,
        instruction,
        note,
        done_at: null,
      })),
    };
  });
}

function offset(index) {
  return CUES.slice(0, index).reduce((sum, cue) => sum + cue.planned_sec, 0);
}

function cueId(index) {
  return `cue-${String(index + 1).padStart(2, "0")}`;
}
