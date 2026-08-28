# 개발 스택

백엔드는 스캐폴드가 이미 정해두었다 — 이 문서는 그 위에서 남은 결정(프론트·실시간·DB 운영)만 담는다.

---

## 확정된 것 (스캐폴드)

| 층 | 선택 | 출처 |
|---|---|---|
| 런타임 | Python 3.13 + uv | [.docker/Dockerfile.develop.api](../../.docker/Dockerfile.develop.api) |
| 웹 | FastAPI | [rules/api/server.md](../rules/api/server.md) |
| DB | PostgreSQL 16 (dev / test 2대) | [.docker/docker-compose.develop.yml](../../.docker/docker-compose.develop.yml) |
| ORM | SQLAlchemy async + asyncpg | [rules/api/repository.md](../rules/api/repository.md) |
| 비동기 처리 | worker (LISTEN/NOTIFY 도메인 이벤트 dispatch) | [rules/api/worker.md](../rules/api/worker.md) |
| 개발 환경 | Docker Compose + devcontainer | [.devcontainer/](../../.devcontainer/) |

앞서 검토했던 SQLite + SQLModel은 폐기한다. 인프라가 이미 Postgres이고,
테넌트 격리를 RLS로 하는 규칙([column-scope.md](../rules/api/column-scope.md))이 Postgres 전용이다.

---

## 프론트 — 정적 HTML + fetch 폴링

빌드 스텝 없음. HTMX 없음. 프레임워크 없음.

```
cuesheet/web/index.html      손으로 쓴 HTML + CSS 한 파일
cuesheet/web/app.js          fetch 폴링 + 렌더 + 카운트다운. 바닐라
```

`bin/server.py`에서 한 줄로 서빙한다. 빌드 산출물이 아니라 손으로 쓴 디렉토리를 그대로 가리킨다.

```python
app.frontend("/", directory="cuesheet/web")
```

### HTMX를 쓰지 않는 이유

endpoint는 `Output.to_dict()`를 그대로 JSON으로 응답해야 한다 — [INV-8], [endpoint.md](../rules/api/endpoint.md).
HTMX는 서버가 HTML fragment를 돌려줘야 동작하므로 이 규칙과 정면 충돌한다.
규칙을 우회해 view 전용 endpoint 종류를 새로 만드는 것보다, JSON API를 그대로 두고
클라이언트가 렌더하는 쪽이 싸다. 어차피 화면이 폴링하는 endpoint는 `cuesheet_get` 하나다.

### 클라이언트가 하는 일

- 2초마다 `GET /cuesheets/{id}` 한 번, 응답으로 화면 전체를 다시 그린다. diff 없음
- 카운트다운은 서버가 내려준 목표 시각(epoch)만 보고 1초마다 로컬에서 센다

카운트다운을 서버 응답이 아니라 로컬 시계로 돌리면 **폴링이 끊겨도 화면이 멈추지 않는다.**
지하 행사장 네트워크 대응이 별도 오프라인 처리 없이 자동으로 된다.

### Preline

[example/preline/](../../example/preline/)은 마크업 참고용이다. 그대로 가져다 쓰지 않는다 —
`main.min.css` 966KB + `preline.js` 435KB는 행사장 회선에서 첫 로딩이 감당이 안 된다.
필요한 컴포넌트의 구조만 보고 CSS는 직접 쓴다.

---

## 실시간성 — 2초 폴링

WebSocket / SSE 쓰지 않는다.

- 상태를 바꾸는 주체가 사람(manager의 버튼 클릭)이라 이벤트 빈도가 낮다
- 폴링은 끊겨도 다음 요청에서 알아서 복구된다. 소켓은 재연결 로직이 필요하다
- worker의 LISTEN/NOTIFY는 서버 내부 이벤트 처리용이지 클라이언트 푸시 경로가 아니다

---

## 마이그레이션

초기 스키마는 `create_all`. Alembic은 도입하지 않는다.
행사 전에 스키마가 확정되고, 운영 중 스키마를 바꿀 일이 없다.

> 여러 행사가 동시에 돌기 시작해 무중단 스키마 변경이 필요해지면 그때 Alembic을 넣는다.

---

## 쓰지 않는 것

| 항목 | 이유 |
|---|---|
| React / Vue | 클라이언트 상태가 없다. 화면 전체 재렌더로 끝난다 |
| HTMX | [INV-8]과 충돌 — 위 참고 |
| Tailwind / Preline 번들 | 빌드 스텝 또는 1.4MB 페이로드 |
| Alembic | 위 참고 |
| Redis | 캐시할 것이 없다. 파생값은 산술 몇 줄이다 |
| 인증 라이브러리 | 계정이 없다. 초대 토큰 + 세션 토큰 쿠키가 전부 |

---

## 아직 없는 것

스캐폴드가 참조하지만 이 저장소에 존재하지 않는 파일들. 구현 시작 전에 채워야 한다.

| 경로 | 참조하는 곳 |
|---|---|
| `pyproject.toml` | Dockerfile (`uv pip compile pyproject.toml --extra app`) |
| `.claude/hooks/*.py` | [.claude/settings.json](../settings.json) PreToolUse/PostToolUse |
| `scripts/develop/*.sh` | [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json) |
| `cuesheet/api/CLAUDE.md` | rules 전반이 "루트" 로 링크 |
| `.claude/documents/ontology.md` | rules의 온톨로지 블록쿼트 |
