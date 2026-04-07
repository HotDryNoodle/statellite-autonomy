# PM Load Routing

Use the smallest context that can decide the next step.

## Always Load

1. `AGENTS.md`
2. `skills/project-manager/SKILL.md`
3. `docs/memory/working/current_focus.md`
4. `docs/memory/short_term/task_board.md`
5. `docs/memory/short_term/active_context.md`
6. `docs/traceability/known_limitations.md`
7. `docs/traceability/scope_to_contract.md`
8. Relevant `contracts/*.contract.md`

## Conditional Loads

- `docs/architecture/agent-collaboration.md`
  - Need lifecycle, handoff, rollback, or control-plane details
- `docs/architecture/harness_product_split.md`
  - Task touches orchestration, repository structure, or toolchain boundaries
- `docs/traceability/decision_log.md`
  - Need prior frozen constraints or must add a new one
- `docs/traceability/agent_activity_log.md`
  - Need recent task history or restart context

## Routing Notes

- Default to the general PM path first; do not eagerly load architecture or long-term history.
- Domain or architecture skills should be loaded only after PM identifies the need.
- `docs/_generated/` stays out of the default read chain.
