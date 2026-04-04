# Repository Agents Guide

This file is the single entrypoint for agent collaboration in this repository.

## Read First

Read these files before making architecture, code, or test changes:

1. `docs/architecture/agent-collaboration.md`
2. `docs/architecture/harness_product_split.md` when the task touches repository structure, orchestration, or toolchain boundaries
3. `docs/memory/working/current_focus.md`
4. `docs/memory/short_term/task_board.md`
5. `docs/memory/short_term/active_context.md`
6. `docs/traceability/known_limitations.md`
7. `docs/traceability/scope_to_contract.md`
8. `docs/traceability/decision_log.md` when frozen constraints or prior decisions are relevant
9. `docs/traceability/agent_activity_log.md` when recent execution history is relevant
10. Relevant `contracts/*.contract.md`
11. Relevant project skills discovered through `.agents/skills/*/SKILL.md` and maintained in `skills/*/SKILL.md`

## Default Workflow

The repository workflow is:

1. `project-manager` reduces the request, coordinates active contracts, and owns task flow.
2. `architecture-expert` provides architecture decisions when the task touches technical route, module boundaries, key trade-offs, or NFR constraints.
3. Domain specialists provide constraints only when the task touches PPP or RD-POD scope.
4. `coding-skill` implements code and adds `@contract` evidence.
5. `testing-skill` adds verification and `@verify` / `@covers` evidence.
6. Local toolchain commands run build, test, and traceability.
7. `traceability-manager` checks evidence completeness and updates governance docs.
8. `project-manager` closes the task with acceptance status and next task/archive moves.

Do not skip traceability before acceptance.

## Policy Loading Rule

`AGENTS.md` only carries global collaboration and governance constraints. Task-specific execution rules must be loaded through policy skills instead of being kept as always-on context.

Use this routing by default:

- C++ implementation / C++ test changes: load `coding-style-rules`
- PlantUML architecture diagrams: load `plantuml-architecture-styleguide`
- Commit / publish / PR / release-finalization tasks: load `commit-message-policy`

`project-manager` is responsible for declaring which policy skills are active for the current task or handoff.

## Required Outputs Per Task

Every task must leave these artifacts updated when applicable:

- `docs/memory/working/current_focus.md`
- `docs/memory/short_term/task_board.md`
- `docs/memory/short_term/active_context.md`
- `docs/traceability/agent_activity_log.md`
- `docs/traceability/decision_log.md` for frozen decisions only
- Contract, code, test, and generated traceability evidence when behavior changes

Use the handoff fields defined in `docs/architecture/agent-collaboration.md`:

- `task_id`
- `goal`
- `affected_contracts`
- `affected_files`
- `status`
- `next_agent`
- `evidence`
- `blocking_issues`
- `notes`

## Approved Local Entrypoints

Use repo-local commands. Do not rely on auto-started project integrations or project MCP config.

```bash
python3 tools/nav-toolchain-cli/toolchain_cli.py build --reconfigure
python3 tools/nav-toolchain-cli/toolchain_cli.py test --no-rebuild
python3 tools/nav-toolchain-cli/toolchain_cli.py traceability --yes
python3 tools/nav-toolchain-cli/toolchain_cli.py benchmark --report-path eval/reports/time_benchmark_report.json --yes
python3 tools/traceability-cli/traceability_cli.py status
python3 scripts/check_quality.py --report-json
python3 scripts/check_quality.py --report-json --skip-build-test --skip-project-dashboard
python3 scripts/render_project_dashboard.py
```

This repository does not keep project-level MCP config in the default Codex startup path.

## Git And Branching

- Repository default branch: `main`
- Integration branch: `develop`
- Task branches: `feature/<task-id>-<topic>`
- Exploratory branches: `spike/<topic>` only when the result is not yet contract-frozen

Each accepted task maps to one branch and one `task_id`.

## Hard Constraints

- Contracts are the source of truth for behavior and boundaries.
- `harness/` manages orchestration artifacts and runtime state only; `product/` manages buildable source and tests.
- `docs/memory/working/` stores the current execution snapshot only.
- `docs/memory/short_term/` stores active iteration state only.
- `docs/traceability/` stores long-term governance memory, frozen constraints, and task history only.
- `docs/_generated/` stores CI-generated runtime status and evidence only.
- The default agent read order must not include `docs/_generated/`.
- Keep the default Codex project path aligned to root `AGENTS.md`, project `.agents/skills`, and repo-local CLI.
- Do not add automatic project MCP startup back into the default flow.
- Do not implement business modules outside the currently frozen contract scope unless the scope files are updated first.

## Task Start Checklist

Before editing:

1. Identify the active contracts.
2. Update `docs/memory/working/current_focus.md`.
3. Add or update the task row in `docs/memory/short_term/task_board.md`.
4. Update `docs/memory/short_term/active_context.md` when scope, gates, or policy skills change.
5. Record the task start in `docs/traceability/agent_activity_log.md`.
6. Confirm the next downstream agent and acceptance target.

## Task Close Checklist

Before claiming completion:

1. Run `python3 scripts/check_quality.py --report-json`.
2. Update working and short-term memory status plus evidence links.
3. Record the handoff or completion in `docs/traceability/agent_activity_log.md`.
4. Update `docs/traceability/decision_log.md` only if a new constraint is frozen.
5. Move completed tasks out of short-term memory once they are archived in `docs/traceability/task_archive.md`.
6. If the task includes commit or publish work, load `commit-message-policy` before preparing the final commit message.
