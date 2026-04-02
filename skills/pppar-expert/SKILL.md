---
name: pride-pppar-expert
description: Use when the task involves installing, running, diagnosing, or explaining PRIDE-PPPAR for PPP-AR and LEO precise orbit workflows. Prefer the standalone PRIDE project at ~/projects/PRIDE-PPPAR, using its root source tree as implementation evidence and tools/PRIDE as the installed runtime.
version: 1.0.0
depends_on:
  - system-architect
tools:
  - /home/hotdry/projects/PRIDE-PPPAR
triggers:
  - ppp
  - pride-pppar
  - leo-orbit
---

# PRIDE-PPPAR Expert

Use this skill for three task types:
- Install or repair the standalone PRIDE-PPPAR runtime.
- Run or diagnose PRIDE-based PPP-AR or LEO orbit workflows.
- Answer algorithm or implementation questions using PRIDE source code and local manuals.

## Project Authority

Treat `~/projects/PRIDE-PPPAR` as the authoritative standalone PRIDE project.

- Use the project root for source, manuals, tables, and upstream-style engineering structure:
  - `src/`
  - `scripts/`
  - `doc/`
  - `table/`
- Use `tools/PRIDE/` only as the installed runtime prefix consumed by wrappers, tests, and env files.
- The global entry `~/.codex/skills/pride-pppar-expert` is only a symlinked discovery path. The maintained skill content lives under `~/projects/PRIDE-PPPAR/.codex/skills/pride-pppar-expert`.

## Ground Truth

Use local evidence in this order:
1. `~/projects/PRIDE-PPPAR/src/`, `~/projects/PRIDE-PPPAR/scripts/`, `~/projects/PRIDE-PPPAR/table/`
2. `~/projects/PRIDE-PPPAR/doc/PRIDE PPP-AR v3.2 manual-ch.pdf` and `~/projects/PRIDE-PPPAR/doc/PRIDE PPP-AR v3.2 manual-en.pdf`
3. Installed-runtime evidence under `~/projects/PRIDE-PPPAR/tools/PRIDE/`
4. Local validation outputs and project integration tests that wrap PRIDE

Do not rely on online PRIDE material unless the user explicitly asks for it.

## Runtime Workflow

1. Check runtime health first with `skills/pppar-expert/scripts/check_pride_runtime.py` or the authoritative copy under `~/projects/PRIDE-PPPAR/.codex/skills/pride-pppar-expert/scripts/check_pride_runtime.py`.
2. If the runtime is missing or broken, install with `skills/pppar-expert/scripts/install_pride_runtime.py` or the authoritative copy under `~/projects/PRIDE-PPPAR/.codex/skills/pride-pppar-expert/scripts/install_pride_runtime.py`.
3. Prefer the standalone runtime environment file `tools/PRIDE/env.sh`.
4. When diagnosing failures, map them to the actual `pdp3.sh` stages:
   - `CheckExecutables`
   - `PrepareTables`
   - `PrepareProducts`
   - `ProcessSingleSession`
5. Treat missing GNSS products, ERP files, or attitude products as data availability problems, not install problems.

## Path Rules

- If the current working tree is `~/projects/PRIDE-PPPAR`, use its root source tree and its `tools/PRIDE` runtime directly.
- If the current working tree is another project, prefer the standalone runtime at `~/projects/PRIDE-PPPAR/tools/PRIDE`.
- Only fall back to a repo-local `tools/PRIDE` when a task explicitly targets another checked-out PRIDE installation.

## Algorithm Questions

When explaining PPP-AR behavior:
- Identify the relevant PRIDE module and routine first.
- State the mathematical object being computed.
- Describe the implementation in accurate mathematical language.
- Tie the explanation back to the runtime chain and output artifacts.

Minimum answer shape:
- mathematical object or constraint
- source routine(s) and file path
- where it enters the runtime chain
- where it appears in outputs or diagnostics

When this local copy differs from the standalone PRIDE project, always defer to `~/projects/PRIDE-PPPAR`.

Use these reference files as needed:
- `references/install-and-runtime.md`
- `references/operations-and-errors.md`
- `references/architecture-and-algorithms.md`
- `references/manual-index.md`
