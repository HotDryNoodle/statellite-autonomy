# Default Session Policy

- 每个 subtask 只能读取最小必要上下文。
- phase 推进必须通过 `task_state`、`handoff`、`execution_report` 等显式工件。
- runtime 工件不得替代 `governance/records/` 中的人类可读治理记录，但正式任务必须保留最小 runtime record 作为控制面证据。
- expert session 必须使用 `expert/<task_id>/<agent_name>` 独立命名空间；不得复用 `coding/`、`testing/`、`eval/` 会话路径。
- 外部 Obsidian knowledge 只能通过 repo-local CLI wrapper 访问；不得直接读取或写入 vault 文档。
- 治理 docs 漂移修复必须通过 `harness_cli.py sync-governance`，不得把手工 patch docs 当成正常路径。
