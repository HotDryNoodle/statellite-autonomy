# Dashboard Entrypoints

- `python3 tools/governance-cli/governance_cli.py dashboard`
- `python3 tools/governance-cli/governance_cli.py dashboard --output-dir docs/_generated`

生成产物：

- `docs/_generated/project_dashboard.md`
- `docs/_generated/project_status.json`

说明：

- 仪表盘生成逻辑已从 `scripts/render_project_dashboard.py` 迁入 `tools/governance-cli`
- `site-cli build` 会读取这些派生产物来生成首页快照和仪表盘页面
