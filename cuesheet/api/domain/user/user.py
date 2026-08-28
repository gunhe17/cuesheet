from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.user.login_id import LoginId
from cuesheet.api.domain.user.user_name import UserName
from cuesheet.api.domain.user.pin_hash import PinHash
from cuesheet.api.domain.user.session_token import SessionToken
from cuesheet.api.domain.user.failed_count import FailedCount
from cuesheet.api.domain.user.locked_until import LockedUntil


@dataclass(frozen=True, kw_only=True)
class User(Entity):
    login_id: LoginId
    name: UserName
    pin_hash: PinHash
    session_token: SessionToken | None = None
    failed_count: FailedCount = FailedCount.from_int(0)
    locked_until: LockedUntil | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        login_id: LoginId,
        name: UserName,
        pin_hash: PinHash,
    ) -> "User":
        user = cls(
            login_id=login_id,
            name=name,
            pin_hash=pin_hash,
            failed_count=FailedCount.from_int(0),
            by_factory=True,
        )
        return user

    # #
    # update

    def with_session_token(self, session_token: SessionToken) -> "User":
        return replace(self, session_token=session_token, by_factory=True)

    # #
    # transition

    def fail_login(self, *, at: datetime, max_attempts: int, lock_sec: int) -> "User":
        attempted = self.failed_count.increment()

        # cap
        if attempted.to_int() >= max_attempts:
            return replace(
                self,
                failed_count=FailedCount.from_int(0),
                locked_until=LockedUntil.from_datetime(at + timedelta(seconds=lock_sec)),
                by_factory=True,
            )

        return replace(self, failed_count=attempted, by_factory=True)

    def succeed_login(self, *, session_token: SessionToken) -> "User":
        return replace(
            self,
            session_token=session_token,
            failed_count=FailedCount.from_int(0),
            locked_until=None,
            by_factory=True,
        )

    def is_locked(self, *, at: datetime) -> bool:
        return self.locked_until is not None and self.locked_until.is_active(at=at)

    # #
    # query

    def to_dict(self):
        # pin_hash·session_token 은 to_dict 에 안 실음
        return {
            "id": str(self.id),
            "login_id": self.login_id.to_str(),
            "name": self.name.to_str(),
            "locked_until": (
                self.locked_until.to_str() if self.locked_until else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "login_id": self.login_id.to_str(),
            "name": self.name.to_str(),
            "pin_hash": self.pin_hash.to_str(),
            "session_token": (
                self.session_token.to_str() if self.session_token else None
            ),
            "failed_count": self.failed_count.to_int(),
            "locked_until": (
                self.locked_until.to_datetime() if self.locked_until else None
            ),
        }
