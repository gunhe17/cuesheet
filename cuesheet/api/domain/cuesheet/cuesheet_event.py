from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cuesheet import Cuesheet


class CuesheetEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class CuesheetEvent(Event):
    _kind: CuesheetEventKind
    cuesheet: Cuesheet

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, cuesheet: Cuesheet) -> tuple["CuesheetEvent", Cuesheet]:
        return cls(_kind=CuesheetEventKind.CREATED, cuesheet=cuesheet), cuesheet

    @classmethod
    @typecheck
    def updated(cls, *, cuesheet: Cuesheet) -> tuple["CuesheetEvent", Cuesheet]:
        return cls(_kind=CuesheetEventKind.UPDATED, cuesheet=cuesheet), cuesheet

    @classmethod
    @typecheck
    def deleted(cls, *, cuesheet: Cuesheet) -> tuple["CuesheetEvent", Cuesheet]:
        return cls(_kind=CuesheetEventKind.DELETED, cuesheet=cuesheet), cuesheet

    @classmethod
    @typecheck
    def read(cls, *, cuesheet: Cuesheet) -> tuple["CuesheetEvent", Cuesheet]:
        return cls(_kind=CuesheetEventKind.READ, cuesheet=cuesheet), cuesheet

    @classmethod
    @typecheck
    def read_many(cls, *, cuesheets: list) -> list[tuple["CuesheetEvent", Cuesheet]]:
        return [
            (cls(_kind=CuesheetEventKind.READ, cuesheet=cuesheet), cuesheet)
            for cuesheet in cuesheets
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "cuesheet"

    def act_entity_id(self) -> UUID:
        return self.cuesheet.id

    def payload(self) -> dict:
        return {"title": self.cuesheet.title.to_str()}
