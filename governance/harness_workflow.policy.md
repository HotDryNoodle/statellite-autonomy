# Harness Workflow Policy

冻结 harness 控制面的任务生命周期、核心工件和反馈路由规则。本文件是治理 policy，不参与 `ClauseId` 追溯。

## Policy Rules

### Lifecycle State Machine

- harness 只允许 `intake -> contract_freeze -> implementation -> verification -> traceability -> acceptance` 这条主状态机。
- phase 回退必须显式记录原因，不允许跳过 `traceability` 直接进入 `acceptance`。
- `project-manager` 是唯一流程 owner；`architecture-expert` 只在被调度时给出边界与 trade-off 结论。

### Core Artifacts

- harness 至少维护 `task_brief`、`handoff`、`review_feedback`、`execution_report`、`task_state` 五类工件。
- 工件推进必须通过显式字段而不是自由对话隐含状态。
- `task_state` 必须至少包含 `task_id`、`phase`、`owner`、`allowed_next_states`、`evidence_refs`、`blocking_issues`。

### Feedback And Replay

- agent 间反馈必须通过 orchestrator 汇总后转发，不允许自由持续对话替代 handoff。
- harness 必须保留足够的事件记录以支持 replay。
- runtime 事件用于复盘，不直接替代长期 decision log 或 activity log。

### Control Plane Entry And Governance Sync

- 正式任务必须先在 `harness/runtime/tasks/<task_id>/` 生成 `task_state` 与 runtime events，再同步 `docs/memory/*` 和相关治理记录。
- archived task 允许通过 retention policy 压缩 tracked raw artifacts，但必须继续保留 machine-verifiable proof；对 compacted task，最小证明为 `task_state.json`、`events.jsonl` 和 `compact_manifest.json`。
- 新任务启动默认走 `harness/orchestrator/harness_cli.py pm-workflow`；不需要 expert dispatch 的任务必须使用 `pm-workflow --skip-dispatch`，而不是绕开 harness。
- phase 推进必须通过 `advance` 或 `pm-workflow`；acceptance 收尾必须通过 `close-task` / `archive-task`。
- runtime compaction 必须通过 `compact-runtime` 执行；`harness/runtime/archive/` 只作为 gitignored 的本地冷存储，不是 official proof。
- `current_focus.md`、`task_board.md`、`active_context.md`、`agent_activity_log.md`、`task_archive.md` 默认只允许作为 harness 同步结果更新；漂移修复通过 `sync-governance` 进行。

## Stable References


| Policy Ref                                                                      | Meaning    |
| ------------------------------------------------------------------------------- | ---------- |
| `governance/harness_workflow.policy.md#lifecycle-state-machine`                 | 生命周期状态机    |
| `governance/harness_workflow.policy.md#core-artifacts`                          | 核心工件       |
| `governance/harness_workflow.policy.md#feedback-and-replay`                     | 反馈与回放      |
| `governance/harness_workflow.policy.md#control-plane-entry-and-governance-sync` | 控制面入口与治理同步 |
