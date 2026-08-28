from __future__ import annotations

from dataclasses import dataclass

from cuesheet.api.core.value_object import ValueObject
from cuesheet.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Color(ValueObject):
    _value: str

    # hint
    # 원시 색값이 아니라 팔레트 키다 — 테마별 실제 색은 화면이 정한다
    _allowed_list: tuple[str, ...] = (
        "slate", "blue", "teal", "amber", "rose", "violet",
    )
    _default: str = "slate"

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Color":
        # type
        if not isinstance(value, str):
            raise InvalidError("Color")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("Color")

        return cls(_value=value, by_factory=True)

    @classmethod
    def default(cls) -> "Color":
        return cls(_value=cls._default, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
