from __future__ import annotations

from uuid import UUID
from typing import AsyncIterator, Callable
from dataclasses import dataclass, field

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from cuesheet.api.core.behavior import Action, Behavior, Scope, Memory

from cuesheet.api.behavior.context.access import UserContext
from cuesheet.api.behavior.context.access import ParticipantContext
from cuesheet.api.behavior.context.event import EventGroupContext
from cuesheet.api.behavior.action.access import AuthenticateUser, AuthorizeParticipant, AuthorizeManager
from cuesheet.api.behavior.action.event import OpenEventGroup

from cuesheet.api.infrastructure.database.postgresql.session import postgresql_transactional_session


# #
# server

class Server(Behavior):

    # #
    # Request

    def request(self, *requires: Action) -> Callable[..., AsyncIterator[Scope]]:

        # scope
        @dataclass(frozen=True)
        class RequestScope(Scope):
            # db
            session: AsyncSession
            # user
            user_id: UUID | None = None
            # event
            event_group_id: UUID | None = None

        # memory
        class RequestMemory(Memory):
            authorization: str | None = None
            session: AsyncSession | None = None
            user: UserContext | None = None
            participant: ParticipantContext | None = None
            event_group: EventGroupContext | None = None

        actions = self.set_action(requires)

        # flow
        async def request_flow(
            authorization: str | None = Header(default=None),
        ) -> AsyncIterator[Scope]:
            memory = RequestMemory(actions=actions)
            memory.authorization = authorization

            await self.run_action(memory, action=OpenEventGroup)

            async with postgresql_transactional_session() as session:
                memory.session = session

                await self.run_action(memory, action=AuthenticateUser)

                yield RequestScope(
                    session=session,
                    user_id=memory.user.user_id if memory.user else None,
                    event_group_id=memory.event_group.event_group_id if memory.event_group else None,
                )

        return request_flow


    # #
    # Request Cuesheet

    def request_cuesheet(self, *requires: Action) -> Callable[..., AsyncIterator[Scope]]:

        # scope
        @dataclass(frozen=True)
        class RequestCuesheetScope(Scope):
            # db
            session: AsyncSession
            # user
            user_id: UUID | None = None
            cuesheet_id: UUID | None = None
            participant_id: UUID | None = None
            can_advance: bool = False
            role_ids: list[str] = field(default_factory=list)
            # event
            event_group_id: UUID | None = None

        # memory
        class RequestMemory(Memory):
            cuesheet_id: UUID | None = None
            authorization: str | None = None
            session: AsyncSession | None = None
            user: UserContext | None = None
            participant: ParticipantContext | None = None
            event_group: EventGroupContext | None = None

        actions = self.set_action(requires)

        # flow
        async def request_flow(
            cuesheet_id: UUID,
            authorization: str | None = Header(default=None),
        ) -> AsyncIterator[Scope]:
            memory = RequestMemory(actions=actions)
            memory.cuesheet_id = cuesheet_id
            memory.authorization = authorization

            await self.run_action(memory, action=OpenEventGroup)

            async with postgresql_transactional_session() as session:
                memory.session = session

                await self.run_action(memory, action=AuthenticateUser)
                await self.run_action(memory, action=AuthorizeParticipant)
                await self.run_action(memory, action=AuthorizeManager)

                yield RequestCuesheetScope(
                    session=session,
                    user_id=memory.user.user_id if memory.user else None,
                    cuesheet_id=cuesheet_id,
                    participant_id=memory.participant.participant_id if memory.participant else None,
                    can_advance=memory.participant.can_advance if memory.participant else False,
                    role_ids=memory.participant.role_ids if memory.participant else [],
                    event_group_id=memory.event_group.event_group_id if memory.event_group else None,
                )

        return request_flow


behavior = Server()
