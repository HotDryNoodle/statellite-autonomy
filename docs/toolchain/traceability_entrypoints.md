# Traceability Entrypoints

- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py traceability`
- `./scripts/nav-toolchain traceability`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp python tools/nav-toolchain-mcp/toolchain_mcp.py traceability`
- `python3 tools/traceability-mcp/traceability_cli.py status`
- `python3 tools/traceability-mcp/traceability_cli.py query-clause TimeSys_4_4_4`
- `scripts/run_uv_mcp.sh tools/traceability-mcp tools/traceability-mcp/server.py`

生成产物：

- `docs/_generated/traceability/contract_index.json`
- `docs/_generated/traceability/trace.json`
- `docs/_generated/traceability/clause_trace_matrix.md`
- `docs/_generated/traceability/contract_coverage_summary.md`
- `docs/_generated/traceability/verify_coverage_summary.md`

扫描范围：

- `contracts/*.contract.md`
- `product/src/**/*.h`
- `product/tests/**/*.cpp`
