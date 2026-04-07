# Active Context

## Current Scope

- Harness/product dual-tree is now the canonical repository structure.
- Product scope remains platform-only after the migration; Navigation / Prediction / Mission Planning stay at their current implementation maturity.
- Future feature work should start from `product/` for code and from `harness/` for orchestration/runtime artifacts.
- Codex project integration is migrating back to the official default project layout: root `AGENTS.md`, project `.agents/skills`, and repo-local CLI only.
- Repo-local engineering tools now use `*-cli` layout only; MCP wrapper/server remnants have been removed.
- Harness now contains an Agents SDK-oriented runtime adapter scaffold, shared transition logic, expert registry, tool allowlist, and workflow eval fixtures.
- The adapter reuses the existing harness state machine; future work must not introduce a second phase-transition rule set.
- Runtime execution remains synchronous and repo-native; hosted retrieval and background mode remain future-phase work.
- `COLLAB-012` upgrades the harness from placeholder expert scaffolding to a real `pppar_expert_agent` dispatch path with isolated expert sessions.
- `harness_cli.py` now exposes a PM workflow entrypoint that can create a task, promote it into `contract_freeze`, dispatch `pppar_expert_agent`, and advance to the next requested phase in one command.
- The PM workflow now persists `task_brief` and `handoff` artifacts under the task runtime directory, and `resume-agent` can reopen the isolated expert session without exposing that session to coding/testing roles.
- The same PM workflow now synchronizes `current_focus.md`, `task_board.md`, `active_context.md`, and the activity log from the generated artifacts, so task kickoff and governance state stay aligned through one repo-local entrypoint.
- Task closure is now part of the same control surface: `close-task` and `archive-task` can finalize an acceptance-stage task, move it into `task_archive.md`, and clear its short-term memory footprint; `pm-workflow` can invoke that same close/archive path when resuming an existing acceptance task.
- External expert knowledge now comes from the `expert-system` Obsidian vault only through repo-local CLI wrappers; direct file reads and writes against the vault are out of scope.
- Obsidian knowledge lookup fails closed when the desktop app is not running; fresh expert dispatch cannot bypass that gate.
- Sandbox execution now uses the same CLI-only policy and reports host-visibility failures through a CLI probe; when host Obsidian is outside the sandbox boundary, `OBSIDIAN_CLI_PREFIX` or a host-visible `OBSIDIAN_CLI_BIN` wrapper is the supported bridge.
- `contracts/ppp_family.contract.md` is being expanded from a placeholder into a v1 contract that freezes PPP-AR core scope plus the LEO coupling entry.

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
- Keep `project-manager` as the only orchestrator even after adding an `architecture_expert_agent`.
- Treat `harness-expert-system-supplement.md` and `plan.md` as implementation inputs; the repo contracts remain the runtime source of truth.
- Route every Obsidian vault interaction through the repo-local `knowledge` CLI wrappers; do not read or write vault notes through filesystem helpers.
- Keep `pppar_expert_agent` session state isolated from coding, testing, and eval sessions; cross-role state transfer must happen through validated artifacts only.
- Keep PRIDE-PPPAR as the authority for PPP implementation evidence even when Obsidian returns supplemental notes.
