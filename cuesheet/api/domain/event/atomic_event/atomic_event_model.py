from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Identity, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model

from cuesheet.api.domain.event.atomic_event.atomic_event import AtomicEvent
from cuesheet.api.domain.event.atomic_event.act import Act
from cuesheet.api.domain.event.atomic_event.entity_name import EntityName


# #
# model

class AtomicEventModel(Model):
    __tablename__ = "atomic_events"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        nullable=False,
        unique=True,
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    actor_cuesheet_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        info={"scope": "cuesheet"},
    )
    act: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    act_entity_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    act_entity_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        info={"ref_by": "act_entity_name"},
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# #
# mapper

def _to_atomic_event(model: AtomicEventModel) -> AtomicEvent:
    atomic_event = AtomicEvent(
        id=model.id,
        sequence=model.sequence,
        event_id=model.event_id,
        actor_user_id=model.actor_user_id,
        actor_cuesheet_id=model.actor_cuesheet_id,
        act=Act.from_str(model.act),
        act_entity_name=EntityName.from_str(model.act_entity_name),
        act_entity_id=model.act_entity_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return atomic_event
