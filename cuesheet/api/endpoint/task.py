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

from cuesheet.api.usecase import task_create
from cuesheet.api.usecase import task_update
from cuesheet.api.usecase import task_delete
from cuesheet.api.usecase import task_check
from cuesheet.api.usecase import task_uncheck


# #
# body

class UpdateBody(BaseModel):
    instruction: str | None = None
    note: str | None = None


# #
# command

async def post_create(
    cuesheet_id: UUID,
    body: task_create.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    created = await task_create.create(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def patch_update(
    cuesheet_id: UUID,
    task_id: UUID,
    body: UpdateBody,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    updated = await task_update.update(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=task_update.Input(
            id=str(task_id),
            instruction=body.instruction,
            note=body.note,
        ),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=updated.to_dict())


async def delete_task(
    cuesheet_id: UUID,
    task_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    removed = await task_delete.delete(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=task_delete.Input(id=str(task_id)),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=removed.to_dict())


async def post_check(
    cuesheet_id: UUID,
    task_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), OpenEventGroup())),
) -> JSONResponse:
    checked = await task_check.check(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=task_check.Input(id=str(task_id)),
        cuesheet_id=cuesheet_id,
        participant_id=scope.participant_id,
        can_advance=scope.can_advance,
        role_ids=scope.role_ids,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=checked.to_dict())


async def delete_check(
    cuesheet_id: UUID,
    task_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), OpenEventGroup())),
) -> JSONResponse:
    unchecked = await task_uncheck.uncheck(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=task_uncheck.Input(id=str(task_id)),
        cuesheet_id=cuesheet_id,
        can_advance=scope.can_advance,
        role_ids=scope.role_ids,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=unchecked.to_dict())
