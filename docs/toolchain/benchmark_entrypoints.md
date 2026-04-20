# Benchmark Entrypoints

- `python3 tools/meson-cli/meson_cli.py eval --domain time --report-path eval/reports/time_benchmark_report.json`
- `python3 tools/meson-cli/meson_cli.py benchmark --yes`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/meson-cli python tools/meson-cli/meson_cli.py benchmark --yes`
- `python3 tools/meson-cli/meson_cli.py benchmark --report-path eval/reports/custom.json`

`eval` 是统一入口，`benchmark` 仅保留为 time domain 兼容别名。time domain 当前会运行真实 benchmark 场景并输出标准化 Eval report；默认报告文件仍为 `eval/reports/time_benchmark_report.json`。
