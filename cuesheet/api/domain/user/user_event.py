from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.user.user import User


class UserEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class UserEvent(Event):
    _kind: UserEventKind
    user: User

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, user: User) -> tuple["UserEvent", User]:
        return cls(_kind=UserEventKind.CREATED, user=user), user

    @classmethod
    @typecheck
    def updated(cls, *, user: User) -> tuple["UserEvent", User]:
        return cls(_kind=UserEventKind.UPDATED, user=user), user

    @classmethod
    @typecheck
    def read(cls, *, user: User) -> tuple["UserEvent", User]:
        return cls(_kind=UserEventKind.READ, user=user), user

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "user"

    def act_entity_id(self) -> UUID:
        return self.user.id

    def payload(self) -> dict:
        # pin_hash·session_token 은 절대 싣지 않는다
        return {"login_id": self.user.login_id.to_str()}
