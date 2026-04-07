"""Tracing helpers for local adapter metadata and redaction."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+"),
    re.compile(r"ghp_[A-Za-z0-9]+"),
)


def normalize_path(text: str) -> str:
    normalized = text.replace(str(REPO_ROOT), "<repo>")
    return normalized


def redact_text(text: str, *, max_length: int = 400) -> str:
    redacted = normalize_path(text)
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted[:max_length]
