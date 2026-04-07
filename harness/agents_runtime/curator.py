"""PM-embedded curator helpers."""

from __future__ import annotations

from typing import Any


def build_knowledge_patch_proposal(
    task_id: str,
    evidence_refs: list[str],
    target_paths: list[str],
    affected_clauses: list[str],
    rationale: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "kind": "knowledge_patch_proposal",
        "evidence_refs": evidence_refs,
        "target_paths": target_paths,
        "affected_clauses": affected_clauses,
        "rationale": rationale,
        "approval_mode": "human_in_the_loop",
    }
