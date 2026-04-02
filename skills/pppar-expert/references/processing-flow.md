# Processing Flow

## PRIDE PPP-AR Main Workflow

PRIDE PPP-AR does not solve a full independent solution at each epoch and then pass only the epoch-wise result forward. The main estimator instead works in a sequential scan over epochs while accumulating a session-level normal equation, with time-update constraints applied to dynamic parameters between epochs.

High-level `pdp3` processing chain:

```text
RINEX obs/nav
  -> PrepareTables
  -> PrepareRinexNav
  -> PrepareProducts
  -> spp for initial coordinates/trajectory
  -> tedit for observation screening and arc editing
  -> lsq float solution
  -> redig residual-based cleaning / ambiguity break insertion
  -> lsq
  -> redig
  -> ... iterate until stable
  -> optional arsig for ambiguity fixing
  -> final lsq with ambiguity constraints
  -> output kin/pos, res, amb, stt, rck, etc.
```

Relevant driver locations:
- `scripts/pdp3.sh`
- `src/lsq/lsq.f90`
- `src/lsq/lsq_add_obs.f90`
- `src/lsq/lsq_process.f90`

## What Each Stage Does

### 1. Pre-run preparation

`PrepareTables`, `PrepareRinexNav`, and `PrepareProducts` populate the working directory with the table files, navigation files, precise orbit/clock/ERP products, attitude products, OSB products, and optional LEO products required by the run.

### 2. Initial position / trajectory

`ComputeInitialPos()` runs `spp` first. This provides an initial coordinate or trajectory estimate for later editing and estimation. In LEO mode, if `pso_*` exists, PRIDE can convert PSO to a `kin_*` prior trajectory and use it instead of raw SPP output.

### 3. Observation pre-editing

`tedit` performs observation-domain preprocessing before the main estimator:
- time matching against the requested processing grid
- basic quality control
- cycle-slip and short-arc detection
- generation of edit / log information used by `lsq`

The `Time window` / `-twnd` setting is only a time-matching tolerance for non-standard or high-rate observation epochs. It is not a batch-estimation window.

### 4. Float estimation with `lsq`

The core estimator in `lsq` runs epoch by epoch in time order:
- read one epoch of observations
- update or create ambiguity parameters as needed
- build the observation equations for that epoch
- add those equations into the session-level normal matrix
- apply time-update constraints for process parameters
- continue to the next epoch

After all epochs are scanned, PRIDE:
- applies any remaining ambiguity constraints
- removes inactive process/state parameters
- solves the accumulated normal equation once
- recovers parameter series and residuals

This is best described as:

`sequential epoch scan + process-model constraints + session-level least-squares normal equation`

It is therefore not:
- a pure epoch-wise independent LSQ
- a standard real-time Kalman filter that outputs the final state at every epoch
- a short sliding-window batch processor

### 5. Residual-driven re-editing

After one float solution, `redig` reads the residual file `res_*` and:
- removes newly detected outliers
- inserts new ambiguity boundaries when residual behavior implies a slip or break

Then `pdp3` reruns `lsq`. This `lsq -> redig -> lsq -> redig` loop continues until the residual editing stabilizes.

### 6. Ambiguity fixing

If ambiguity resolution is enabled and OSB information is available:
- `arsig` reads the float ambiguity results and inverse-normal-equation information
- selects resolvable ambiguities
- writes integer ambiguity constraints
- `lsq` is run again with those constraints to produce the final fixed solution

So `arsig` is not the main estimator. It is a post-float ambiguity-resolution stage that feeds constraints back into `lsq`.

## Internal LSQ Interpretation

At the estimator level, the key point is:

- observations are ingested epoch by epoch
- information is accumulated into one normal equation over the session
- stochastic / dynamic parameters are propagated with process constraints between epochs
- the main solve occurs after the epoch scan, not after every epoch

This is why PRIDE can support:
- kinematic and LEO orbit determination
- piece-wise coordinate models
- stochastic ZTD / HTG models
- ambiguity birth/death and later fixing

within one unified least-squares framework.

## Practical Summary

For algorithm discussions, the safest compact description is:

PRIDE PPP-AR uses `tedit` for observation editing, then `lsq` performs a sequential epoch scan that accumulates a session-level normal equation with process-model updates between epochs. `redig` iteratively refines the editing based on residuals, and `arsig` optionally adds integer ambiguity constraints before a final `lsq` re-solve.
