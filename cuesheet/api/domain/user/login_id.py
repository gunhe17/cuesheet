from __future__ import annotations

import re
from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class LoginId(ValueObject):
    _value: str

    # hint
    _pattern: str = r"^[a-z0-9][a-z0-9._-]*$"
    _min_length: int = 3
    _max_length: int = 32

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "LoginId":
        # type
        if not isinstance(value, str):
            raise InvalidError("LoginId")

        # normalize
        normalized = value.strip().lower()

        # length
        if not (cls._min_length <= len(normalized) <= cls._max_length):
            raise InvalidFormatError("LoginId")

        # format
        if not re.match(cls._pattern, normalized):
            raise InvalidFormatError("LoginId")

        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
