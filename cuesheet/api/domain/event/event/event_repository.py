from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.event.event.event import Event
from cuesheet.api.domain.event.event.event_name import EventName
from cuesheet.api.domain.event.event.payload import Payload

from cuesheet.api.domain.event.atomic_event.atomic_event import AtomicEvent
from cuesheet.api.domain.event.atomic_event.atomic_event_model import AtomicEventModel
from cuesheet.api.domain.event.atomic_event.atomic_event_model import _to_atomic_event

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class EventModel(Model):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
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

    __table_args__ = (
        {"info": {"scope": "global"}},
    )


# #
# mapper

def _to_event(model: EventModel) -> Event:
    event = Event(
        id=model.id,
        name=EventName.from_str(model.name),
        payload=Payload.from_dict(model.payload),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return event


# #
# repository

class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    # #
    # create

    @classmethod
    @typecheck
    async def emit(
        cls,
        *,
        session: AsyncSession,
        id: UUID,
        name: str,
        atomics: list,
        actor_user_id: UUID | None = None,
        actor_cuesheet_id: UUID | None = None,
    ) -> list[AtomicEvent]:
        # merge
        payload = {}
        for atomic in atomics:
            payload.update(atomic.payload())

        # event
        statement = (
            pg_insert(cls.model)
            .values(**Event.new(
                id=id,
                name=EventName.from_str(name),
                payload=Payload.from_dict(payload),
            ).to_model())
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(statement)

        # atomic
        entities = [
            AtomicEvent.from_atomic(
                atomic=atomic,
                event_id=id,
                actor_user_id=actor_user_id,
                actor_cuesheet_id=actor_cuesheet_id,
            )
            for atomic in atomics
        ]
        models = [AtomicEventModel(**entity.to_model()) for entity in entities]
        session.add_all(models)
        await session.flush()
        return [
            _to_atomic_event(model) for model in models
        ]

    # #
    # atomic

    @classmethod
    @typecheck
    async def filter_by_event_id(cls, *, session: AsyncSession, event_id: UUID) -> list[AtomicEvent]:
        result = await session.scalars(
            select(AtomicEventModel)
            .where(
                AtomicEventModel.event_id == event_id,
                AtomicEventModel.deleted_at.is_(None),
            )
            .order_by(AtomicEventModel.sequence.asc())
        )
        return [
            _to_atomic_event(model) for model in result
        ]
