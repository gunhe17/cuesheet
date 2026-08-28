from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class EventName(ValueObject):
    _value: str

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "EventName":
        # type
        if not isinstance(value, str):
            raise InvalidError("EventName")

        # format
        if not value.strip():
            raise InvalidFormatError("EventName")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
