# Harness Product Boundary Policy

冻结 `harness/` 控制面与 `product/` 产品面的职责边界。本文件是治理 policy，不参与 `ClauseId` 追溯。

## Policy Rules

### Harness Responsibility

- `harness/` 负责任务编排、工件模板、状态机、handoff、feedback 与 replay。
- `harness/` 可以调用 repo-local CLI，但不得承载业务求解实现。
- `harness/` 运行工件属于可重建 runtime state，不得替代 `governance/records/` 中的人类可读治理记录。

### Product Responsibility

- `product/` 负责可编译、可测试、可 benchmark 的真实源码与测试。
- `product/` 内的模块边界继续受 `layer_boundary.contract.md`、`navigation.contract.md` 等 product contracts 约束。
- 任何需要进入二进制产物的逻辑都必须沉到 `product/`，不得停留在 skill、prompt 或 harness runtime 中。

### Root Entrypoints

- 仓库根目录继续承载 `contracts/`、`governance/`、`docs/`、`skills/`、`.agents/`、`tools/` 等入口层。
- 根目录 CLI 入口必须保持稳定；`src/` 与 `tests/` 迁入 `product/` 后，用户仍通过现有 repo-local 命令完成 build/test/traceability。
- Codex 默认项目入口固定为根 `AGENTS.md` + 项目 `.agents/skills`，不把 harness runtime 或额外 repo-local 集成暴露为项目级自动启动配置。

### Runtime Record And Governance Mirrors

- `harness/runtime/tasks/<task_id>/` 必须为正式任务保留最小控制面记录，例如 `task_state.json`、`events.jsonl` 与必要 artifacts。
- compacted archived task 允许删除 tracked raw artifacts，但必须继续在 `harness/runtime/tasks/<task_id>/` 保留 `task_state.json`、`events.jsonl` 与 `compact_manifest.json` 作为正式证明。
- `harness/runtime/archive/` 只保存 gitignored 的本地冷存储副本，不承载正式治理证明。
- 这些 runtime records 用于 control-plane 可验证性与治理同步，但不替代 `governance/records/` 的人类可读治理文档。
- `governance/records/*`、`governance/records/agent_activity_log.md`、`governance/records/task_archive.md` 默认作为 runtime state 的同步镜像维护；正常流程不得把它们当作独立主写入口。

## Stable References


| Policy Ref                                                                            | Meaning                |
| ------------------------------------------------------------------------------------- | ---------------------- |
| `governance/policies/harness_product_boundary.policy.md#harness-responsibility`                | Harness 责任             |
| `governance/policies/harness_product_boundary.policy.md#product-responsibility`                | Product 责任             |
| `governance/policies/harness_product_boundary.policy.md#root-entrypoints`                      | 根目录入口                  |
| `governance/policies/harness_product_boundary.policy.md#runtime-record-and-governance-mirrors` | Runtime Record 与治理镜像边界 |
