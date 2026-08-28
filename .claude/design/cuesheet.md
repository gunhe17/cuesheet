# 큐시트 도메인 설계

행사 진행용 큐시트. 큐시트는 순서의 기본 정보 + 역할별 todo로 구성된다.
manager가 순서를 넘기면 모든 참가자 화면이 갱신되고, 각 역할 담당자는 자기 todo만 본다.

레이어 패턴은 [rules/api/](../rules/api/) — 이 문서는 그 패턴 위에 얹힌 도메인 결정만 담는다.

---

## aggregate 이름 — 행사는 `Cuesheet`

행사 aggregate를 `Event`로 부르지 않는다. `Event`·`EventRepository`·`EventGroupContext`·`DispatchEvents`가
도메인 이벤트 인프라([domain-event.md](../rules/api/domain-event.md))의 이름이라 정면 충돌한다.

행사 하나 = 큐시트 하나(1:1)라 `Cuesheet`가 tenant root를 겸한다. `Cue`가 그 아래 사는 것도 자연스럽다.

---

## aggregate

| aggregate | 무엇 | scope |
|---|---|---|
| `User` | 계정. `login_id` + PIN | global (RLS 밖) |
| `Cuesheet` | 행사 = 큐시트 = 테넌트 루트. 진행 상태를 겸한다 | `id` (root) |
| `Role` | 역할군. 음향·영상·조명. 행사마다 자유 추가 | `cuesheet_id` |
| `Participant` | User가 이 큐시트에 참여한 것. 권한·역할이 여기 붙는다 | `cuesheet_id` |
| `Cue` | 순서 하나 | `cuesheet_id` |
| `Task` | 역할별 todo | `cuesheet_id` |

`users`를 뺀 모든 테이블이 `cuesheet_id`로 격리된다 —
[column-scope.md](../rules/api/column-scope.md) 완전성 충족. RLS 축은 `cuesheet` 하나뿐이다.

---

## User

계정과 참여를 가른다. `User`는 사람, `Participant`는 그 사람의 이 큐시트에서의 자격이다.
같은 사람이 여러 행사에 참여하고 행사마다 역할·권한이 다르다.

| 필드 | VO | 비고 |
|---|---|---|
| `login_id` | `LoginId` | 유일. `add_unique_by_login_id` |
| `name` | `UserName` | 표시 이름. "누가 체크했나"에 쓰인다 |
| `pin_hash` | `PinHash` | sensitive=secret. argon2 |
| `session_token` | `SessionToken \| None` | sensitive=secret. sha256 지문, 로그인 시 재발급 |
| `failed_count` | `FailedCount` | 연속 로그인 실패 |
| `locked_until` | `LockedUntil \| None` | 5회 실패 시 +5분 |

### 인증은 임시 구현

PIN 4자리, 세션 토큰은 `users` 행에 직접. 본격적인 인증 체계 전의 자리표시자다.
전달은 `Authorization: Bearer <raw>` 헤더이고 DB에는 `sha256(raw)` 지문만 남는다.

- **한 기기만 로그인** — 로그인하면 이전 세션 토큰이 무효화된다. 세션 테이블을 만들지 않은 대가다.
  manager가 노트북으로 편집하고 폰으로 진행해야 하면 `user_sessions` 테이블로 승격한다.
- **PIN 4자리는 10,000 조합** — argon2 해싱은 DB가 털렸을 때의 오프라인 크래킹만 막는다.
  온라인 무차별 대입은 5회 실패 5분 잠금(`AuthConfig`)이 막는다.
- **실패 누적은 요청 트랜잭션 밖에서 확정한다** — 거부하며 raise 하면 같은 session 의 쓰기가 롤백돼
  카운터가 사라진다. 별도 트랜잭션으로 쓴다([INV-5] 예외).

`users`는 RLS를 걸지 않는 명시적 global이다. 로그인은 인증 이전에 `login_id`로 조회해야 해서
테넌트 스코프를 걸 수 없다. 본인 행 접근 제한은 usecase가 진다.

---

## Cuesheet

진행 상태를 별도 aggregate로 가르지 않는다. 큐시트와 1:1이라 테이블을 나눌 이유가 없다.

| 필드 | VO | 비고 |
|---|---|---|
| `owner_user_id` | raw `UUID` | FK users. 격리 아닌 기록이라 scope 안 붙인다 |
| `title` | `CuesheetTitle` | |
| `scheduled_at` | `ScheduledAt` | 예정 시작 시각. 준비중일 때 예상시각의 기준 |
| `manager_token` | `InviteToken` | sensitive=secret. 이 링크로 합류하면 `can_advance=true` |
| `viewer_token` | `InviteToken` | sensitive=secret |
| `current_cue_id` | raw `UUID \| None` | FK cues |
| `prev_cue_id` | raw `UUID \| None` | FK cues. 되돌리기 1단계용 |
| `cue_started_at` | `CueStartedAt \| None` | 현재 큐를 시작한 시각. 진행중 예상시각의 기준 |
| `ended_at` | `EndedAt \| None` | |

`owner_user_id`는 "누가 만들었나"만 기록하고 인가에 쓰지 않는다. 조직 테넌시를 도입하면
`org_id`로 승격할 자리다 — 그때까지는 컬럼 하나의 값이다.

상태는 별도 컬럼 없이 세 필드로 판정한다.

| `current_cue_id` | `ended_at` | 상태 |
|---|---|---|
| null | null | 준비중 |
| 있음 | null | 진행중 |
| - | 있음 | 종료 (읽기 전용) |

상태 전이는 동사 메서드 — 단순 필드 교체가 아니라 여러 필드가 함께 움직이므로 `with_X`가 아니다.

```python
def start(self, *, cue_id: UUID, at: CueStartedAt) -> "Cuesheet"
def advance(self, *, next_cue_id: UUID, at: CueStartedAt) -> "Cuesheet"
def rewind(self, *, at: CueStartedAt) -> "Cuesheet"
def end(self, *, at: EndedAt) -> "Cuesheet"
```

`rewind`는 `prev_cue_id`를 `current_cue_id`로 올리고 `prev_cue_id`를 비운다 — 1단계만 되돌린다.

---

## Role

| 필드 | VO |
|---|---|
| `cuesheet_id` | raw `UUID` |
| `name` | `RoleName` |

---

## Participant

| 필드 | VO | 비고 |
|---|---|---|
| `cuesheet_id` | raw `UUID` | 격리 컬럼 |
| `user_id` | raw `UUID` | FK users. 참조일 뿐 격리 아님 — scope 안 붙인다 |
| `can_advance` | `CanAdvance` | `from_bool`. manager 여부 |
| `role_ids` | `RoleIds` | `from_json` — UUID 문자열 list |

`(cuesheet_id, user_id)` 복합 유일 — `add_unique_by_cuesheet_and_user`.
이름은 여기 없다. `User.name`을 조회해 붙인다.

권한은 `can_advance` 하나다. manager가 viewer의 상위집합이라 별도 권한 테이블·다중 권한 할당이
표현할 것이 없다. 역할만 복수 할당된다.

`role_ids`를 membership 테이블 대신 JSONB list로 둔다. 행사당 참가자 수십 명 규모라
`role_ids @> [role_id]` 한 번이면 끝나고, aggregate·repository·scope 컬럼이 하나씩 안 는다.

> 한계: role 삭제 시 dangling id가 남는다(필터에 안 걸릴 뿐 오류는 아님). 참가자가 수백 명이 되거나
> "이 역할의 담당자 목록"을 자주 조회하게 되면 `participant_roles` 테이블로 승격한다.

---

## Cue

| 필드 | VO |
|---|---|
| `cuesheet_id` | raw `UUID` |
| `seq` | `Seq` |
| `title` | `CueTitle` |
| `planned_sec` | `PlannedSec` |

시간은 소요시간만 저장한다. 앞 순서가 밀리면 뒤 순서가 자동으로 밀리게 하기 위함이며,
절대시각은 표시 전용 파생값이라 컬럼이 없다.

---

## Task

| 필드 | VO | 비고 |
|---|---|---|
| `cuesheet_id` | raw `UUID` | |
| `cue_id` | raw `UUID` | FK cues |
| `role_id` | raw `UUID` | FK roles |
| `instruction` | `Instruction` | "BGM #3 페이드인". VO명을 `Action`으로 두지 않는다 — behavior `Action` base와 충돌 |
| `note` | `Note \| None` | 트랙 번호, 마이크 채널 |
| `done_at` | `DoneAt \| None` | null = 미완료 |
| `done_by_participant_id` | raw `UUID \| None` | FK participants. 역할 이름만 쓰지 않고 대상 테이블을 referent로 |

완료 여부는 모든 참가자에게 공유된다. manager는 모든 todo를 체크할 수 있다 —
무전으로 듣고 대신 누르는 것이 실제 운영이며, 누가 눌렀는지는 `done_by_participant_id`에 남는다.

---

## 파생값

저장하지 않는다. `cuesheet_get` 한 곳에서 `# schedule` 단계로 계산한다.

```
elapsed  = now - cue_started_at
delay    = elapsed - current_cue.planned_sec          # 양수일 때만 지연
eta(cue) = now + Σ(현재 큐 이후 ~ 해당 큐 직전까지 planned_sec)
```

준비중이면 기준이 `cue_started_at`이 아니라 `scheduled_at`이다.

파생을 위한 도메인 서비스 레이어를 따로 두지 않는다 — 이 계산을 필요로 하는 usecase가 하나뿐이다.

---

## behavior — 봉투와 action

라우트-가변 필수 입력은 `cuesheet_id` 하나라 봉투는 둘이다.

| 봉투 | 라우트 |
|---|---|
| `request` | 가입·로그인·큐시트 생성 |
| `request_cuesheet` | 나머지 전부 |

| action | 하는 일 |
|---|---|
| `AuthenticateUser` | 쿠키의 `session_token` → User 확정. 실패 시 `UnauthorizedError` |
| `AuthorizeParticipant` | 이 User가 이 큐시트의 Participant인지. `role_ids`·`can_advance`를 memory에 |
| `AuthorizeManager` | `can_advance` 확인. 아니면 `ForbiddenError` |
| `OpenEventGroup` | 요청당 `event_group_id` 1개 |

`DispatchEvents`가 없다 — reaction이 0개라 dispatch 절반을 쓰지 않는다.

### 예외

| 예외 | 코드 | 발생처 | 사는 곳 |
|---|---|---|---|
| `UnauthorizedError` | 401 | 세션 토큰 무효, 초대 토큰 불일치 | behavior · domain |
| `InvalidCredentialError` | 401 | 아이디·PIN 불일치 | domain |
| `ForbiddenError` | 403 | manager 아님, 남의 역할 todo 체크, 비참여자 | behavior · domain |
| `TooManyAttemptsError` | 429 | 로그인 5회 실패 후 잠금 | domain |

---

## 라우트 ↔ usecase

`request_cuesheet` 라우트는 전부 `AuthenticateUser` + `AuthorizeParticipant`를 단다.
`M` = `AuthorizeManager` 추가.

| 라우트 | usecase | 봉투 | M | MVP |
|---|---|---|---|---|
| `POST /users` | `user_register.register` | `request` | | O |
| `POST /users/session` | `user_login.login` | `request` | | O |
| `POST /cuesheets` | `cuesheet_create.create` | `request` | | O |
| `GET /cuesheets` | `cuesheet_search.search` | `request` | | O |
| `GET /cuesheets/{id}` | `cuesheet_get.get` | `request_cuesheet` | | O |
| `PATCH /cuesheets/{id}` | `cuesheet_update.update` | `request_cuesheet` | M | |
| `POST /cuesheets/{id}/run` | `cuesheet_start.start` | `request_cuesheet` | M | O |
| `POST /cuesheets/{id}/run/advance` | `cuesheet_advance.advance` | `request_cuesheet` | M | O |
| `POST /cuesheets/{id}/run/rewind` | `cuesheet_rewind.rewind` | `request_cuesheet` | M | O |
| `POST /cuesheets/{id}/run/end` | `cuesheet_end.end` | `request_cuesheet` | M | O |
| `POST /cuesheets/{id}/participants` | `participant_join.join` | `request_cuesheet` | | O |
| `PATCH /cuesheets/{id}/participants/{pid}` | `participant_update.update` | `request_cuesheet` | M | |
| `POST /cuesheets/{id}/roles` | `role_create.create` | `request_cuesheet` | M | O |
| `DELETE /cuesheets/{id}/roles/{rid}` | `role_delete.delete` | `request_cuesheet` | M | |
| `POST /cuesheets/{id}/cues` | `cue_create.create` | `request_cuesheet` | M | O |
| `PATCH /cuesheets/{id}/cues/{cid}` | `cue_update.update` | `request_cuesheet` | M | O |
| `DELETE /cuesheets/{id}/cues/{cid}` | `cue_delete.delete` | `request_cuesheet` | M | |
| `POST /cuesheets/{id}/tasks` | `task_create.create` | `request_cuesheet` | M | O |
| `PATCH /cuesheets/{id}/tasks/{tid}` | `task_update.update` | `request_cuesheet` | M | |
| `DELETE /cuesheets/{id}/tasks/{tid}` | `task_delete.delete` | `request_cuesheet` | M | |
| `POST /cuesheets/{id}/tasks/{tid}/check` | `task_check.check` | `request_cuesheet` | | O |
| `DELETE /cuesheets/{id}/tasks/{tid}/check` | `task_uncheck.uncheck` | `request_cuesheet` | | O |

예외 둘:
- `user_register`·`user_login`은 인증 이전이라 `AuthenticateUser`를 달지 않는다.
- `participant_join`은 아직 Participant가 아니라 `AuthorizeParticipant`를 달지 않는다.
  로그인은 되어 있어야 하고, 초대 토큰은 Input으로 들어와 usecase가 대조한다.

`{aggregate}` prefix는 라우트 그룹을 따른다 — `cuesheet_advance`는 Cuesheet 엔티티를 만지고
`/cuesheets/...` 라우트라 `cuesheet_`.

큐시트 안쪽의 read-many usecase(`cue_search`·`role_search`·`participant_search`)는 없다.
모바일 화면이 필요로 하는 전부를 `cuesheet_get` 하나가 돌려주고, 폴링도 그 하나만 친다.
`cuesheet_search`는 큐시트 *바깥*의 목록이라 별개다 — `participants` 를 user 로 역조회한다.

로그아웃 usecase를 두지 않는다 — 다시 로그인하면 이전 토큰이 무효화된다.

---

## 불변조건

1. `advance`/`rewind`의 Input은 클라이언트가 화면에서 본 `expected_cue_id`를 담는다.
   서버의 `current_cue_id`와 다르면 전이하지 않고 현재 상태를 그대로 반환한다(멱등).
   manager 여러 명이 동시에 눌러 큐가 두 칸 점프하는 것을 막는다.
   부재·불일치가 정상인 멱등 케이스라 새 예외를 만들지 않고 usecase가 분기한다.
2. `advance`/`rewind`/`end`는 미완료 todo와 무관하게 항상 허용된다.
   미완료로 남은 todo는 자동 완료 처리하지 않는다 — 실제로 안 한 것이기 때문이다.
3. `current_cue_id`가 가리키는 Cue는 삭제할 수 없다. 제목·소요시간·todo 수정은 진행 중에도 가능하다.
4. viewer는 자기 `role_ids`에 속한 Task만 체크할 수 있다. manager는 전부 가능하다.
5. `ended_at`이 찍힌 큐시트는 읽기 전용이다.
6. 한 User는 한 큐시트에 Participant 하나다.

---

## 동작 요약

| 동작 | manager | viewer |
|---|---|---|
| 조회 | O | O |
| 자기 역할 todo 체크 | O | O |
| 다른 역할 todo 체크 | O | X |
| 시작 / 다음 / 되돌리기 / 종료 | O | X |
| 큐·역할·참가자·todo 편집 | O | X |

---

## 의도적으로 제외한 것

| 항목 | 이유 | 추가할 시점 |
|---|---|---|
| `user_sessions` 테이블 | `users.session_token` 한 컬럼으로 충분 | 한 사람이 두 기기로 동시에 써야 할 때 |
| 로그인 실패 제한 | PIN이 임시 구현 | 실제 행사에 쓰기 전 (필수) |
| 순서별 실제 종료시각 테이블 | 도메인 이벤트가 `cuesheet_advance`를 시각과 함께 이미 기록한다 | 리뷰 리포트를 만들 때 그 이벤트를 읽으면 된다 |
| `participant_roles` 테이블 | 참가자 수십 명 규모에 JSONB `role_ids`로 충분 | 참가자 수백 명 / 역할별 담당자 조회가 잦아질 때 |
| 정각 고정 순서 (`fixed_at`) | 절대시각이 표시 전용이면 불필요 | 외부 중계처럼 시간 고정 순서가 생길 때 |
| 진행 상태 별도 aggregate | 큐시트와 1:1 | - |
| 순서 건너뛰기 | `advance`를 두 번 부르면 된다 | - |
| 푸시 알림 | 담당자는 화면을 켜둔다 | - |
