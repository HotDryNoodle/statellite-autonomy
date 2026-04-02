#!/usr/bin/env bash
set -euo pipefail

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

PROJECT_PATH="$1"
SERVER_PATH="$2"
shift 2

exec uv run --project "${PROJECT_PATH}" "${SERVER_PATH}" "$@"
