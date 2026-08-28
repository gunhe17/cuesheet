from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cue.cue import Cue


class CueEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class CueEvent(Event):
    _kind: CueEventKind
    cue: Cue

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, cue: Cue) -> tuple["CueEvent", Cue]:
        return cls(_kind=CueEventKind.CREATED, cue=cue), cue

    @classmethod
    @typecheck
    def updated(cls, *, cue: Cue) -> tuple["CueEvent", Cue]:
        return cls(_kind=CueEventKind.UPDATED, cue=cue), cue

    @classmethod
    @typecheck
    def deleted(cls, *, cue: Cue) -> tuple["CueEvent", Cue]:
        return cls(_kind=CueEventKind.DELETED, cue=cue), cue

    @classmethod
    @typecheck
    def read(cls, *, cue: Cue) -> tuple["CueEvent", Cue]:
        return cls(_kind=CueEventKind.READ, cue=cue), cue

    @classmethod
    @typecheck
    def read_many(cls, *, cues: list) -> list[tuple["CueEvent", Cue]]:
        return [
            (cls(_kind=CueEventKind.READ, cue=cue), cue)
            for cue in cues
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "cue"

    def act_entity_id(self) -> UUID:
        return self.cue.id

    def payload(self) -> dict:
        return {"cue_title": self.cue.title.to_str(), "cue_seq": self.cue.seq.to_int()}
