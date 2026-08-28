from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class FailedCount(ValueObject):
    _value: int

    # #
    # factory

    @classmethod
    def from_int(cls, value) -> "FailedCount":
        # type
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidError("FailedCount")

        # value
        if value < 0:
            raise InvalidFormatError("FailedCount")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_int(self) -> int:
        return self._value

    def increment(self) -> "FailedCount":
        return FailedCount.from_int(self._value + 1)
