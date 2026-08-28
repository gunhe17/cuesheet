from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cue.seq import Seq
from cuesheet.api.domain.cue.cue_title import CueTitle
from cuesheet.api.domain.cue.planned_sec import PlannedSec
from cuesheet.api.domain.cue.color import Color


@dataclass(frozen=True, kw_only=True)
class Cue(Entity):
    cuesheet_id: UUID
    seq: Seq
    title: CueTitle
    planned_sec: PlannedSec
    color: Color

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        cuesheet_id: UUID,
        seq: Seq,
        title: CueTitle,
        planned_sec: PlannedSec,
        color: Color,
    ) -> "Cue":
        cue = cls(
            cuesheet_id=cuesheet_id,
            seq=seq,
            title=title,
            planned_sec=planned_sec,
            color=color,
            by_factory=True,
        )
        return cue

    # #
    # update

    def with_seq(self, seq: Seq) -> "Cue":
        return replace(self, seq=seq, by_factory=True)

    def with_title(self, title: CueTitle) -> "Cue":
        return replace(self, title=title, by_factory=True)

    def with_planned_sec(self, planned_sec: PlannedSec) -> "Cue":
        return replace(self, planned_sec=planned_sec, by_factory=True)

    def with_color(self, color: Color) -> "Cue":
        return replace(self, color=color, by_factory=True)

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "cuesheet_id": str(self.cuesheet_id),
            "seq": self.seq.to_int(),
            "title": self.title.to_str(),
            "planned_sec": self.planned_sec.to_int(),
            "color": self.color.to_str(),
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
            "seq": self.seq.to_int(),
            "title": self.title.to_str(),
            "planned_sec": self.planned_sec.to_int(),
            "color": self.color.to_str(),
        }
