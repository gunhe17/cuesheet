from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from cuesheet.api.core.entity import Entity
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.task.instruction import Instruction
from cuesheet.api.domain.task.note import Note
from cuesheet.api.domain.task.done_at import DoneAt


@dataclass(frozen=True, kw_only=True)
class Task(Entity):
    cuesheet_id: UUID
    cue_id: UUID
    role_id: UUID
    instruction: Instruction
    note: Note | None = None
    done_at: DoneAt | None = None
    done_by_participant_id: UUID | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        cuesheet_id: UUID,
        cue_id: UUID,
        role_id: UUID,
        instruction: Instruction,
        note: Note | None = None,
    ) -> "Task":
        task = cls(
            cuesheet_id=cuesheet_id,
            cue_id=cue_id,
            role_id=role_id,
            instruction=instruction,
            note=note,
            by_factory=True,
        )
        return task

    # #
    # update

    def with_instruction(self, instruction: Instruction) -> "Task":
        return replace(self, instruction=instruction, by_factory=True)

    def with_note(self, note: Note | None) -> "Task":
        return replace(self, note=note, by_factory=True)

    # #
    # transition

    def check(self, *, at: DoneAt, participant_id: UUID) -> "Task":
        return replace(
            self,
            done_at=at,
            done_by_participant_id=participant_id,
            by_factory=True,
        )

    def uncheck(self) -> "Task":
        return replace(
            self,
            done_at=None,
            done_by_participant_id=None,
            by_factory=True,
        )

    # #
    # query

    def is_done(self) -> bool:
        return self.done_at is not None

    def to_dict(self):
        return {
            "id": str(self.id),
            "cuesheet_id": str(self.cuesheet_id),
            "cue_id": str(self.cue_id),
            "role_id": str(self.role_id),
            "instruction": self.instruction.to_str(),
            "note": (
                self.note.to_str() if self.note else None
            ),
            "done_at": (
                self.done_at.to_str() if self.done_at else None
            ),
            "done_by_participant_id": (
                str(self.done_by_participant_id) if self.done_by_participant_id else None
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
            "cuesheet_id": self.cuesheet_id,
            "cue_id": self.cue_id,
            "role_id": self.role_id,
            "instruction": self.instruction.to_str(),
            "note": (
                self.note.to_str() if self.note else None
            ),
            "done_at": (
                self.done_at.to_datetime() if self.done_at else None
            ),
            "done_by_participant_id": self.done_by_participant_id,
        }
