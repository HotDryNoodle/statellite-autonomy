"""Knowledge artifact helpers for CLI-only Obsidian access."""

from __future__ import annotations

import json
from typing import Any


def build_knowledge_context(
    task_id: str,
    agent_name: str,
    source_mode: str,
    query: str,
    refs: list[str],
    artifact_ref: str,
    excerpt_meta: list[str],
    *,
    note_path: str = "",
) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "artifact_version": "1.0",
        "task_id": task_id,
        "agent_name": agent_name,
        "source_mode": source_mode,
        "query": query,
        "refs": refs,
        "artifact_ref": artifact_ref,
        "excerpt_meta": excerpt_meta,
    }
    if note_path:
        payload["note_path"] = note_path
    return payload


def knowledge_context_from_tool_result(
    task_id: str,
    agent_name: str,
    tool_name: str,
    query: str,
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    raw_output = tool_result.get("stdout") or tool_result["stdout_excerpt"]
    raw_payload = json.loads(raw_output)
    source_mode = raw_payload.get("source_mode", "obsidian_cli")
    if tool_name == "knowledge_search":
        refs = list(raw_payload.get("matches", []))
        excerpt_meta = [f"match_count={raw_payload.get('match_count', len(refs))}"]
        artifact_ref = f"knowledge_context:{task_id}:{agent_name}:search"
        return build_knowledge_context(
            task_id,
            agent_name,
            source_mode,
            query,
            refs,
            artifact_ref,
            excerpt_meta,
        )
    if tool_name == "knowledge_read":
        note_path = raw_payload.get("note_path", "")
        content = raw_payload.get("content", "")
        refs = [note_path] if note_path else []
        excerpt_meta = [f"content_length={len(content)}"]
        artifact_ref = f"knowledge_context:{task_id}:{agent_name}:read"
        return build_knowledge_context(
            task_id,
            agent_name,
            source_mode,
            query,
            refs,
            artifact_ref,
            excerpt_meta,
            note_path=note_path,
        )
    raise ValueError(f"unsupported knowledge tool: {tool_name}")
