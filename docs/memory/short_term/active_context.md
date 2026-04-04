# Active Context

## Current Scope

- Harness/product dual-tree is now the canonical repository structure.
- Product scope remains platform-only after the migration; Navigation / Prediction / Mission Planning stay at their current implementation maturity.
- Future feature work should start from `product/` for code and from `harness/` for orchestration/runtime artifacts.
- Codex project integration is migrating back to the official default project layout: root `AGENTS.md`, project `.agents/skills`, and repo-local CLI only.
- Repo-local engineering tools now use `*-cli` layout only; MCP wrapper/server remnants have been removed.

## Active Policy Skills

- none

## Acceptance Gates

- `python3 scripts/check_quality.py --report-json`
- `python3 tools/traceability-cli/traceability_cli.py status`
- `python3 tools/nav-toolchain-cli/toolchain_cli.py benchmark --report-path eval/reports/time_benchmark_report.json --yes`

## Handoff Expectations

- Keep `docs/_generated/` out of the default agent read chain.
- Keep `project-manager` as the only flow owner and `architecture-expert` as an invoked specialist.
- Keep harness responsible for orchestration artifacts and product responsible for buildable business code.
- Keep root CLI entrypoints stable after `product/src/` and `product/tests/` become the only product code roots.
- Remove plugin-bundle and project MCP-config entrypoints from the default Codex path.
- Treat the two repo-local tools as copy-pastable CLIs first: command examples in help, dry-run for side-effectful commands, and actionable error messages.
