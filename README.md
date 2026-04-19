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

## Collaboration Entry

Start from `AGENTS.md`. That file defines the repository workflow, required artifacts, and approved tool entrypoints.

This repository follows the default Codex project layout: root `AGENTS.md`, project `.agents/skills`, and repo-local CLI entrypoints. Repo-local engineering tools remain plain CLIs and are not exposed through project Codex config.
