from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.role.role import Role
from cuesheet.api.domain.role.role_name import RoleName
from cuesheet.api.domain.role.role_repository import RoleRepository
from cuesheet.api.domain.role.role_event import RoleEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    name: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def create(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # persist
    event, role = RoleEvent.created(
        role=(
            await RoleRepository.add_unique_by_name(
                session=session,
                entity=Role.new(
                    cuesheet_id=cuesheet_id,
                    name=RoleName.from_str(input.name),
                ),
            )
        )
    )

    # return
    return Output(
        data=role.to_dict(),
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="role_create",
                    atomics=[event],
                    actor_user_id=user_id,
                    actor_cuesheet_id=cuesheet_id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuesheet-id", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await create(
                session=session,
                event_group_id=uuid4(),
                input=Input(name=args.name),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
