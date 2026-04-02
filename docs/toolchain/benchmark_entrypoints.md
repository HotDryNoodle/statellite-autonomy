# Benchmark Entrypoints

- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark`
- `./scripts/nav-toolchain benchmark`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp python tools/nav-toolchain-mcp/toolchain_mcp.py benchmark`
- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark --report-path eval/reports/custom.json`

当前仅输出占位报告路径，不运行真实 benchmark。
