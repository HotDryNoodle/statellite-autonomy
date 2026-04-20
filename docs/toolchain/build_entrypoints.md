# Build Entrypoints

- `python3 tools/meson-cli/meson_cli.py build`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/meson-cli python tools/meson-cli/meson_cli.py build`
- `python3 tools/meson-cli/meson_cli.py build --cross-file <path> --native-file <path>`
- `meson setup builddir`
- `meson compile -C builddir`

支持项：

- `--build-dir`：指定构建目录
- `--cross-file`：Meson 交叉编译描述
- `--native-file`：本机工具链覆盖
- `--meson-option key=value`：透传 `-Dkey=value`
- `--reconfigure`：强制重新配置
- `--dry-run`：预览将执行的命令与写入目标

说明：

- 根目录 Meson 入口保持不变，但真实产品源码位于 `product/src/`。
- `scripts/meson-cli` 已移除，避免把兼容 shim 误读成正式工具本体。
