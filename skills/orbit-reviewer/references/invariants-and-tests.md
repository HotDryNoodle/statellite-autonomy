## Physical Invariants & What Tests Must Demonstrate

本文件不提供新实现；只定义“测试应证明什么”，用于指出验证不足的风险。

### 1) Two-Body (No Perturbation, No Thrust)

**Assumptions**

- Point-mass gravity: \u03c1\u0308 = -\u03bc \u03c1 / r^3
- Inertial frame, constant \u03bc

**Invariants**

- Specific angular momentum: \u210e = \u03c1 \u00d7 \u03bd  (constant vector) \u00a0[m^2\u00b7s^-1]
- Specific mechanical energy: \u03b5 = v^2/2 - \u03bc/r (constant scalar) \u00a0[m^2\u00b7s^-2]
- Orbital plane normal direction fixed (since \u210e is constant)

**What a test must show**

- Over a specified time horizon, \u0394\u210e and \u0394\u03b5 remain within an error bound consistent with the integrator order and tolerance.
- The bound is stated in physical units (e.g., |\u0394\u03b5| < X m^2/s^2), not only relative error, to avoid masking unit bugs.

**Common failure modes to flag**

- Using ECEF quantities with inertial equations (spurious non-conservation).
- Unit mismatch (km vs m) that still produces “stable-looking” trajectories.
- Too-large dt leading to secular energy drift not caught by tests.

### 2) Central Body Oblateness (J2) as a Perturbation

**Assumptions**

- Gravity includes J2 term; model definition must specify Earth radius R_e and J2, and whether higher terms are ignored.

**Expected qualitative behavior**

- Secular changes in \u03a9 and \u03c9; semi-major axis a approximately constant in the absence of drag/thrust.

**What a test must show**

- Whether the code reproduces known secular rates within tolerance for a chosen reference case (must name the reference: formula, textbook, or trusted dataset).

**Common failure modes to flag**

- Sign errors causing regression direction reversal (\u03a9\u0307 sign).
- Using degrees where radians expected in rate formulas.

### 3) Atmospheric Drag (Non-Conservative)

**Assumptions**

- Requires density model, ballistic coefficient, atmosphere co-rotation assumptions; all must be stated.

**Expected qualitative behavior**

- Mechanical energy decreases; a decreases over time; behavior depends on altitude and density.

**What a test must show**

- Energy is not conserved (and decreases in a physically plausible way) under drag-only perturbation, to avoid “drag accidentally disabled”.

### 4) Relative Motion Linear Models (CW/Hill)

**Assumptions**

- Circular reference orbit; small relative distance; rotating LVLH frame.

**What a test must show**

- With consistent initial conditions, the closed-form solution (or known properties like boundedness in z) matches within tolerance.

**Common failure modes to flag**

- Mixing instantaneous angular rate with mean motion n without declaring it.
- Using RTN vs LVLH axis order mismatch.

### 5) Estimation / Linearization (Jacobian, STM)

**Assumptions**

- Linearization valid for small errors over the update interval.

**What a test must show**

- Jacobian/STM consistency via finite-difference checks: \u03a6\u03b4x \u2248 (x(t;\u03c7+\u03b4x)-x(t;\u03c7)).
- Residual definition consistent with measurement function h(x): r = y - h(x) (or stated alternative).

