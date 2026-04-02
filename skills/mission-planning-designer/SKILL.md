---
name: mission-planning-designer
description: Mission Planning 层占位设计 skill。用于定义未来 mission planning 接口边界和与 prediction 的耦合约束。
version: 1.0.0
depends_on:
  - project-manager
tools:
  - contracts/mission_planning.contract.md
triggers:
  - mission-planning
  - interface-design
  - scope-freeze
---

# Mission Planning Designer

## 定位

Mission Planning 层占位设计 agent。

## 当前成熟度

- L1

## 核心职责

- 冻结 Mission Planning 接口边界。
- 维护与 Prediction / Navigation 的输入输出关系。

## 典型输入

- `contracts/mission_planning.contract.md`
- 顶层架构设计

## 典型输出

- 接口草案
- 未来耦合约束

## 明确边界

- 只做边界设计，不做本轮实现。

## 协作关系

- 接受 `project-manager` 调度
- 涉及架构边界时吸收 `architecture-expert` 结论

## 触发场景

- Mission Planning 边界收敛

## 工作流程

1. 读取相关合同。
2. 输出层边界和接口建议。

## 交付物

- Mission Planning 设计说明
