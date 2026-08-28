from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import NotFoundError

from cuesheet.api.domain.task.task import Task
from cuesheet.api.domain.task.instruction import Instruction
from cuesheet.api.domain.task.note import Note
from cuesheet.api.domain.task.done_at import DoneAt

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class TaskModel(Model):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    cuesheet_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        info={"scope": "cuesheet"},
    )
    cue_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    instruction: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    done_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    done_by_participant_id: Mapped[UUID | None] = mapped_column(
        Uuid,
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

def _to_task(model: TaskModel) -> Task:
    task = Task(
        id=model.id,
        cuesheet_id=model.cuesheet_id,
        cue_id=model.cue_id,
        role_id=model.role_id,
        instruction=Instruction.from_str(model.instruction),
        note=(
            Note.from_str(model.note) if model.note else None
        ),
        done_at=(
            DoneAt.from_datetime(model.done_at) if model.done_at else None
        ),
        done_by_participant_id=model.done_by_participant_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return task


# #
# repository

class TaskRepository(PostgresRepository[Task, TaskModel]):
    model = TaskModel
    mapper = _to_task

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID, cuesheet_id: UUID) -> Task:
        task = await cls._find(
            session=session,
            where=[TaskModel.id == id, TaskModel.cuesheet_id == cuesheet_id],
        )
        if task is None:
            raise NotFoundError("Task", str(id))
        return task

    @classmethod
    @typecheck
    async def filter_by_cuesheet_id(cls, *, session: AsyncSession, cuesheet_id: UUID) -> list[Task]:
        return await cls._filter(
            session=session,
            where=[TaskModel.cuesheet_id == cuesheet_id],
            order_by="created_at",
        )

    # #
    # update

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: Task) -> Task:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Task", str(entity.id))
        return updated

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> Task:
        removed = await super().remove_by_id(session=session, id=id)
        if removed is None:
            raise NotFoundError("Task", str(id))
        return removed
