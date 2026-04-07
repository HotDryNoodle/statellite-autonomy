@page requirements_harness_product_boundary_contract HarnessProductBoundary Contract
@ingroup requirements

# Harness Product Boundary Contract

## 1. 目标

冻结 `harness/` 控制面与 `product/` 产品面的职责边界，避免协作系统与业务实现再次耦合。

## 2. 边界定义

### 2.1 Harness 责任
@contract{HarnessBoundary_2_1}

Contract：

- `harness/` 负责任务编排、工件模板、状态机、handoff、feedback 与 replay。
- `harness/` 可以调用 repo-local CLI，但不得承载业务求解实现。
- `harness/` 运行工件属于可重建 runtime state，不得替代 `docs/memory/` 或 `docs/traceability/`。

### 2.2 Product 责任
@contract{HarnessBoundary_2_2}

Contract：

- `product/` 负责可编译、可测试、可 benchmark 的真实源码与测试。
- `product/` 内的模块边界继续受 `layer_boundary.contract.md`、`navigation.contract.md` 等业务合同约束。
- 任何需要进入二进制产物的逻辑都必须沉到 `product/`，不得停留在 skill、prompt 或 harness runtime 中。

### 2.3 根目录入口
@contract{HarnessBoundary_2_3}

Contract：

- 仓库根目录继续承载 `contracts/`、`docs/`、`skills/`、`.agents/`、`tools/` 等治理与入口层。
- 根目录 CLI 入口必须保持稳定；`src/` 与 `tests/` 迁入 `product/` 后，用户仍通过现有 repo-local 命令完成 build/test/traceability。
- Codex 默认项目入口固定为根 `AGENTS.md` + 项目 `.agents/skills`，不把 harness runtime 或额外 repo-local 集成暴露为项目级自动启动配置。

### 2.4 Runtime Record 与治理镜像边界
@contract{HarnessBoundary_2_4}

Contract：

- `harness/runtime/tasks/<task_id>/` 必须为正式任务保留最小控制面记录，例如 `task_state.json`、`events.jsonl` 与必要 artifacts。
- compacted archived task 允许删除 tracked raw artifacts，但必须继续在 `harness/runtime/tasks/<task_id>/` 保留 `task_state.json`、`events.jsonl` 与 `compact_manifest.json` 作为正式证明。
- `harness/runtime/archive/` 只保存 gitignored 的本地冷存储副本，不承载正式治理证明。
- 这些 runtime records 用于 control-plane 可验证性与治理同步，但不替代 `docs/memory/` 和 `docs/traceability/` 的人类可读治理文档。
- `docs/memory/*`、`docs/traceability/agent_activity_log.md`、`docs/traceability/task_archive.md` 默认作为 runtime state 的同步镜像维护；正常流程不得把它们当作独立主写入口。

## 3. 测试要求（verify）

@verify{HarnessBoundary_3_1}

- 目的：验证路径迁移后 repo-local build/test/traceability 入口仍可执行。
- 关联合同：`@contract{HarnessBoundary_2_2}` `@contract{HarnessBoundary_2_3}`

@verify{HarnessBoundary_3_2}

- 目的：验证 harness runtime 不替代长期治理记忆入口。
- 关联合同：`@contract{HarnessBoundary_2_1}` `@contract{HarnessBoundary_2_3}`

@verify{HarnessBoundary_3_3}

- 目的：验证正式任务的 runtime record 能支撑治理一致性检查，但仍不把 runtime state 当成长周期治理正文。
- 关联合同：`@contract{HarnessBoundary_2_4}` `@contract{HarnessBoundary_2_1}`

## 附录A：设计约束表

| ClauseId | 说明 |
| --- | --- |
| `@contract{HarnessBoundary_2_1}` | Harness 责任 |
| `@contract{HarnessBoundary_2_2}` | Product 责任 |
| `@contract{HarnessBoundary_2_3}` | 根目录入口 |
| `@contract{HarnessBoundary_2_4}` | Runtime Record 与治理镜像边界 |

## 附录B：测试验证表

| verify-ID | 说明 |
| --- | --- |
| `@verify{HarnessBoundary_3_1}` | 入口稳定性 |
| `@verify{HarnessBoundary_3_2}` | 治理记忆边界 |
| `@verify{HarnessBoundary_3_3}` | runtime record 与治理同步边界 |
