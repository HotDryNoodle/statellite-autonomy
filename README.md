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

## Quick Start

```bash
python3 tools/nav-toolchain-cli/toolchain_cli.py build --reconfigure
python3 tools/nav-toolchain-cli/toolchain_cli.py test --no-rebuild
python3 tools/nav-toolchain-cli/toolchain_cli.py traceability --yes
python3 tools/nav-toolchain-cli/toolchain_cli.py eval --domain time --report-path eval/reports/time_benchmark_report.json --yes
python3 tools/traceability-cli/traceability_cli.py status
python3 scripts/check_quality.py --report-json
```

## Project Site

`site/` 生成面向仓库内开发者的只读静态项目视图（合同、架构蓝图、仪表盘、Harness 任务摘要等）；侧栏与站点元数据以中文为主。站点为派生视图，不修改任何权威资产。

```bash
pip install -r site/requirements.txt
sudo dnf install -y plantuml graphviz   # or: apt-get install plantuml graphviz

python3 site/scripts/build_site.py --build
python3 -m http.server -d site/build/site 8000
```

If `plantuml` is not installed locally, the bundled podman image works too:

```bash
podman run -d --rm --name plantuml-server -p 8080:8080 \
    docker.io/plantuml/plantuml-server:jetty
PLANTUML_MODE=server PLANTUML_SERVER_URL=http://localhost:8080 \
    python3 site/scripts/build_site.py --build
```

`python3 site/scripts/build_site.py --serve` gives a live-reload preview. CI publishes the same output to GitHub Pages via `.github/workflows/pages.yml`. See `site/README.md` for the full design.

## Collaboration Entry

Start from `AGENTS.md`. That file defines the repository workflow, required artifacts, and approved tool entrypoints.

This repository follows the default Codex project layout: root `AGENTS.md`, project `.agents/skills`, and repo-local CLI entrypoints. Repo-local engineering tools remain plain CLIs and are not exposed through project Codex config.
