# Backlog

Use this file for active and planned multi-agent work. Keep one row per task.

| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| COLLAB-005 | Refactor task-specific rules into policy-skill routing and slim rule loading context | project-manager | `contracts/layer_boundary.contract.md` | done | `AGENTS.md` contains only governance plus policy routing, `commit-message-policy` exists, and rule skills expose TL;DR plus references-based details | `python3 scripts/check_quality.py --report-json` |
| COLLAB-004 | Implement relaxed commit-message governance and make it visible to project agents | project-manager | `contracts/layer_boundary.contract.md` | done | repo-local commit-msg hook exists, installation script is documented, and AGENTS/skills reference `commit-message-relaxed-spec.md` | `python3 scripts/check_quality.py --report-json` |
| COLLAB-003 | Split `system-architect` into explicit `project-manager` and `architecture-expert` skills and migrate workflow governance | project-manager | `contracts/layer_boundary.contract.md` | done | dual-role skills exist, workflow docs use `project-manager` as flow owner, and downstream skills no longer depend on `system-architect` | `python3 scripts/check_quality.py --report-json` |
| COLLAB-001 | Establish repository-level agent collaboration entrypoints and quality gate | system-architect | `contracts/layer_boundary.contract.md`, `contracts/time_system.contract.md` | done | `AGENTS.md`, collaboration protocol, backlog/activity log templates, and `scripts/check_quality.py` are present and runnable | `python3 scripts/check_quality.py --report-json` |
| COLLAB-002 | Initialize git baseline, add CI workflow, real unit::time benchmark assets, phase roadmap, and standardized skill metadata | system-architect | `contracts/layer_boundary.contract.md`, `contracts/time_system.contract.md`, `contracts/navigation.contract.md`, `contracts/prediction.contract.md`, `contracts/mission_planning.contract.md` | done | git repo initialized, CI workflow present, benchmark report generated from scenarios/baselines, roadmap updated, and skill frontmatter standardized | `python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark --report-path eval/reports/time_benchmark_report.json` |

Status values:

- `planned`
- `ready_for_impl`
- `in_progress`
- `blocked`
- `ready_for_verify`
- `ready_for_acceptance`
- `done`
