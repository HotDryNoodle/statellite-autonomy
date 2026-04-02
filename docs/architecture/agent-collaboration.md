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

- owner: `system-architect`
- 输入：用户需求、现有合同、当前决策日志、当前 backlog
- 退出条件：
  - 明确 `task_id`
  - 明确目标与非目标
  - 明确候选影响合同
  - `docs/backlog.md` 已创建或更新任务行

### 2. `contract_freeze`

- owner: `system-architect`
- 协作：`pppar-expert` / `rdpod-analyst` 仅在领域边界相关时参与
- 退出条件：
  - `affected_contracts` 已冻结
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

- owner: `system-architect`
- 输入要求：
  - handoff `status=ready_for_acceptance`
  - backlog 和 activity log 已更新
- 退出条件：
  - 任务状态写回 `done` 或 `blocked`
  - 下一步 agent 或 backlog 去向明确

## CI/CD 职责

仓库级自动化默认映射本地 CLI，不在 CI 中引入与本地不同的业务逻辑：

- `build-and-test`: 执行 build / test，并上传 `meson-logs`
- `traceability-gate`: 执行 traceability 与 `check_quality.py`，上传生成证据
- `benchmark`: 执行 `toolchain_mcp.py benchmark`，输出回归报告；在基线稳定前默认为非阻塞

当前阶段的 CD 只负责 artifacts 与 release metadata，不做部署。

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
