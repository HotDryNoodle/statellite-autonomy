# Active Context

## Current Scope

- Refactor project-state docs into three memory layers under `docs/`.
- Treat `docs/traceability/` as long-term governance memory only.
- Treat `docs/_generated/` as CI runtime output only.
- Add a project dashboard that combines traceability status and recent project progress.

## Active Policy Skills

- `none`

## Acceptance Gates

- `python3 scripts/check_quality.py --report-json`
- `python3 tools/traceability-mcp/traceability_cli.py status`

## Handoff Expectations

- Keep `docs/_generated/` out of the default agent read chain.
- Keep working memory to a single snapshot file.
- Keep short-term memory strict-schema and free of `done` tasks.
