from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cuesheet_title import CuesheetTitle
from cuesheet.api.domain.cuesheet.scheduled_at import ScheduledAt
from cuesheet.api.domain.cuesheet.invite_token import InviteToken
from cuesheet.api.domain.cuesheet.cue_started_at import CueStartedAt
from cuesheet.api.domain.cuesheet.ended_at import EndedAt


@dataclass(frozen=True, kw_only=True)
class Cuesheet(Entity):
    owner_user_id: UUID
    title: CuesheetTitle
    scheduled_at: ScheduledAt
    manager_token: InviteToken
    viewer_token: InviteToken
    current_cue_id: UUID | None = None
    prev_cue_id: UUID | None = None
    cue_started_at: CueStartedAt | None = None
    ended_at: EndedAt | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        owner_user_id: UUID,
        title: CuesheetTitle,
        scheduled_at: ScheduledAt,
        manager_token: InviteToken,
        viewer_token: InviteToken,
    ) -> "Cuesheet":
        cuesheet = cls(
            owner_user_id=owner_user_id,
            title=title,
            scheduled_at=scheduled_at,
            manager_token=manager_token,
            viewer_token=viewer_token,
            by_factory=True,
        )
        return cuesheet

    # #
    # update

    def with_title(self, title: CuesheetTitle) -> "Cuesheet":
        return replace(self, title=title, by_factory=True)

    def with_scheduled_at(self, scheduled_at: ScheduledAt) -> "Cuesheet":
        return replace(self, scheduled_at=scheduled_at, by_factory=True)

    # #
    # transition

    def start(self, *, cue_id: UUID, at: CueStartedAt) -> "Cuesheet":
        return replace(
            self,
            current_cue_id=cue_id,
            prev_cue_id=None,
            cue_started_at=at,
            by_factory=True,
        )

    def advance(self, *, next_cue_id: UUID, at: CueStartedAt) -> "Cuesheet":
        return replace(
            self,
            current_cue_id=next_cue_id,
            prev_cue_id=self.current_cue_id,
            cue_started_at=at,
            by_factory=True,
        )

    def rewind(self, *, at: CueStartedAt) -> "Cuesheet":
        # 1단계만 되돌린다
        return replace(
            self,
            current_cue_id=self.prev_cue_id,
            prev_cue_id=None,
            cue_started_at=at,
            by_factory=True,
        )

    def end(self, *, at: EndedAt) -> "Cuesheet":
        return replace(self, ended_at=at, by_factory=True)

    # #
    # query

    def state(self) -> str:
        if self.ended_at is not None:
            return "ended"
        if self.current_cue_id is not None:
            return "running"
        return "ready"

    def to_dict(self):
        # 초대 토큰은 싣지 않는다. cuesheet_create 응답에서만 raw 로 한 번 나간다
        return {
            "id": str(self.id),
            "owner_user_id": str(self.owner_user_id),
            "title": self.title.to_str(),
            "scheduled_at": self.scheduled_at.to_str(),
            "state": self.state(),
            "current_cue_id": (
                str(self.current_cue_id) if self.current_cue_id else None
            ),
            "prev_cue_id": (
                str(self.prev_cue_id) if self.prev_cue_id else None
            ),
            "cue_started_at": (
                self.cue_started_at.to_str() if self.cue_started_at else None
            ),
            "ended_at": (
                self.ended_at.to_str() if self.ended_at else None
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
            "owner_user_id": self.owner_user_id,
            "title": self.title.to_str(),
            "scheduled_at": self.scheduled_at.to_datetime(),
            "manager_token": self.manager_token.to_str(),
            "viewer_token": self.viewer_token.to_str(),
            "current_cue_id": self.current_cue_id,
            "prev_cue_id": self.prev_cue_id,
            "cue_started_at": (
                self.cue_started_at.to_datetime() if self.cue_started_at else None
            ),
            "ended_at": (
                self.ended_at.to_datetime() if self.ended_at else None
            ),
        }
