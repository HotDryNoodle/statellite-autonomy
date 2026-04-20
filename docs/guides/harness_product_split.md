# Harness Product Split

## Summary

- 根目录权威资产按职责拆分为 `contracts/`、`architecture/blueprints/`、`governance/policies/`、`governance/records/`、`eval/domains/` 和 `harness/runtime/`。
- `harness/` 承载协作控制面：状态机、工件 schema、模板、runtime 事件、workflow eval 与最小 orchestrator CLI。
- `product/` 承载真实产品工程：`src/`、`tests/`、Meson 子构建入口。
- `docs/` 只保留 guide、索引和迁移说明；不再承载 authority blueprint、policy 或 tracked governance mirror 主副本。

## Role Model

- `project-manager` 是唯一 flow owner，负责任务编排和 phase 推进。
- `architecture-expert` 是被调度的专家角色，负责边界、依赖方向、trade-off、NFR 与接口冻结，并在需要时产出 repo-local blueprint 主副本。
- `coding-skill`、`testing-skill`、`traceability-manager` 继续分别承担实现、验证和追踪闭环。
- `benchmark-evaluator` 作为 Eval Owner 维护场景/基线治理、统一评测协议和 acceptance-ready verdict。

## Responsibilities

### Harness

- 维护 `task_brief`、`handoff`、`review_feedback`、`execution_report`、`task_state`。
- 在需要架构裁决时，维护 `architecture_freeze` artifact 引用与默认读取链。
- 管理 phase transition、allowed next states、runtime replay。
- 通过 repo-local CLI 路由 build/test/traceability/benchmark，不承载业务算法实现。
- 维护 `architecture-expert` 输出的 runtime artifact 引用，不把正式图纸主副本放在 runtime 目录中。

### Product

- 承载所有进入二进制的源码、测试与 benchmark runner。
- 继续遵守 `layer_boundary.contract.md` 和业务 family contracts。
- 在 Codex 之外也必须可独立 build/test/benchmark。

## Stable Entrypoints

- 根目录 Meson 入口保持稳定，但只做薄封装并转交 `product/`。
- `tools/` 承载正式 repo-local CLI 本体；`scripts/` 只保留轻量脚本、hook 安装器和验证器。
- `python3 tools/meson-cli/meson_cli.py`
- `python3 tools/traceability-cli/traceability_cli.py`
- `python3 tools/governance-cli/governance_cli.py quality --report-json`

## Runtime And Governance

- `harness/runtime/tasks/<task_id>/` 现在保留正式任务的最小控制面记录：`task_state.json`、`events.jsonl` 与必要 artifacts。
- `governance/records/working/` 与 `governance/records/short_term/` 承载当前执行快照，但默认由 `harness_cli` 从 runtime state 同步，不再作为独立主状态机。
- `governance/records/` 根承载冻结约束、历史活动和长期决策；这些治理文档仍然不是 runtime event log 的替代品。
- 正式架构图纸与冻结说明主副本保留在 `architecture/blueprints/`；`system/` 目录保存稳定总图，`decisions/` 保存 task 级冻结图纸。
- runtime artifacts 只保存路径引用、handoff 摘要和当轮约束；完整架构裁决内容落在 `architecture_freeze` artifact。
