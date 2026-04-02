---
name: coding-skill
description: 本项目 contract 驱动编码执行 skill。负责按照本仓库 contracts 和编码规范落地 C++/Python 实现，并补齐 `@contract` 追踪标签。
version: 1.0.0
depends_on:
  - contract-driven-coding
  - coding-style-rules
tools:
  - python3 tools/nav-toolchain-mcp/toolchain_mcp.py
  - python3 tools/traceability-mcp/traceability_cli.py
triggers:
  - implementation
  - refactor
  - code-change
---
# Coding Skill

## 定位

本项目主要编码执行 agent。

## 当前成熟度

- L3

## 核心职责

- 按合同实现生产代码。
- 为公共 API 和 contract boundary 补齐 Doxygen 与 `@contract{ClauseId}`。
- 遵守本仓库方法型 skills：
  - `skills/contract-driven-coding/`
  - `skills/coding-style-rules/`
- 通过仓库内 `nav-toolchain` CLI 做 build / test 验证。
- 通过仓库内 `traceability` CLI 检查 ClauseId 到代码证据是否完整。

## 典型输入

- active contracts
- current focus
- active context
- 已冻结接口
- 当前源码树
- 决策日志

## 典型输出

- 生产代码实现
- API 注释与 traceability tags
- 最小验证结果

## 明确边界

### 应该做

- 按合同实现代码
- 显式实现失败语义
- 保持命名、注释、风格一致

### 不应该做

- 擅自发明合同外行为
- 把测试职责整体转嫁给生产代码
- 遇到合同冲突时绕过确认

## 协作关系

- 上游：`project-manager`
- 架构输入：`architecture-expert`
- 协同：`testing-skill`、`traceability-manager`
- 工具：`python3 tools/nav-toolchain-mcp/toolchain_mcp.py`、`python3 tools/traceability-mcp/traceability_cli.py`

## 触发场景

- 需要按合同实现或重构代码
- 需要补 `@contract` 标签
- 需要把边界文档落成 API

## 工作流程

1. 按固定读取顺序读取 current focus、task board、active context 和 active contracts。
2. 提取条款清单、失败语义和 test obligation。
3. 映射 ClauseId 到代码位置。
4. 编写实现并补 `@contract` 标签。
5. 用 `nav-toolchain` CLI 做构建验证。
6. 用 `traceability` CLI 检查 ClauseId 映射是否可被提取。

## 交付物

- 代码补丁
- 覆盖的 ClauseId 清单
- 已执行的最小验证

## 必须遵守

- `skills/contract-driven-coding/SKILL.md`
- `skills/coding-style-rules/SKILL.md`
