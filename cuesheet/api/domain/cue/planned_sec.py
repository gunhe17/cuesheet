from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class PlannedSec(ValueObject):
    _value: int

    # hint
    _max_value: int = 86400

    # #
    # factory

    @classmethod
    def from_int(cls, value) -> "PlannedSec":
        # type
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidError("PlannedSec")

        # value
        if not (0 < value <= cls._max_value):
            raise InvalidFormatError("PlannedSec")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_int(self) -> int:
        return self._value
