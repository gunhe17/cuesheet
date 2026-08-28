from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cuesheet.api.core.model import Model
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import AlreadyExistsError, InvalidCredentialError, NotFoundError

from cuesheet.api.domain.user.user import User
from cuesheet.api.domain.user.login_id import LoginId
from cuesheet.api.domain.user.user_name import UserName
from cuesheet.api.domain.user.pin_hash import PinHash
from cuesheet.api.domain.user.session_token import SessionToken
from cuesheet.api.domain.user.failed_count import FailedCount
from cuesheet.api.domain.user.locked_until import LockedUntil

from cuesheet.api.infrastructure.database.postgresql.repository import PostgresRepository
from cuesheet.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class UserModel(Model):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        info={"scope": "user"},
    )
    login_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    pin_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    session_token: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        Index(
            "uq_users_login_id_active",
            "login_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_session_token_active",
            "session_token",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND session_token IS NOT NULL"),
        ),
    )


# #
# mapper

def _to_user(model: UserModel) -> User:
    user = User(
        id=model.id,
        login_id=LoginId.from_str(model.login_id),
        name=UserName.from_str(model.name),
        pin_hash=PinHash.from_str(model.pin_hash),
        session_token=(
            SessionToken.from_str(model.session_token) if model.session_token else None
        ),
        failed_count=FailedCount.from_int(model.failed_count),
        locked_until=(
            LockedUntil.from_datetime(model.locked_until) if model.locked_until else None
        ),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return user


# #
# repository

class UserRepository(PostgresRepository[User, UserModel]):
    model = UserModel
    mapper = _to_user

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_login_id(cls, *, session: AsyncSession, entity: User) -> User:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=["login_id"],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("User", entity.login_id.to_str())
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID) -> User:
        user = await cls.find_by_id(session=session, id=id)
        if user is None:
            raise NotFoundError("User", str(id))
        return user

    @classmethod
    @typecheck
    async def verify_login_id(cls, *, session: AsyncSession, login_id: LoginId) -> User:
        # 없음 = 인증 실패. 계정 존재 여부를 노출하지 않는다
        user = await cls._find_by(session=session, column="login_id", value=login_id.to_str())
        if user is None:
            raise InvalidCredentialError()
        return user

    @classmethod
    @typecheck
    async def get_by_session_token(cls, *, session: AsyncSession, session_token: SessionToken) -> User:
        user = await cls._find_by(
            session=session,
            column="session_token",
            value=session_token.to_str(),
        )
        if user is None:
            raise InvalidCredentialError()
        return user

    # #
    # update

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: User) -> User:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("User", str(entity.id))
        return updated
