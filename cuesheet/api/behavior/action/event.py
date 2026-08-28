from __future__ import annotations

from cuesheet.api.core.behavior import Action, Memory

from cuesheet.api.behavior.context.event import EventGroupContext


# #
# require

class OpenEventGroup(Action):

    @classmethod
    async def act(cls, memory: Memory) -> None:
        memory.event_group = await EventGroupContext.setup()
