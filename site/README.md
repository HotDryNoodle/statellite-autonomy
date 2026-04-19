# 项目静态站点

本目录生成只读静态站点，聚合权威资产（合同、架构蓝图、仪表盘、Harness 任务摘要等）。站点为**派生视图**，不修改任何权威源文件。

## 内容来源

| 站点栏目 | 来源 | 说明 |
|---|---|---|
| 首页 | `README.md` + `docs/_generated/project_status.json` | 若存在 `project_status.json` 则追加「项目快照」块。 |
| 项目仪表盘 | `docs/_generated/project_dashboard.md` | 注入「近期任务（最近 3 条）」表。 |
| 产品合同 | `contracts/*.md` | 每份合同独立成页。 |
| 架构蓝图 | `architecture/blueprints/**/*.md` + `*.puml` | 每页内联嵌入 `.puml` 渲染的 SVG；非 `active` 的决策蓝图在侧栏标注状态。 |
| Harness 运行时 | `harness/runtime/tasks/<id>/task_state.json` + `events.jsonl` | 仅摘要，不展开 artifacts。 |
| 追溯与合规 | `docs/_generated/traceability/*.md` + `compliance_status.json` | 生成证据。 |
| 评测 | `eval/domains/README.md` 与各域 `README.md` | |
| 协作指南 / 工具链 | `docs/guides/`、`docs/toolchain/` | |

`governance/records/**` **不**作为独立页面上架；相关信息仅通过仪表盘汇总呈现。

## 本地构建

```bash
uv sync --group site --no-default-groups

uv run --group site --no-default-groups statellite-site build
uv run --group site --no-default-groups statellite-site start
```

停止后台预览服务：

```bash
uv run --group site --no-default-groups statellite-site stop
```

### 实时预览

```bash
uv run --group site --no-default-groups statellite-site serve
```

### 预览最近一次构建的静态产物

在已执行 `statellite-site build` 且存在 `site/_generated/index.html` 时：

```bash
uv run --group site --no-default-groups statellite-site open
```

默认在 `127.0.0.1:8765` 提供静态文件并打开浏览器；仅打印 URL 时用 `statellite-site open --no-browser`。

### PlantUML server 选择

```bash
# 显式指定已有 server
PLANTUML_SERVER_URL=http://127.0.0.1:8080 \
    uv run --group site --no-default-groups statellite-site build
```

若未提供 `PLANTUML_SERVER_URL`，`statellite-site build` 与 `statellite-plantuml` 会先尝试从现有 `podman` / `docker` 的 `plantuml-server` 容器推断 URL；若仍找不到，再临时拉起容器，成功或失败后都自动清理。

## CI / GitHub Pages

`.github/workflows/pages.yml` 在推送到 `main` 时：

1. 启动 job 级 `plantuml-server` service container，并执行 `uv sync --group site --no-default-groups`。
2. 刷新 traceability / compliance / dashboard 产物。
3. 以 `PLANTUML_SERVER_URL=http://127.0.0.1:8080` 执行 `uv run --group site --no-default-groups statellite-site build`。
4. 通过 `actions/upload-pages-artifact` + `actions/deploy-pages` 发布 `site/_generated`。

在仓库 **Settings → Pages** 中将 **Build and deployment** 设为 **GitHub Actions**。

## 扩展站点

- 新增顶层栏目：在 `tools/site-cli/site_cli/build_site.py::main` 中增加 `stage_*` 并返回 `NavNode`。
- PlantUML：`tools/plantuml-cli/plantuml_cli/cli.py` 只提供 server-based `render` / `lint`。
- 导航由构建脚本写入 `site/_staging/mkdocs.generated.yml`；`site/mkdocs.yml` 只作为模板保留。
