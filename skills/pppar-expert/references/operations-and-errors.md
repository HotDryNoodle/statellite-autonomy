# Operations And Errors

## `pdp3.sh` stage map

- `CheckExecutables`: missing `arsig`, `lsq`, `sp3orb`, `spp`, `tedit`, `otl`, `mhm`, `get_ctrl`, shell helpers, or Python helpers.
- `PrepareTables`: missing `table/` assets such as `leap.sec`, `sat_parameters`, ANTEX files, or ocean loading tables.
- `PrepareProducts`: missing orbit, clock, ERP, bias, quaternion, or ionosphere products.
- `ProcessSingleSession`: downstream processing failure after inputs are staged.

## Typical diagnostics

### Install problems
- `pdp3` not found: runtime not installed or env not loaded.
- `get_ctrl` or `lsq` not found: build incomplete or `PPP_FLOAT_PRIDE_BIN_DIR` unset.

### Data problems
- ERP download failure: runtime is installed, but required ERP product is absent locally.
- Missing `kin_*` or `res_*`: upstream processing failed earlier; inspect `run_log.stderr` and stage mapping first.
- Illegal RINEX naming warnings: often non-fatal, but confirm content and observation span.

## Diagnostic command

```bash
./.venv/bin/python .codex/skills/pride-pppar-expert/scripts/check_pride_runtime.py
```
