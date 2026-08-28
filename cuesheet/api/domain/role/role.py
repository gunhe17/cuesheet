from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.role.role_name import RoleName


@dataclass(frozen=True, kw_only=True)
class Role(Entity):
    cuesheet_id: UUID
    name: RoleName

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, cuesheet_id: UUID, name: RoleName) -> "Role":
        role = cls(cuesheet_id=cuesheet_id, name=name, by_factory=True)
        return role

    # #
    # update

    def with_name(self, name: RoleName) -> "Role":
        return replace(self, name=name, by_factory=True)

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "cuesheet_id": str(self.cuesheet_id),
            "name": self.name.to_str(),
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
            "cuesheet_id": self.cuesheet_id,
            "name": self.name.to_str(),
        }
