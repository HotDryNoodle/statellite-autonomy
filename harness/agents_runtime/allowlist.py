"""Repo-local tool allowlist and wrapper parameter filtering."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "harness" / "config" / "tool_allowlist.json"


@dataclass
class ToolInvocation:
    name: str
    params: dict[str, Any]


@dataclass
class ToolResult:
    tool_name: str
    command: list[str]
    return_code: int
    stdout_excerpt: str
    stderr_excerpt: str
    artifact_paths: list[str]


def load_tool_allowlist() -> dict[str, Any]:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def sanitize_tool_params(name: str, params: dict[str, Any]) -> dict[str, Any]:
    config = load_tool_allowlist()
    if name not in config["tools"]:
        raise ValueError(f"unknown tool: {name}")
    tool_config = config["tools"][name]
    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        if key not in tool_config["allowed_params"]:
            raise ValueError(f"disallowed param for {name}: {key}")
        sanitized[key] = value
    return sanitized


def build_tool_command(name: str, params: dict[str, Any]) -> tuple[list[str], list[str]]:
    config = load_tool_allowlist()["tools"][name]
    sanitized = sanitize_tool_params(name, params)
    command = list(config["command"])
    artifacts: list[str] = []
    for key, value in sanitized.items():
        if isinstance(value, bool):
            if value:
                command.append(f"--{key.replace('_', '-')}")
        elif isinstance(value, list):
            for item in value:
                command.extend([f"--{key.replace('_', '-')}", str(item)])
        else:
            command.extend([f"--{key.replace('_', '-')}", str(value)])
        if key in config.get("artifact_params", []):
            artifacts.append(str(value))
    return command, artifacts


def execute_tool(name: str, params: dict[str, Any]) -> ToolResult:
    command, artifacts = build_tool_command(name, params)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    return ToolResult(
        tool_name=name,
        command=command,
        return_code=completed.returncode,
        stdout_excerpt=stdout[:4000],
        stderr_excerpt=stderr[:4000],
        artifact_paths=artifacts,
    )
