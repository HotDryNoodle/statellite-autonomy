# Test Entrypoints

- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py test`
- `./scripts/nav-toolchain test`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp python tools/nav-toolchain-mcp/toolchain_mcp.py test`
- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py test --test-name time`
- `meson test -C builddir --print-errorlogs`

支持项：

- `--build-dir`
- `--test-name`
- `--no-rebuild`
- `--cross-file`
- `--native-file`
