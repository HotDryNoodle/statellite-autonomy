---
name: testing-skill
description: 本项目 contract 驱动测试执行 skill。负责把合同条款转换为可执行测试、失败语义验证和 `@verify`/`@covers` 追踪证据。
version: 1.0.0
depends_on:
  - contract-driven-testing
tools:
  - python3 tools/nav-toolchain-mcp/toolchain_mcp.py
  - python3 tools/traceability-mcp/traceability_cli.py
triggers:
  - testing
  - verification
  - acceptance
---

# Testing Skill

## 定位

本项目主要测试设计与验证执行 agent。

## 当前成熟度

- L3

## 核心职责

- 从 active contracts 提取验证义务。
- 设计和实现测试用例，补齐 `@verify{ClauseId}` 与 `@covers{ApiSymbol}`。
- 优先使用 GTest 组织 C++ 单元测试与失败语义验证。
- 验证失败语义可观测，不允许 silent fallback。
- 协助 traceability-manager 维护代码到测试映射。

## 典型输入

- active contracts
- 生产代码入口
- 失败语义与容差约束

## 典型输出

- 测试代码
- 验证矩阵
- 失败用例与观察结果

## 明确边界

### 应该做

- 设计测试矩阵
- 明确 arrange / act / assert
- 确认每个失败条款可观测

### 不应该做

- 替代 coding-skill 写主要生产实现
- 自行定义合同外容差

## 协作关系

- 上游：`project-manager`
- 架构输入：`architecture-expert`
- 协同：`coding-skill`、`traceability-manager`
- 工具：`python3 tools/nav-toolchain-mcp/toolchain_mcp.py`、`python3 tools/traceability-mcp/traceability_cli.py`

## 触发场景

- 新增或变更 contract
- 生产代码落地后需要验证
- 失败语义需要回归保护

## 工作流程

1. 读取 active contracts。
2. 抽取 invariants、failure contracts、容差来源。
3. 设计测试场景和标签。
4. 实现带 `@verify/@covers` 的 GTest。
5. 通过 `nav-toolchain` CLI 运行并归档结果。
6. 调用 `traceability` CLI 确认 verify 与 code 证据闭环。

## 交付物

- 测试用例
- `@verify` / `@covers` 映射
- 失败观察结论

## 必须遵守

- `skills/contract-driven-testing/SKILL.md`
- `skills/coding-style-rules/SKILL.md`
