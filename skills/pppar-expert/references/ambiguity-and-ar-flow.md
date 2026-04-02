# Ambiguity And AR Flow

## Overview

In PRIDE PPP-AR, ambiguity handling is spread across preprocessing, float estimation, residual re-editing, and optional ambiguity fixing.

The main implementation points are:
- `src/lsq/lsq_add_newamb.f90`
- `src/lsq/lsq_add_ambcon.f90`
- `src/lsq/lsq.f90`
- `src/arsig/arsig.f90`
- `src/arsig/read_ambiguity.f90`

## Stage 1: Ambiguity Birth From Editing Results

Before `lsq` runs, `tedit` and later `redig` determine where ambiguities begin and end.

These edits are transferred into the observation structure through:
- ambiguity flags
- ambiguity lifetime information

When `lsq` scans an epoch, `lsq_add_newamb.f90` checks `OB%flag(isat)` and creates a new ambiguity parameter when needed.

Each inserted ambiguity:
- is named `AMBC`
- is type `S`
- is attached to one satellite
- stores a begin and end active time

So a PRIDE ambiguity is a time-bounded arc parameter, not merely an epoch label.

## Stage 2: Float Ambiguity Estimation Inside LSQ

During `lsq_add_obs.f90`, the phase equation and code equation are both injected into the normal equation.

For a newly activated ambiguity, PRIDE also initializes:
- the float ambiguity value
- the Melbourne-Wubbena related wide-lane quantities
- observation statistics used later for fixing

As the epoch scan continues, the ambiguity accumulates:
- observation counts
- wide-lane statistics
- elevation statistics
- active time history

The output of this stage is the float ambiguity solution written into the ambiguity result file `amb_*`.

## Stage 3: Ambiguity Death And Removal

At each epoch, PRIDE checks whether an ambiguity has expired.

If its active interval has ended:
- ambiguity constraints may be applied
- the ambiguity can be removed from the active normal equation
- the observation-to-parameter mapping is reset for that satellite arc

This is controlled in `lsq.f90` together with `lsq_rmv_normal.f90`.

So ambiguity handling in PRIDE is an explicit birth-death process tied to observation arcs.

## Stage 4: Residual Re-Editing

After a float `lsq`, PRIDE runs `redig` on `res_*`.

`redig` can:
- remove additional outliers
- insert new ambiguity boundaries

This is important algorithmically: the ambiguity structure is not fixed once at the beginning. It can be revised after residual inspection.

That is why PRIDE often repeats:

```text
lsq -> redig -> lsq -> redig
```

until no new removals or ambiguity insertions are produced.

## Stage 5: Selecting Resolvable Ambiguities

If ambiguity resolution is enabled, `arsig` reads the float ambiguity file.

In `read_ambiguity.f90`, PRIDE filters ambiguities by conditions such as:
- cutoff elevation
- wide-lane scatter / quality
- minimum common time span

Only eligible ambiguities are passed into the AR stage.

So not every float ambiguity arc becomes a fixing candidate.

## Stage 6: ARSIG Processing

`arsig.f90` then performs the ambiguity-resolution logic:

1. Read float ambiguities, and optionally inverse normal information.
2. Form single-difference ambiguity pairs.
3. Fix wide-lane ambiguities first.
4. Find independent satellite pairs.
5. If configured, search and validate narrow-lane fixes.
6. Write ambiguity constraint file for the fixed subset.

In the code, this is the role of:
- `define_sat_pairs`
- `fixamb_rounding`
- `find_indep`
- `fixamb_search`
- `write_ambcon`

So `arsig` is a dedicated ambiguity-resolution engine sitting after the float LSQ.

## Stage 7: Feeding Integer Constraints Back To LSQ

The constraint file written by `arsig` is later consumed by `lsq_add_ambcon.f90`.

This routine:
- reads the ambiguity constraint file
- finds the matching one-way ambiguity parameters in the active LSQ system
- converts the fixed SD ambiguity relation into a normal-equation constraint
- injects that constraint into the normal equation with high weight

In other words, PRIDE does not replace the estimator with a separate fixed solver. It feeds integer information back into the same LSQ framework as additional constraints.

## Conceptual Interpretation

The ambiguity workflow is therefore:

```text
editing defines arcs
  -> lsq estimates float one-way ambiguities
  -> redig may split / revise arcs
  -> arsig selects a fixable subset and writes SD constraints
  -> lsq re-solves with those ambiguity constraints
```

This is a hybrid strategy:
- ambiguity arcs are managed in one-way form inside LSQ
- fixing is performed through SD combinations in ARSIG
- fixed information returns to LSQ as constraints

## Practical Summary

The safest compact description is:

In PRIDE PPP-AR, ambiguities are dynamic arc-level state parameters created and removed according to editing results. Float ambiguities are estimated inside the main LSQ, refined through residual-driven re-editing, and optionally fixed by `arsig`, which writes integer constraints that are added back into the final LSQ normal equation.
