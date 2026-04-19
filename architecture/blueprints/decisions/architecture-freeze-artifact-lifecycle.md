---
blueprint_type: decision
status: active
created_from_task: COLLAB-023
effective_specs:
  - governance/policies/harness_workflow.policy.md
  - governance/policies/harness_product_boundary.policy.md
valid_for_task: COLLAB-023
replaced_by: ""
superseded_reason: ""
---

# Architecture Freeze Artifact Lifecycle

本图纸冻结 `contract_freeze` 阶段的架构裁决交付链：`project-manager` 提出待裁决问题，`architecture-expert` 产出 `architecture_freeze` artifact，并把 repo-local `.puml` 图纸主副本下发给实现、测试和追踪角色。

## Read With

- [architecture-freeze-artifact-lifecycle.puml](architecture-freeze-artifact-lifecycle.puml)
- [harness_workflow.policy.md](../../../governance/policies/harness_workflow.policy.md#architecture-freeze-outputs)
