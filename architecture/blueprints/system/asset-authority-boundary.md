---
blueprint_type: system
status: active
effective_specs:
  - governance/policies/harness_workflow.policy.md
  - governance/policies/harness_product_boundary.policy.md
replaced_by: ""
---

# Asset Authority Boundary Blueprint

本图纸冻结文档/资产重构后的 canonical 信息架构：

- `contracts/` 只承载产品行为合同与验证锚点。
- `architecture/blueprints/` 是架构冻结主副本根，不再挂在 `docs/` 下。
- `governance/policies/` 承载流程与约束规则。
- `governance/records/` 承载长期治理记录与人类可读历史。
- `harness/runtime/` 是正式任务机器可验证真相源。
- `harness/eval/` 承载控制面 workflow 级评测夹具。
- `eval/domains/` 承载产品级评测资产。
- `docs/` 只保留索引、说明、迁移手册与阅读视图。

## Frozen Decisions

- 同一类事实只允许一个权威目录；可读视图只能是派生物，不得与权威目录形成手工双写。
- `governance/records/*` 与长期治理记录不再作为默认权威输入链，它们迁入 `governance/records/`。
- workflow 级 eval 与产品级 eval 必须物理分层，避免 `eval/` 混放控制面夹具。
- 所有 runtime、tooling、quality gate、测试与历史工件最终只接受新路径。

## Read With

- [asset-authority-boundary.puml](asset-authority-boundary.puml)
