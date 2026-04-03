# Build Entrypoints

- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py build`
- `./scripts/nav-toolchain build`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp python tools/nav-toolchain-mcp/toolchain_mcp.py build`
- `python3 tools/nav-toolchain-mcp/toolchain_mcp.py build --cross-file <path> --native-file <path>`
- `meson setup builddir`
- `meson compile -C builddir`
- `scripts/run_uv_mcp.sh tools/nav-toolchain-mcp tools/nav-toolchain-mcp/server.py`

支持项：

- `--build-dir`：指定构建目录
- `--cross-file`：Meson 交叉编译描述
- `--native-file`：本机工具链覆盖
- `--meson-option key=value`：透传 `-Dkey=value`
- `--reconfigure`：强制重新配置

说明：

- 根目录 Meson 入口保持不变，但真实产品源码位于 `product/src/`。
