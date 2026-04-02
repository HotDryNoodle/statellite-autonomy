# Traceability Tool

本目录提供 ClauseId 级 `contract <-> code <-> tests` 追溯工具：

- `generate`
- `query-clause`
- `status`
- `gen_contract_index.py`
- `gen_trace.py`
- `server.py`：本地 stdio wrapper，包装 traceability CLI 供手动 MCP 调试使用
- `pyproject.toml`：`uv` 运行环境

核心输出目录：

- `docs/_generated/traceability/contract_index.json`
- `docs/_generated/traceability/trace.json`
- `docs/_generated/traceability/clause_trace_matrix.md`
- `docs/_generated/traceability/contract_coverage_summary.md`
- `docs/_generated/traceability/verify_coverage_summary.md`
