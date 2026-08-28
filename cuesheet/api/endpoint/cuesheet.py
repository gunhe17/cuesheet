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

from cuesheet.api.usecase import cuesheet_create
from cuesheet.api.usecase import cuesheet_search
from cuesheet.api.usecase import cuesheet_get
from cuesheet.api.usecase import cuesheet_update
from cuesheet.api.usecase import cuesheet_start
from cuesheet.api.usecase import cuesheet_advance
from cuesheet.api.usecase import cuesheet_rewind
from cuesheet.api.usecase import cuesheet_end


# #
# command

async def post_create(
    body: cuesheet_create.Input,
    *,
    scope=Depends(behavior.request(AuthenticateUser(), OpenEventGroup())),
) -> JSONResponse:
    created = await cuesheet_create.create(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def get_list(
    *,
    scope=Depends(behavior.request(AuthenticateUser(), OpenEventGroup())),
) -> JSONResponse:
    listed = await cuesheet_search.search(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cuesheet_search.Input(),
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=listed.to_dict())


async def get_read(
    cuesheet_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), OpenEventGroup())),
) -> JSONResponse:
    found = await cuesheet_get.get(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cuesheet_get.Input(),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=found.to_dict())


async def patch_update(
    cuesheet_id: UUID,
    body: cuesheet_update.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    updated = await cuesheet_update.update(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=updated.to_dict())


async def post_start(
    cuesheet_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    started = await cuesheet_start.start(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cuesheet_start.Input(),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=started.to_dict())


async def post_advance(
    cuesheet_id: UUID,
    body: cuesheet_advance.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    advanced = await cuesheet_advance.advance(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=advanced.to_dict())


async def post_rewind(
    cuesheet_id: UUID,
    body: cuesheet_rewind.Input,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    rewound = await cuesheet_rewind.rewind(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=body,
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=rewound.to_dict())


async def post_end(
    cuesheet_id: UUID,
    *,
    scope=Depends(behavior.request_cuesheet(AuthenticateUser(), AuthorizeParticipant(), AuthorizeManager(), OpenEventGroup())),
) -> JSONResponse:
    ended = await cuesheet_end.end(
        session=scope.session,
        event_group_id=scope.event_group_id,
        input=cuesheet_end.Input(),
        cuesheet_id=cuesheet_id,
        user_id=scope.user_id,
    )
    return JSONResponse(status_code=200, content=ended.to_dict())
