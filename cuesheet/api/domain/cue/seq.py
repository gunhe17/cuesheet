from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Seq(ValueObject):
    _value: int

    # #
    # factory

    @classmethod
    def from_int(cls, value) -> "Seq":
        # type
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidError("Seq")

        # value
        if value < 0:
            raise InvalidFormatError("Seq")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_int(self) -> int:
        return self._value
