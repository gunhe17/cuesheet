from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class RoleIds(ValueObject):
    _value: tuple[str, ...]

    # #
    # factory

    @classmethod
    def from_json(cls, value) -> "RoleIds":
        # type
        if not isinstance(value, list):
            raise InvalidError("RoleIds")

        # format
        for item in value:
            if not isinstance(item, str):
                raise InvalidFormatError("RoleIds")
            try:
                UUID(item)
            except ValueError:
                raise InvalidFormatError("RoleIds")

        # normalize
        # list 는 unhashable 이라 frozen 불변성을 깨므로 tuple 로 보관한다
        return cls(_value=tuple(dict.fromkeys(value)), by_factory=True)

    # #
    # query

    def to_json(self) -> list:
        return list(self._value)

    def has(self, id: UUID) -> bool:
        return str(id) in self._value
