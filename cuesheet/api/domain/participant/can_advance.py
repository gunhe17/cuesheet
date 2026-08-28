from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class CanAdvance(ValueObject):
    _value: bool

    # #
    # factory

    @classmethod
    def from_bool(cls, value) -> "CanAdvance":
        # type
        if not isinstance(value, bool):
            raise InvalidError("CanAdvance")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_bool(self) -> bool:
        return self._value
