# Governance Quality Entrypoints

- `python3 tools/governance-cli/governance_cli.py quality --report-json`
- `python3 tools/governance-cli/governance_cli.py quality --skip-build-test --skip-project-dashboard`

检查范围：

- `product/` 合同标签与测试标签
- `governance/records/` 结构与 runtime 一致性
- `architecture/blueprints/` 元数据与 freeze artifact 引用
- `tools/tests/` 与 `harness/tests/`

说明：

- 这是当前正式的仓库质量门入口。
- 旧的 `scripts/check_quality.py` 已迁入 `tools/governance-cli`。
