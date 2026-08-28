from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.event.event.event_name import EventName
from cuesheet.api.domain.event.event.payload import Payload


@dataclass(frozen=True, kw_only=True)
class Event(Entity):
    name: EventName
    payload: Payload

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, id: UUID, name: EventName, payload: Payload) -> "Event":
        event = cls(
            id=id,
            name=name,
            payload=payload,
            by_factory=True,
        )
        return event

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name.to_str(),
            "payload": self.payload.to_dict(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "name": self.name.to_str(),
            "payload": self.payload.to_dict(),
        }
