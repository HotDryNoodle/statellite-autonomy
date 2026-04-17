#!/usr/bin/env python3
"""Repository-local quality gate for build, test, traceability, and evidence tags."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard_common import (
    ACTIVE_CONTEXT_SECTIONS,
    TASK_ARCHIVE_HEADER,
    TASK_BOARD_HEADER,
    WORKING_SECTIONS,
    load_governance_policy,
    load_task_compact_manifest,
    load_task_events,
    load_task_state,
    parse_bullet_sections,
    parse_task_archive,
    parse_task_board,
    requires_runtime_record,
    task_artifacts_dir,
    task_compact_manifest_path,
    task_events_path,
    task_state_path,
    task_status_for_phase,
)
from harness.agents_runtime.registry import load_expert_registry

TOOLCHAIN = REPO_ROOT / "tools" / "nav-toolchain-cli" / "toolchain_cli.py"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-cli" / "traceability_cli.py"
RENDER_DASHBOARD = REPO_ROOT / "scripts" / "render_project_dashboard.py"
BASELINE_STATUS = {
    "contract_count": 15,
    "verify_count": 12,
    "contracts_with_code": 8,
    "contracts_with_tests": 6,
    "verifies_with_tests": 8,
}
WORKING_PATH = REPO_ROOT / "docs" / "memory" / "working" / "current_focus.md"
TASK_BOARD_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "task_board.md"
ACTIVE_CONTEXT_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "active_context.md"
PROJECT_STATUS_PATH = REPO_ROOT / "docs" / "_generated" / "project_status.json"
TASK_ARCHIVE_PATH = REPO_ROOT / "docs" / "traceability" / "task_archive.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PM_SKILL_PATH = REPO_ROOT / "skills" / "project-manager" / "SKILL.md"
PM_LOAD_ROUTING_PATH = REPO_ROOT / "skills" / "project-manager" / "references" / "load-routing.md"
PM_SOP_PATH = REPO_ROOT / "skills" / "project-manager" / "references" / "control-plane-sop.md"
AGENT_COLLAB_PATH = REPO_ROOT / "docs" / "governance" / "agent-collaboration.md"
HARNESS_SPLIT_PATH = REPO_ROOT / "docs" / "governance" / "harness_product_split.md"
TRACEABILITY_README_PATH = REPO_ROOT / "docs" / "traceability" / "README.md"
BLUEPRINT_ROOT = REPO_ROOT / "docs" / "architecture" / "blueprints"
SYSTEM_BLUEPRINT_DIR = BLUEPRINT_ROOT / "system"
DECISION_BLUEPRINT_DIR = BLUEPRINT_ROOT / "decisions"
PROMPT_DOC_LIMITS = {
    AGENTS_PATH: 100,
    PM_SKILL_PATH: 100,
    AGENT_COLLAB_PATH: 100,
    HARNESS_SPLIT_PATH: 100,
    TRACEABILITY_README_PATH: 100,
}
SOP_COMMAND_SNIPPETS = (
    "pm-workflow --task-id",
    "dispatch-expert --task-id",
    "close-task --task-id",
    "archive-task --task-id",
    "sync-governance --task-id",
)

# Tracked text-like paths checked for POSIX final newline (EditorConfig insert_final_newline).
_FINAL_NEWLINE_SUFFIXES = frozenset(
    {
        ".md",
        ".cpp",
        ".c",
        ".cc",
        ".cxx",
        ".h",
        ".hpp",
        ".py",
        ".sh",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".ini",
        ".in",
        ".cmake",
        ".plantuml",
        ".puml",
    }
)
_FINAL_NEWLINE_NAMES = frozenset({"meson.build", "CMakeLists.txt", "Dockerfile"})
BLUEPRINT_STATUSES = frozenset({"active", "superseded", "obsolete"})


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def run_command(args: list[str]) -> tuple[bool, str, str]:
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0, completed.stdout.strip(), completed.stderr.strip()


def format_command_output(stdout: str, stderr: str) -> str:
    return "\n".join(part for part in (stdout, stderr) if part).strip()


def contract_evidence_sources() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("product/src/**/*.h"))


def test_sources() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("product/tests/**/*.cpp"))


def extract_contract_ids(text: str) -> list[str]:
    return re.findall(r"@contract\{([^}]+)\}", text)


def extract_tagged_tests(text: str) -> list[tuple[str, bool, bool]]:
    pattern = re.compile(
        r"(?P<comment>(?:\s*/\*\*.*?\*/\s*)?)TEST(?:_F|_P)?\s*\(\s*([^,]+)\s*,\s*([^)]+)\)",
        re.DOTALL,
    )
    tagged: list[tuple[str, bool, bool]] = []
    for match in pattern.finditer(text):
        comment = match.group("comment") or ""
        test_name = f"{match.group(2).strip()}.{match.group(3).strip()}"
        tagged.append(
            (
                test_name,
                "@verify{" in comment,
                "@covers{" in comment,
            )
        )
    return tagged


def check_final_newline() -> CheckResult:
    """Require non-empty tracked text files to end with a newline (EditorConfig)."""
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return CheckResult(
            "final_newline",
            False,
            completed.stderr.strip() or "git ls-files failed",
        )
    bad: list[str] = []
    for line in completed.stdout.splitlines():
        path = REPO_ROOT / line
        if not path.is_file():
            continue
        suf = path.suffix.lower()
        if suf not in _FINAL_NEWLINE_SUFFIXES and path.name not in _FINAL_NEWLINE_NAMES:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            return CheckResult("final_newline", False, f"read {line}: {exc}")
        if not data:
            continue
        if not data.endswith(b"\n"):
            bad.append(line)
    if bad:
        preview = bad[:20]
        extra = f" (+{len(bad) - len(preview)} more)" if len(bad) > len(preview) else ""
        return CheckResult(
            "final_newline",
            False,
            "missing final newline: " + ", ".join(preview) + extra,
        )
    return CheckResult("final_newline", True, "tracked text files end with newline")


def check_contract_tags() -> CheckResult:
    missing_files: list[str] = []
    total_tags = 0
    for path in contract_evidence_sources():
        text = path.read_text(encoding="utf-8")
        tags = extract_contract_ids(text)
        total_tags += len(tags)
        if not tags:
            missing_files.append(str(path.relative_to(REPO_ROOT)))
    if missing_files:
        return CheckResult(
            "contract_tags",
            False,
            "missing @contract tags in: " + ", ".join(missing_files),
        )
    return CheckResult("contract_tags", True, f"found {total_tags} @contract tags")


def check_test_tags() -> CheckResult:
    failures: list[str] = []
    test_count = 0
    for path in test_sources():
        text = path.read_text(encoding="utf-8")
        for test_name, has_verify, has_covers in extract_tagged_tests(text):
            test_count += 1
            if not has_verify or not has_covers:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}::{test_name} "
                    f"(verify={has_verify}, covers={has_covers})"
                )
    if failures:
        return CheckResult(
            "test_tags",
            False,
            "missing @verify/@covers on: " + ", ".join(failures),
        )
    return CheckResult("test_tags", True, f"validated {test_count} tagged tests")


def check_traceability_baseline() -> CheckResult:
    ok, stdout, stderr = run_command([sys.executable, str(TRACEABILITY), "status"])
    output = format_command_output(stdout, stderr)
    if not ok:
        return CheckResult("traceability_status", False, output or "status command failed")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return CheckResult("traceability_status", False, f"invalid JSON: {exc}")

    regressions: list[str] = []
    for key, expected in BASELINE_STATUS.items():
        actual = payload.get(key)
        if not isinstance(actual, int):
            regressions.append(f"{key}=missing")
        elif actual < expected:
            regressions.append(f"{key}={actual} < {expected}")
    if regressions:
        return CheckResult(
            "traceability_status",
            False,
            "baseline regression: " + ", ".join(regressions),
        )
    return CheckResult("traceability_status", True, json.dumps(payload, ensure_ascii=False))


def check_compliance_status() -> CheckResult:
    ok, stdout, stderr = run_command([sys.executable, str(TRACEABILITY), "compliance", "--refresh"])
    output = format_command_output(stdout, stderr)
    if not ok:
        return CheckResult("compliance_status", False, output or "compliance command failed")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return CheckResult("compliance_status", False, f"invalid JSON: {exc}")
    if not payload.get("ok", False):
        return CheckResult("compliance_status", False, json.dumps(payload, ensure_ascii=False))
    return CheckResult("compliance_status", True, json.dumps(payload, ensure_ascii=False))


def check_agent_eval_datasets() -> CheckResult:
    missing = load_expert_registry(repo_root=REPO_ROOT).missing_eval_datasets(repo_root=REPO_ROOT)
    if missing:
        return CheckResult(
            "agent_eval_datasets",
            False,
            "missing eval datasets: " + ", ".join(missing),
        )
    return CheckResult("agent_eval_datasets", True, "declared agent eval_dataset paths exist")


def parse_simple_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"{path.relative_to(REPO_ROOT)} missing YAML frontmatter")
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise ValueError(f"{path.relative_to(REPO_ROOT)} missing closing frontmatter delimiter")

    payload: dict[str, object] = {}
    current_list: str | None = None
    for raw in lines[1:end_index]:
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current_list is None:
                raise ValueError(f"{path.relative_to(REPO_ROOT)} has list item without key")
            payload.setdefault(current_list, [])
            assert isinstance(payload[current_list], list)
            payload[current_list].append(stripped[2:].strip().strip("'\""))
            continue
        if ":" not in line:
            raise ValueError(f"{path.relative_to(REPO_ROOT)} has invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not value:
            payload[key] = []
            current_list = key
            continue
        payload[key] = value.strip("'\"")
        current_list = None
    return payload


def paired_blueprint_md(path: Path) -> Path:
    if path.suffix == ".md":
        return path
    return path.with_suffix(".md")


def resolve_blueprint_status(path: Path) -> str:
    md_path = paired_blueprint_md(path)
    payload = parse_simple_frontmatter(md_path)
    status = str(payload.get("status", "") or "")
    if status not in BLUEPRINT_STATUSES:
        raise ValueError(f"{md_path.relative_to(REPO_ROOT)} has invalid status `{status}`")
    return status


def check_architecture_blueprints() -> CheckResult:
    failures: list[str] = []
    if not BLUEPRINT_ROOT.exists():
        failures.append(f"missing {BLUEPRINT_ROOT.relative_to(REPO_ROOT)}")
    for required in (SYSTEM_BLUEPRINT_DIR, DECISION_BLUEPRINT_DIR):
        if not required.exists():
            failures.append(f"missing {required.relative_to(REPO_ROOT)}")

    for directory, expected_type in (
        (SYSTEM_BLUEPRINT_DIR, "system"),
        (DECISION_BLUEPRINT_DIR, "decision"),
    ):
        if not directory.exists():
            continue
        for md_path in sorted(directory.glob("*.md")):
            puml_path = md_path.with_suffix(".puml")
            if not puml_path.exists():
                failures.append(f"{md_path.relative_to(REPO_ROOT)} missing paired {puml_path.name}")
                continue
            try:
                metadata = parse_simple_frontmatter(md_path)
            except ValueError as exc:
                failures.append(str(exc))
                continue
            blueprint_type = str(metadata.get("blueprint_type", "") or "")
            status = str(metadata.get("status", "") or "")
            if blueprint_type != expected_type:
                failures.append(
                    f"{md_path.relative_to(REPO_ROOT)} blueprint_type={blueprint_type or 'missing'} != {expected_type}"
                )
            if status not in BLUEPRINT_STATUSES:
                failures.append(f"{md_path.relative_to(REPO_ROOT)} has invalid status `{status or 'missing'}`")
            effective_specs = metadata.get("effective_specs", [])
            if not isinstance(effective_specs, list) or not effective_specs:
                failures.append(f"{md_path.relative_to(REPO_ROOT)} missing effective_specs list")
            replaced_by = str(metadata.get("replaced_by", "") or "")
            if expected_type == "decision":
                if not str(metadata.get("created_from_task", "") or ""):
                    failures.append(f"{md_path.relative_to(REPO_ROOT)} missing created_from_task")
                if "valid_for_task" not in metadata:
                    failures.append(f"{md_path.relative_to(REPO_ROOT)} missing valid_for_task")
                if "superseded_reason" not in metadata:
                    failures.append(f"{md_path.relative_to(REPO_ROOT)} missing superseded_reason")
            if status != "active":
                if not replaced_by:
                    failures.append(f"{md_path.relative_to(REPO_ROOT)} missing replaced_by for inactive blueprint")
                elif not (REPO_ROOT / replaced_by).exists():
                    failures.append(f"{md_path.relative_to(REPO_ROOT)} replaced_by target missing: {replaced_by}")
    if failures:
        return CheckResult("architecture_blueprints", False, "; ".join(failures))
    return CheckResult("architecture_blueprints", True, "blueprint layout and lifecycle metadata are valid")


def check_architecture_freeze_artifacts() -> CheckResult:
    failures: list[str] = []
    task_roots = sorted((REPO_ROOT / "harness" / "runtime" / "tasks").glob("*/artifacts"))
    for artifacts_root in task_roots:
        for freeze_path in sorted(artifacts_root.glob("architecture_freeze*.json")):
            try:
                payload = json.loads(freeze_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{freeze_path.relative_to(REPO_ROOT)} invalid JSON: {exc}")
                continue
            refs = [str(ref) for ref in payload.get("blueprint_refs", [])]
            if not refs:
                failures.append(f"{freeze_path.relative_to(REPO_ROOT)} missing blueprint_refs")
                continue
            if not any(ref.endswith(".puml") for ref in refs):
                failures.append(f"{freeze_path.relative_to(REPO_ROOT)} missing .puml blueprint ref")
            for ref in refs:
                ref_path = REPO_ROOT / ref
                if not ref_path.exists():
                    failures.append(f"{freeze_path.relative_to(REPO_ROOT)} references missing blueprint {ref}")
                    continue
                try:
                    status = resolve_blueprint_status(ref_path)
                except ValueError as exc:
                    failures.append(str(exc))
                    continue
                if "docs/architecture/blueprints/decisions/" in ref and status != "active":
                    failures.append(
                        f"{freeze_path.relative_to(REPO_ROOT)} references inactive decision blueprint {ref}"
                    )
        for handoff_path in sorted(artifacts_root.glob("handoff*.json")):
            payload = json.loads(handoff_path.read_text(encoding="utf-8"))
            freeze_ref = str(payload.get("architecture_freeze_ref", "") or "")
            if freeze_ref and not (REPO_ROOT / freeze_ref).exists():
                failures.append(
                    f"{handoff_path.relative_to(REPO_ROOT)} references missing architecture freeze {freeze_ref}"
                )
    if failures:
        return CheckResult("architecture_freeze_artifacts", False, "; ".join(failures))
    return CheckResult("architecture_freeze_artifacts", True, "architecture freeze artifacts reference active repo-local blueprints")


def check_line_limit(path: Path, limit: int) -> CheckResult:
    if not path.exists():
        return CheckResult(path.name, False, f"missing file: {path.relative_to(REPO_ROOT)}")
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count > limit:
        return CheckResult(path.name, False, f"{path.relative_to(REPO_ROOT)} has {line_count} lines > {limit}")
    return CheckResult(path.name, True, f"{path.relative_to(REPO_ROOT)} has {line_count} lines")


def validate_bullet_sections(path: Path, allowed_sections: tuple[str, ...]) -> tuple[bool, str]:
    try:
        parse_bullet_sections(path, allowed_sections)
    except ValueError as exc:
        return False, str(exc)
    return True, "ok"


def strip_code_ticks(text: str) -> str:
    return text.replace("`", "").strip()


def extract_task_ids(items: list[str]) -> list[str]:
    task_ids: list[str] = []
    for item in items:
        match = re.search(r"`([^`]+)`", item)
        if match:
            task_ids.append(match.group(1))
    return task_ids


def check_working_memory() -> CheckResult:
    if not WORKING_PATH.exists():
        return CheckResult("working_memory_schema", False, f"missing {WORKING_PATH.relative_to(REPO_ROOT)}")
    ok, details = validate_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
    return CheckResult("working_memory_schema", ok, details)


def check_short_term_context() -> CheckResult:
    if not ACTIVE_CONTEXT_PATH.exists():
        return CheckResult("active_context_schema", False, f"missing {ACTIVE_CONTEXT_PATH.relative_to(REPO_ROOT)}")
    ok, details = validate_bullet_sections(ACTIVE_CONTEXT_PATH, ACTIVE_CONTEXT_SECTIONS)
    return CheckResult("active_context_schema", ok, details)


def check_task_board() -> CheckResult:
    if not TASK_BOARD_PATH.exists():
        return CheckResult("task_board_schema", False, f"missing {TASK_BOARD_PATH.relative_to(REPO_ROOT)}")
    try:
        rows = parse_task_board(TASK_BOARD_PATH)
    except ValueError as exc:
        return CheckResult("task_board_schema", False, str(exc))
    return CheckResult("task_board_schema", True, f"validated {len(rows)} task rows against {TASK_BOARD_HEADER}")


def check_task_archive() -> CheckResult:
    if not TASK_ARCHIVE_PATH.exists():
        return CheckResult("task_archive_schema", False, f"missing {TASK_ARCHIVE_PATH.relative_to(REPO_ROOT)}")
    try:
        rows = parse_task_archive(TASK_ARCHIVE_PATH)
    except ValueError as exc:
        return CheckResult("task_archive_schema", False, str(exc))
    return CheckResult("task_archive_schema", True, f"validated {len(rows)} task rows against {TASK_ARCHIVE_HEADER}")


def check_runtime_task_board_consistency() -> CheckResult:
    policy = load_governance_policy(REPO_ROOT)
    try:
        rows = parse_task_board(TASK_BOARD_PATH)
    except ValueError as exc:
        return CheckResult("runtime_task_board_consistency", False, str(exc))

    failures: list[str] = []
    for row in rows:
        task_id = strip_code_ticks(row["task_id"])
        if not requires_runtime_record(task_id, policy):
            continue
        state = load_task_state(REPO_ROOT, task_id)
        if state is None:
            failures.append(
                f"{task_id} missing {task_state_path(REPO_ROOT, task_id).relative_to(REPO_ROOT)}"
            )
            continue
        if not task_events_path(REPO_ROOT, task_id).exists():
            failures.append(
                f"{task_id} missing {task_events_path(REPO_ROOT, task_id).relative_to(REPO_ROOT)}"
            )
        expected_status = task_status_for_phase(str(state.get("phase", "")))
        if strip_code_ticks(row["owner_agent"]) != str(state.get("owner", "")):
            failures.append(
                f"{task_id} owner_agent={row['owner_agent']} != runtime owner={state.get('owner', '')}"
            )
        if row["status"] != expected_status:
            failures.append(
                f"{task_id} status={row['status']} != runtime-derived status={expected_status}"
            )
    if failures:
        return CheckResult(
            "runtime_task_board_consistency",
            False,
            "; ".join(failures),
        )
    return CheckResult("runtime_task_board_consistency", True, "task board rows match official runtime tasks")


def check_runtime_current_focus_consistency() -> CheckResult:
    try:
        working = parse_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
    except ValueError as exc:
        return CheckResult("runtime_current_focus_consistency", False, str(exc))

    active_items = [item for item in working["In Progress"] if item != "none"]
    if active_items and not extract_task_ids(active_items):
        return CheckResult(
            "runtime_current_focus_consistency",
            False,
            "current_focus.md active task entries must include a backticked task_id synchronized from harness",
        )
    policy = load_governance_policy(REPO_ROOT)
    task_ids = [task_id for task_id in extract_task_ids(active_items) if requires_runtime_record(task_id, policy)]
    if not task_ids:
        return CheckResult("runtime_current_focus_consistency", True, "no cutover task in current focus")
    if len(task_ids) != 1:
        return CheckResult(
            "runtime_current_focus_consistency",
            False,
            f"current_focus.md must point to exactly one official active task, found {task_ids}",
        )
    task_id = task_ids[0]
    state = load_task_state(REPO_ROOT, task_id)
    if state is None:
        return CheckResult(
            "runtime_current_focus_consistency",
            False,
            f"{task_id} missing {task_state_path(REPO_ROOT, task_id).relative_to(REPO_ROOT)}",
        )
    current_phase = strip_code_ticks(working["Current Phase"][0])
    next_agent = strip_code_ticks(working["Next Agent"][0])
    failures: list[str] = []
    if current_phase != str(state.get("phase", "")):
        failures.append(f"{task_id} current_focus phase={current_phase} != runtime phase={state.get('phase', '')}")
    if next_agent != str(state.get("owner", "")):
        failures.append(f"{task_id} next_agent={next_agent} != runtime owner={state.get('owner', '')}")
    if failures:
        return CheckResult("runtime_current_focus_consistency", False, "; ".join(failures))
    return CheckResult("runtime_current_focus_consistency", True, "current focus matches official runtime task")


def check_runtime_archive_consistency() -> CheckResult:
    policy = load_governance_policy(REPO_ROOT)
    retention = dict(policy.get("runtime_retention", {}))
    try:
        rows = parse_task_archive(TASK_ARCHIVE_PATH)
    except ValueError as exc:
        return CheckResult("runtime_archive_consistency", False, str(exc))

    failures: list[str] = []
    for row in rows:
        task_id = strip_code_ticks(row["task_id"])
        if not requires_runtime_record(task_id, policy):
            continue
        state = load_task_state(REPO_ROOT, task_id)
        if state is None:
            failures.append(
                f"{task_id} missing {task_state_path(REPO_ROOT, task_id).relative_to(REPO_ROOT)}"
            )
            continue
        events = load_task_events(REPO_ROOT, task_id)
        event_names = {str(event.get("event", "")) for event in events}
        if "close_task" not in event_names:
            failures.append(f"{task_id} missing close_task event")
        if "archive_task" not in event_names:
            failures.append(f"{task_id} missing archive_task event")
        retention_mode = str(state.get("retention_mode", "") or "")
        artifacts_dir = task_artifacts_dir(REPO_ROOT, task_id)
        tracked_artifacts = sorted(artifacts_dir.glob("*.json")) if artifacts_dir.exists() else []
        if retention_mode == "compacted":
            manifest = load_task_compact_manifest(REPO_ROOT, task_id)
            if manifest is None:
                failures.append(
                    f"{task_id} missing {task_compact_manifest_path(REPO_ROOT, task_id).relative_to(REPO_ROOT)}"
                )
            if "compact_runtime" not in event_names:
                failures.append(f"{task_id} missing compact_runtime event")
            if tracked_artifacts and bool(retention.get("drop_tracked_artifacts", True)):
                failures.append(f"{task_id} still retains tracked raw artifacts after compaction")
        if not bool(state.get("archived", False)):
            failures.append(f"{task_id} runtime state is not marked archived")
        runtime_status = str(state.get("acceptance_status", ""))
        if runtime_status and row["status"] != runtime_status:
            failures.append(f"{task_id} archive status={row['status']} != runtime acceptance_status={runtime_status}")
    if failures:
        return CheckResult("runtime_archive_consistency", False, "; ".join(failures))
    return CheckResult("runtime_archive_consistency", True, "archive rows have official runtime close/archive evidence")


def check_dashboard_status_schema() -> CheckResult:
    if not PROJECT_STATUS_PATH.exists():
        return CheckResult("project_status_schema", False, f"missing {PROJECT_STATUS_PATH.relative_to(REPO_ROOT)}")
    try:
        payload = json.loads(PROJECT_STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CheckResult("project_status_schema", False, f"invalid JSON: {exc}")

    required = {
        "generated_at",
        "current_phase",
        "in_progress",
        "current_blockers",
        "active_specs",
        "next_acceptance_target",
        "next_agent",
        "active_tasks",
        "blocked_tasks",
        "recent_activity",
        "recent_decisions",
        "accepted_limitations",
        "open_risks",
        "traceability_status",
        "compliance_status",
    }
    missing = sorted(required - payload.keys())
    if missing:
        return CheckResult("project_status_schema", False, f"missing keys: {', '.join(missing)}")
    if not isinstance(payload["current_phase"], str):
        return CheckResult("project_status_schema", False, "current_phase must be a string")
    for field in (
        "in_progress",
        "current_blockers",
        "active_specs",
        "next_acceptance_target",
        "next_agent",
        "active_tasks",
        "blocked_tasks",
        "recent_activity",
        "recent_decisions",
        "accepted_limitations",
        "open_risks",
    ):
        if not isinstance(payload[field], list):
            return CheckResult("project_status_schema", False, f"{field} must be a list")
    traceability = payload["traceability_status"]
    if not isinstance(traceability, dict):
        return CheckResult("project_status_schema", False, "traceability_status must be an object")
    for field in BASELINE_STATUS:
        if not isinstance(traceability.get(field), int):
            return CheckResult("project_status_schema", False, f"traceability_status.{field} must be an int")
    compliance = payload["compliance_status"]
    if not isinstance(compliance, dict):
        return CheckResult("project_status_schema", False, "compliance_status must be an object")
    for field in ("ok", "policy_count", "failures"):
        if field not in compliance:
            return CheckResult("project_status_schema", False, f"compliance_status missing {field}")
    return CheckResult("project_status_schema", True, "required dashboard status keys present")


def check_generated_files_not_tracked() -> CheckResult:
    ok, stdout, stderr = run_command(["git", "ls-files", "docs/_generated"])
    if not ok:
        return CheckResult(
            "generated_files_untracked",
            False,
            format_command_output(stdout, stderr) or "git ls-files docs/_generated failed",
        )
    tracked = [line for line in stdout.splitlines() if line.strip()]
    if tracked:
        return CheckResult(
            "generated_files_untracked",
            False,
            "tracked generated files found: " + ", ".join(tracked),
        )
    return CheckResult("generated_files_untracked", True, "no tracked files under docs/_generated")


def check_prompt_doc_limits() -> CheckResult:
    failures: list[str] = []
    for path, limit in PROMPT_DOC_LIMITS.items():
        try:
            display = str(path.relative_to(REPO_ROOT))
        except ValueError:
            display = str(path)
        if not path.exists():
            failures.append(f"missing {display}")
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > limit:
            failures.append(f"{display} has {line_count} lines > {limit}")
    if failures:
        return CheckResult("prompt_doc_limits", False, "; ".join(failures))
    return CheckResult("prompt_doc_limits", True, "main-path prompt docs stay within line limits")


def check_project_manager_references() -> CheckResult:
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in (PM_LOAD_ROUTING_PATH, PM_SOP_PATH)
        if not path.exists()
    ]
    if missing:
        return CheckResult("pm_references", False, "missing references: " + ", ".join(missing))
    skill_text = PM_SKILL_PATH.read_text(encoding="utf-8")
    failures: list[str] = []
    for path in (PM_LOAD_ROUTING_PATH, PM_SOP_PATH):
        rel = str(path.relative_to(REPO_ROOT))
        if rel not in skill_text:
            failures.append(f"{rel} not referenced from skills/project-manager/SKILL.md")
    if failures:
        return CheckResult("pm_references", False, "; ".join(failures))
    return CheckResult("pm_references", True, "project-manager references exist and are linked from the skill")


def check_prompt_doc_routing() -> CheckResult:
    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    pm_skill_text = PM_SKILL_PATH.read_text(encoding="utf-8")
    failures: list[str] = []

    for required in (
        "Load only when needed:",
        "docs/traceability/decision_log.md",
        "docs/traceability/agent_activity_log.md",
        "Detailed PM command templates live in `skills/project-manager/references/control-plane-sop.md`.",
    ):
        if required not in agents_text:
            failures.append(f"AGENTS.md missing `{required}`")

    read_first_section = agents_text.split("## Workflow", 1)[0]
    if "docs/traceability/decision_log.md" in read_first_section and "Load only when needed:" not in read_first_section:
        failures.append("AGENTS.md places decision_log in the eager read chain")
    if "docs/traceability/agent_activity_log.md" in read_first_section and "Load only when needed:" not in read_first_section:
        failures.append("AGENTS.md places agent_activity_log in the eager read chain")

    for snippet in SOP_COMMAND_SNIPPETS:
        if snippet in agents_text:
            failures.append(f"AGENTS.md should not include detailed SOP snippet `{snippet}`")
        if snippet in pm_skill_text:
            failures.append(f"skills/project-manager/SKILL.md should not include detailed SOP snippet `{snippet}`")

    if "docs/governance/agent-collaboration.md" not in pm_skill_text:
        failures.append("skills/project-manager/SKILL.md must keep conditional loading guidance for agent-collaboration.md")
    if "docs/traceability/decision_log.md" not in pm_skill_text:
        failures.append("skills/project-manager/SKILL.md must keep conditional loading guidance for decision_log.md")

    if failures:
        return CheckResult("prompt_doc_routing", False, "; ".join(failures))
    return CheckResult("prompt_doc_routing", True, "prompt-doc routing follows progressive disclosure")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-json", action="store_true")
    parser.add_argument("--skip-build-test", action="store_true")
    parser.add_argument("--skip-project-dashboard", action="store_true")
    args = parser.parse_args()

    checks: list[CheckResult] = []

    commands: list[tuple[str, list[str]]] = []
    if not args.skip_build_test:
        commands.extend(
            (
                ("build", [sys.executable, str(TOOLCHAIN), "build"]),
                ("test", [sys.executable, str(TOOLCHAIN), "test", "--no-rebuild"]),
            )
        )
    commands.append(("traceability_generate", [sys.executable, str(TOOLCHAIN), "traceability", "--yes"]))
    commands.append(("harness_tests", [sys.executable, "-m", "unittest", "discover", "-s", "harness/tests", "-p", "test_*.py"]))
    commands.append(("cli_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-p", "test_*.py"]))
    commands.append(("scripts_tests", [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_*.py"]))
    if not args.skip_project_dashboard:
        commands.append(("project_dashboard", [sys.executable, str(RENDER_DASHBOARD)]))

    for name, command in commands:
        ok, stdout, stderr = run_command(command)
        output = format_command_output(stdout, stderr)
        checks.append(CheckResult(name, ok, output or "(no output)"))
        if not ok:
            payload = {"ok": False, "checks": [check.__dict__ for check in checks]}
            if args.report_json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"{name}: failed\n{output}".strip())
            return 1

    checks.append(check_traceability_baseline())
    checks.append(check_compliance_status())
    checks.append(check_agent_eval_datasets())
    checks.append(check_architecture_blueprints())
    checks.append(check_architecture_freeze_artifacts())
    checks.append(check_line_limit(WORKING_PATH, 50))
    checks.append(check_line_limit(TASK_BOARD_PATH, 120))
    checks.append(check_line_limit(ACTIVE_CONTEXT_PATH, 120))
    checks.append(check_prompt_doc_limits())
    checks.append(check_working_memory())
    checks.append(check_task_board())
    checks.append(check_task_archive())
    checks.append(check_short_term_context())
    checks.append(check_project_manager_references())
    checks.append(check_prompt_doc_routing())
    checks.append(check_runtime_task_board_consistency())
    checks.append(check_runtime_current_focus_consistency())
    checks.append(check_runtime_archive_consistency())
    if not args.skip_project_dashboard:
        checks.append(check_dashboard_status_schema())
    checks.append(check_generated_files_not_tracked())
    checks.append(check_contract_tags())
    checks.append(check_test_tags())
    checks.append(check_final_newline())

    ok = all(check.ok for check in checks)
    payload = {"ok": ok, "checks": [check.__dict__ for check in checks]}
    if args.report_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for check in checks:
            state = "PASS" if check.ok else "FAIL"
            print(f"[{state}] {check.name}: {check.details}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
