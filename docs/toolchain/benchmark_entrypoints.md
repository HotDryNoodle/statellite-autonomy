# Benchmark Entrypoints

- `python3 tools/nav-toolchain-cli/toolchain_cli.py benchmark --yes`
- `./scripts/nav-toolchain benchmark`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-cli python tools/nav-toolchain-cli/toolchain_cli.py benchmark --yes`
- `python3 tools/nav-toolchain-cli/toolchain_cli.py benchmark --report-path eval/reports/custom.json`

当前会运行真实 benchmark 场景并输出 JSON 摘要；默认报告文件为 `eval/reports/time_benchmark_report.json`。
