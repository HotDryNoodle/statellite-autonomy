# Nav Tool

本目录提供基于 Meson 的工程入口与 stdio MCP server：

- `build`
- `test`
- `benchmark`
- `traceability`
- `status`
- `server.py`：本地 stdio MCP server
- `pyproject.toml`：`uv` 运行环境
- 支持 `--cross-file` / `--native-file` / `--build-dir`

执行方式：

```bash
python3 tools/nav-toolchain-mcp/toolchain_mcp.py status
```

推荐的手动 CLI 入口：

```bash
./scripts/nav-toolchain build --reconfigure
./scripts/nav-toolchain test --no-rebuild
./scripts/nav-toolchain traceability
./scripts/nav-toolchain benchmark --report-path eval/reports/time_benchmark_report.json
```

如果需要直接用 `uv` 调试：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp \
  python tools/nav-toolchain-mcp/toolchain_mcp.py status
```

或通过 `uv` MCP 包装脚本：

```bash
scripts/run_uv_mcp.sh tools/nav-toolchain-mcp tools/nav-toolchain-mcp/server.py
```
