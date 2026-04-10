# Scope To Contract

本文件记录已经冻结的 phase 历史、scope 变迁和 contract 绑定演进。

当前执行态、当前 phase 和当前 blocker 不在本文件中维护。

| 冻结范围 | 对应合同 |
| --- | --- |
| 建立公共时间基础模块闭环 | `contracts/time_system.contract.md` |
| 冻结公共层与业务层边界 | `contracts/layer_boundary.contract.md` |
| 冻结 Navigation 第一阶段范围 | `contracts/navigation.contract.md` |
| 冻结 harness/product 双树边界与工作流 | `contracts/harness_product_boundary.contract.md`, `contracts/harness_workflow.contract.md` |
| 冻结 Codex 项目默认入口与技能发现路径 | `contracts/layer_boundary.contract.md`, `contracts/harness_product_boundary.contract.md` |
| 冻结 repo-local engineering tools 的 CLI-first 入口与帮助语义 | `contracts/layer_boundary.contract.md`, `contracts/harness_product_boundary.contract.md` |
| 冻结 Agents SDK v1 harness adapter、expert registry、tool allowlist 与 workflow eval 骨架 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/layer_boundary.contract.md` |
| 冻结 CLI-only Obsidian expert bridge、`pppar_expert_agent` 独立 session 与 PPP family v1 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/navigation.contract.md`, `contracts/ppp_family.contract.md` |
| 冻结 harness control-plane 强制入口、runtime record 保留策略与 governance sync 门禁 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md` |
| 冻结 prompt-doc 主路径压缩、PM role-specific loading 与 progressive disclosure 门禁 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md` |
| 冻结 Eval Owner 资产治理、统一评测协议与 acceptance verdict 证据 | `contracts/eval_governance.contract.md`, `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/time_system.contract.md`, `contracts/ppp_family.contract.md` |


维护规则：

- 只记录当前迭代真正纳入实现或冻结的范围。
- 不记录 current focus、current blockers 或 active tasks。
- 不重复自动生成的 ClauseId 覆盖统计。
- 新增目标时先补合同，再更新本表。
- phase 路线由 `project-manager` 起草，但只在 `contract_freeze` 后写入本文件；涉及技术路线、模块边界、关键 trade-off 或 NFR 约束时，需吸收 `architecture-expert` 结论。

## Phase Roadmap

| Phase | 目标 | 主合同 | 状态 |
| --- | --- | --- | --- |
| Phase 1 | `unit::time` 公共时间基础模块闭环 | `contracts/time_system.contract.md`, `contracts/layer_boundary.contract.md` | done |
| Phase 1.5 | `harness/` 与 `product/` 双树重构、工作流与入口冻结 | `contracts/harness_product_boundary.contract.md`, `contracts/harness_workflow.contract.md`, `contracts/layer_boundary.contract.md` | done |
| Phase 1.6 | Agents SDK v1 harness adapter、expert governance 与 workflow eval 骨架 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/layer_boundary.contract.md` | done |
| Phase 1.7 | CLI-only Obsidian expert bridge、`pppar_expert_agent` 独立 session、PPP family v1 | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/navigation.contract.md`, `contracts/ppp_family.contract.md` | done |
| Phase 1.8 | Harness governance hard cutover、official runtime records、runtime-vs-memory quality gate | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md` | done |
| Phase 1.9 | Prompt-doc entrypoint compaction、PM references 化与 role-specific default loading | `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md` | done |
| Phase 1.10 | Eval Owner 治理、统一 eval 协议与 acceptance verdict 闭环 | `contracts/eval_governance.contract.md`, `contracts/harness_workflow.contract.md`, `contracts/harness_product_boundary.contract.md`, `contracts/time_system.contract.md`, `contracts/ppp_family.contract.md` | done |
| Phase 2 | `navigation/ppp` 第一批接口与实现收口 | `contracts/navigation.contract.md`, `contracts/ppp_family.contract.md` | planned |
| Phase 3 | `navigation/rdpod` 家族建模与验证闭环 | `contracts/navigation.contract.md`, `contracts/rdpod_family.contract.md` | planned |
| Phase 4 | `prediction` 接口与 handoff 约束收口 | `contracts/prediction.contract.md`, `contracts/state_handoff_navigation_to_prediction.contract.md` | planned |
| Phase 5 | `mission_planning` 接口与调度约束收口 | `contracts/mission_planning.contract.md` | planned |
