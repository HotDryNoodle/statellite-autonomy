# Nav Tool

本目录提供基于 Meson 的工程入口与 stdio MCP server。

当前仓库采用根目录治理层 + `harness/` + `product/` 双树结构：

- Meson 根入口保持在仓库根目录
- 真实产品源码位于 `product/src/`
- 真实测试与 benchmark runner 位于 `product/tests/`

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
