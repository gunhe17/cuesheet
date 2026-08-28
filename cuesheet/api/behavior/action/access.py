from __future__ import annotations

from cuesheet.api.core.behavior import Action, Memory

from cuesheet.api.behavior.context.access import UserContext
from cuesheet.api.behavior.context.access import ParticipantContext
from cuesheet.api.behavior.context.access import ensure_manager
from cuesheet.api.behavior.action.tenant import Tenant


# #
# access

class AuthenticateUser(Action):

    @classmethod
    async def act(cls, memory: Memory) -> None:
        memory.user = await UserContext.setup(
            session=memory.session,
            authorization=memory.authorization,
        )


class AuthorizeParticipant(Action):

    @classmethod
    async def act(cls, memory: Memory) -> None:
        memory.participant = await ParticipantContext.setup(
            memory.cuesheet_id,
            session=memory.session,
            user=memory.user,
        )
        await Tenant.set_tenant_scope(session=memory.session, cuesheet_id=memory.participant.cuesheet_id)


class AuthorizeManager(Action):

    @classmethod
    async def act(cls, memory: Memory) -> None:
        ensure_manager(memory.participant)
