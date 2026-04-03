# Active Context

## Current Scope

- Harness/product dual-tree is now the canonical repository structure.
- Product scope remains platform-only after the migration; Navigation / Prediction / Mission Planning stay at their current implementation maturity.
- Future feature work should start from `product/` for code and from `harness/` for orchestration/runtime artifacts.

## Active Policy Skills

- none

## Acceptance Gates

- `python3 scripts/check_quality.py --report-json`
- `python3 tools/traceability-mcp/traceability_cli.py status`
- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark --report-path eval/reports/time_benchmark_report.json`

## Handoff Expectations

- Keep `docs/_generated/` out of the default agent read chain.
- Keep `project-manager` as the only flow owner and `architecture-expert` as an invoked specialist.
- Keep harness responsible for orchestration artifacts and product responsible for buildable business code.
- Keep root CLI entrypoints stable after `product/src/` and `product/tests/` become the only product code roots.
