from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse

from cuesheet.api.behavior import (
    behavior,
    AuthenticateUser,
    AuthorizeParticipant,
    AuthorizeManager,
    OpenEventGroup,
)

from cuesheet.api.usecase import participant_join
from cuesheet.api.usecase import participant_update


# #
# body

class UpdateBody(BaseModel):
    can_advance: bool | None = None
    role_ids: list[str] | None = None


# #
# command

async def post_join(
    cuesheet_id: UUID,
    body: participant_join.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), OpenEventGroup())),
) -> JSONResponse:
    joined = await participant_join.join(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=joined.to_dict())


async def patch_update(
    cuesheet_id: UUID,
    participant_id: UUID,
    body: UpdateBody,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    updated = await participant_update.update(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=participant_update.Input(
            id=str(participant_id),
            can_advance=body.can_advance,
            role_ids=body.role_ids,
        ),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=updated.to_dict())
