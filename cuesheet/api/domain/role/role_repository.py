from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import AlreadyExistsError, NotFoundError

from cuesheet.api.domain.role.role import Role
from cuesheet.api.domain.role.role_name import RoleName

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository
from cuesheet.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class RoleModel(Model):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    cuesheet_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        info={"scope": "cuesheet"},
    )
    name: Mapped[str] = mapped_column(
        String,
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
            "uq_roles_name_active",
            "cuesheet_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_role(model: RoleModel) -> Role:
    role = Role(
        id=model.id,
        cuesheet_id=model.cuesheet_id,
        name=RoleName.from_str(model.name),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return role


# #
# repository

class RoleRepository(PostgresRepository[Role, RoleModel]):
    model = RoleModel
    mapper = _to_role

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_name(cls, *, session: AsyncSession, entity: Role) -> Role:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("cuesheet_id", "name")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("Role", entity.name.to_str())
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID, cuesheet_id: UUID) -> Role:
        role = await cls._find(
            session=session,
            where=[RoleModel.id == id, RoleModel.cuesheet_id == cuesheet_id],
        )
        if role is None:
            raise NotFoundError("Role", str(id))
        return role

    @classmethod
    @typecheck
    async def filter_by_cuesheet_id(cls, *, session: AsyncSession, cuesheet_id: UUID) -> list[Role]:
        return await cls._filter(
            session=session,
            where=[RoleModel.cuesheet_id == cuesheet_id],
            order_by="name",
        )

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> Role:
        removed = await super().remove_by_id(session=session, id=id)
        if removed is None:
            raise NotFoundError("Role", str(id))
        return removed
