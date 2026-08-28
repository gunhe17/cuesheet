# 구현 계획

도메인 결정은 [design/cuesheet.md](../../design/cuesheet.md), 스택은 [design/stack.md](../../design/stack.md).
이 문서는 "어떤 파일을 어떤 순서로 쓰는가"만 담는다.

## 참조 구현

`/Users/gunhee/workspace/codespace/service/personal-secret` — 같은 rules를 따르는 선행 구현.
아래 표의 `참조` 열은 그 저장소의 `personal_secret/api/` 기준 상대 경로다.

| 종류 | 뜻 |
|---|---|
| copy | import 경로(`personal_secret` → `cuesheet`)만 바꿔 그대로 |
| adapt | 구조는 그대로, 도메인 어휘·필드 교체 |
| new | 참조에 대응 파일 없음 |
| skip | 참조에 있지만 우리는 안 쓴다 |

---

## Phase 0 — 스캐폴드 보강

스캐폴드가 참조하는데 없는 파일들. 이게 없으면 컨테이너도 훅도 안 뜬다.

| 파일 | 종류 | 참조 | 메모 |
|---|---|---|---|
| `pyproject.toml` | adapt | `../pyproject.toml` | `app` extra = fastapi · uvicorn[standard] · sqlalchemy[asyncio] · asyncpg · argon2-cffi · pydantic. alembic·cryptography·httpx·keyring 제거. `cli`/`mcp` extra 삭제, `dev`는 pytest·pytest-asyncio·httpx·ruff |
| `scripts/develop/*.sh` | copy | `../scripts/develop/` | devcontainer-initialize · devcontainer-postcreate · docker-compose-{up,down,build} |
| `scripts/production/*.sh` | copy | `../scripts/production/` | |
| `.claude/hooks/*.py` | copy | `../.claude/hooks/` | hint_dependents · hint_dependencies · check_label_comments (settings.json이 이미 참조) + check_column_scope |
| `.docker/docker-compose.develop.yml` | adapt | | `worker`·`mcp` 서비스 제거 |
| `.docker/docker-compose.production.yml` | adapt | | 동일 |
| `.docker/Dockerfile.develop.mcp` | skip | | 삭제 |

verify: `sh scripts/develop/docker-compose-up.sh` → api·database·database-test 3개 컨테이너가 뜬다.

---

## Phase 1 — core + infrastructure

도메인을 모르는 층. 거의 전부 그대로 가져온다.

| 파일 | 종류 | 참조 | 메모 |
|---|---|---|---|
| `core/{entity,value_object,usecase,model,exception,i18n,validate,behavior,event}.py` | copy | 동일 | 9개 |
| `core/retry.py` | skip | | 재시도 대상이 없다 |
| `config.py` | adapt | `config.py` | `Env`·`AppConfig`·`PostgresConfig`(+Test)·`AuthConfig`만. Worker·Email config 삭제 |
| `infrastructure/common/exception.py` | copy | 동일 | |
| `infrastructure/database/common/{client,exception,repository,session}.py` | copy | 동일 | |
| `infrastructure/database/postgresql/{client,repository,session}.py` | copy | 동일 | |
| `infrastructure/database/postgresql/rls.py` | adapt | 동일 | 아래 참고 |
| `infrastructure/database/postgresql/notification.py` | skip | | LISTEN 안 쓴다 |
| `infrastructure/hash/common/{client,exception}.py` · `argon2/client.py` · `sha256/client.py` | copy | 동일 | argon2 = PIN 해싱, sha256 = 토큰 지문 |
| `infrastructure/token/common/client.py` · `secrets/client.py` | copy | 동일 | `secrets.token_urlsafe(32)` |
| `infrastructure/{notification,map}/` | skip | | 메일 없음, map 도구 불필요 |
| `server/{server,router,middleware,lifecycle,exception}.py` | copy | 동일 | 팩토리명 `personal_secret_api()` → `cuesheet_api()` |
| `server/frontend.py` | new | | 아래 참고 |

### rls.py

```python
TENANT_SETTING = "app.current_cuesheet"

_TENANT_COLUMNS = {
    "roles":         "cuesheet_id",
    "cues":          "cuesheet_id",
    "tasks":         "cuesheet_id",
    "atomic_events": "actor_cuesheet_id",
}
```

`cuesheets`·`users`·`participants`는 RLS에서 뺀다. 참조가 `teams`·`accounts`·`team_access`를 뺀 것과 같은 이유다 —
`AuthorizeParticipant`가 스코프를 걸기 *전에* `participants`를 읽어 멤버십을 확인해야 해서,
RLS를 걸면 자기 자신을 못 읽는 교착이 된다. 세 테이블의 격리는 repository의 명시적 `where`가 진다.

### server/frontend.py

`server/`의 다른 래퍼와 같은 형태 — 생성자에 설정, `register(app)` 하나.

```python
class Frontend:
    def __init__(self, path: str, directory: str): ...
    def register(self, app: FastAPI):
        app.frontend(self._path, directory=self._directory)
```

`Server`에 `frontend()` 등록 큐 + `app()`에서 호출. 정적 파일 서빙이 `bin/server.py`에 인라인되지 않게 한다.

verify: `python -m cuesheet.api.infrastructure.database.postgresql.client` → 테이블 생성 로그(아직 0개).

---

## Phase 2 — event 도메인 (기록 전용)

dispatch 절반을 버린다. `Event`가 outbox에서 로그 헤더로 줄어든다.

| 파일 | 종류 | 참조 | 메모 |
|---|---|---|---|
| `domain/event/event/event.py` | adapt | 동일 | `status`·`attempts`·`errors`·`claimed_at`·`succeeded_at`·`failed_at` 제거 → `name`·`payload`만. `succeed`/`fail` 전이 메서드 삭제 |
| `domain/event/event/{event_name,payload}.py` | copy | 동일 | |
| `domain/event/event/{dispatch_status,attempts,errors}.py` | skip | | 위 필드와 함께 소멸 |
| `domain/event/event/event_repository.py` | adapt | 동일 | `emit`·`filter_by_event_id`만. `claim`/`succeed`/`fail` 삭제. `EventModel`에서 dispatch 컬럼 제거 |
| `domain/event/atomic_event/atomic_event.py` | adapt | 동일 | `actor_team_id` → `actor_cuesheet_id`, `actor_account_id` → `actor_user_id` |
| `domain/event/atomic_event/atomic_event_model.py` | adapt | 동일 | 동일 rename + `info={"scope": "cuesheet"}` |
| `domain/event/atomic_event/act.py` | adapt | 동일 | `_allowed_list = ("created", "updated", "deleted", "read")` — `rotated` 제거 |
| `domain/event/atomic_event/entity_name.py` | adapt | 동일 | `_allowed_list = ("user", "cuesheet", "role", "participant", "cue", "task")` |

`advance`/`rewind`/`check`에 새 act를 만들지 않는다. 전부 `updated`이고,
"어느 usecase였나"는 `Event.name`(`"cuesheet_advance"`)이 이미 구분한다.

verify: 테이블 2개 생성 확인.

---

## Phase 3 — user + behavior

| 파일 | 종류 | 참조 | 메모 |
|---|---|---|---|
| `domain/user/user.py` | adapt | `domain/account/account.py` | 필드 4개. `with_session_token` evolve |
| `domain/user/login_id.py` | new | `domain/account/email.py` 형태 | 소문자 영숫자 + `_-`, 3~32자 |
| `domain/user/user_name.py` | adapt | `domain/team/team_name.py` | 표시 이름 |
| `domain/user/pin_hash.py` | adapt | `domain/account/login_verifier.py` | argon2 해시 문자열. sensitive=secret |
| `domain/user/session_token.py` | adapt | `domain/account_token/fingerprint.py` | sha256 지문. sensitive=secret |
| `domain/user/user_event.py` | adapt | `domain/account/account_event.py` | `payload()`는 `login_id`만 — PIN·토큰 금지 |
| `domain/user/user_repository.py` | adapt | `domain/account/account_repository.py` | `add_unique_by_login_id` · `get_by_login_id` · `get_by_session_token` |
| `behavior/common/exception.py` | copy | 동일 | `UnauthorizedError`·`ForbiddenError` 이미 있음 |
| `behavior/context/event.py` | copy | 동일 | |
| `behavior/context/access.py` | adapt | 동일 | `UserContext`(Bearer → User) · `ParticipantContext`(멤버십 + `role_ids`·`can_advance`). `OwnerAccessContext` 대신 `ParticipantContext.is_manager()` |
| `behavior/action/tenant.py` | adapt | 동일 | `team_id` → `cuesheet_id` |
| `behavior/action/event.py` | adapt | 동일 | `OpenEventGroup`만. `DispatchEvents`·`Event.dispatch_event`(pg_notify) 삭제 |
| `behavior/action/access.py` | adapt | 동일 | `AuthenticateUser` · `AuthorizeParticipant` · `AuthorizeManager` |
| `behavior/server.py` | adapt | 동일 | `request` · `request_cuesheet`. flow 끝의 `DispatchEvents` 호출 제거 |
| `behavior/__init__.py` | adapt | 동일 | worker UoW export 제거 |
| `behavior/{worker.py,action/job.py}` | skip | | |
| `usecase/user_register.py` | adapt | `usecase/auth_register.py` | 개인 팀 생성 부분 없음 — User 하나만 |
| `usecase/user_login.py` | adapt | `usecase/auth_login.py` | 토큰을 별도 테이블이 아니라 `users.session_token`에 `with_session_token`으로 |
| `endpoint/user.py` | adapt | `endpoint/auth.py` | `post_register` · `post_session` |
| `endpoint/system.py` | adapt | 동일 | `health`만. map 페이지 제거 |
| `bin/server.py` | adapt | 동일 | 라우터 등록 + `server.frontend(...)` |
| `domain/__init__.py` | adapt | 동일 | Model import 등록(`create_all`이 이걸로 테이블을 안다) |

### 세션 토큰

참조의 `Authorization: Bearer <raw>` 헤더 방식을 그대로 쓴다(쿠키 아님). 프론트가 `fetch`라 헤더가 더 단순하다.
raw 토큰은 응답으로 한 번만 나가고, DB에는 `sha256(raw)` 지문만 남는다.

`user_login`은 기존 `session_token`을 덮어쓴다 — 한 기기만 로그인되는 제약이 여기서 나온다.

verify: register → login → `Bearer`로 아무 `request_cuesheet` 라우트 호출 시 401이 아닌 404/403이 나온다.

---

## Phase 4 — cuesheet 도메인

VO 클래스명은 폴더 prefix를 붙여 충돌을 피한다(참조의 `TeamName` 선례).

| aggregate | 파일 |
|---|---|
| `domain/cuesheet/` | `cuesheet.py` · `cuesheet_title.py` · `scheduled_at.py` · `invite_token.py` · `cue_started_at.py` · `ended_at.py` · `cuesheet_event.py` · `cuesheet_repository.py` |
| `domain/role/` | `role.py` · `role_name.py` · `role_event.py` · `role_repository.py` |
| `domain/participant/` | `participant.py` · `can_advance.py` · `role_ids.py` · `participant_event.py` · `participant_repository.py` |
| `domain/cue/` | `cue.py` · `seq.py` · `cue_title.py` · `planned_sec.py` · `cue_event.py` · `cue_repository.py` |
| `domain/task/` | `task.py` · `instruction.py` · `note.py` · `done_at.py` · `task_event.py` · `task_repository.py` |

전부 `domain/secret/` 3종 세트(entity · VO · repository+model+mapper)를 본뜬다.

### 주의점

- `Cuesheet`의 상태 전이 4개(`start`/`advance`/`rewind`/`end`)는 `with_X`가 아니라 동사 메서드.
  `dataclasses.replace(self, ..., by_factory=True)`로 여러 필드를 한 번에 바꾼다.
- `role_ids.py`는 `from_json`/`to_json` — list는 불변성 위해 `tuple`로 보관, `to_json`에서 `list` 복원.
  model 컬럼은 JSONB.
- `invite_token.py`는 sensitive=secret. `manager_token`/`viewer_token` 두 컬럼이 같은 VO를 쓴다.
- 유일성: `UserRepository.add_unique_by_login_id`, `ParticipantRepository.add_unique_by_cuesheet_and_user`
  (`unique=[("cuesheet_id", "user_id")]`), `CueRepository.add_unique_by_seq`(`unique=[("cuesheet_id", "seq")]`).
  전부 partial unique index(`WHERE deleted_at IS NULL`)를 model `__table_args__`에 함께 건다.
- must-exist 조회는 repo의 `get_by_id(*, session, id, cuesheet_id)` — 다른 큐시트의 행은 존재해도 `NotFoundError`.

verify: `create_all`로 테이블 8개(users · cuesheets · roles · participants · cues · tasks · events · atomic_events).

---

## Phase 5 — 진행 제어 usecase

| 파일 | 라우트 | 메모 |
|---|---|---|
| `usecase/cuesheet_create.py` | `POST /cuesheets` | 초대 토큰 2개 발급. 생성자를 manager Participant로 함께 등록 |
| `usecase/cuesheet_start.py` | `POST /cuesheets/{id}/run` | 첫 큐(`seq` 최소)로 시작 |
| `usecase/cuesheet_advance.py` | `POST .../run/advance` | 아래 멱등 가드 |
| `usecase/cuesheet_rewind.py` | `POST .../run/rewind` | 동일 가드 |
| `usecase/cuesheet_end.py` | `POST .../run/end` | |
| `endpoint/cuesheet.py` | | 위 5개 + get/update |

### 멱등 가드

`Input`에 `expected_cue_id: str`. 새 예외를 만들지 않는다.

```python
# find
cuesheet = await CuesheetRepository.get_by_id(session=session, id=cuesheet_id)

# guard (불일치 = 다른 manager가 이미 넘김 → 전이 없이 현재 상태 반환)
if str(cuesheet.current_cue_id) != input.expected_cue_id:
    return Output(data=cuesheet.to_dict(), event=[])
```

`event=[]`로 반환한다 — 아무 일도 안 일어났으므로 기록할 것이 없다.

verify: 같은 `expected_cue_id`로 advance를 두 번 호출 → 큐가 한 칸만 움직인다.

---

## Phase 6 — 편집 usecase

`cue`·`task`·`role`·`participant` 각각 create/update/delete. `usecase/secret_{create,update,delete}.py`를 본뜬다.

| 파일 |
|---|
| `usecase/cue_{create,update,delete}.py` |
| `usecase/task_{create,update,delete,check,uncheck}.py` |
| `usecase/role_{create,delete}.py` |
| `usecase/participant_{join,update}.py` |
| `usecase/cuesheet_update.py` |
| `endpoint/{cue,task,role,participant}.py` |

### 주의점

- `cue_delete`는 `current_cue_id`와 같으면 거부 — `ForbiddenError`가 아니라 `InvalidError("Cue")`.
  진행 중인 순서를 지우는 것은 권한 문제가 아니라 잘못된 요청이다.
- `task_check`는 manager가 아니면 `scope.role_ids`에 `task.role_id`가 있는지 확인, 없으면 `ForbiddenError("Task")`.
- `participant_join`은 Input의 초대 토큰을 `cuesheet.manager_token`/`viewer_token`과 대조해
  `can_advance`를 정한다. 어느 쪽과도 안 맞으면 `UnauthorizedError`.

verify: viewer 토큰으로 join한 계정이 남의 역할 todo를 체크하면 403.

---

## Phase 7 — 조회 usecase

| 파일 | 메모 |
|---|---|
| `usecase/cuesheet_get.py` | 모바일 화면이 필요한 전부를 한 번에. 폴링이 치는 유일한 엔드포인트 |

`# find`에서 cuesheet · cues · tasks · roles · participants + 참가자 이름용 `UserRepository.find_by_ids`,
`# schedule`에서 파생값 계산, `# return`에서 `Output(data, event)`.

파생 계산은 같은 파일 아래쪽 순수 함수 `_schedule(...)`로 둔다 — 도메인 서비스 레이어를 새로 만들지 않는다.
호출자가 위, 피호출자가 아래.

```
data = {
  "cuesheet": {...,  "state": "ready|running|ended", "delay_sec": int},
  "current":  {"cue": {...}, "started_at": iso, "eta": iso},
  "cues":     [{..., "eta": iso, "tasks": [...]}],
  "roles":    [...],
  "participants": [{"id", "name", "can_advance", "role_ids"}],
  "me":       {"participant_id", "role_ids", "can_advance"}
}
```

`eta`는 절대시각 문자열로 내려보낸다. 클라이언트는 이 값과 로컬 시계만으로 카운트다운을 돌린다.

verify: 준비중 / 진행중 / 지연 세 상태에서 `eta`가 각각 `scheduled_at` 기준, `cue_started_at` 기준,
지연분 만큼 밀린 값으로 나온다.

---

## Phase 8 — 프론트

| 파일 | 메모 |
|---|---|
| `cuesheet/web/index.html` | 담당자 화면. 손으로 쓴 CSS 한 파일 인라인 |
| `cuesheet/web/app.js` | 로그인 → 토큰 보관 → 2초 폴링 → 렌더 → 카운트다운 |

`bin/server.py`에 `server.frontend(Frontend("/", directory="cuesheet/web"))`.

- 렌더는 전체 교체. diff 없음
- 카운트다운은 `data-eta` 속성의 절대시각과 로컬 시계 차이. 폴링이 끊겨도 계속 돈다
- 토큰은 `localStorage`

verify: 폰 브라우저에서 열고, manager가 다음을 누르면 2초 안에 갱신된다. 기내모드로 바꿔도 카운트다운은 계속 돈다.

---

## 검증

참조의 `tests/`(`run.py` + `factories.py`)를 본뜬다. 프레임워크 최소.

| 대상 | 왜 |
|---|---|
| `_schedule` 파생 계산 | 분기와 누적이 있는 유일한 계산. 준비중/진행중/지연 3케이스 |
| advance 멱등 가드 | 같은 `expected_cue_id` 두 번 → 한 칸 |
| `task_check` 권한 | viewer가 남의 역할 → 403 |
| RLS | 다른 큐시트의 cue가 안 보인다 |

나머지는 테스트하지 않는다. 대부분 참조에서 그대로 가져온 코드이거나 단순 위임이다.

---

## design 문서에 반영할 정정

참조 구현을 읽고 드러난 두 가지. Phase 3 시작 전에 [design/cuesheet.md](../../design/cuesheet.md)를 고친다.

| 문서에 쓴 것 | 실제 |
|---|---|
| 세션 토큰을 쿠키에 | `Authorization: Bearer` 헤더 (참조 방식, fetch에 더 단순) |
| `UnauthorizedError`/`ForbiddenError`를 추가해야 함 | `domain/common/exception.py`·`behavior/common/exception.py`에 이미 있다. 그대로 복사하면 끝 |
