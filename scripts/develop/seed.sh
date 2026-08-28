#!/usr/bin/env bash
set -euo pipefail

# 개발 DB에 시드 데이터를 넣는다. 여러 번 돌려도 된다 — 계정은 재사용, 큐시트는 매번 새로 생긴다
cd "$(dirname "$0")/../.."
exec python -m cuesheet.api.bin.seed "$@"
