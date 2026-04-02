# Scope To Contract

本文件记录当前阶段主动纳入管理的工程目标，以及它们对应的合同边界。


| 当前工程目标               | 对应合同                                   |
| -------------------- | -------------------------------------- |
| 建立公共时间基础模块闭环         | `contracts/time_system.contract.md`    |
| 冻结公共层与业务层边界          | `contracts/layer_boundary.contract.md` |
| 冻结 Navigation 第一阶段范围 | `contracts/navigation.contract.md`     |


维护规则：

- 只记录当前迭代真正纳入实现或冻结的范围。
- 不重复自动生成的 ClauseId 覆盖统计。
- 新增目标时先补合同，再更新本表。
- phase 路线由 `system-architect` 起草，但只在 `contract_freeze` 后写入本文件。

## Phase Roadmap

| Phase | 目标 | 主合同 | 状态 |
| --- | --- | --- | --- |
| Phase 1 | `unit::time` 公共时间基础模块闭环 | `contracts/time_system.contract.md`, `contracts/layer_boundary.contract.md` | done |
| Phase 2 | `navigation/ppp` 第一批接口与实现收口 | `contracts/navigation.contract.md`, `contracts/ppp_family.contract.md` | planned |
| Phase 3 | `navigation/rdpod` 家族建模与验证闭环 | `contracts/navigation.contract.md`, `contracts/rdpod_family.contract.md` | planned |
| Phase 4 | `prediction` 接口与 handoff 约束收口 | `contracts/prediction.contract.md`, `contracts/state_handoff_navigation_to_prediction.contract.md` | planned |
| Phase 5 | `mission_planning` 接口与调度约束收口 | `contracts/mission_planning.contract.md` | planned |
