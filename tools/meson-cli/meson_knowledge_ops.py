"""CLI-only knowledge access helpers for expert-system Obsidian vaults."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_REGISTRY_PATH = REPO_ROOT / "harness" / "config" / "knowledge_registry.json"
DEFAULT_OBSIDIAN_CLI_BIN = "obsidian"


class KnowledgeError(RuntimeError):
    """Raised when knowledge access cannot satisfy the CLI-only policy."""


def load_knowledge_registry() -> dict[str, Any]:
    return json.loads(KNOWLEDGE_REGISTRY_PATH.read_text(encoding="utf-8"))


def resolve_agent_config(agent_name: str) -> dict[str, Any]:
    registry = load_knowledge_registry()
    agent = registry.get("agents", {}).get(agent_name)
    if agent is None:
        raise KnowledgeError(f"unknown knowledge agent: {agent_name}")
    if not agent.get("enabled", False):
        raise KnowledgeError(f"knowledge agent is not enabled: {agent_name}")
    return agent


def obsidian_cli_bin() -> str:
    return os.environ.get("OBSIDIAN_CLI_BIN", DEFAULT_OBSIDIAN_CLI_BIN)


def binary_available(binary: str) -> bool:
    if "/" in binary:
        return Path(binary).exists()
    return shutil.which(binary) is not None


def shell_join(command: list[str]) -> str:
    return shlex.join(command)


def obsidian_cli_prefix() -> list[str]:
    raw = os.environ.get("OBSIDIAN_CLI_PREFIX", "").strip()
    if not raw:
        return []
    return shlex.split(raw)


def run_capture(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def obsidian_command(subcommand: str, params: list[str], *, vault_name: str = "") -> list[str]:
    command = [*obsidian_cli_prefix(), obsidian_cli_bin()]
    if vault_name:
        command.append(f"vault={vault_name}")
    command.append(subcommand)
    command.extend(params)
    return command


def summarize_command_error(command: list[str], stdout: str, stderr: str) -> str:
    detail = stderr or stdout or "no diagnostic output"
    if "unable to find Obsidian" in detail:
        detail = (
            f"{detail} If this command is running inside a sandbox, configure "
            "OBSIDIAN_CLI_PREFIX to a host bridge command or point OBSIDIAN_CLI_BIN "
            "at a host-visible wrapper."
        )
    return f"{shell_join(command)} failed: {detail}"


def probe_app_reachable(agent_name: str) -> tuple[bool, str, str]:
    config = resolve_agent_config(agent_name)
    command = obsidian_command("help", [], vault_name=config["vault_name"])
    code, stdout, stderr = run_capture(command)
    if code == 0:
        return True, shell_join(command), ""
    return False, shell_join(command), summarize_command_error(command, stdout, stderr)


def ensure_gate_open(agent_name: str) -> None:
    cli_bin = obsidian_cli_bin()
    if not binary_available(cli_bin):
        raise KnowledgeError(f"required Obsidian CLI is unavailable: {cli_bin}")
    ok, _command, detail = probe_app_reachable(agent_name)
    if not ok:
        raise KnowledgeError(detail)


def run_obsidian_command(agent_name: str, subcommand: str, params: list[str]) -> tuple[list[str], str]:
    config = resolve_agent_config(agent_name)
    ensure_gate_open(agent_name)
    command = obsidian_command(subcommand, params, vault_name=config["vault_name"])
    code, stdout, stderr = run_capture(command)
    if code != 0:
        raise KnowledgeError(summarize_command_error(command, stdout, stderr))
    return command, stdout


def normalize_note_path(note_path: str) -> str:
    normalized = note_path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def ensure_allowed_path(note_path: str, allowed_roots: list[str]) -> str:
    normalized = normalize_note_path(note_path)
    for root in allowed_roots:
        if normalized == root.rstrip("/") or normalized.startswith(root):
            return normalized
    raise KnowledgeError(
        f"note path is outside allowed roots: {normalized}; allowed={allowed_roots}"
    )


def parse_json_output(output: str) -> Any:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def extract_matches(payload: Any) -> list[str]:
    if isinstance(payload, list):
        matches: list[str] = []
        for item in payload:
            if isinstance(item, str):
                matches.append(item)
            elif isinstance(item, dict):
                for key in ("path", "file", "name"):
                    value = item.get(key)
                    if isinstance(value, str):
                        matches.append(value)
                        break
        return matches
    if isinstance(payload, dict):
        for key in ("matches", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return extract_matches(value)
    return []


def build_status(agent_name: str) -> dict[str, Any]:
    config = resolve_agent_config(agent_name)
    cli_bin = obsidian_cli_bin()
    prefix = obsidian_cli_prefix()
    cli_ok = binary_available(cli_bin)
    payload: dict[str, Any] = {
        "status": "ok",
        "agent": agent_name,
        "vault_name": config["vault_name"],
        "allowed_note_roots": config["allowed_note_roots"],
        "repo_reference_roots": config.get("repo_reference_roots", []),
        "authority_mode": config.get("authority_mode", "repo_first"),
        "access_mode": "cli_only",
        "obsidian_cli_bin": cli_bin,
        "obsidian_cli_prefix": prefix,
        "obsidian_cli_available": cli_ok,
        "app_reachable": False,
    }
    if not cli_ok:
        payload["status"] = "blocked"
        payload["error"] = f"required Obsidian CLI is unavailable: {cli_bin}"
        return payload

    reachable, command, detail = probe_app_reachable(agent_name)
    payload["app_reachable"] = reachable
    payload["probe_command"] = command
    if not reachable:
        payload["status"] = "blocked"
        payload["error"] = detail
    return payload


def search_notes(agent_name: str, query: str, limit: int) -> tuple[list[str], dict[str, Any]]:
    if not query.strip():
        raise KnowledgeError("search query must not be empty")
    config = resolve_agent_config(agent_name)
    matches: list[str] = []
    commands: list[str] = []
    for root in config["allowed_note_roots"]:
        command, stdout = run_obsidian_command(
            agent_name,
            "search",
            [
                f"query={query}",
                f"path={root.rstrip('/')}",
                f"limit={limit}",
                "format=json",
            ],
        )
        commands.append(shell_join(command))
        parsed = parse_json_output(stdout)
        raw_matches = extract_matches(parsed)
        if not raw_matches:
            raw_matches = [line for line in stdout.splitlines() if line.strip()]
        for item in raw_matches:
            normalized = normalize_note_path(item)
            if normalized.startswith(root):
                matches.append(normalized)
    deduped = sorted(dict.fromkeys(matches))
    payload = {
        "status": "ok",
        "agent": agent_name,
        "vault_name": config["vault_name"],
        "source_mode": "obsidian_cli",
        "query": query,
        "limit": limit,
        "search_roots": config["allowed_note_roots"],
        "matches": deduped,
        "match_count": len(deduped),
        "commands": commands,
    }
    return deduped, payload


def read_note(agent_name: str, note_path: str) -> tuple[str, dict[str, Any]]:
    config = resolve_agent_config(agent_name)
    normalized = ensure_allowed_path(note_path, config["allowed_note_roots"])
    command, stdout = run_obsidian_command(
        agent_name,
        "read",
        [f"path={normalized}"],
    )
    payload = {
        "status": "ok",
        "agent": agent_name,
        "vault_name": config["vault_name"],
        "source_mode": "obsidian_cli",
        "note_path": normalized,
        "allowed_note_roots": config["allowed_note_roots"],
        "content": stdout,
        "command": shell_join(command),
    }
    return stdout, payload
