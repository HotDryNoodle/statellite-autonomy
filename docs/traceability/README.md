# Traceability Governance Docs

本目录只放人工维护的治理文档，不放脚本自动生成的证据报表。

职责边界：

- `scope_to_contract.md`
  - 记录当前阶段的工程目标与合同绑定关系。
  - 用于说明“为什么现在要维护这些 contract”。
- `decision_log.md`
  - 记录已冻结的架构、接口、流程和工具链决策。
  - 只写对后续实现有约束力的决定。
- `known_limitations.md`
  - 记录当前明确接受的缺口、占位和未完成项。
  - 用于验收和迭代规划，不放自动统计。

自动生成的 ClauseId 证据、覆盖率和矩阵统一放在：

- `docs/_generated/traceability/`

推荐理解方式：

- 本目录 = 人工治理结论
- `_generated/traceability` = 工具扫描证据
