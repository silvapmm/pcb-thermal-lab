# The New Approach: What Was Built and How It Compares with the Old Program

2026-10-16, branch `feature/physics-core`. This document records why the program was rebuilt, what the new design is, and how
its results compare with the original wxPython program on the same board. Formulas and the API are in
[`physics_core.md`](physics_core.md); the review of the old solvers is in [`thermal_models.md`](thermal_models.md); everything found along
the way is in [`findings.md`](findings.md); methods found in the literature are in [`candidate_methods.md`](candidate_methods.md).

## 1. Why a new approach

The review of the original program found, and experiments confirmed, that:

- the **Analytic** and **Lumped** formulas were dimensionally or structurally wrong (1000 °C and 24 000 °C on a board that reaches about 86 °C);
- the **FDM** injected the wrong power (8.17 W for 5.50 W on the default 10 mm grid), reported `converged` while far from the solution
  (step-size stopping rule) and ignored lateral conduction in the FR-4;
- numerics, plotting and the wxPython windows were mixed in the same files, so nothing could be tested or reused by a new interface.

## 2. The new design

| Decision | Reason |
| :-- | :-- |
| Physics in a package with no GUI (`pcbthermal`) | testable, usable from scripts and from any interface (the PySide 6 GUI is one client) |
| One `Problem` description shared by all models | the three models can be compared on identical input |
| FVM as the reference model: cell-centred finite volumes, sparse matrices | exact conservation of power and energy, no half-cell boundary tricks, exact solve instead of iterating |
| Lumped and Analytic rebuilt from the same physics | they answer "what does the FVM say?" fast, with a known error |
| Energy balance and input checks in every result | an immediate test that nothing was lost, and a warning when the input makes a model doubtful |
| Public API (`SolverOptions`, `simulate`, `Problem` builder, project files) | one validated object for settings, readable results, units hidden from the caller |
| PySide 6 GUI with undo/redo, project files, themes, animation | the functions of the old editor with a modern workflow |
| 88 tests, among them a documentation gate | regressions and undocumented code are caught automatically |

## 3. Old versus new on the same board

Board: 100 × 80 mm, 4 layers, two heaters (4 W + 1.5 W), 3 × 3 vias under the larger heater, partial top copper, a bottom sink
(`examples/example_board.pcbt.json`). There is no measurement of this board, so the reference is the new FVM at 0.5 mm
(grid-converged, energy balance 1e-12, checked against exact solutions). The old numbers come from running the original code at commit `641da87`
(`git archive 641da87`) and are reproduced exactly on each run.

| | Model | Tmax [°C] | ΔT error | Tmean [°C] | Power used [W] | Time [s] | Note |
| :-- | :-- | --: | --: | --: | --: | --: | :-- |
| old | Analytic, Basic | 603.95 | +851.1 % | 314.48 | 5.50 | 0.00 |  |
| old | Lumped, Basic | 32.24 | -88.1 % | 97.42 | 5.50 | 0.00 |  |
| old | Analytic, Advanced | 34081.12 | +55844.9 % | 17053.06 | 5.50 | 0.00 |  |
| old | Lumped, Advanced | 449.00 | +596.5 % | 4264.97 | 5.50 | 0.00 |  |
| old | FDM, dx 10 mm (app defaults) | 124.93 | +64.2 % | 55.64 | 8.17 | 1.98 | 152 it, converged=True |
| old | FDM, dx 2 mm (defaults tol/omega) | 76.94 | -14.7 % | 45.27 | 5.50 | 0.07 | 554 it, converged=True |
| old | FDM, dx 1 mm (defaults tol/omega) | 66.56 | -31.7 % | 34.59 | 5.50 | 0.28 | 593 it, converged=True |
| old | FDM, dx 1 mm (tight tol, omega 1.9) | 82.50 | -5.5 % | 49.98 | 5.50 | 0.53 | 1251 it, converged=True |
| new | FVM, direct matrices, cell 2 mm | 85.34 | -0.9 % | 50.09 | 5.50 | 0.04 | energy balance +7e-14 |
| new | FVM, direct matrices, cell 1 mm | 85.81 | -0.1 % | 50.09 | 5.50 | 0.24 | energy balance -7e-13 |
| new | FVM, direct matrices, cell 0.5 mm | 85.87 | +0.0 % | 50.09 | 5.50 | 1.82 | energy balance +2e-12 |
| new | FVM, SOR (residual 1e-9), cell 1 mm | 85.81 | -0.1 % | 50.09 | 5.50 | 0.74 | 2247 sweeps |
| new | FVM, SOR with the old stop rule, cell 1 mm | 69.64 | -26.7 % | 34.18 | 5.50 | 0.18 | 562 sweeps, stops too early |
| new | Lumped (offset-contour networks) | 84.66 | -2.0 % | 50.26 | 5.50 | 0.01 |  |
| new | Analytic (modal + local corrections) | 84.65 | -2.0 % | 50.70 | 5.50 | 0.05 |  |

Reading:

- The old **Analytic** and **Lumped** models are unusable here (errors from -88 % to +55 845 %); the new ones are both within 2 % of the reference.
- The old **FDM** gives -14.7 % at 2 mm and **-31.7 % at 1 mm**: the error grows when the mesh is refined, because of the step-size stopping rule.
  Even with a tight tolerance and a better ω (-5.5 %) the remaining error is modelling (solid vias, no lateral conduction in the FR-4).
- On the default 10 mm grid the old FDM used **8.17 W** for a 5.50 W request.
- The new **FVM** agrees with itself across meshes (within 0.9 % from 2 mm to 0.25 mm; 0.2 % from 1 mm) and costs 0.04 s (2 mm), 0.2 s (1 mm) or 1.8 s (0.5 mm).
  Its mesh convergence is slow only in the sense that point vias keep adding a little constriction as the mesh is refined (82.996 / 85.342 / 85.814 / 85.874 / 85.955 °C for 4 / 2 / 1 / 0.5 / 0.25 mm).

## 4. Do SOR and the matrix method give the same result?

**Yes, when SOR is stopped by the residual.** Same boards, same physics, four ways of solving the linear system:

| Board | Solver | Tmax [°C] | max abs diff to direct [K] | Residual | Sweeps | Time [s] |
| :-- | :-- | --: | --: | --: | --: | --: |
| reference, 2 layers | direct (sparse LU) | 90.0657 | 0.0e+00 | 3e-14 | - | 0.01 |
| reference, 2 layers | cg (Jacobi) | 90.0657 | 1.8e-12 | 9e-13 | - | 0.01 |
| reference, 2 layers | SOR, residual 1e-9, auto omega | 90.0657 | 7.6e-09 | 1e-09 | 656 | 0.05 |
| reference, 2 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 87.3447 | 2.7e+00 | 6e-02 | 369 | 0.03 |
| reference, 8 layers | direct (sparse LU) | 65.6612 | 0.0e+00 | 1e-13 | - | 0.23 |
| reference, 8 layers | cg (Jacobi) | 65.6612 | 2.2e-12 | 1e-12 | - | 0.02 |
| reference, 8 layers | SOR, residual 1e-9, auto omega | 65.6612 | 1.7e-08 | 1e-09 | 3247 | 0.69 |
| reference, 8 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 53.1158 | 1.3e+01 | 1e-01 | 384 | 0.08 |
| example board (vias, sink, 2 heaters) | direct (sparse LU) | 85.8143 | 0.0e+00 | 1e-13 | - | 0.23 |
| example board (vias, sink, 2 heaters) | cg (Jacobi) | 85.8143 | 8.0e-12 | 1e-12 | - | 0.09 |
| example board (vias, sink, 2 heaters) | SOR, residual 1e-9, auto omega | 85.8143 | 1.1e-08 | 1e-09 | 2247 | 0.76 |
| example board (vias, sink, 2 heaters) | SOR, step 0.01 K, omega 1.5 (original rule) | 69.6449 | 1.6e+01 | 1e-01 | 562 | 0.18 |
| weak cooling (h = 2 W/m²K, 200 mm) | direct (sparse LU) | 44.2990 | 0.0e+00 | 9e-14 | - | 0.07 |
| weak cooling (h = 2 W/m²K, 200 mm) | cg (Jacobi) | 44.2990 | 5.7e-13 | 1e-12 | - | 0.03 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, residual 1e-9, auto omega | 44.2990 | 2.6e-09 | 1e-09 | 2237 | 0.48 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, step 0.01 K, omega 1.5 (original rule) | 37.5624 | 6.7e+00 | 3e-01 | 162 | 0.04 |
| reference, insulated edges | direct (sparse LU) | 90.3925 | 0.0e+00 | 1e-13 | - | 0.07 |
| reference, insulated edges | cg (Jacobi) | 90.3925 | 2.8e-12 | 1e-12 | - | 0.03 |
| reference, insulated edges | SOR, residual 1e-9, auto omega | 90.3925 | 3.9e-09 | 1e-09 | 1391 | 0.30 |
| reference, insulated edges | SOR, step 0.01 K, omega 1.5 (original rule) | 80.3174 | 1.0e+01 | 2e-01 | 550 | 0.11 |

- Direct sparse LU, conjugate gradients and SOR with the residual criterion agree to **1e-8 K** or better on all five boards (fine and coarse meshes, 2 to 8 layers, strong and weak cooling).
- SOR with the rule of the original program (step below 0.01 K, ω = 1.5) stops **2.7 to 16 K away** from the solution and violates the heat balance (residual 0.06 to 0.3).
- The direct solve is 3 to 30 times faster than a correct SOR, and does not depend on ω or a stopping rule.

**Decision:** the matrix (direct) solver is the default everywhere (API, command line, GUI). SOR stays available (`linear_solver="sor"`,
`python -m pcbthermal solvers`) as an independent check and for teaching.

## 5. Animation of the heat evolution

The matrix method gives the animation naturally and with real time. The steady problem is `K θ = Q`; adding the heat capacity `C` gives
`C dθ/dt + K θ = Q`, advanced with the θ-method `(C/Δt + θK) x⁺ = (C/Δt − (1−θ)K) x + Q` (θ = 1 implicit Euler, θ = 0.5 Crank-Nicolson),
which is unconditionally stable. Every time step is one frame. The old program animated the SOR iterations, which is not time.

Validation on a board that has an exact answer (one layer, heater over the whole board, insulated edges: `C dθ/dt = P − Gθ`, time constant 109.1 s, steady rise 40 K),
maximum error in kelvin over 0 to 3 time constants, halving the step each time:

| Scheme | Δt | Δt/2 | Δt/4 | Δt/8 |
| :-- | --: | --: | --: | --: |
| Implicit Euler | 3.0626 | 1.6688 | 0.8746 | 0.4482 |
| Crank-Nicolson | 0.3152 | 0.0772 | 0.0192 | 0.0048 |

Euler halves its error with the step (first order), Crank-Nicolson divides it by four (second order), and the stored plus lost heat equals the injected heat within 0.2 %
(`tests/test_fvm.py`).

How to get the animation:

- **GUI:** Results ▸ **Animation**: choose the duration (preset to five board time constants), frames, scheme and spacing, press Compute, then play, scrub or export a GIF.
- **Command line:** `python -m pcbthermal transient board.pcbt.json --t-end 300 --gif`.
- Cost on the example board, 60 frames: 0.4 s with 2 mm cells and 2.5 s with 1 mm cells (the time step doubles in ten stages, so only ten matrix factorisations are needed).
  The hottest point reaches 63 % in about 19 s, the whole board needs minutes.

## 6. Accuracy of the simplified models

Error of the temperature rise against the FVM (1 mm). Regenerate with `python examples/accuracy_study.py` and `python examples/stress_study.py`.

| Case | FVM Tmax [°C] | Lumped Tmax | Lumped ΔT error | Analytic Tmax | Analytic ΔT error | Analytic warns |
| :-- | --: | --: | --: | --: | --: | :-: |
| reference board (centred 20 mm heater) | 90.13 | 89.70 | -0.7 % | 90.35 | +0.3 % | - |
| example board (full) | 85.81 | 84.66 | -1.9 % | 84.65 | -1.9 % | - |
| example, no sink | 88.91 | 87.60 | -2.1 % | 87.78 | -1.8 % | - |
| example, no vias | 94.67 | 96.51 | +2.6 % | 94.56 | -0.2 % | - |
| example, top copper over the full board | 85.29 | 84.14 | -1.9 % | 84.62 | -1.1 % | - |
| example, uniform (no sink, no vias, full copper) | 96.68 | 98.34 | +2.3 % | 97.15 | +0.7 % | - |
| example, only heater U1 | 79.97 | 77.82 | -3.9 % | 78.71 | -2.3 % | - |
| example, only U1, uniform | 90.30 | 91.10 | +1.2 % | 90.62 | +0.5 % | - |
| reference board, heater in the corner | 109.40 | 102.09 | -8.7 % | 110.42 | +1.2 % | - |
| reference board, small 5 mm heater | 103.06 | 102.87 | -0.2 % | 103.44 | +0.5 % | - |
| reference board, 8 layers | 65.70 | 66.17 | +1.1 % | 66.11 | +1.0 % | - |

Stress cases, where the models are pushed:

| Case | FVM Tmax [°C] | Lumped Tmax | Lumped ΔT error | Analytic Tmax | Analytic ΔT error | Input check |
| :-- | --: | --: | --: | --: | --: | :-- |
| heater 5 mm inside the top-copper edge | 94.45 | 91.45 | -4.3 % | 93.83 | -0.9 % | - |
| heater straddling the top-copper edge | 143.89 | 111.52 | -27.2 % | 114.54 | -24.7 % | warns |
| no copper on the heater layer | 150.16 | 150.12 | -0.0 % | 150.44 | +0.2 % | warns |
| 30 x 30 mm copper island around the heater | 92.38 | 91.66 | -1.1 % | 89.49 | -4.3 % | - |
| hatched copper (fill 0.5) on the top layer | 105.78 | 105.72 | -0.1 % | 106.00 | +0.3 % | warns |
| heater on the bottom layer | 88.37 | 87.97 | -0.6 % | 88.65 | +0.4 % | - |
| long thin heater, 40 x 4 mm | 67.84 | 71.90 | +9.5 % | 68.12 | +0.7 % | - |
| heater in the corner (10 mm from two edges) | 105.34 | 98.51 | -8.5 % | 106.06 | +0.9 % | - |
| two heaters 60 mm apart (4 W + 2 W) | 100.41 | 99.10 | -1.7 % | 101.07 | +0.9 % | - |

How the two models were tuned after the first comparison (first versions: Lumped +24 %, Analytic +47 % on the example board):

| Change | Effect |
| :-- | :-- |
| Lumped: rings by distance to the real footprint instead of a circle, contour lengths from the real geometry | long thin heater +35 % → +9.5 %; edges and corners follow the board outline |
| Lumped: footprint interior from the logarithmic potential, with the exact vertical-loss (Bessel) correction | no copper under the heater +24 % → 0 %; centred heater +7 % → -1 % |
| Analytic: copper weighted with each layer's own fin length (5 mm for a heater layer, not 34 mm for the stack) | partial copper +9 to +16 % → -2 % |
| Input checks and validity warnings | the remaining failure (a copper edge crossing the heater, about -25 %) is flagged before and after the run |

## 7. What changed for the user

| Before | Now |
| :-- | :-- |
| `python main.py` (wxPython) | `python -m pcbthermal gui` (PySide 6); command line `python -m pcbthermal run board.pcbt.json` |
| Editor JSON in canvas pixels | Project files `.pcbt.json` in mm; old editor JSON still opens (File ▸ Open, or `convert`) |
| One set of numbers per solver, no warnings | table of the models with the error against the reference, energy balance and validity warnings |
| Hotspots as log lines | hotspot list with position and area, gradients, profiles, heater and junction temperatures, zone statistics |
| Iterations GIF | real-time animation (GUI tab and `--gif`) |
| Dependencies installed system-wide | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |

## 8. Limits and what comes next

- Radiation and natural convection are inside a constant `h`; temperature-dependent `h` is the next accuracy step (`candidate_methods.md`, item 7).
- The GUI animation uses a power step from ambient; pulses and duty cycles are not yet inputs.
- Lumped and Analytic are unreliable when a copper edge crosses the heater; the Lumped model is weaker at corners (-8.7 %) and for thin heaters (+9.5 %).
- The GUI was verified offscreen with automated tests and screenshots; interactive use on a real display is the next check.

## 9. Reproduce

```sh
.venv/bin/python -m pytest -q tests                              # 88 tests
.venv/bin/python examples/accuracy_study.py                      # section 6
.venv/bin/python examples/stress_study.py                        # section 6
.venv/bin/python examples/solver_equivalence.py                  # section 4
.venv/bin/python -m pcbthermal transient examples/example_board.pcbt.json --t-end 300 --gif   # section 5
git archive 641da87 | tar -x -C <empty folder>                   # old code; run examples/legacy_comparison.py there (section 3)
```
