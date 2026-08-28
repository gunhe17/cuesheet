from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Pin(ValueObject):
    _value: str

    # hint
    _length: int = 4

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Pin":
        # type
        if not isinstance(value, str):
            raise InvalidError("Pin")

        # format
        if len(value) != cls._length or not value.isdecimal():
            raise InvalidFormatError("Pin")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
