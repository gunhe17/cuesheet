from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.event.atomic_event.act import Act
from cuesheet.api.domain.event.atomic_event.entity_name import EntityName


@dataclass(frozen=True, kw_only=True)
class AtomicEvent(Entity):
    event_id: UUID
    act: Act
    act_entity_name: EntityName
    act_entity_id: UUID
    actor_user_id: UUID | None = None
    actor_cuesheet_id: UUID | None = None
    sequence: int | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        id: UUID,
        event_id: UUID,
        act: Act,
        act_entity_name: EntityName,
        act_entity_id: UUID,
        actor_user_id: UUID | None = None,
        actor_cuesheet_id: UUID | None = None,
    ) -> "AtomicEvent":
        return cls(
            id=id,
            event_id=event_id,
            act=act,
            act_entity_name=act_entity_name,
            act_entity_id=act_entity_id,
            actor_user_id=actor_user_id,
            actor_cuesheet_id=actor_cuesheet_id,
            by_factory=True,
        )

    @classmethod
    @typecheck
    def from_atomic(
        cls,
        *,
        atomic,
        event_id: UUID,
        actor_user_id: UUID | None = None,
        actor_cuesheet_id: UUID | None = None,
    ) -> "AtomicEvent":
        return cls.new(
            id=atomic.id(),
            event_id=event_id,
            act=Act.from_str(atomic.act()),
            act_entity_name=EntityName.from_str(atomic.act_entity_name()),
            act_entity_id=atomic.act_entity_id(),
            actor_user_id=actor_user_id,
            actor_cuesheet_id=actor_cuesheet_id,
        )

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sequence": self.sequence,
            "event_id": str(self.event_id),
            "actor_user_id": (
                str(self.actor_user_id) if self.actor_user_id else None
            ),
            "actor_cuesheet_id": (
                str(self.actor_cuesheet_id) if self.actor_cuesheet_id else None
            ),
            "act": self.act.to_str(),
            "act_entity_name": self.act_entity_name.to_str(),
            "act_entity_id": str(self.act_entity_id),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "actor_user_id": self.actor_user_id,
            "actor_cuesheet_id": self.actor_cuesheet_id,
            "act": self.act.to_str(),
            "act_entity_name": self.act_entity_name.to_str(),
            "act_entity_id": self.act_entity_id,
        }
