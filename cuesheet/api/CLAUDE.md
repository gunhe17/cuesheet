# api

행사 진행용 큐시트 API. 도메인 결정은 [design/cuesheet.md](../../.claude/design/cuesheet.md).

## 레이어

의존은 아래로만. 위 레이어를 import하면 방향 위반이다.

| 레이어 | 무엇 | 도메인을 아나 |
|---|---|---|
| `bin/` | 합성 루트. 라우터·핸들러·프론트 등록 | 조립만 |
| `endpoint/` | HTTP 핸들러. usecase 호출 + 직렬화 | O |
| `usecase/` | 비즈니스 흐름. 트랜잭션 경계를 받는다 | O |
| `behavior/` | 한 요청을 감싸는 정책 — 트랜잭션·인증·인가·테넌트·이벤트 그룹 | O |
| `domain/` | aggregate — entity · VO · repository+model · atomic event | 자기 자신 |
| `infrastructure/` | DB·hash·token 어댑터 | X |
| `server/` | FastAPI 프리미티브 래퍼 | X |
| `core/` | Entity·ValueObject·In/Out·exception·i18n·validate 베이스 | X |

`config.py`는 환경별 설정 단일 출처. 모듈 수준 상수 블록을 두지 않는다.

## aggregate

| aggregate | scope 컬럼 | RLS |
|---|---|---|
| `user` | `id` | 없음 (로그인이 인증 이전 조회라 스코프를 걸 수 없다) |
| `cuesheet` | `id` | 없음 (테넌트 루트) |
| `participant` | `cuesheet_id` | 없음 (인가가 스코프를 걸기 전에 읽는다) |
| `role` · `cue` · `task` | `cuesheet_id` | 있음 |
| `event` · `event/atomic_event` | `actor_cuesheet_id` | atomic_events 만 |

RLS 축은 `cuesheet` 하나. 정책 정의는 `infrastructure/database/postgresql/rls.py`.

## 불변조건

| | |
|---|---|
| **[INV-1]** | 어댑터(`server/`·`infrastructure/`)는 도메인 무지. `Callable`·primitive만 안다 |
| **[INV-2]** | Entity·VO는 팩토리로만 생성. `by_factory` 가드가 직접 생성을 막는다 |
| **[INV-3]** | base 단건 write/fetch 반환은 `E \| None`. must-exist는 domain repo가 override해 `E`로 좁히고 not-found를 raise |
| **[INV-4]** | 모든 예외는 `ClientError`(4xx)/`DevelopError`(5xx)로 귀결. 핸들러 2개가 MRO로 분기 |
| **[INV-5]** | 같은 session = 같은 transaction. usecase는 session을 받기만, 만들지 않는다 |
| **[INV-6]** | repository는 stateless classmethod. 인스턴스화 금지, session은 메서드 인자 |
| **[INV-7]** | atomic event는 순수. IO·async·타 aggregate 의존 0 |
| **[INV-8]** | usecase 반환은 언제나 `Output(data, event)`. endpoint는 `to_dict()` 그대로 응답 |
| **[INV-9]** | 유일성은 base `_ensure_unique` + domain 변환 2계층 |
| **[INV-10]** | 도메인 값은 전부 VO. 예외는 UUID id/FK와 audit datetime 뿐 |

**[INV-5] 예외 하나** — 로그인 실패 누적은 요청 트랜잭션의 롤백을 타면 안 되므로 별도 세션에서 확정한다
(`usecase/user_login.py`). 거부하면서 상태를 남겨야 하는 유일한 지점이다.

## 이벤트

기록 전용이다. dispatch(worker·claim·retry·reaction)를 쓰지 않는다 — reaction이 0개다.

`events`는 묶음 이름과 평문 스냅샷, `atomic_events`는 append-only 엔티티 인덱스.
`Act`는 `created`/`updated`/`deleted`/`read` 넷뿐 — "어느 usecase였나"는 `Event.name`이 구분한다.

## 인증

`Authorization: Bearer <raw>` 헤더. DB에는 `sha256(raw)` 지문만 남는다.
PIN 4자리 + 5회 실패 잠금은 임시 구현이다 — 본격 인증 체계 전의 자리표시자.
