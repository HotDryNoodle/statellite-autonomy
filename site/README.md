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
pip install -r site/requirements.txt

# 方案 A：本机已安装 plantuml（推荐）
sudo dnf install -y plantuml graphviz   # Fedora
# 或：sudo apt-get install -y plantuml graphviz   # Debian/Ubuntu

python3 site/scripts/build_site.py --build
python3 -m http.server -d site/build/site 8000
```

### 方案 B：使用 podman 的 plantuml-server

若本机未安装 `plantuml`，可用 podman 镜像作为渲染后端：

```bash
podman run -d --rm --name plantuml-server -p 8080:8080 \
    docker.io/plantuml/plantuml-server:jetty
```

```bash
PLANTUML_MODE=server PLANTUML_SERVER_URL=http://localhost:8080 \
    python3 site/scripts/build_site.py --build
```

### 实时预览

```bash
python3 site/scripts/build_site.py --serve
```

## CI / GitHub Pages

`.github/workflows/pages.yml` 在推送到 `main` 时：

1. 通过 apt 安装 `plantuml`、`graphviz`，并安装 `site/requirements.txt`。
2. 刷新 traceability / compliance / dashboard 产物。
3. 以 `PLANTUML_MODE=cli` 执行 `python3 site/scripts/build_site.py --build`。
4. 通过 `actions/upload-pages-artifact` + `actions/deploy-pages` 发布 `site/build/site`。

在仓库 **Settings → Pages** 中将 **Build and deployment** 设为 **GitHub Actions**。

## 扩展站点

- 新增顶层栏目：在 `site/scripts/build_site.py::main` 中增加 `stage_*` 并返回 `NavNode`。
- PlantUML：`site/scripts/render_plantuml.py` 已支持 `cli`、`server`、`auto`。
- 导航由构建脚本重写 `site/mkdocs.yml` 中 `# --- AUTO_NAV_BEGIN ---` 与 `# --- AUTO_NAV_END ---` 之间的内容；手工编辑时请保留这两个标记。
