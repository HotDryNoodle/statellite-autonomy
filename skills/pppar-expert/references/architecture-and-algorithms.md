# Architecture And Algorithms

## Runtime topology

- `scripts/pdp3.sh`: top-level orchestration and product preparation.
- `src/orbit/`: precise orbit interpolation and orbit-file generation.
- `src/tedit/`: observation editing, cycle-slip checks, receiver clock jump checks.
- `src/lsq/`: PPP parameter estimation and state update.
- `src/arsig/`: ambiguity fixing and ambiguity validation.
- `src/lib/`: shared observation models, atmospheric models, interpolation, attitude, and product readers.

Runtime note:
- `tools/PRIDE/` is the installed runtime prefix used by wrappers.
- Source-level explanations should cite the project root tree first.

## Key algorithm entry points

- Precise orbit interpolation: `orbit/sp3orb.f90`, `orbit/lagrange_interp_sp3.f90`
- ERP and clock handling: `lib/read_igserp.f90`, `lib/read_satclk.f90`
- Troposphere: `lib/troposphere_delay.f90`, `lib/troposphere_map.f90`, `lib/vmf1_*.f90`, `lib/vmf3_*.f90`
- Phase windup: `lib/phase_windup.f90`, `lib/lphase_windup.f90`
- LEO attitude and quaternion handling: `lib/leoqua2mat.f90`, `lib/quater2mat.f90`, `lsq/qzsmod.f90`
- Integer ambiguity logic: `lib/lambda.f90`, `arsig/*.f90`, `lsq/lsq_add_ambcon.f90`

## Project Notes

- Filtering and recursive-estimation note: `doc/pride-pppar-filtering.md`
- State-vector and observation decomposition: `doc/pride-pppar-state-vector-and-observation.md`
- Ambiguity float-to-AR chain: `doc/pride-pppar-ambiguity-chain.md`
- ARSIG search and validation: `doc/pride-pppar-arsig-search-and-validation.md`

## Expected explanation pattern

For algorithm questions, answer in this order:
1. Objective function or state/observation quantity.
2. Relevant correction terms and constraints.
3. Source routine(s) implementing the computation.
4. Where the result appears in PRIDE outputs.
