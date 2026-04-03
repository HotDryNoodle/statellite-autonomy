@page requirements_harness_workflow_contract HarnessWorkflow Contract
@ingroup requirements

# Harness Workflow Contract

## 1. 目标

冻结 harness 控制面的任务生命周期、核心工件和反馈路由规则。

## 2. 工作流约束

### 2.1 生命周期状态机
@contract{HarnessWorkflow_2_1}

Contract：

- harness 只允许 `intake -> contract_freeze -> implementation -> verification -> traceability -> acceptance` 这条主状态机。
- phase 回退必须显式记录原因，不允许跳过 `traceability` 直接进入 `acceptance`。
- `project-manager` 是唯一流程 owner；`architecture-expert` 只在被调度时给出边界与 trade-off 结论。

### 2.2 核心工件
@contract{HarnessWorkflow_2_2}

Contract：

- harness 至少维护 `task_brief`、`handoff`、`review_feedback`、`execution_report`、`task_state` 五类工件。
- 工件推进必须通过显式字段而不是自由对话隐含状态。
- `task_state` 必须至少包含 `task_id`、`phase`、`owner`、`allowed_next_states`、`evidence_refs`、`blocking_issues`。

### 2.3 反馈与回放
@contract{HarnessWorkflow_2_3}

Contract：

- agent 间反馈必须通过 orchestrator 汇总后转发，不允许自由持续对话替代 handoff。
- harness 必须保留足够的事件记录以支持 replay。
- runtime 事件用于复盘，不直接替代长期 decision log 或 activity log。

## 3. 测试要求（verify）

@verify{HarnessWorkflow_3_1}

- 目的：验证非法 phase transition 会被 harness 拒绝。
- 关联合同：`@contract{HarnessWorkflow_2_1}` `@contract{HarnessWorkflow_2_2}`

@verify{HarnessWorkflow_3_2}

- 目的：验证 harness 能生成最小 task_state 并回放事件。
- 关联合同：`@contract{HarnessWorkflow_2_2}` `@contract{HarnessWorkflow_2_3}`

## 附录A：设计约束表

| ClauseId | 说明 |
| --- | --- |
| `@contract{HarnessWorkflow_2_1}` | 生命周期状态机 |
| `@contract{HarnessWorkflow_2_2}` | 核心工件 |
| `@contract{HarnessWorkflow_2_3}` | 反馈与回放 |

## 附录B：测试验证表

| verify-ID | 说明 |
| --- | --- |
| `@verify{HarnessWorkflow_3_1}` | phase transition 校验 |
| `@verify{HarnessWorkflow_3_2}` | task state 与 replay |
