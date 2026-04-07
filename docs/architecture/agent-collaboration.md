# Agent Collaboration

## Baseline

- Root entrypoint: `AGENTS.md`
- Role cards: `.agents/skills/` with content maintained in `skills/`
- Control plane: `python3 harness/orchestrator/harness_cli.py`
- Engineering tools: `python3 tools/nav-toolchain-cli/toolchain_cli.py`, `python3 tools/traceability-cli/traceability_cli.py`

From `COLLAB-013` onward, official tasks must keep `task_state.json` and `events.jsonl` under `harness/runtime/tasks/<task_id>/`.

## Lifecycle

| phase | owner | exit signal |
| --- | --- | --- |
| `intake` | `project-manager` | task exists and affected contracts are identified |
| `contract_freeze` | `project-manager` | contracts and boundaries are frozen |
| `implementation` | `coding-skill` | code and `@contract` evidence are ready |
| `verification` | `testing-skill` | tests and `@verify` / `@covers` evidence are ready |
| `traceability` | `traceability-manager` | `traceability` and quality gates are green |
| `acceptance` | `project-manager` | task is closed and, when applicable, archived |

Do not skip `traceability` before `acceptance`.

## Handoff

Each phase handoff must carry:

```text
task_id:
goal:
affected_contracts:
affected_files:
status:
next_agent:
evidence:
blocking_issues:
notes:
```

`affected_contracts` cannot be empty before implementation.

## Control Plane Rules

- Start tasks with `pm-workflow`.
- Use `pm-workflow --skip-dispatch` for tasks that do not need expert sessions.
- Use `dispatch-expert` / `resume-agent` only for expert context.
- Advance phases through `advance` or `pm-workflow`.
- Close accepted tasks through `close-task` and `archive-task`.
- Treat `docs/memory/*`, `docs/traceability/agent_activity_log.md`, and `docs/traceability/task_archive.md` as harness-synchronized views; use `sync-governance` only for repair.

## Rollback

- `implementation` failure -> back to `contract_freeze`
- `verification` failure -> back to `implementation`
- `traceability` failure -> back to the phase that produced bad evidence
- `acceptance` scope error -> back to `contract_freeze`
