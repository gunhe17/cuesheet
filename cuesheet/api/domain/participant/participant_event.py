from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.participant.participant import Participant


class ParticipantEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class ParticipantEvent(Event):
    _kind: ParticipantEventKind
    participant: Participant

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, participant: Participant) -> tuple["ParticipantEvent", Participant]:
        return cls(_kind=ParticipantEventKind.CREATED, participant=participant), participant

    @classmethod
    @typecheck
    def updated(cls, *, participant: Participant) -> tuple["ParticipantEvent", Participant]:
        return cls(_kind=ParticipantEventKind.UPDATED, participant=participant), participant

    @classmethod
    @typecheck
    def deleted(cls, *, participant: Participant) -> tuple["ParticipantEvent", Participant]:
        return cls(_kind=ParticipantEventKind.DELETED, participant=participant), participant

    @classmethod
    @typecheck
    def read(cls, *, participant: Participant) -> tuple["ParticipantEvent", Participant]:
        return cls(_kind=ParticipantEventKind.READ, participant=participant), participant

    @classmethod
    @typecheck
    def read_many(cls, *, participants: list) -> list[tuple["ParticipantEvent", Participant]]:
        return [
            (cls(_kind=ParticipantEventKind.READ, participant=participant), participant)
            for participant in participants
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "participant"

    def act_entity_id(self) -> UUID:
        return self.participant.id

    def payload(self) -> dict:
        return {"participant_user_id": str(self.participant.user_id)}
