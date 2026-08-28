from __future__ import annotations

from fastapi import Depends
from starlette.responses import JSONResponse

from cuesheet.api.behavior import (
    behavior,
    OpenEventGroup,
)

from cuesheet.api.usecase import user_register
from cuesheet.api.usecase import user_login


# #
# command

async def post_register(
    body: user_register.Input,
    *,
    scope=Depends(behavior.request(OpenEventGroup())),
) -> JSONResponse:
    registered = await user_register.register(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
    )
    return JSONResponse(status_code=200, content=registered.to_dict())


async def post_session(
    body: user_login.Input,
    *,
    scope=Depends(behavior.request(OpenEventGroup())),
) -> JSONResponse:
    logged_in = await user_login.login(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
    )
    return JSONResponse(status_code=200, content=logged_in.to_dict())
