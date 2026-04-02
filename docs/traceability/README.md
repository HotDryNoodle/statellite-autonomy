# Traceability Governance Docs

本目录只放 agent 维护的长期治理记忆、冻结约束和任务历史，不放当前执行态，也不放脚本自动生成的 runtime 报表。

职责边界：

- `scope_to_contract.md`
  - 记录冻结后的 phase 历史、scope 变迁与 contract 绑定演进。
  - 不承载当前任务焦点或当前 active phase。
- `decision_log.md`
  - 记录已冻结的架构、接口、流程和工具链决策。
  - 只写对后续实现有约束力的决定。
- `known_limitations.md`
  - 只记录 `Accepted Limitations` 与 `Open Risks`。
  - 不记录当前 blocker 或当前任务状态。
- `agent_activity_log.md`
  - 记录任务阶段流转和近期执行历史。
- `task_archive.md`
  - 记录从 short-term memory 迁出的已完成任务。

自动生成的 ClauseId 证据、覆盖率和矩阵统一放在：

- `docs/_generated/traceability/`

当前执行态统一放在：

- `docs/memory/working/current_focus.md`
- `docs/memory/short_term/task_board.md`
- `docs/memory/short_term/active_context.md`

推荐理解方式：

- `docs/memory/` = 当前态与短期态
- `docs/traceability/` = 长期治理记忆
- `docs/_generated/` = CI runtime 产物
