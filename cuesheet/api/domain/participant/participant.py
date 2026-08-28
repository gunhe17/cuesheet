from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.participant.can_advance import CanAdvance
from cuesheet.api.domain.participant.role_ids import RoleIds


@dataclass(frozen=True, kw_only=True)
class Participant(Entity):
    cuesheet_id: UUID
    user_id: UUID
    can_advance: CanAdvance
    role_ids: RoleIds

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        cuesheet_id: UUID,
        user_id: UUID,
        can_advance: CanAdvance,
        role_ids: RoleIds,
    ) -> "Participant":
        participant = cls(
            cuesheet_id=cuesheet_id,
            user_id=user_id,
            can_advance=can_advance,
            role_ids=role_ids,
            by_factory=True,
        )
        return participant

    # #
    # update

    def with_can_advance(self, can_advance: CanAdvance) -> "Participant":
        return replace(self, can_advance=can_advance, by_factory=True)

    def with_role_ids(self, role_ids: RoleIds) -> "Participant":
        return replace(self, role_ids=role_ids, by_factory=True)

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "cuesheet_id": str(self.cuesheet_id),
            "user_id": str(self.user_id),
            "can_advance": self.can_advance.to_bool(),
            "role_ids": self.role_ids.to_json(),
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
            "user_id": self.user_id,
            "can_advance": self.can_advance.to_bool(),
            "role_ids": self.role_ids.to_json(),
        }
