# PM Load Routing

Use the smallest context that can decide the next step.

## Always Load

1. `AGENTS.md`
2. `skills/project-manager/SKILL.md`
3. `governance/records/working/current_focus.md`
4. `governance/records/short_term/task_board.md`
5. `governance/records/short_term/active_context.md`
6. `governance/records/known_limitations.md`
7. `governance/records/scope_to_spec.md`
8. Relevant `contracts/*.contract.md`

## Conditional Loads

- `docs/guides/agent-collaboration.md`
  - Need lifecycle, handoff, rollback, or control-plane details
- `docs/guides/harness_product_split.md`
  - Task touches orchestration, repository structure, or toolchain boundaries
- `governance/records/decision_log.md`
  - Need prior frozen constraints or must add a new one
- `governance/records/agent_activity_log.md`
  - Need recent task history or restart context

## Routing Notes

- Default to the general PM path first; do not eagerly load architecture or long-term history.
- Domain or architecture skills should be loaded only after PM identifies the need.
- `docs/_generated/` stays out of the default read chain.
