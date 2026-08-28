from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import AlreadyExistsError, NotFoundError

from cuesheet.api.domain.cue.cue import Cue
from cuesheet.api.domain.cue.seq import Seq
from cuesheet.api.domain.cue.cue_title import CueTitle
from cuesheet.api.domain.cue.planned_sec import PlannedSec
from cuesheet.api.domain.cue.color import Color

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository
from cuesheet.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class CueModel(Model):
    __tablename__ = "cues"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    cuesheet_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        info={"scope": "cuesheet"},
    )
    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    color: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default="slate",
    )
    planned_sec: Mapped[int] = mapped_column(
        Integer,
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
        Index(
            "uq_cues_seq_active",
            "cuesheet_id",
            "seq",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_cue(model: CueModel) -> Cue:
    cue = Cue(
        id=model.id,
        cuesheet_id=model.cuesheet_id,
        seq=Seq.from_int(model.seq),
        title=CueTitle.from_str(model.title),
        planned_sec=PlannedSec.from_int(model.planned_sec),
        color=Color.from_str(model.color),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return cue


# #
# repository

class CueRepository(PostgresRepository[Cue, CueModel]):
    model = CueModel
    mapper = _to_cue

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_seq(cls, *, session: AsyncSession, entity: Cue) -> Cue:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("cuesheet_id", "seq")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("Cue", str(entity.seq.to_int()))
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID, cuesheet_id: UUID) -> Cue:
        cue = await cls._find(
            session=session,
            where=[CueModel.id == id, CueModel.cuesheet_id == cuesheet_id],
        )
        if cue is None:
            raise NotFoundError("Cue", str(id))
        return cue

    @classmethod
    @typecheck
    async def filter_by_cuesheet_id(cls, *, session: AsyncSession, cuesheet_id: UUID) -> list[Cue]:
        return await cls._filter(
            session=session,
            where=[CueModel.cuesheet_id == cuesheet_id],
            order_by="seq",
        )

    @classmethod
    @typecheck
    async def find_first(cls, *, session: AsyncSession, cuesheet_id: UUID) -> Cue | None:
        return await cls._find(
            session=session,
            where=[CueModel.cuesheet_id == cuesheet_id],
            order_by="seq",
        )

    @classmethod
    @typecheck
    async def find_next(cls, *, session: AsyncSession, cuesheet_id: UUID, seq: Seq) -> Cue | None:
        return await cls._find(
            session=session,
            where=[CueModel.cuesheet_id == cuesheet_id, CueModel.seq > seq.to_int()],
            order_by="seq",
        )

    # #
    # update

    @classmethod
    @typecheck
    async def update_unique_by_seq(cls, *, session: AsyncSession, entity: Cue) -> Cue:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("cuesheet_id", "seq")],
                exclude_id=entity.id,
            )
        except UniqueViolationError:
            raise AlreadyExistsError("Cue", str(entity.seq.to_int()))
        return await cls.update(session=session, entity=entity)

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: Cue) -> Cue:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Cue", str(entity.id))
        return updated

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> Cue:
        removed = await super().remove_by_id(session=session, id=id)
        if removed is None:
            raise NotFoundError("Cue", str(id))
        return removed
