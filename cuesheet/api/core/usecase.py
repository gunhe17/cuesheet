from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel


# #
# input

class In(BaseModel):

    @classmethod
    def from_event(cls, payload: dict) -> Self:
        return cls(**{
            name: payload[name] for name in cls.model_fields
        })


# #
# output

@dataclass(frozen=True, kw_only=True)
class Out:
    data: dict | list
    event: list | None
    
    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "event": self.event,
        }
