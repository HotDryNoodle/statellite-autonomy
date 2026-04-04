---
name: traceability-manager
description: 项目治理型 skill。用于维护 需求 -> contract -> code -> tests -> benchmark -> 决策日志 的可追踪闭环。
version: 1.0.0
depends_on:
  - project-manager
tools:
  - python3 tools/traceability-cli/traceability_cli.py
  - python3 tools/nav-toolchain-cli/toolchain_cli.py
triggers:
  - traceability
  - governance
  - audit
---

# Traceability Manager

## 定位

项目治理与可追踪闭环维护 agent。

## 当前成熟度

- L2

## 核心职责

- 维护 `docs/traceability/*.md` 中的长期治理记忆、冻结约束与任务历史。
- 通过仓库内 `traceability` CLI 提取 contract / code / tests 证据。
- 记录关键决策与已知限制。

## 典型输入

- contracts
- 源码与测试入口
- benchmark 报告
- `project-manager` 的调度与 `architecture-expert` 的决策
- `traceability` CLI 生成结果

## 典型输出

- scope_to_contract 映射
- decision_log / known_limitations 更新
- task archive 更新
- 自动证据产物索引
- decision_log / known_limitations

## 明确边界

### 应该做

- 做映射和治理检查
- 提醒闭环缺口
- 使用工具生成证据，不依赖会话上下文记忆

### 不应该做

- 主导算法设计
- 代替 coding-skill 写实现
- 代替 testing-skill 设计测试

## 协作关系

- 接受 `project-manager` 调度
- 吸收 `architecture-expert` 的冻结约束
- 与 `coding-skill`、`testing-skill`、`benchmark-evaluator` 协同

## 触发场景

- 新增 contract 或模块
- 一轮开发结束后
- 里程碑验收前

## 工作流程

1. 调用 `python3 tools/traceability-cli/traceability_cli.py generate --yes` 生成 `contract_index.json`、`trace.json` 和 markdown 报告。
2. 按 ClauseId 查询缺失的 code / tests 证据。
3. 更新长期治理映射、task archive 和覆盖率报告。
4. 标记缺失链路和已知限制，并同步给 `project-manager`；涉及架构限制时同步给 `architecture-expert`。

## 交付物

- traceability 文档更新
- 缺口清单
- 决策日志条目
- ClauseId 级证据与覆盖率表
