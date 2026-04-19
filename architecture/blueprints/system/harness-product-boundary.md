---
blueprint_type: system
status: active
effective_specs:
  - contracts/layer_boundary.contract.md
  - governance/policies/harness_workflow.policy.md
  - governance/policies/harness_product_boundary.policy.md
replaced_by: ""
---

# Harness Product Boundary Blueprint

本图纸冻结当前仓库的主结构边界：根目录治理层、`harness/` 控制面、`product/` 产品面，以及 repo-local blueprints 作为正式设计图纸主副本。

## Frozen Decisions

- `project-manager` 是唯一 flow owner；`architecture-expert` 只在被调度时做架构裁决。
- `harness/` 负责状态机、runtime artifacts 与 orchestration，不承载产品算法实现。
- `product/` 负责进入二进制的源码、测试与 benchmark runner。
- 正式设计图纸主副本固定在 `architecture/blueprints/system/` 和 `architecture/blueprints/decisions/`，task runtime 只保留引用。

## Read With

- [harness-product-boundary.puml](harness-product-boundary.puml)
- [harness_product_split.md](../../../docs/guides/harness_product_split.md)
