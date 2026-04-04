# Traceability Tool

本目录提供 ClauseId 级 `contract <-> code <-> tests` 追溯工具：

- `generate`
- `query-clause`
- `status`
- `gen_contract_index.py`
- `gen_trace.py`
- `pyproject.toml`：`uv` 运行环境

推荐入口：

```bash
python3 tools/traceability-cli/traceability_cli.py generate --yes
python3 tools/traceability-cli/traceability_cli.py status
python3 tools/traceability-cli/traceability_cli.py query-clause TimeSys_4_4_4
```

核心输出目录：

- `docs/_generated/traceability/contract_index.json`
- `docs/_generated/traceability/trace.json`
- `docs/_generated/traceability/clause_trace_matrix.md`
- `docs/_generated/traceability/contract_coverage_summary.md`
- `docs/_generated/traceability/verify_coverage_summary.md`

当前扫描输入：

- `contracts/*.contract.md`
- `product/src/**/*.h`
- `product/tests/**/*.cpp`
