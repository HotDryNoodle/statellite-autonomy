# State And Parameter Model

## Overview

Inside PRIDE PPP-AR, the `lsq` estimator organizes unknowns through a parameter table `PM` and a normal-equation structure `NM`.

At a high level, parameters are split into:
- constant parameters, mainly static coordinates
- process parameters, which evolve through time
- stochastic parameters, mainly ambiguities that are born and removed dynamically

The central implementation entry points are:
- `src/lsq/lsq_init.f90`
- `src/lsq/lsq.f90`
- `src/lsq/lsq_add_obs.f90`
- `src/lsq/lsq_process.f90`
- `src/lsq/lsq_rmv_normal.f90`

## Parameter Classes

In `lsq_init.f90`, PRIDE assigns parameter types through `PM(ipar)%ptype`:

- `C`: constant parameters
- `P`: process parameters
- `S`: stochastic ambiguity parameters

This type split is fundamental to how PRIDE updates, removes, and later recovers parameters.

## Coordinate Parameters

### Static / fixed mode

For `S` and `F` modes, station coordinates are initialized as constant parameters:
- `STAPX`
- `STAPY`
- `STAPZ`

These are treated as session-level constants with explicit a priori variance.

### Piece-wise mode

For `P` mode, coordinates are process parameters with names like:
- `STAPX:<sec>`
- `STAPY:<sec>`
- `STAPZ:<sec>`

The suffix encodes the piece length. PRIDE uses time spans and process weights to create piece-wise coordinate states over the session.

### Kinematic / LEO mode

For `K` and `L` modes, coordinates are process parameters:
- `STAPX`
- `STAPY`
- `STAPZ`

These are not solved independently per epoch. They are sequentially updated and constrained across epochs, then recovered after the session-level solve.

## Receiver Clock And ISB Parameters

Receiver clock parameters are created per system according to the enabled constellation set and inter-system-bias configuration. Typical names are:
- `RECCLK_G_STO`
- `RECCLK_E_STO`
- `RECCLK_C_WNO`

The exact suffix depends on the configured receiver clock model:
- `STO`: stochastic process
- `WNO`: white-noise style epoch-wise behavior in PRIDE's framework

If inter-system biases are enabled, PRIDE also creates `RECISB_*` process parameters.

## Troposphere And Gradient Parameters

For non-LEO runs, PRIDE may create:
- `ZTDSTO` or `ZTDPWC:<sec>`
- `HTGC`
- `HTGS`

depending on the selected ZTD and HTG models.

These are process parameters. For stochastic models they are time-updated continuously; for piece-wise models they are active over configured time spans and then advanced to the next segment.

LEO mode explicitly disables atmosphere estimation in the main LSQ setup.

## Ambiguity Parameters

Ambiguities are not preallocated for all satellites over the whole session. They are created dynamically when needed.

In `lsq_add_newamb.f90`, each newly detected ambiguity is inserted as:
- parameter name `AMBC`
- parameter type `S`
- with an active time interval `[ptbeg, ptend]`

This active interval is derived from the observation editing results and ambiguity life information from preprocessing / residual diagnosis.

So in PRIDE, an ambiguity is a session object with a bounded lifespan, not just an epoch-local unknown.

## How One Epoch Enters The Estimator

For each processed epoch, `lsq.f90` does the following:

1. Read observations for the current epoch.
2. Update kinematic / LEO prior coordinates if needed.
3. Call `lsq_add_newamb()` to insert any new ambiguity states.
4. Build modeled observables through the GNSS-specific model routines.
5. Call `lsq_add_obs()` to add phase and code equations into the global normal equation.
6. Update parameter usage counters and timing information.
7. Call `lsq_process()` to advance process parameters in time.

The important point is that the epoch contributes rows and weights to the global normal equation, not a stand-alone solved state.

## Observation Equation Injection

`lsq_add_obs.f90` converts each valid satellite observation into:
- ionosphere-free code equation
- ionosphere-free phase equation

and inserts them into `NM%norx`, the normal-equation matrix and right-hand side.

During that insertion, PRIDE:
- maps local parameter names to global parameter indices
- counts observations per parameter and per constellation
- initializes newly activated ambiguity values
- accumulates weighted normal-equation terms

This is the point where the epoch-wise data become part of the session solution.

## Time Update Of Process Parameters

`lsq_process.f90` is the key evidence that PRIDE is not doing independent epoch-wise LSQ.

Its purpose is explicitly:
- time update of process parameters

Operationally, PRIDE checks whether a process parameter has reached the end of its current validity span. If so, it removes that active parameter from the current normal equation representation, advances its time tags, and prepares the next active segment.

This is how PRIDE implements dynamic models such as:
- kinematic coordinates
- piece-wise coordinates
- stochastic clocks
- stochastic or piece-wise troposphere / gradients

within a unified least-squares framework.

## Parameter Removal

`lsq_rmv_normal.f90` removes parameters that are no longer active from the normal equation.

This is used for:
- expired process parameters
- ambiguities whose active life has ended
- cleanup before the final solve

The distinction matters:
- `P` parameters are flagged as removed but remain part of the parameter bookkeeping
- `S` ambiguity parameters are zeroed out from the active system once eliminated

This allows PRIDE to keep a coherent parameter history while maintaining a manageable active normal equation.

## Final Solve

Only after the epoch loop finishes does PRIDE:
- apply remaining ambiguity constraints
- remove inactive parameters
- call `lsq_slv_prmt()`
- recover time series and residual outputs

This means the state evolution is encoded in the accumulated normal equation plus process constraints, not in a per-epoch final-state output.

## Practical Summary

The safest compact description is:

PRIDE PPP-AR represents coordinates, clocks, atmosphere terms, and ambiguities as typed state parameters in a session-level LSQ estimator. Epoch observations are added sequentially into the global normal equation, while process parameters are time-updated and ambiguity parameters are dynamically born and removed according to their active intervals.
