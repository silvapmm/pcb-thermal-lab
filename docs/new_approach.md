# The New Approach: What Was Built and How It Compares with the Old Program

2026-10-16, branch `feature/physics-core`. This document records why the program was rebuilt, what the new design is, and how
its results compare with the original wxPython program on the same board. Formulas and the API are in
[`physics_core.md`](physics_core.md); the review of the old solvers is in [`thermal_models.md`](thermal_models.md);
methods found in the literature are in [`candidate_methods.md`](candidate_methods.md).

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
| Lumped and Analytic rebuilt from the same physics | they now answer "what does the FVM say?" fast, with a known error |
| Energy balance in every result | an immediate check that nothing was lost |
| Public API (`SolverOptions`, `simulate`, `Problem` builder, project files) | one validated object for settings, readable results, units hidden from the caller |
| PySide 6 GUI with undo/redo, project files, themes | the same functions as the old editor with a modern workflow |
| Tests (56) against exact solutions and between models | regressions are caught automatically |

## 3. Old versus new on the same board

Board: 100 × 80 mm, 4 layers, two heaters (4 W + 1.5 W), 3 × 3 vias under the larger heater, partial top copper, a bottom sink
(`examples/example_board.pcbt.json`). There is no measurement of this board, so the reference is the new FVM at 0.5 mm
(grid-converged, energy balance 1e-12, and checked against exact solutions). The old numbers come from running the original code at commit `641da87`
(`git archive 641da87`), and are reproduced exactly on each run.

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
| new | FVM, direct matrices, cell 2 mm | 85.34 | -0.9 % | 50.09 | 5.50 | 0.03 | energy balance +7e-14 |
| new | FVM, direct matrices, cell 1 mm | 85.81 | -0.1 % | 50.09 | 5.50 | 0.21 | energy balance -7e-13 |
| new | FVM, direct matrices, cell 0.5 mm | 85.87 | +0.0 % | 50.09 | 5.50 | 1.70 | energy balance +2e-12 |
| new | FVM, SOR (residual 1e-9), cell 1 mm | 85.81 | -0.1 % | 50.09 | 5.50 | 0.76 | 2247 sweeps |
| new | FVM, SOR with the old stop rule, cell 1 mm | 69.64 | -26.7 % | 34.18 | 5.50 | 0.18 | 562 sweeps, stops too early |
| new | Lumped (ring networks) | 86.48 | +1.0 % | 50.23 | 5.50 | 0.01 |  |
| new | Analytic (modal + local corrections) | 91.04 | +8.5 % | 50.64 | 5.50 | 0.05 | warns: partial copper |

Reading:

- The old **Analytic** and **Lumped** models are unusable here (errors from -88 % to +55 845 %); the new ones are within 1 % (Lumped) and 9 % (Analytic, with a warning).
- The old **FDM** gives -14.7 % at 2 mm and **-31.7 % at 1 mm**: the error grows when the mesh is refined, because of the step-size stopping rule.
  Even with a tight tolerance and a better ω (-5.5 %) the remaining error is modelling (solid vias, no lateral conduction in the FR-4).
- On the default 10 mm grid the old FDM used **8.17 W** for a 5.50 W request.
- The new **FVM** agrees with itself across meshes (within 1 % from 2 mm to 0.5 mm) and costs 0.03 s (2 mm), 0.2 s (1 mm) or 1.7 s (0.5 mm).
- Via arrays make Tmax drift slowly with the cell size (82.99 / 85.34 / 85.81 / 85.87 / 85.96 °C for 4 / 2 / 1 / 0.5 / 0.25 mm) because a via is a point conductance
  with a constriction that finer meshes resolve further.

## 4. Do SOR and the matrix method give the same result?

**Yes, when SOR is stopped by the residual.** Same boards, same physics, four ways of solving the linear system:

| Board | Solver | Tmax [°C] | max abs diff to direct [K] | Residual | Sweeps | Time [s] |
| :-- | :-- | --: | --: | --: | --: | --: |
| reference, 2 layers | direct (sparse LU) | 90.0657 | 0.0e+00 | 3e-14 | - | 0.01 |
| reference, 2 layers | cg (Jacobi) | 90.0657 | 1.8e-12 | 9e-13 | - | 0.01 |
| reference, 2 layers | SOR, residual 1e-9, auto omega | 90.0657 | 7.6e-09 | 1e-09 | 656 | 0.05 |
| reference, 2 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 87.3447 | 2.7e+00 | 6e-02 | 369 | 0.03 |
| reference, 8 layers | direct (sparse LU) | 65.6612 | 0.0e+00 | 1e-13 | - | 0.20 |
| reference, 8 layers | cg (Jacobi) | 65.6612 | 2.2e-12 | 1e-12 | - | 0.02 |
| reference, 8 layers | SOR, residual 1e-9, auto omega | 65.6612 | 1.7e-08 | 1e-09 | 3247 | 0.70 |
| reference, 8 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 53.1158 | 1.3e+01 | 1e-01 | 384 | 0.08 |
| example board (vias, sink, 2 heaters) | direct (sparse LU) | 85.8143 | 0.0e+00 | 1e-13 | - | 0.21 |
| example board (vias, sink, 2 heaters) | cg (Jacobi) | 85.8143 | 8.0e-12 | 1e-12 | - | 0.09 |
| example board (vias, sink, 2 heaters) | SOR, residual 1e-9, auto omega | 85.8143 | 1.1e-08 | 1e-09 | 2247 | 0.76 |
| example board (vias, sink, 2 heaters) | SOR, step 0.01 K, omega 1.5 (original rule) | 69.6449 | 1.6e+01 | 1e-01 | 562 | 0.19 |
| weak cooling (h = 2 W/m²K, 200 mm) | direct (sparse LU) | 44.2990 | 0.0e+00 | 9e-14 | - | 0.06 |
| weak cooling (h = 2 W/m²K, 200 mm) | cg (Jacobi) | 44.2990 | 5.7e-13 | 1e-12 | - | 0.03 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, residual 1e-9, auto omega | 44.2990 | 2.6e-09 | 1e-09 | 2237 | 0.49 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, step 0.01 K, omega 1.5 (original rule) | 37.5624 | 6.7e+00 | 3e-01 | 162 | 0.04 |
| reference, insulated edges | direct (sparse LU) | 90.3925 | 0.0e+00 | 1e-13 | - | 0.06 |
| reference, insulated edges | cg (Jacobi) | 90.3925 | 2.8e-12 | 1e-12 | - | 0.03 |
| reference, insulated edges | SOR, residual 1e-9, auto omega | 90.3925 | 3.9e-09 | 1e-09 | 1391 | 0.31 |
| reference, insulated edges | SOR, step 0.01 K, omega 1.5 (original rule) | 80.3174 | 1.0e+01 | 2e-01 | 550 | 0.12 |

- Direct sparse LU, conjugate gradients and SOR with the residual criterion agree to **1e-8 K** or better on all five boards (fine and coarse meshes, 2 to 8 layers, strong and weak cooling).
- SOR with the rule of the original program (step below 0.01 K, ω = 1.5) stops **2.7 to 16 K away** from the solution and violates the heat balance (residual 0.06 to 0.3).
- The direct solve is 3 to 30 times faster than a correct SOR, and does not depend on ω or a stopping rule.

**Decision:** the matrix (direct) solver is the default. SOR stays available (`linear_solver="sor"`, `python -m pcbthermal solvers`) as an independent check and for teaching.

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

Error of the temperature rise against the FVM (1 mm), regenerate with `python examples/accuracy_study.py`:

| Case | FVM Tmax [°C] | Lumped Tmax | Lumped ΔT error | Analytic Tmax | Analytic ΔT error | Analytic warns |
| :-- | --: | --: | --: | --: | --: | :-: |
| reference board (centred 20 mm heater) | 90.13 | 94.86 | +7.3 % | 90.35 | +0.3 % | - |
| example board (full) | 85.81 | 86.48 | +1.1 % | 91.04 | +8.6 % | yes |
| example, no sink | 88.91 | 89.42 | +0.8 % | 94.44 | +8.7 % | yes |
| example, no vias | 94.67 | 99.36 | +6.7 % | 105.86 | +16.1 % | yes |
| example, top copper over the full board | 85.29 | 85.97 | +1.1 % | 84.62 | -1.1 % | - |
| example, uniform (no sink, no vias, full copper) | 96.68 | 101.20 | +6.3 % | 97.15 | +0.7 % | - |
| example, only heater U1 | 79.97 | 79.58 | -0.7 % | 85.20 | +9.5 % | yes |
| example, only U1, uniform | 90.30 | 93.93 | +5.6 % | 90.62 | +0.5 % | - |
| reference board, heater in the corner | 109.40 | 105.80 | -4.3 % | 110.42 | +1.2 % | - |
| reference board, small 5 mm heater | 103.06 | 110.43 | +9.4 % | 103.44 | +0.5 % | - |
| reference board, 8 layers | 65.70 | 68.50 | +6.9 % | 66.11 | +1.0 % | - |

The Lumped model stays within about 10 % in every case and the Analytic model is exact on uniform boards but over-estimates by 9 to 16 % when the copper on the heater layer is partial (it warns).
For decisions that depend on the geometry use the FVM.

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
- Analytic needs uniform copper under the heaters; Lumped assumes circular spreading.
- Vias are point conductances: Tmax varies by about 1 % with the cell size on via arrays.
- The GUI was verified offscreen with automated tests and screenshots; interactive use on a real display is the next check.

## 9. Reproduce

```sh
.venv/bin/python -m pytest -q tests                              # 56 tests
.venv/bin/python examples/accuracy_study.py                      # section 6
.venv/bin/python examples/solver_equivalence.py                  # section 4
.venv/bin/python -m pcbthermal transient examples/example_board.pcbt.json --t-end 300 --gif   # section 5
git archive 641da87 | tar -x -C <empty folder>                   # old code; run examples/legacy_comparison.py there (section 3)
```
