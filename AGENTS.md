# Repository Agents Guide

This file is the global entrypoint for agent collaboration in this repository.

## Read First

Load context in this order:

1. Relevant role skill from `.agents/skills/`
2. `docs/memory/working/current_focus.md`
3. `docs/memory/short_term/task_board.md`
4. `docs/memory/short_term/active_context.md`
5. `docs/traceability/known_limitations.md`
6. `docs/traceability/scope_to_spec.md`
7. Relevant product `contracts/*.contract.md` and, when needed, relevant `governance/*.policy.md`

Load only when needed:

- `docs/architecture/agent-collaboration.md`: lifecycle, handoff, control-plane rules
- `docs/architecture/harness_product_split.md`: structure, orchestration, toolchain boundaries
- `docs/traceability/decision_log.md`: frozen constraints or prior decisions
- `docs/traceability/agent_activity_log.md`: recent execution history

## Workflow

- `project-manager` is the only flow owner.
- `architecture-expert` is invoked only for route, boundary, trade-off, or NFR changes.
- Domain specialists join only when PPP / RD-POD scope is touched.
- `coding-skill`, `testing-skill`, and `traceability-manager` own implementation, verification, and evidence closure.
- Do not skip `traceability` before `acceptance`.

## Policy Routing

- C++ code or tests: load `coding-style-rules`
- PlantUML diagrams: load `plantuml-architecture-styleguide`
- Commit / publish / PR work: load `commit-message-policy`

Task-specific rules belong in skills or references, not in `AGENTS.md`.

## Control Plane

- Product contracts are the source of truth for behavior; governance policies are the source of truth for process constraints and orchestration rules.
- `harness/` manages orchestration artifacts and runtime state only; `product/` manages buildable source and tests.
- From `COLLAB-013` onward, official tasks require `harness/runtime/tasks/<task_id>/task_state.json` and `events.jsonl`.
- Start tasks through `python3 harness/orchestrator/harness_cli.py pm-workflow ...`.
- Advance phases through `advance` or `pm-workflow`.
- Close accepted tasks through `close-task` and `archive-task`.
- Treat `docs/memory/*`, `docs/traceability/agent_activity_log.md`, and `docs/traceability/task_archive.md` as harness-synchronized views; use `sync-governance` only for repair.
- Keep `docs/_generated/` out of the default read chain.

## Approved Entrypoints

Use repo-local command families only:

- `python3 harness/orchestrator/harness_cli.py ...`
- `python3 tools/nav-toolchain-cli/toolchain_cli.py ...`
- `python3 tools/traceability-cli/traceability_cli.py ...`
- `python3 scripts/check_quality.py --report-json`
- `python3 scripts/render_project_dashboard.py`

Detailed PM command templates live in `skills/project-manager/references/control-plane-sop.md`.

## Task Expectations

- Every task must leave current focus, task board, active context, activity log, and relevant evidence updated through the harness path.
- Update `docs/traceability/decision_log.md` only when a new constraint is frozen.
- Do not implement behavior outside frozen product contract or governance policy scope; update scope docs and specs first when the boundary changes.
- If the task includes commit or publish work, load `commit-message-policy` before preparing the commit message.
