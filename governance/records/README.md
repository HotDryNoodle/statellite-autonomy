# Governance Records

本目录承载人类可读的治理记录与同步视图，不承载 policy 本体，也不承载脚本生成的 Clause trace 报表。

## Structure

- `working/current_focus.md`
  - 当前执行快照入口。
- `short_term/task_board.md`
  - 当前迭代任务面板。
- `short_term/active_context.md`
  - 当前作用域、验收门和 handoff 约束。
- `scope_to_spec.md`
  - 冻结后的 phase 历史、scope 变迁与 spec 绑定演进。
- `decision_log.md`
  - 已冻结且约束后续实现的工程决策。
- `known_limitations.md`
  - Accepted Limitations 与 Open Risks。
- `agent_activity_log.md`
  - 近期任务流转和执行历史；默认由 `harness_cli` 同步。
- `task_archive.md`
  - 已完成任务的归档记录；默认由 `archive-task` 同步。

## Boundaries

- `governance/policies/` 才是流程与 orchestration 规则的权威源。
- `harness/runtime/tasks/<task_id>/` 才是正式任务机器可验证 proof 的权威源。
- `docs/_generated/traceability/` 保存 product Clause trace 证据。
- `docs/_generated/compliance/` 保存 governance compliance 产物。

从 `COLLAB-013` 起，`working/`、`short_term/`、`agent_activity_log.md` 和 `task_archive.md` 默认由 `harness_cli` 从 `harness/runtime/tasks/<task_id>/` 同步；它们不再是独立 primary mutation surface。
