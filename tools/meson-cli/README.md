# Meson CLI

本目录提供基于 Meson 的 CLI-first 工程入口。

当前仓库采用根目录治理层 + `harness/` + `product/` 双树结构：

- Meson 根入口保持在仓库根目录
- 真实产品源码位于 `product/src/`
- 真实测试与 benchmark runner 位于 `product/tests/`

- `build`
- `test`
- `eval`
- `benchmark` (time-domain compatibility alias)
- `traceability`
- `status`
- `knowledge` for CLI-only expert-system Obsidian access
- `pyproject.toml`：`uv` 运行环境
- 支持 `--cross-file` / `--native-file` / `--build-dir` / `--dry-run`

执行方式：

```bash
python3 tools/meson-cli/meson_cli.py status
```

推荐的手动 CLI 入口：

```bash
./scripts/meson-cli build --reconfigure
./scripts/meson-cli test --no-rebuild
./scripts/meson-cli traceability --yes
./scripts/meson-cli eval --domain time --report-path eval/reports/time_benchmark_report.json --yes
./scripts/meson-cli benchmark --report-path eval/reports/time_benchmark_report.json --yes
./scripts/meson-cli knowledge status --agent pppar_expert_agent
```

`knowledge` 子命令只允许通过 Obsidian CLI 访问 `expert-system` vault；不得直接读取或写入 vault 文档。

如果需要直接用 `uv` 调试：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/meson-cli \
  python tools/meson-cli/meson_cli.py status
```
