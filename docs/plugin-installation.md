# Plugin Installation

本仓库现在采用“双层结构”：

- 工程仓库根目录：`contracts/`、`docs/`、`skills/`、`tools/`、`plugins/`
- harness 控制面：`harness/`
- product 产品面：`product/src/`、`product/tests/`
- 干净 plugin bundle：`plugins/statellite-autonomy-plugin/`

真正提供给 Codex 加载的是：

- `plugins/statellite-autonomy-plugin/.codex-plugin/plugin.json`
- `plugins/statellite-autonomy-plugin/skills`

默认情况下，这个 plugin 只向 Codex 暴露 `skills/`。
`nav-toolchain` 和 `traceability` 两个 MCP 仍然保留在仓库中，但不进入 plugin 或项目默认自动注册链路。
这样做是为了避免本地 `uv`/stdio 启动链路异常时直接拖垮 Codex 启动。

## 让 Codex 感知并加载

推荐把 `plugins/statellite-autonomy-plugin/` 作为 home-local plugin 注册：

1. 在本机创建插件入口：

```bash
bash scripts/install_local_plugin.sh
```

2. 重启 Codex。

3. 启动后确认：

- plugin 已出现在本地插件列表
- 本仓库下的 `skills/` 可被发现

## MCP 使用策略

仓库内仍保留两个 repo-local MCP：

- `tools/nav-toolchain-mcp/server.py`
- `tools/traceability-mcp/server.py`

默认工作流是手动运行仓库内 CLI，而不是让 Codex 在启动时自动发现它们。

推荐分两步使用：

1. 保持 plugin 仅加载 skills，确认 Codex 启动稳定。
2. 需要工具链能力时，直接在仓库里手动运行对应 CLI。

说明：

- 这不是系统全局配置，不需要改 `~/.codex/config.toml`
- 这也不是项目自动注册，不会在进入仓库时自动拉起 MCP
- Codex 当前不支持会话内热加载项目 MCP，因此默认方案直接避开自动注册

## 当前 MCP 入口

仓库内保留的 MCP 入口如下：

- server name: `nav-toolchain`
- wrapper: `scripts/run_uv_mcp.sh`
- server entry: `tools/nav-toolchain-mcp/server.py`

- server name: `traceability-cli`
- wrapper: `scripts/run_uv_mcp.sh`
- server entry: `tools/traceability-mcp/server.py`

暴露的工具有：

- `nav_toolchain_status`
- `nav_toolchain_build`
- `nav_toolchain_test`
- `nav_toolchain_traceability`
- `nav_toolchain_benchmark`
- `traceability_generate`
- `traceability_query_clause`
- `traceability_status`

推荐手动入口：

```bash
python3 tools/nav-toolchain-mcp/toolchain_mcp.py status
python3 tools/nav-toolchain-mcp/toolchain_mcp.py build --reconfigure
python3 tools/nav-toolchain-mcp/toolchain_mcp.py test --no-rebuild
./scripts/nav-toolchain build --reconfigure
UV_CACHE_DIR=/tmp/uv-cache uv run --project tools/nav-toolchain-mcp python tools/nav-toolchain-mcp/toolchain_mcp.py status
python3 tools/traceability-mcp/traceability_cli.py status
python3 tools/traceability-mcp/traceability_cli.py query-clause TimeSys_4_4_4
```

## 维护约定

- 新增 skill 时，直接放到仓库根的 `skills/` 下，bundle 会通过 symlink 暴露。
- 新增 MCP server 时，先在仓库内实现并手动验证，不进入默认 plugin 安装链路。
- 若要增加 UI 元数据，更新 `plugins/statellite-autonomy-plugin/.codex-plugin/plugin.json`。
