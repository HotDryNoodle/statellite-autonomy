# Traceability Entrypoints

- `python3 tools/nav-toolchain-cli/toolchain_cli.py traceability --yes`
- `./scripts/nav-toolchain traceability`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-cli python tools/nav-toolchain-cli/toolchain_cli.py traceability --yes`
- `python3 tools/traceability-cli/traceability_cli.py status`
- `python3 tools/traceability-cli/traceability_cli.py query-clause TimeSys_4_4_4`

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
