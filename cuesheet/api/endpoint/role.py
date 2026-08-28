from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from starlette.responses import JSONResponse

from cuesheet.api.behavior import (
    behavior,
    AuthenticateUser,
    AuthorizeParticipant,
    AuthorizeManager,
    OpenEventGroup,
)

from cuesheet.api.usecase import role_create
from cuesheet.api.usecase import role_delete


# #
# command

async def post_create(
    cuesheet_id: UUID,
    body: role_create.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    created = await role_create.create(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def delete_role(
    cuesheet_id: UUID,
    role_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    removed = await role_delete.delete(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=role_delete.Input(id=str(role_id)),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=removed.to_dict())
