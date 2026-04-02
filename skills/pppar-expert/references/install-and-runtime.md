# Install And Runtime

## Standalone install

Preferred command:

```bash
./.venv/bin/python .codex/skills/pride-pppar-expert/scripts/install_pride_runtime.py \
  --prefix tools/PRIDE \
  --tarball vendor/PRIDE-PPPAR-master.tar.gz
```

This produces:
- root source tree at `src/`, `scripts/`, `doc/`, `table/`
- `tools/PRIDE/src/` source tree
- `tools/PRIDE/src/bin/` compiled PRIDE executables
- `tools/PRIDE/runtime/pdp3`
- `tools/PRIDE/env.sh`

## Runtime environment

Preferred activation:

```bash
source tools/PRIDE/env.sh
```

Expected variables:
- `PPP_FLOAT_PRIDE_EXECUTABLE`
- `PPP_FLOAT_PRIDE_TABLE_DIR`
- `PPP_FLOAT_PRIDE_BIN_DIR`
- `PPP_FLOAT_PRIDE_SCRIPT_DIR`

## Notes

- The install script is intentionally offline and uses the vendored tarball.
- The install flow does not patch `leoatx.py`.
- `igs20_2388.atx` is synthesized from the latest available `igs20_*.atx` if absent, because some clock headers expect that file name.
- Use the project root `src/`, `scripts/`, `doc/`, and `table/` as the primary evidence base; use `tools/PRIDE/` as the operational runtime prefix.
