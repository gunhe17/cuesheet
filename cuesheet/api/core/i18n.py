from __future__ import annotations

from enum import StrEnum


# #
# locale

class Locale(StrEnum):
    KO = "ko"
    EN = "en"


# #
# catalog

_CATALOG = {
    "invalid": {
        Locale.KO: "{target} 타입이 올바르지 않습니다",
        Locale.EN: "{target} has an invalid type",
    },
    "invalid_format": {
        Locale.KO: "{target} 형식이 올바르지 않습니다",
        Locale.EN: "{target} has an invalid format",
    },
    "not_found": {
        Locale.KO: "{target} 찾을 수 없습니다 (식별자: {identifier})",
        Locale.EN: "{target} not found (identifier: {identifier})",
    },
    "already_exists": {
        Locale.KO: "{target} 이미 존재합니다 (식별자: {identifier})",
        Locale.EN: "{target} already exists (identifier: {identifier})",
    },
    "invalid_credential": {
        Locale.KO: "아이디 또는 PIN이 올바르지 않습니다",
        Locale.EN: "Invalid login id or PIN",
    },
    "unauthorized": {
        Locale.KO: "인증이 필요합니다",
        Locale.EN: "Authentication required",
    },
    "forbidden": {
        Locale.KO: "{target}에 대한 권한이 없습니다",
        Locale.EN: "No permission for {target}",
    },
    "too_many_attempts": {
        Locale.KO: "로그인 시도가 너무 많습니다 (재시도: {seconds}초 후)",
        Locale.EN: "Too many login attempts (retry after: {seconds}s)",
    },
    "unique_violation": {
        Locale.KO: "이미 존재합니다",
        Locale.EN: "Already exists",
    },
    "database_error": {
        Locale.KO: "DB 실패 (작업: {operation}, 원인: {reason})",
        Locale.EN: "DB failed (operation: {operation}, reason: {reason})",
    },
    "hash_verify_failed": {
        Locale.KO: "hash verify 실패 (원인: {reason})",
        Locale.EN: "hash verify failed (reason: {reason})",
    },
    "hash_unsupported": {
        Locale.KO: "hash {operation} 미지원",
        Locale.EN: "hash {operation} not supported",
    },
}


# #
# render

DEFAULT = Locale.KO

def render(*, key: str, params: dict, locale: Locale) -> str:
    templates = _CATALOG[key]
    template = templates.get(locale) or templates[DEFAULT]
    return template.format(**params)
