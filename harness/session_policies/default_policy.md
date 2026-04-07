# Default Session Policy

- 每个 subtask 只能读取最小必要上下文。
- phase 推进必须通过 `task_state`、`handoff`、`execution_report` 等显式工件。
- runtime 工件不得替代 `docs/memory/` 或 `docs/traceability/` 中的治理记录。
- expert session 必须使用 `expert/<task_id>/<agent_name>` 独立命名空间；不得复用 `coding/`、`testing/`、`eval/` 会话路径。
- 外部 Obsidian knowledge 只能通过 repo-local CLI wrapper 访问；不得直接读取或写入 vault 文档。
