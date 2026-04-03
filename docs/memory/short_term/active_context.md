# Active Context

## Current Scope

- Tighten commit message validation from relaxed header-only format to a strict structured template.
- Require `Goal`、`Changes`、`Contracts`、`Traceability`、`Validation`、`Refs` sections in every commit message.
- Keep the repository hook entrypoint at `.githooks/commit-msg`.
- Keep section labels fixed in English and encourage body content in Chinese.

## Active Policy Skills

- `commit-message-policy`

## Acceptance Gates

- `python3 scripts/check_quality.py --report-json`
- `python3 tools/traceability-mcp/traceability_cli.py status`
- `python3 scripts/validate_commit_message.py <message-file>`

## Handoff Expectations

- Keep `docs/_generated/` out of the default agent read chain.
- Keep commit message validation strict and deterministic.
- Keep required section names stable so hook, examples, and policy docs do not drift.
