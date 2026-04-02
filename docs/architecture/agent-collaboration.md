# Agent Collaboration

## 协作基线

本仓库采用 `skills` 常驻、repo-local CLI 手动触发的协作模式：

- 默认入口：`AGENTS.md`
- 默认工具：`python3 tools/nav-toolchain-mcp/toolchain_mcp.py`、`python3 tools/traceability-mcp/traceability_cli.py`
- `.mcp.template.json` 仅作为手动模板，不进入默认自动启动链路
- 默认分支策略：`main` 稳定、`develop` 集成、`feature/<task-id>-<topic>` 交付、`spike/<topic>` 探索

## 任务生命周期

固定阶段如下：

1. `intake`
2. `contract_freeze`
3. `implementation`
4. `verification`
5. `traceability`
6. `acceptance`

任何任务都必须按这个顺序流转；不得跳过 `traceability` 直接进入 `acceptance`。

## 阶段职责与门禁

### 1. `intake`

- owner: `project-manager`
- 输入：用户需求、现有合同、当前 working memory、当前 short-term memory、当前决策日志
- 退出条件：
  - 明确 `task_id`
  - 明确目标与非目标
  - 明确候选影响合同
  - `docs/memory/working/current_focus.md` 已更新
  - `docs/memory/short_term/task_board.md` 已创建或更新任务行
  - `docs/memory/short_term/active_context.md` 已同步当前 scope / gates / handoff expectations

### 2. `contract_freeze`

- owner: `project-manager`
- 协作：`pppar-expert` / `rdpod-analyst` 仅在领域边界相关时参与
- 架构输入：`architecture-expert` 在技术路线、模块边界、关键 trade-off、NFR 约束、跨模块依赖拓扑变更时必须参与
- 退出条件：
  - `affected_contracts` 已冻结
  - 若涉及架构边界或关键技术取舍，已有 `architecture-expert` 设计结论
  - 若范围调整，先更新合同或 `docs/traceability/scope_to_contract.md`
  - 若形成新约束，更新 `docs/traceability/decision_log.md`

### 3. `implementation`

- owner: `coding-skill`
- 输入要求：
  - handoff `status=ready_for_impl`
  - `affected_contracts` 非空
- 退出条件：
  - 代码变更完成
  - 新增或修改实现具有 `@contract` 证据
  - handoff `status=ready_for_verify`

### 4. `verification`

- owner: `testing-skill`
- 输入要求：
  - handoff `status=ready_for_verify`
- 退出条件：
  - 测试覆盖目标合同条款
  - 新增或修改测试具有 `@verify` 与 `@covers` 证据
  - handoff `status=ready_for_acceptance` 或进入 `traceability`

### 5. `traceability`

- owner: `traceability-manager`
- 必跑命令：
  - `python3 tools/nav-toolchain-mcp/toolchain_mcp.py traceability`
  - `python3 tools/traceability-mcp/traceability_cli.py status`
  - `python3 scripts/check_quality.py --report-json`
- 退出条件：
  - 生成证据成功
  - 追溯覆盖率不低于基线
  - handoff `status=ready_for_acceptance`

### 6. `acceptance`

- owner: `project-manager`
- 输入要求：
  - handoff `status=ready_for_acceptance`
  - short-term memory 和 activity log 已更新
- 退出条件：
  - 若本轮变更触及架构边界、NFR 或关键依赖，已有 `architecture-expert` 审核结论
  - 任务状态写回 `done` 或 `blocked`
  - 下一步 agent 或 task archive 去向明确

## CI/CD 职责

仓库级自动化默认映射本地 CLI，不在 CI 中引入与本地不同的业务逻辑：

- `build-and-test`: 执行 build / test，并上传 `meson-logs`
- `traceability-gate`: 执行 traceability、baseline/schema/tag checks，并上传 traceability runtime 证据；该 job 不生成 dashboard
- `project-dashboard`: 在 traceability 之后生成项目状态看板与 machine-readable status，并上传 runtime artifacts；该 job 不重复 build / test
- `benchmark`: 执行 `toolchain_mcp.py benchmark`，输出回归报告；在基线稳定前默认为非阻塞

当前阶段的 CD 只负责 artifacts 与 release metadata，不做部署。

## 角色分工

- `project-manager`：流程 owner。负责需求分解、任务调度、状态推进、验收编排、里程碑管理，并对整体进度与质量负责。
- `architecture-expert`：专家角色。接受 `project-manager` 调度，负责技术路线、模块边界、关键 trade-off、NFR 约束，以及跨模块数据/依赖拓扑设计。
- `pppar-expert`、`rdpod-analyst`、`coding-skill`、`testing-skill`、`benchmark-evaluator`、`traceability-manager` 由 `project-manager` 编排；涉及架构决策时依赖 `architecture-expert` 结论。

## Handoff 协议

每次阶段交接必须至少包含下列字段：

```text
task_id:
goal:
affected_contracts:
affected_files:
status:
next_agent:
evidence:
blocking_issues:
notes:
```

字段约束：

- `task_id`: 仓库内唯一，例如 `COLLAB-001`
- `affected_contracts`: 合同路径列表；无合同则不得进入实现阶段
- `affected_files`: 已改或计划改动的路径列表
- `status`: 仅允许 `planned`、`ready_for_impl`、`in_progress`、`blocked`、`ready_for_verify`、`ready_for_acceptance`、`done`
- `next_agent`: 下一棒角色；终态可为 `none`
- `evidence`: 命令、报告、生成物或测试名称
- `blocking_issues`: 无阻塞写 `none`

## 回退规则

- `implementation` 失败：回退到 `contract_freeze`
- `verification` 失败：回退到 `implementation`
- `traceability` 失败：回退到最近一个产生错误证据的阶段，通常为 `implementation` 或 `verification`
- `acceptance` 发现范围错误：回退到 `contract_freeze`

禁止跨阶段跳回并直接标记完成。

## 当前实装范围

- 公共层：`unit::time`
- Navigation / Prediction / Mission Planning：边界与占位

## 默认读取顺序

agents 默认按以下顺序读取上下文：

1. `AGENTS.md`
2. `docs/memory/working/current_focus.md`
3. `docs/memory/short_term/task_board.md`
4. `docs/memory/short_term/active_context.md`
5. `docs/traceability/known_limitations.md`
6. `docs/traceability/scope_to_contract.md`
7. `docs/traceability/decision_log.md`（按需）
8. `docs/traceability/agent_activity_log.md`（按需）
9. relevant `contracts/*.contract.md`
10. relevant `skills/*/SKILL.md`

`docs/_generated/` 只用于 CI runtime 产物与人类查看，不进入默认读取链路。
