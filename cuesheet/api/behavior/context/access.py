from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from cuesheet.api.core.behavior import Context

from cuesheet.api.behavior.common.exception import ForbiddenError, UnauthorizedError

from cuesheet.api.domain.user.session_token import SessionToken
from cuesheet.api.domain.user.user_repository import UserRepository
from cuesheet.api.domain.participant.participant_repository import ParticipantRepository

from cuesheet.api.infrastructure.hash.sha256.client import sha256


# #
# user

@dataclass(frozen=True)
class UserContext(Context):
    user_id: UUID

    @classmethod
    async def setup(
        cls,
        *,
        session: AsyncSession,
        authorization: str | None = None,
    ) -> UserContext:
        return UserContext(
            user_id=(
                await _resolve_user(
                    session=session,
                    authorization=authorization,
                )
            )
        )


# #
# participant

@dataclass(frozen=True)
class ParticipantContext(Context):
    user_id: UUID
    cuesheet_id: UUID
    participant_id: UUID
    can_advance: bool
    role_ids: list[str]

    @classmethod
    async def setup(
        cls,
        cuesheet_id: UUID,
        *,
        session: AsyncSession,
        user: UserContext,
    ) -> ParticipantContext:
        participant = await ParticipantRepository.get_valid_by_user_and_cuesheet(
            session=session,
            user_id=user.user_id,
            cuesheet_id=cuesheet_id,
        )
        return ParticipantContext(
            user_id=user.user_id,
            cuesheet_id=cuesheet_id,
            participant_id=participant.id,
            can_advance=participant.can_advance.to_bool(),
            role_ids=participant.role_ids.to_json(),
        )


# #
# helpers

async def _resolve_user(*, session: AsyncSession, authorization: str | None) -> UUID:
    # bearer
    if authorization is None or not authorization.startswith("Bearer "):
        raise UnauthorizedError()

    # authenticate
    raw = authorization[len("Bearer "):].strip()
    user = await UserRepository.get_by_session_token(
        session=session,
        session_token=SessionToken.from_str(sha256.hash(value=raw)),
    )
    return user.id


def ensure_manager(participant: ParticipantContext | None) -> None:
    # 봉투가 AuthorizeParticipant 를 먼저 돌리지 않았다는 뜻이라 조립 실수다
    if participant is None:
        raise UnauthorizedError()
    if not participant.can_advance:
        raise ForbiddenError("Cuesheet")
