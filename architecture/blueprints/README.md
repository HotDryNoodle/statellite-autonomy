# Architecture Blueprints

本目录保存正式冻结的 repo-primary 设计图纸。

规则：

- 主副本固定在仓库内，不以外部 wiki 作为权威源。
- 图纸分两类：
  - `system/`: 长期有效的全局结构图和稳定边界。
  - `decisions/`: 某次 task 为冻结 trade-off 或局部边界产出的决策图纸。
- 每个正式图纸使用一对文件：`<slug>.puml` 和 `<slug>.md`。
- `slug` 使用 kebab-case，表达域和主题。
- `.puml` 是正式原图；`.md` 负责生命周期元数据、适用 specs、关键 trade-off 和阅读入口。
- `decision` 图纸必须带 frontmatter：`blueprint_type`、`status`、`created_from_task`、`effective_specs`、`valid_for_task`、`replaced_by`、`superseded_reason`。
- `system` 图纸必须带 frontmatter：`blueprint_type`、`status`、`effective_specs`、`replaced_by`。
- 默认读链只加载 `active` 的 `system` 图纸，以及命中当前 task/spec 的 `active decision` 图纸。
- `superseded` / `obsolete` 图纸保留历史，但退出默认读链；如已失效，必须给出 `replaced_by`。
- task runtime artifacts 只引用本目录路径，不把正式图纸复制到 `harness/runtime/`。
- 需要正式绘图时，默认吸收 `plantuml-architecture-styleguide`。
