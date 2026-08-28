from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cuesheet.api.core.event import Event
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.task.task import Task


class TaskEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class TaskEvent(Event):
    _kind: TaskEventKind
    task: Task

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, task: Task) -> tuple["TaskEvent", Task]:
        return cls(_kind=TaskEventKind.CREATED, task=task), task

    @classmethod
    @typecheck
    def updated(cls, *, task: Task) -> tuple["TaskEvent", Task]:
        return cls(_kind=TaskEventKind.UPDATED, task=task), task

    @classmethod
    @typecheck
    def deleted(cls, *, task: Task) -> tuple["TaskEvent", Task]:
        return cls(_kind=TaskEventKind.DELETED, task=task), task

    @classmethod
    @typecheck
    def read(cls, *, task: Task) -> tuple["TaskEvent", Task]:
        return cls(_kind=TaskEventKind.READ, task=task), task

    @classmethod
    @typecheck
    def read_many(cls, *, tasks: list) -> list[tuple["TaskEvent", Task]]:
        return [
            (cls(_kind=TaskEventKind.READ, task=task), task)
            for task in tasks
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "task"

    def act_entity_id(self) -> UUID:
        return self.task.id

    def payload(self) -> dict:
        return {"instruction": self.task.instruction.to_str()}
