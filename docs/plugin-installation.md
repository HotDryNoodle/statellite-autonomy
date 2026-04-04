# Codex Project Setup

本仓库采用官方默认的 Codex 项目级发现方式，而不是本地 plugin bundle。

- 工程仓库根目录：`contracts/`、`docs/`、`skills/`、`.agents/`、`tools/`
- harness 控制面：`harness/`
- product 产品面：`product/src/`、`product/tests/`

真正提供给 Codex 发现的是：

- 根目录 `AGENTS.md`
- 项目 `.agents/skills`

`.agents/skills` 是项目级发现路径，实际维护内容仍放在根 `skills/`。
`nav-toolchain` 和 `traceability` 两个工具仍然保留在仓库中，但只作为 repo-local CLI 使用，不通过 plugin 或项目级配置暴露给 Codex。
这样做是为了把默认入口收敛回官方项目模型，并避免额外集成链路直接影响 Codex 启动。

## 让 Codex 感知并加载

推荐方式：

1. 进入仓库根目录。
2. 确认存在根 `AGENTS.md`。
3. 确认 `.agents/skills` 可解析到根 `skills/`。
4. 启动 Codex 并在该仓库工作。

启动后确认：

- 项目根 `AGENTS.md` 被读取
- `.agents/skills` 下的 skills 可被发现

## CLI 使用策略

仓库内仍保留两个 repo-local CLI：

- `tools/nav-toolchain-cli/toolchain_cli.py`
- `tools/traceability-cli/traceability_cli.py`

默认工作流是手动运行仓库内 CLI，而不是让 Codex 在启动时自动发现任何额外集成。

说明：

- 这不是系统全局配置，不需要改 `~/.codex/config.toml`
- 本仓库当前不提供项目级 `.codex/config.toml`
- 本仓库当前不提供 `.mcp.json` 或 `.mcp.template.json`
- 需要工具链能力时，直接在仓库里手动运行对应 CLI

## 当前 CLI 入口

仓库内保留的 CLI 入口如下，供人工或脚本显式调用：

- `python3 tools/nav-toolchain-cli/toolchain_cli.py`
- `python3 tools/traceability-cli/traceability_cli.py`

推荐手动入口：

```bash
python3 tools/nav-toolchain-cli/toolchain_cli.py status
python3 tools/nav-toolchain-cli/toolchain_cli.py build --reconfigure
python3 tools/nav-toolchain-cli/toolchain_cli.py test --no-rebuild
python3 tools/nav-toolchain-cli/toolchain_cli.py traceability --yes
python3 tools/nav-toolchain-cli/toolchain_cli.py benchmark --report-path eval/reports/time_benchmark_report.json --yes
./scripts/nav-toolchain build --reconfigure
UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-cli python tools/nav-toolchain-cli/toolchain_cli.py status
python3 tools/traceability-cli/traceability_cli.py status
python3 tools/traceability-cli/traceability_cli.py query-clause TimeSys_4_4_4
```

## 维护约定

- 新增 skill 时，直接放到仓库根的 `skills/` 下，并保持 `.agents/skills` 可发现。
- 新增 repo-local 工具时，优先做成 plain CLI，并在仓库内手动验证，不进入项目默认 Codex 配置链路。
- 若未来确实需要项目级 Codex 覆盖配置，再单独引入 `.codex/config.toml`。
