# Harness Product Split

## Summary

- 仓库根目录保留治理入口：`contracts/`、`docs/`、`skills/`、`.agents/`、`tools/`。
- `harness/` 承载协作控制面：状态机、工件 schema、模板、runtime 事件与最小 orchestrator CLI。
- `product/` 承载真实产品工程：`src/`、`tests/`、Meson 子构建入口。
- Codex 项目发现入口固定为根 `AGENTS.md` + `.agents/skills`；不再依赖 plugin bundle 或项目 MCP 配置。

## Role Model

- `project-manager` 是唯一 flow owner，负责任务编排和 phase 推进。
- `architecture-expert` 是被调度的专家角色，只负责边界、trade-off、NFR 与接口冻结。
- `coding-skill`、`testing-skill`、`traceability-manager` 继续分别承担实现、验证和追踪闭环。

## Responsibilities

### Harness

- 维护 `task_brief`、`handoff`、`review_feedback`、`execution_report`、`task_state`。
- 管理 phase transition、allowed next states、runtime replay。
- 通过 repo-local CLI 路由 build/test/traceability/benchmark，不承载业务算法实现。

### Product

- 承载所有进入二进制的源码、测试与 benchmark runner。
- 继续遵守 `layer_boundary.contract.md` 和业务 family contracts。
- 在 Codex 之外也必须可独立 build/test/benchmark。

## Stable Entrypoints

- 根目录 Meson 入口保持稳定，但只做薄封装并转交 `product/`。
- `python3 tools/nav-toolchain-cli/toolchain_cli.py`
- `python3 tools/traceability-cli/traceability_cli.py`
- `python3 scripts/check_quality.py --report-json`

## Runtime And Governance

- `harness/runtime/tasks/<task_id>/` 现在保留正式任务的最小控制面记录：`task_state.json`、`events.jsonl` 与必要 artifacts。
- `docs/memory/` 继续承载当前执行快照，但默认由 `harness_cli` 从 runtime state 同步，不再作为独立主状态机。
- 冻结约束、历史活动和长期决策仍写入 `docs/traceability/`；这些治理文档仍然不是 runtime event log 的替代品。
