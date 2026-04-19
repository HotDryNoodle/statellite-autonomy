#!/usr/bin/env python3
"""Stage repo assets into site/build/docs, render PlantUML, and build the MkDocs site.

Design principles:

- The site is a *derived* reading view. No canonical asset is moved; we only
  copy-and-transform into ``site/build/docs/``.
- PlantUML sources are pre-rendered to SVG so the resulting site has no runtime
  JS dependency. Rendering uses site/scripts/render_plantuml.py which supports a
  local ``plantuml`` binary or an HTTP plantuml-server.
- Contracts and blueprints are priority-1 content: every single ``*.md`` under
  those roots becomes an independent page; any referenced ``.puml`` is embedded
  inline in the same page as SVG.
- Governance records are not listed directly; the only surface is the Dashboard
  page, which is enriched with a "Recent Tasks" table (latest 3).
- Harness runtime exposes only a summary view derived from each
  ``task_state.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SITE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_DIR.parent

sys.path.insert(0, str(SITE_DIR / "scripts"))
from render_plantuml import render_plantuml  # noqa: E402

BUILD_DIR = SITE_DIR / "build"
STAGE_DOCS = BUILD_DIR / "docs"
MKDOCS_YML = SITE_DIR / "mkdocs.yml"

CONTRACTS_DIR = REPO_ROOT / "contracts"
BLUEPRINTS_DIR = REPO_ROOT / "architecture" / "blueprints"
DOCS_DIR = REPO_ROOT / "docs"
GUIDES_DIR = DOCS_DIR / "guides"
TOOLCHAIN_DIR = DOCS_DIR / "toolchain"
GENERATED_DIR = DOCS_DIR / "_generated"
TASKS_DIR = REPO_ROOT / "harness" / "runtime" / "tasks"
TASK_ARCHIVE = REPO_ROOT / "governance" / "records" / "task_archive.md"
TASK_BOARD = REPO_ROOT / "governance" / "records" / "short_term" / "task_board.md"
EVAL_DOMAINS_DIR = REPO_ROOT / "eval" / "domains"
REPO_README = REPO_ROOT / "README.md"

NAV_BEGIN = "# --- AUTO_NAV_BEGIN ---"
NAV_END = "# --- AUTO_NAV_END ---"

PUML_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+\.puml)\)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
SKIP_EXTS = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".puml")

# repo-relative posix path -> site-relative posix path (under build/docs/).
PATH_MAP: dict[str, str] = {}
# (repo_rel, site_rel) pairs of staged markdown files that may contain repo
# cross-references and need a post-pass rewrite.
STAGED_MD: list[tuple[str, str]] = []

# 站点侧栏与导航标题（面向仓库内开发者，中文优先）
CONTRACT_NAV_TITLE: dict[str, str] = {
    "README.md": "概述",
    "layer_boundary.contract.md": "分层边界",
    "mission_planning.contract.md": "任务规划",
    "navigation.contract.md": "导航",
    "ppp_family.contract.md": "PPP 族",
    "prediction.contract.md": "预测",
    "rdpod_family.contract.md": "RD-POD 族",
    "state_handoff_navigation_to_prediction.contract.md": "导航到预测交接",
    "time_system.contract.md": "时间系统",
}

BLUEPRINT_NAV_TITLE: dict[str, str] = {
    "asset-authority-boundary": "资产权威边界",
    "harness-product-boundary": "产品与 Harness 边界",
    "architecture-freeze-artifact-lifecycle": "架构冻结工件生命周期",
}

GUIDE_NAV_TITLE: dict[str, str] = {
    "agent-collaboration.md": "Agent 协作流程",
    "harness_product_split.md": "Harness / Product 拆分",
}

TOOLCHAIN_NAV_TITLE: dict[str, str] = {
    "benchmark_entrypoints.md": "基准入口",
    "build_entrypoints.md": "构建入口",
    "test_entrypoints.md": "测试入口",
    "traceability_entrypoints.md": "追溯入口",
}

EVAL_DOMAIN_NAV_TITLE: dict[str, str] = {
    "time": "时间评测域",
    "pppar": "PPPAR 评测域",
}

BLUEPRINT_STATUS_NAV_SUFFIX: dict[str, str] = {
    "superseded": "（已取代）",
    "obsolete": "（已废弃）",
}


@dataclass
class NavNode:
    title: str
    path: str | None = None
    children: list["NavNode"] = field(default_factory=list)
    overview_label: str = "概述"

    def to_yaml_lines(self, indent: int = 0) -> list[str]:
        pad = "  " * indent
        if self.path and not self.children:
            return [f"{pad}- {yaml_quote(self.title)}: {self.path}"]
        lines = [f"{pad}- {yaml_quote(self.title)}:"]
        if self.path:
            lines.append(
                f"{pad}  - {yaml_quote(self.overview_label)}: {self.path}"
            )
        for child in self.children:
            lines.extend(child.to_yaml_lines(indent + 1))
        return lines


def yaml_quote(text: str) -> str:
    """Return a scalar suitable for use as a YAML key in mkdocs nav."""
    if re.fullmatch(r"[A-Za-z0-9 _./()+\-]+", text) and ":" not in text:
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def log(msg: str) -> None:
    print(f"[build_site] {msg}", flush=True)


def read_first_heading(path: Path) -> str | None:
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        return None
    return None


def slug_title(fallback: str) -> str:
    stem = fallback.rsplit(".", 1)[0]
    stem = stem.replace(".contract", "").replace("_", " ").replace("-", " ")
    return stem.strip().title() or fallback


def strip_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    meta: dict[str, str] = {}
    for raw_line in raw.splitlines():
        if ":" in raw_line and not raw_line.lstrip().startswith("-"):
            key, _, value = raw_line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body


def transform_puml_links(md_text: str) -> str:
    """Replace links to sibling .puml files with an inline SVG embed plus raw source.

    The replacement is a single logical line so it does not break surrounding
    markdown list context.
    """

    def _repl(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        if target.startswith(("http://", "https://")):
            return match.group(0)
        svg_target = target[:-5] + ".svg"
        return (
            f"![{label}]({svg_target})"
            f' <small>[PlantUML 源码]({target})</small>'
        )

    return PUML_LINK_RE.sub(_repl, md_text)


def reset_stage() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    STAGE_DOCS.mkdir(parents=True, exist_ok=True)
    PATH_MAP.clear()
    STAGED_MD.clear()


def _site_rel(path: Path) -> str:
    return path.relative_to(STAGE_DOCS).as_posix()


def register_mapping(repo_src: Path | None, stage_path: Path) -> None:
    """Track that a repo file now lives at stage_path inside the site."""
    site_rel = _site_rel(stage_path)
    if repo_src is not None:
        try:
            repo_rel = repo_src.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        except ValueError:
            return
        PATH_MAP[repo_rel] = site_rel
        if stage_path.suffix == ".md":
            STAGED_MD.append((repo_rel, site_rel))


def write_staged(path: Path, text: str, repo_src: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    register_mapping(repo_src, path)


def copy_staged(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    register_mapping(src, dst)


def _rewrite_link(
    origin_repo_dir: str,
    site_rel_path: str,
    match: re.Match[str],
) -> str:
    label = match.group(1)
    href = match.group(2)
    if href.startswith(("http://", "https://", "mailto:", "#")) or "://" in href:
        return match.group(0)

    if "#" in href:
        path_part, anchor = href.split("#", 1)
        anchor = "#" + anchor
    else:
        path_part, anchor = href, ""

    if not path_part:
        return match.group(0)
    if path_part.lower().endswith(SKIP_EXTS):
        return match.group(0)

    try:
        abs_target = (REPO_ROOT / origin_repo_dir / path_part).resolve()
    except OSError:
        return match.group(0)
    try:
        repo_rel = abs_target.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return match.group(0)

    if repo_rel in PATH_MAP:
        site_target = PATH_MAP[repo_rel]
        from_dir = posixpath.dirname(site_rel_path) or "."
        rel = posixpath.relpath(site_target, from_dir)
        return f"[{label}]({rel}{anchor})"

    return f"{label} (repo: `{repo_rel}`)"


def rewrite_cross_refs() -> None:
    for repo_rel, site_rel in STAGED_MD:
        origin_dir = posixpath.dirname(repo_rel)
        stage_file = STAGE_DOCS / site_rel
        original = stage_file.read_text(encoding="utf-8")
        rewritten = MD_LINK_RE.sub(
            lambda m: _rewrite_link(origin_dir, site_rel, m),
            original,
        )
        if rewritten != original:
            stage_file.write_text(rewritten, encoding="utf-8")


def stage_home(project_status: dict | None) -> NavNode:
    readme = REPO_README.read_text(encoding="utf-8")
    header = "# 卫星自主插件工程\n\n"
    body = readme
    if body.lstrip().startswith("# "):
        body = "\n".join(body.splitlines()[1:]).lstrip() + "\n"

    extra_lines: list[str] = []
    if project_status:
        trace = project_status.get("traceability_status", {})
        compliance = project_status.get("compliance_status", {})
        extra_lines += [
            "\n## 项目快照\n",
            f"- 当前阶段：`{project_status.get('current_phase', 'unknown')}`",
            f"- 合同：`{trace.get('contract_count', 'n/a')}` 份 | 已落代码 `{trace.get('contracts_with_code', 'n/a')}` | 已有测试 `{trace.get('contracts_with_tests', 'n/a')}`",
            f"- `@verify` 锚点：`{trace.get('verify_count', 'n/a')}` | 已绑定测试 `{trace.get('verifies_with_tests', 'n/a')}`",
            f"- 治理合规：ok=`{compliance.get('ok', 'n/a')}`，策略数=`{compliance.get('policy_count', 'n/a')}`，失败项=`{len(compliance.get('failures', []) or [])}`",
            "",
            "完整状态见 [项目仪表盘](dashboard.md)。",
            "",
        ]

    text = header + body + "\n".join(extra_lines) + "\n"
    write_staged(STAGE_DOCS / "index.md", text, repo_src=REPO_README)
    return NavNode("首页", "index.md")


def _parse_archive_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
    if len(lines) < 3:
        return []
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def build_recent_tasks_section() -> str:
    archived = _parse_archive_rows(TASK_ARCHIVE)
    active_rows: list[dict[str, str]] = []
    if TASK_BOARD.exists():
        lines = [l for l in TASK_BOARD.read_text(encoding="utf-8").splitlines() if l.startswith("|")]
        if len(lines) >= 3:
            header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
            for line in lines[2:]:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == len(header):
                    active_rows.append(dict(zip(header, cells)))

    selected: list[dict[str, str]] = list(active_rows)
    for row in archived:
        if len(selected) >= 3:
            break
        if row not in selected:
            selected.append(row)
    selected = selected[:3]

    out = [
        "## 近期任务（最近 3 条）",
        "",
        "| task_id | 标题 | owner_agent | 状态 |",
        "| --- | --- | --- | --- |",
    ]
    if not selected:
        out.append("| （无） | | | |")
    else:
        for row in selected:
            out.append(
                "| {task_id} | {title} | {owner} | {status} |".format(
                    task_id=row.get("task_id", ""),
                    title=row.get("title", ""),
                    owner=row.get("owner_agent", ""),
                    status=row.get("status", ""),
                )
            )
    out.append("")
    return "\n".join(out)


def stage_dashboard() -> NavNode | None:
    src = GENERATED_DIR / "project_dashboard.md"
    if not src.exists():
        log("project_dashboard.md not found; skipping dashboard page")
        return None
    text = src.read_text(encoding="utf-8")
    if text.startswith("# Project Dashboard"):
        text = "# 项目仪表盘\n" + text[len("# Project Dashboard") :].lstrip("\n")
    elif not text.lstrip().startswith("# "):
        text = "# 项目仪表盘\n\n" + text
    text = text.rstrip() + "\n\n" + build_recent_tasks_section()
    write_staged(STAGE_DOCS / "dashboard.md", text, repo_src=src)
    return NavNode("项目仪表盘", "dashboard.md")


def stage_contracts() -> NavNode | None:
    if not CONTRACTS_DIR.is_dir():
        return None
    node = NavNode("产品合同")
    readme = CONTRACTS_DIR / "README.md"
    if readme.exists():
        copy_staged(readme, STAGE_DOCS / "contracts" / "README.md")
        node.path = "contracts/README.md"

    md_files = sorted(p for p in CONTRACTS_DIR.glob("*.md") if p.name != "README.md")
    for src in md_files:
        text = src.read_text(encoding="utf-8")
        text = transform_puml_links(text)
        rel = Path("contracts") / src.name
        write_staged(STAGE_DOCS / rel, text, repo_src=src)
        title = CONTRACT_NAV_TITLE.get(
            src.name,
            read_first_heading(src) or slug_title(src.name),
        )
        node.children.append(NavNode(title, rel.as_posix()))
    return node


def _stage_blueprint_dir(
    root: Path,
    rel_root: Path,
    puml_targets: list[tuple[Path, Path]],
) -> list[NavNode]:
    nodes: list[NavNode] = []
    md_files = sorted(p for p in root.glob("*.md") if p.name != "README.md")
    for src in md_files:
        text = src.read_text(encoding="utf-8")
        text = transform_puml_links(text)
        rel = rel_root / src.name
        write_staged(STAGE_DOCS / rel, text, repo_src=src)

        for puml in src.parent.glob("*.puml"):
            out_svg = STAGE_DOCS / rel_root / (puml.stem + ".svg")
            if (puml, out_svg) not in puml_targets:
                puml_targets.append((puml, out_svg))
            raw_dst = STAGE_DOCS / rel_root / puml.name
            if not raw_dst.exists():
                copy_staged(puml, raw_dst)

        meta, _ = strip_frontmatter(src.read_text(encoding="utf-8"))
        status = meta.get("status", "").strip().lower()
        base = BLUEPRINT_NAV_TITLE.get(
            src.stem,
            read_first_heading(src) or slug_title(src.name),
        )
        suffix = BLUEPRINT_STATUS_NAV_SUFFIX.get(status, "")
        if status and status != "active" and not suffix:
            suffix = f" [{status}]"
        title = base + suffix
        nodes.append(NavNode(title, rel.as_posix()))
    return nodes


def stage_blueprints(puml_targets: list[tuple[Path, Path]]) -> NavNode | None:
    if not BLUEPRINTS_DIR.is_dir():
        return None
    node = NavNode("架构蓝图")
    readme = BLUEPRINTS_DIR / "README.md"
    if readme.exists():
        copy_staged(readme, STAGE_DOCS / "architecture" / "blueprints" / "README.md")
        node.path = "architecture/blueprints/README.md"

    system_dir = BLUEPRINTS_DIR / "system"
    if system_dir.is_dir():
        sys_node = NavNode("系统蓝图")
        sys_node.children.extend(
            _stage_blueprint_dir(
                system_dir,
                Path("architecture/blueprints/system"),
                puml_targets,
            )
        )
        if sys_node.children:
            node.children.append(sys_node)

    decisions_dir = BLUEPRINTS_DIR / "decisions"
    if decisions_dir.is_dir():
        dec_node = NavNode("决策蓝图")
        dec_node.children.extend(
            _stage_blueprint_dir(
                decisions_dir,
                Path("architecture/blueprints/decisions"),
                puml_targets,
            )
        )
        if dec_node.children:
            node.children.append(dec_node)

    return node if node.children or node.path else None


def stage_flat_dir(
    src_dir: Path,
    stage_subdir: str,
    nav_title: str,
    include_readme: bool = False,
    nav_title_map: dict[str, str] | None = None,
) -> NavNode | None:
    if not src_dir.is_dir():
        return None
    node = NavNode(nav_title)
    files = sorted(p for p in src_dir.glob("*.md"))
    for src in files:
        if src.name == "README.md" and not include_readme:
            continue
        text = transform_puml_links(src.read_text(encoding="utf-8"))
        rel = Path(stage_subdir) / src.name
        write_staged(STAGE_DOCS / rel, text, repo_src=src)
        if nav_title_map and src.name in nav_title_map:
            title = nav_title_map[src.name]
        else:
            title = read_first_heading(src) or slug_title(src.name)
        node.children.append(NavNode(title, rel.as_posix()))
    return node if node.children else None


def _summarize_task(state: dict, events_path: Path) -> dict[str, str]:
    archived = state.get("archived", False)
    updated_at = state.get("updated_at", "")
    first_event_ts = ""
    last_event_ts = ""
    event_count = 0
    if events_path.exists():
        try:
            for line in events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event_count += 1
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = evt.get("timestamp", "")
                if not first_event_ts:
                    first_event_ts = ts
                last_event_ts = ts
        except OSError:
            pass
    return {
        "task_id": state.get("task_id", ""),
        "phase": state.get("phase", ""),
        "owner": state.get("owner", ""),
        "archived": "yes" if archived else "no",
        "acceptance_status": state.get("acceptance_status", "") or "",
        "updated_at": updated_at,
        "goal": state.get("goal", ""),
        "acceptance_summary": state.get("acceptance_summary", "") or "",
        "first_event_ts": first_event_ts,
        "last_event_ts": last_event_ts,
        "event_count": str(event_count),
        "affected_specs": ", ".join(state.get("affected_specs", []) or []),
    }


def stage_harness_summary() -> NavNode | None:
    if not TASKS_DIR.is_dir():
        return None
    summaries: list[dict[str, str]] = []
    for task_dir in sorted(TASKS_DIR.iterdir()):
        state_path = task_dir / "task_state.json"
        if not state_path.exists():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        events_path = task_dir / "events.jsonl"
        summaries.append(_summarize_task(state, events_path))

    summaries.sort(key=lambda row: row.get("updated_at", ""), reverse=True)

    lines: list[str] = [
        "# Harness 运行时任务摘要",
        "",
        "由每个 `harness/runtime/tasks/<id>/task_state.json` 派生的只读摘要；权威细节仍在 harness 目录内，本页不修改任何源文件。",
        "",
        "| task_id | 阶段 | 负责人 | 已归档 | 验收 | 事件数 | 更新时间 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not summaries:
        lines.append("| （无） | | | | | | |")
    else:
        for row in summaries:
            lines.append(
                "| `{task_id}` | {phase} | {owner} | {archived} | {acceptance} | {events} | {updated} |".format(
                    task_id=row["task_id"],
                    phase=row["phase"],
                    owner=row["owner"],
                    archived=row["archived"],
                    acceptance=row["acceptance_status"] or "—",
                    events=row["event_count"],
                    updated=row["updated_at"] or "—",
                )
            )
    lines.append("")

    lines.append("## 各任务目标与验收")
    lines.append("")
    for row in summaries:
        lines.append(f"### `{row['task_id']}`")
        lines.append("")
        lines.append(f"- 阶段：`{row['phase']}`")
        lines.append(f"- 负责人：`{row['owner']}`")
        lines.append(f"- 已归档：`{row['archived']}`")
        if row["affected_specs"]:
            lines.append(f"- 影响规格：{row['affected_specs']}")
        if row["goal"]:
            lines.append(f"- 目标：{row['goal']}")
        if row["acceptance_status"]:
            lines.append(f"- 验收状态：`{row['acceptance_status']}`")
        if row["acceptance_summary"]:
            lines.append(f"- 验收摘要：{row['acceptance_summary']}")
        lines.append("")

    write_staged(STAGE_DOCS / "harness" / "tasks.md", "\n".join(lines) + "\n")
    node = NavNode("Harness 运行时")
    node.children.append(NavNode("任务摘要", "harness/tasks.md"))
    return node


def stage_eval_overview() -> NavNode | None:
    if not EVAL_DOMAINS_DIR.is_dir():
        return None
    node = NavNode("评测", overview_label="评测域概述")
    readme = EVAL_DOMAINS_DIR / "README.md"
    if readme.exists():
        copy_staged(readme, STAGE_DOCS / "eval" / "index.md")
        node.path = "eval/index.md"

    for domain_dir in sorted(p for p in EVAL_DOMAINS_DIR.iterdir() if p.is_dir()):
        d_readme = domain_dir / "README.md"
        if d_readme.exists():
            rel = Path("eval") / "domains" / f"{domain_dir.name}.md"
            copy_staged(d_readme, STAGE_DOCS / rel)
            title = EVAL_DOMAIN_NAV_TITLE.get(
                domain_dir.name,
                read_first_heading(d_readme) or domain_dir.name,
            )
            node.children.append(NavNode(title, rel.as_posix()))
    return node if node.children or node.path else None


def stage_traceability_evidence() -> NavNode | None:
    trace_dir = GENERATED_DIR / "traceability"
    compliance_dir = GENERATED_DIR / "compliance"
    parts: list[str] = ["# 追溯与合规证据", ""]

    def _append(md: Path, heading: str) -> None:
        if md.exists():
            parts.append(f"## {heading}")
            parts.append("")
            parts.append(md.read_text(encoding="utf-8").strip())
            parts.append("")

    _append(trace_dir / "contract_coverage_summary.md", "合同覆盖摘要")
    _append(trace_dir / "verify_coverage_summary.md", "Verify 覆盖摘要")
    _append(trace_dir / "clause_trace_matrix.md", "条款追溯矩阵")

    compliance_status = compliance_dir / "compliance_status.json"
    if compliance_status.exists():
        try:
            data = json.loads(compliance_status.read_text(encoding="utf-8"))
            parts.append("## 治理合规")
            parts.append("")
            parts.append(f"- ok: `{data.get('ok')}`")
            parts.append(f"- 策略数: `{data.get('policy_count')}`")
            parts.append(f"- 失败项: `{len(data.get('failures') or [])}`")
            parts.append("")
        except json.JSONDecodeError:
            pass

    if len(parts) <= 2:
        return None

    write_staged(STAGE_DOCS / "traceability" / "coverage.md", "\n".join(parts) + "\n")
    return NavNode("追溯与合规", "traceability/coverage.md")


def render_all_puml(targets: Iterable[tuple[Path, Path]], mode: str) -> None:
    unique: dict[Path, Path] = {}
    for src, dst in targets:
        unique[src.resolve()] = dst
    for src_abs, dst in unique.items():
        src = Path(src_abs)
        log(f"rendering {src.relative_to(REPO_ROOT)} -> {dst.relative_to(BUILD_DIR)}")
        render_plantuml(src, dst, mode)


def load_project_status() -> dict | None:
    status_path = GENERATED_DIR / "project_status.json"
    if not status_path.exists():
        return None
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_nav(nav_nodes: list[NavNode]) -> None:
    lines = ["nav:"]
    for node in nav_nodes:
        lines.extend(node.to_yaml_lines(indent=1))
    nav_block = "\n".join(lines) + "\n"

    mkdocs_text = MKDOCS_YML.read_text(encoding="utf-8")
    start = mkdocs_text.find(NAV_BEGIN)
    end = mkdocs_text.find(NAV_END)
    if start == -1 or end == -1:
        raise RuntimeError(
            f"mkdocs.yml missing AUTO_NAV sentinels ({NAV_BEGIN} / {NAV_END})"
        )
    head = mkdocs_text[: start + len(NAV_BEGIN) + 1]
    tail = mkdocs_text[end:]
    new_text = head + nav_block + tail
    MKDOCS_YML.write_text(new_text, encoding="utf-8")


def run_mkdocs(action: str) -> int:
    cmd = [sys.executable, "-m", "mkdocs", action, "-f", str(MKDOCS_YML)]
    if action == "build":
        cmd.append("--strict")
    log(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(SITE_DIR))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["auto", "cli", "server"],
        default=os.environ.get("PLANTUML_MODE", "auto"),
        help="PlantUML rendering mode; can also be set via PLANTUML_MODE env var.",
    )
    parser.add_argument(
        "--skip-puml",
        action="store_true",
        help="Skip PlantUML rendering (blueprint pages will link to raw .puml only).",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="After staging, run `mkdocs serve` for local preview (Ctrl-C to stop).",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="After staging, run `mkdocs build --strict`.",
    )
    args = parser.parse_args()

    log(f"repo_root={REPO_ROOT}")
    log(f"site_dir={SITE_DIR}")

    reset_stage()
    puml_targets: list[tuple[Path, Path]] = []

    project_status = load_project_status()
    nav: list[NavNode] = []

    nav.append(stage_home(project_status))
    dashboard = stage_dashboard()
    if dashboard:
        nav.append(dashboard)
    contracts = stage_contracts()
    if contracts:
        nav.append(contracts)
    blueprints = stage_blueprints(puml_targets)
    if blueprints:
        nav.append(blueprints)
    harness = stage_harness_summary()
    if harness:
        nav.append(harness)
    trace = stage_traceability_evidence()
    if trace:
        nav.append(trace)
    eval_overview = stage_eval_overview()
    if eval_overview:
        nav.append(eval_overview)
    guides = stage_flat_dir(
        GUIDES_DIR, "guides", "协作指南", nav_title_map=GUIDE_NAV_TITLE
    )
    if guides:
        nav.append(guides)
    toolchain = stage_flat_dir(
        TOOLCHAIN_DIR,
        "toolchain",
        "工具链",
        nav_title_map=TOOLCHAIN_NAV_TITLE,
    )
    if toolchain:
        nav.append(toolchain)

    rewrite_cross_refs()

    if not args.skip_puml and puml_targets:
        try:
            render_all_puml(puml_targets, args.mode)
        except RuntimeError as exc:
            log(f"PlantUML rendering failed: {exc}")
            return 2

    write_nav(nav)
    log(f"staged {len(list(STAGE_DOCS.rglob('*')))} files under {STAGE_DOCS}")

    if args.serve:
        return run_mkdocs("serve")
    if args.build:
        return run_mkdocs("build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
