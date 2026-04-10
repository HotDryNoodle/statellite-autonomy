# Nav Tool

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
python3 tools/nav-toolchain-cli/toolchain_cli.py status
```

推荐的手动 CLI 入口：

```bash
./scripts/nav-toolchain build --reconfigure
./scripts/nav-toolchain test --no-rebuild
./scripts/nav-toolchain traceability --yes
./scripts/nav-toolchain eval --domain time --report-path eval/reports/time_benchmark_report.json --yes
./scripts/nav-toolchain benchmark --report-path eval/reports/time_benchmark_report.json --yes
./scripts/nav-toolchain knowledge status --agent pppar_expert_agent
```

`knowledge` 子命令只允许通过 Obsidian CLI 访问 `expert-system` vault；不得直接读取或写入 vault 文档。

如果需要直接用 `uv` 调试：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-cli \
  python tools/nav-toolchain-cli/toolchain_cli.py status
```
