from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import NotFoundError

from cuesheet.api.domain.cuesheet.cuesheet import Cuesheet
from cuesheet.api.domain.cuesheet.cuesheet_title import CuesheetTitle
from cuesheet.api.domain.cuesheet.scheduled_at import ScheduledAt
from cuesheet.api.domain.cuesheet.invite_token import InviteToken
from cuesheet.api.domain.cuesheet.cue_started_at import CueStartedAt
from cuesheet.api.domain.cuesheet.ended_at import EndedAt

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class CuesheetModel(Model):
    __tablename__ = "cuesheets"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        info={"scope": "cuesheet"},
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    manager_token: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
    )
    viewer_token: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
    )
    current_cue_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    prev_cue_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    cue_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

def _to_cuesheet(model: CuesheetModel) -> Cuesheet:
    cuesheet = Cuesheet(
        id=model.id,
        owner_user_id=model.owner_user_id,
        title=CuesheetTitle.from_str(model.title),
        scheduled_at=ScheduledAt.from_datetime(model.scheduled_at),
        manager_token=InviteToken.from_str(model.manager_token),
        viewer_token=InviteToken.from_str(model.viewer_token),
        current_cue_id=model.current_cue_id,
        prev_cue_id=model.prev_cue_id,
        cue_started_at=(
            CueStartedAt.from_datetime(model.cue_started_at) if model.cue_started_at else None
        ),
        ended_at=(
            EndedAt.from_datetime(model.ended_at) if model.ended_at else None
        ),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return cuesheet


# #
# repository

class CuesheetRepository(PostgresRepository[Cuesheet, CuesheetModel]):
    model = CuesheetModel
    mapper = _to_cuesheet

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID) -> Cuesheet:
        cuesheet = await cls.find_by_id(session=session, id=id)
        if cuesheet is None:
            raise NotFoundError("Cuesheet", str(id))
        return cuesheet

    @classmethod
    @typecheck
    async def filter_by_ids(cls, *, session: AsyncSession, ids: list) -> list[Cuesheet]:
        if not ids:
            return []
        return await cls._filter(
            session=session,
            where=[CuesheetModel.id.in_(ids)],
            order_by="scheduled_at",
            descending=True,
        )

    # #
    # update

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: Cuesheet) -> Cuesheet:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Cuesheet", str(entity.id))
        return updated
