# Backlog

Use this file for active and planned multi-agent work. Keep one row per task.

| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |
| --- | --- | --- | --- | --- | --- | --- |
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
