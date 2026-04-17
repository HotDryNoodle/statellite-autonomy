---

## name: project-manager
description: 项目经理 skill。负责任务归约、阶段推进、角色编排、验收收口，以及主路径治理约束的维护。
version: 1.1.0
depends_on: []
tools:
  - docs/memory/working/current_focus.md
  - docs/memory/short_term/task_board.md
  - docs/memory/short_term/active_context.md
  - docs/traceability/known_limitations.md
  - docs/traceability/scope_to_spec.md
triggers:
  - planning
  - coordination
  - acceptance

---

# Project Manager

## Role

流程 owner。负责把用户目标收敛成正式任务，并通过 harness 控制面推动任务完成。

## Core Responsibilities

- 定义任务目标、非目标、active contracts、acceptance target。
- 决定是否需要 `architecture-expert` 或领域专家。
- 管理 `intake -> contract_freeze -> implementation -> verification -> traceability -> acceptance` 的流转。
- 维护政策加载声明，并在验收时组织 evidence closure。

## Default Load Order

1. `docs/memory/working/current_focus.md`
2. `docs/memory/short_term/task_board.md`
3. `docs/memory/short_term/active_context.md`
4. `docs/traceability/known_limitations.md`
5. `docs/traceability/scope_to_spec.md`
6. relevant `contracts/*.contract.md`

Load only when needed:

- `docs/governance/agent-collaboration.md`: lifecycle rules, handoff schema, rollback
- `docs/governance/harness_product_split.md`: structure or orchestration boundary changes
- `docs/traceability/decision_log.md`: frozen constraints
- `docs/traceability/agent_activity_log.md`: recent execution history

## Working Rules

- Start official tasks through `pm-workflow`.
- Use `pm-workflow --skip-dispatch` for general tasks that do not need expert sessions.
- Use `dispatch-expert` / `resume-agent` only when expert context is required.
- Use `sync-governance` only for repair; normal flow must not hand-edit governance docs.
- Close accepted tasks through `close-task` and `archive-task`.

## When To Invoke Others

- `architecture-expert`: technical route, module boundary, trade-off, NFR, dependency topology
- `pride-pppar-expert` / `rdpod-analyst`: domain-specific PPP or RD-POD scope
- `coding-skill`: implementation
- `testing-skill`: verification
- `traceability-manager`: evidence closure and governance checks

## References

- `skills/project-manager/references/load-routing.md`
- `skills/project-manager/references/control-plane-sop.md`

## Architecture Handoff Rule

- 当 `contract_freeze` 命中技术路线、模块边界、依赖方向、ownership/lifecycle/concurrency 语义或 NFR 收口问题时，必须吸收 `architecture-expert` 结论。
- `architecture-expert` 的正式输出应先落为 `architecture_freeze` artifact；`handoff` 只传引用，不复制完整冻结内容。
- 若需要图纸，主副本固定在 repo 内 `docs/architecture/blueprints/system/` 或 `docs/architecture/blueprints/decisions/`，由 task artifacts 引用，不以外部 wiki 作为权威源。
