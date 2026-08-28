from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import AlreadyExistsError, ForbiddenError, NotFoundError

from cuesheet.api.domain.participant.participant import Participant
from cuesheet.api.domain.participant.can_advance import CanAdvance
from cuesheet.api.domain.participant.role_ids import RoleIds

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository
from cuesheet.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class ParticipantModel(Model):
    __tablename__ = "participants"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    cuesheet_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        info={"scope": "cuesheet"},
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    can_advance: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    role_ids: Mapped[list] = mapped_column(
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
        Index(
            "uq_participants_cuesheet_user_active",
            "cuesheet_id",
            "user_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_participant(model: ParticipantModel) -> Participant:
    participant = Participant(
        id=model.id,
        cuesheet_id=model.cuesheet_id,
        user_id=model.user_id,
        can_advance=CanAdvance.from_bool(model.can_advance),
        role_ids=RoleIds.from_json(model.role_ids),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return participant


# #
# repository

# participants 는 RLS 밖이다. AuthorizeParticipant 가 스코프를 걸기 전에 읽어야 해서,
# 격리는 아래 finder 들의 명시적 cuesheet_id 조건이 진다
class ParticipantRepository(PostgresRepository[Participant, ParticipantModel]):
    model = ParticipantModel
    mapper = _to_participant

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_cuesheet_and_user(cls, *, session: AsyncSession, entity: Participant) -> Participant:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("cuesheet_id", "user_id")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("Participant", str(entity.user_id))
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID, cuesheet_id: UUID) -> Participant:
        participant = await cls._find(
            session=session,
            where=[ParticipantModel.id == id, ParticipantModel.cuesheet_id == cuesheet_id],
        )
        if participant is None:
            raise NotFoundError("Participant", str(id))
        return participant

    @classmethod
    @typecheck
    async def get_valid_by_user_and_cuesheet(
        cls,
        *,
        session: AsyncSession,
        user_id: UUID,
        cuesheet_id: UUID,
    ) -> Participant:
        # 참여자가 아니면 403. 존재 여부를 묻는 질문이 아니라 접근 질문이다
        participant = await cls._find(
            session=session,
            where=[
                ParticipantModel.user_id == user_id,
                ParticipantModel.cuesheet_id == cuesheet_id,
            ],
        )
        if participant is None:
            raise ForbiddenError("Cuesheet")
        return participant

    @classmethod
    @typecheck
    async def find_by_user_and_cuesheet(
        cls,
        *,
        session: AsyncSession,
        user_id: UUID,
        cuesheet_id: UUID,
    ) -> Participant | None:
        return await cls._find(
            session=session,
            where=[
                ParticipantModel.user_id == user_id,
                ParticipantModel.cuesheet_id == cuesheet_id,
            ],
        )

    @classmethod
    @typecheck
    async def filter_by_user_id(cls, *, session: AsyncSession, user_id: UUID) -> list[Participant]:
        return await cls._filter(
            session=session,
            where=[ParticipantModel.user_id == user_id],
        )

    @classmethod
    @typecheck
    async def filter_by_cuesheet_id(cls, *, session: AsyncSession, cuesheet_id: UUID) -> list[Participant]:
        return await cls._filter(
            session=session,
            where=[ParticipantModel.cuesheet_id == cuesheet_id],
            order_by="created_at",
        )

    # #
    # update

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: Participant) -> Participant:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Participant", str(entity.id))
        return updated
