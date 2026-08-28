import os
from pathlib import Path

from cuesheet.api.config import get_app_environment, is_develop
from cuesheet.api.server.server import cuesheet_api
from cuesheet.api.server import middleware
from cuesheet.api.server.router import Router
from cuesheet.api.server.frontend import Frontend
from cuesheet.api.server import exception
from cuesheet.api.endpoint import system
from cuesheet.api.endpoint import user
from cuesheet.api.endpoint import cuesheet
from cuesheet.api.endpoint import cue
from cuesheet.api.endpoint import task
from cuesheet.api.endpoint import role
from cuesheet.api.endpoint import participant


# #
# server

server = cuesheet_api()

# middleware
server.middleware(middleware.cors())
server.middleware(middleware.proxy_headers())

# #
# router

# system
server.router(
    Router(path="/system/health", methods=["GET"], endpoint=system.health)
)

# user
server.router(
    Router(path="/users", methods=["POST"], endpoint=user.post_register)
)
server.router(
    Router(path="/users/session", methods=["POST"], endpoint=user.post_session)
)

# cuesheet
server.router(
    Router(path="/cuesheets", methods=["POST"], endpoint=cuesheet.post_create)
)
server.router(
    Router(path="/cuesheets", methods=["GET"], endpoint=cuesheet.get_list)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}", methods=["GET"], endpoint=cuesheet.get_read)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}", methods=["PATCH"], endpoint=cuesheet.patch_update)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/run", methods=["POST"], endpoint=cuesheet.post_start)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/run/advance", methods=["POST"], endpoint=cuesheet.post_advance)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/run/rewind", methods=["POST"], endpoint=cuesheet.post_rewind)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/run/end", methods=["POST"], endpoint=cuesheet.post_end)
)

# participant
server.router(
    Router(path="/cuesheets/{cuesheet_id}/participants", methods=["POST"], endpoint=participant.post_join)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/participants/{participant_id}", methods=["PATCH"], endpoint=participant.patch_update)
)

# role
server.router(
    Router(path="/cuesheets/{cuesheet_id}/roles", methods=["POST"], endpoint=role.post_create)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/roles/{role_id}", methods=["DELETE"], endpoint=role.delete_role)
)

# cue
server.router(
    Router(path="/cuesheets/{cuesheet_id}/cues", methods=["POST"], endpoint=cue.post_create)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/cues/{cue_id}", methods=["PATCH"], endpoint=cue.patch_update)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/cues/{cue_id}", methods=["DELETE"], endpoint=cue.delete_cue)
)

# task
server.router(
    Router(path="/cuesheets/{cuesheet_id}/tasks", methods=["POST"], endpoint=task.post_create)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/tasks/{task_id}", methods=["PATCH"], endpoint=task.patch_update)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/tasks/{task_id}", methods=["DELETE"], endpoint=task.delete_task)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/tasks/{task_id}/check", methods=["POST"], endpoint=task.post_check)
)
server.router(
    Router(path="/cuesheets/{cuesheet_id}/tasks/{task_id}/check", methods=["DELETE"], endpoint=task.delete_check)
)

# exception handler
server.exception_handler(exception.client())
server.exception_handler(exception.internal())

# frontend
# 루트 마운트가 뒤의 모든 경로를 먹으므로 카탈로그를 먼저 등록한다
if is_develop():
    server.frontend(
        Frontend(
            path="/catalog",
            directory=(
                Path(
                    __file__
                )
                .resolve()
                .parent.parent.parent / "catalog"
            ),
        )
    )

server.frontend(
    Frontend(
        path="/",
        directory=(
            Path(
                __file__
            )
            .resolve()
            .parent.parent.parent / "web"
        ),
    )
)

# app
app = server.app()


# #
# run

if __name__ == "__main__":
    import uvicorn

    environment = get_app_environment()
    develop = is_develop()

    uvicorn.run(
        app="cuesheet.api.bin.server:app",
        host=str(os.environ[f"{environment.upper()}_API_HOST"]),
        port=int(os.environ[f"{environment.upper()}_API_CONTAINER_PORT"]),
        reload=develop,
    )
