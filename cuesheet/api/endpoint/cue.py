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

from cuesheet.api.usecase import cue_create
from cuesheet.api.usecase import cue_update
from cuesheet.api.usecase import cue_delete


# #
# body

class UpdateBody(BaseModel):
    seq: int | None = None
    title: str | None = None
    planned_sec: int | None = None


# #
# command

async def post_create(
    cuesheet_id: UUID,
    body: cue_create.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    created = await cue_create.create(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def patch_update(
    cuesheet_id: UUID,
    cue_id: UUID,
    body: UpdateBody,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    updated = await cue_update.update(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cue_update.Input(
            id=str(cue_id),
            seq=body.seq,
            title=body.title,
            planned_sec=body.planned_sec,
        ),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=updated.to_dict())


async def delete_cue(
    cuesheet_id: UUID,
    cue_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    removed = await cue_delete.delete(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cue_delete.Input(id=str(cue_id)),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=removed.to_dict())
