from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.role.role import Role


class RoleEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class RoleEvent(Event):
    _kind: RoleEventKind
    role: Role

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, role: Role) -> tuple["RoleEvent", Role]:
        return cls(_kind=RoleEventKind.CREATED, role=role), role

    @classmethod
    @typecheck
    def updated(cls, *, role: Role) -> tuple["RoleEvent", Role]:
        return cls(_kind=RoleEventKind.UPDATED, role=role), role

    @classmethod
    @typecheck
    def deleted(cls, *, role: Role) -> tuple["RoleEvent", Role]:
        return cls(_kind=RoleEventKind.DELETED, role=role), role

    @classmethod
    @typecheck
    def read(cls, *, role: Role) -> tuple["RoleEvent", Role]:
        return cls(_kind=RoleEventKind.READ, role=role), role

    @classmethod
    @typecheck
    def read_many(cls, *, roles: list) -> list[tuple["RoleEvent", Role]]:
        return [
            (cls(_kind=RoleEventKind.READ, role=role), role)
            for role in roles
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "role"

    def act_entity_id(self) -> UUID:
        return self.role.id

    def payload(self) -> dict:
        return {"role_name": self.role.name.to_str()}
