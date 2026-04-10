# Test Entrypoints

- `python3 tools/nav-toolchain-cli/toolchain_cli.py test`
- `./scripts/nav-toolchain test`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-cli python tools/nav-toolchain-cli/toolchain_cli.py test`
- `python3 tools/nav-toolchain-cli/toolchain_cli.py test --test-name time`
- `meson test -C builddir --print-errorlogs`

支持项：

- `--build-dir`
- `--test-name`
- `--no-rebuild`
- `--cross-file`
- `--native-file`
- `--dry-run`

说明：

- 真实测试源码位于 `product/tests/`，但命令入口保持不变。