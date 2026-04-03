# statellite-autonomy-plugin

Contract-driven satellite autonomy engineering workspace with a harness control plane, a product engineering tree, local skills, traceability tooling, and Meson/GTest-based validation.

## Repository Layout

- `contracts/`: contract source of truth
- `docs/`: architecture, memory, toolchain, and governance docs
- `skills/`: repo-local agent roles and workflows
- `harness/`: orchestration artifacts, schemas, templates, and runtime helpers
- `product/`: implementation and verification trees
- `tools/`: local toolchain and traceability CLIs / MCP servers
- `docs/traceability/`: governance docs
- `docs/_generated/traceability/`: generated evidence

## Quick Start

```bash
python3 tools/nav-toolchain-mcp/toolchain_mcp.py build --reconfigure
python3 tools/nav-toolchain-mcp/toolchain_mcp.py test --no-rebuild
python3 tools/nav-toolchain-mcp/toolchain_mcp.py traceability
python3 tools/nav-toolchain-mcp/toolchain_mcp.py benchmark --report-path eval/reports/time_benchmark_report.json
python3 tools/traceability-mcp/traceability_cli.py status
python3 scripts/check_quality.py --report-json
```

## Collaboration Entry

Start from `AGENTS.md`. That file defines the repository workflow, required artifacts, and approved tool entrypoints.

This repository keeps Codex plugin startup `skills`-only by default. Local MCP servers remain manual tools and are not auto-registered on session start.
