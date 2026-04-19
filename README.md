# statellite-autonomy-plugin

Contract-driven satellite autonomy engineering workspace with a harness control plane, a product engineering tree, local skills, traceability tooling, and Meson/GTest-based validation.

## Repository Layout

- `contracts/`: contract source of truth
- `architecture/blueprints/`: canonical architecture freezes and diagrams
- `governance/policies/`: process and orchestration rules
- `governance/records/`: synchronized working state and long-term governance records
- `docs/`: guides, indexes, and reading material only
- `skills/`: maintained agent roles and workflows
- `.agents/skills`: Codex project-level discovery path for the maintained `skills/` inventory
- `harness/`: orchestration artifacts, workflow eval fixtures, schemas, templates, and runtime helpers
- `product/`: implementation and verification trees
- `tools/`: local toolchain and traceability CLIs
- `docs/_generated/traceability/`: generated, non-tracked evidence outputs
- `site/_generated/`: generated static site output

## Quick Start

```bash
python3 tools/meson-cli/meson_cli.py build --reconfigure
python3 tools/meson-cli/meson_cli.py test --no-rebuild
python3 tools/meson-cli/meson_cli.py traceability --yes
python3 tools/meson-cli/meson_cli.py eval --domain time --report-path eval/reports/time_benchmark_report.json --yes
python3 tools/traceability-cli/traceability_cli.py status
python3 scripts/check_quality.py --report-json
```

## Project Site

`site/` 生成面向仓库内开发者的只读静态项目视图（合同、架构蓝图、仪表盘、Harness 任务摘要等）；侧栏与站点元数据以中文为主。站点为派生视图，不修改任何权威资产。

```bash
uv sync --group site --no-default-groups

uv run --group site --no-default-groups site-cli build
uv run --group site --no-default-groups site-cli start
# 停止后台预览服务
uv run --group site --no-default-groups site-cli stop
```

PlantUML rendering is server-only. You can point at an existing server explicitly:

```bash
PLANTUML_SERVER_URL=http://127.0.0.1:8080 \
    uv run --group site --no-default-groups site-cli build
```

If no `PLANTUML_SERVER_URL` is provided, `plantuml-cli` / `site-cli build` first try to discover a running `plantuml-server` container and only then start a temporary local container. `uv run --group site --no-default-groups site-cli serve` keeps the live-reload preview in the foreground; `site-cli open` serves the already built tree in the foreground; `site-cli start` / `stop` manage a background preview server for `site/_generated`. PlantUML lint is available via `uv run --group plantuml --no-default-groups plantuml-cli lint --input <file.puml>`. CI publishes `site/_generated` to GitHub Pages via `.github/workflows/pages.yml`. See `site/README.md` for the full design.

## Collaboration Entry

Start from `AGENTS.md`. That file defines the repository workflow, required artifacts, and approved tool entrypoints.

This repository follows the default Codex project layout: root `AGENTS.md`, project `.agents/skills`, and repo-local CLI entrypoints. Repo-local engineering tools remain plain CLIs and are not exposed through project Codex config.
