# Repository Agents Guide

This file is the single entrypoint for agent collaboration in this repository.

## Read First

Read these files before making architecture, code, or test changes:

1. `docs/architecture/agent-collaboration.md`
2. `docs/traceability/scope_to_contract.md`
3. `docs/traceability/decision_log.md`
4. Relevant `contracts/*.contract.md`
5. Relevant `skills/*/SKILL.md`

## Default Workflow

The repository workflow is:

1. `system-architect` reduces the request and freezes the active contracts.
2. Domain specialists provide constraints only when the task touches PPP or RD-POD scope.
3. `coding-skill` implements code and adds `@contract` evidence.
4. `testing-skill` adds verification and `@verify` / `@covers` evidence.
5. Local toolchain commands run build, test, and traceability.
6. `traceability-manager` checks evidence completeness and updates governance docs.
7. `system-architect` closes the task with acceptance status and next backlog moves.

Do not skip traceability before acceptance.

## Required Outputs Per Task

Every task must leave these artifacts updated when applicable:

- `docs/backlog.md`
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

Use repo-local commands. Do not rely on auto-started project MCP servers.

```bash
python3 tools/nav-toolchain-mcp/toolchain_mcp.py build --reconfigure
python3 tools/nav-toolchain-mcp/toolchain_mcp.py test --no-rebuild
python3 tools/nav-toolchain-mcp/toolchain_mcp.py traceability
python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark --report-path eval/reports/time_benchmark_report.json
python3 tools/traceability-mcp/traceability_cli.py status
python3 scripts/check_quality.py --report-json
```

`.mcp.template.json` is only a manual template. It is not part of the default startup path.

## Git And Branching

- Repository default branch: `main`
- Integration branch: `develop`
- Task branches: `feature/<task-id>-<topic>`
- Exploratory branches: `spike/<topic>` only when the result is not yet contract-frozen

Each accepted task maps to one branch and one `task_id`.

## Hard Constraints

- Contracts are the source of truth for behavior and boundaries.
- `docs/traceability/` stores human governance only.
- `docs/_generated/traceability/` stores generated evidence only.
- Keep the plugin workflow `skills`-only by default; use CLI or manual stdio MCP only when needed.
- Do not add automatic project MCP startup back into the default flow.
- Do not implement business modules outside the currently frozen contract scope unless the scope files are updated first.

## Task Start Checklist

Before editing:

1. Identify the active contracts.
2. Add or update the task row in `docs/backlog.md`.
3. Record the task start in `docs/traceability/agent_activity_log.md`.
4. Confirm the next downstream agent and acceptance target.

## Task Close Checklist

Before claiming completion:

1. Run `python3 scripts/check_quality.py --report-json`.
2. Update backlog status and evidence links.
3. Record the handoff or completion in `docs/traceability/agent_activity_log.md`.
4. Update `docs/traceability/decision_log.md` only if a new constraint is frozen.
