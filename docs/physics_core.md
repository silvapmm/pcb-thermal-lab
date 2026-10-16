# Physics Core (`pcbthermal`): Models, API, Checks, GUI, Verification

GUI-independent physics package and PySide 6 application that replaced the original wxPython program
(its solvers are reviewed in [`thermal_models.md`](thermal_models.md), results compared in
[`legacy_vs_new.md`](legacy_vs_new.md) and [`new_approach.md`](new_approach.md); everything found along the way is in
[`findings.md`](findings.md)). Version 2.0.0, 2026-10-16 (see `CHANGELOG.md`).

- SI units inside the package (m, W, K, W/mK, W/m²K, J/kgK, kg/m³).
- JSON files and the builder API use millimetres and 1-based layers (layer 1 = top).
- Dependencies: NumPy, SciPy (solvers), Matplotlib (figures), PySide 6 (GUI only). Use a virtual environment:
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (`.venv/` is git-ignored).

## 1. Layout

```
pcbthermal/
  model.py      Board, Materials, Zone, Heater, Via, Sink, Problem (+ builder API), JSON readers/writer
  geometry.py   shoelace area, centroid, vectorised point-in-polygon, cell coverage fractions
  fvm.py        reference model: finite volumes, steady (sparse direct / CG / SOR) and transient
  lumped.py     offset-contour ring network per heater, superposed
  analytic.py   multilayer cosine series with per-layer copper weighting and local via/sink corrections
  profiles.py   power profiles: options, average-or-resolve decision, window-by-window time simulation shared by the models (section 3.4)
  checks.py     input validity checks (heater outside the board, no copper, copper edge across a heater, ...)
  results.py    SteadyResult, TransientResult (energy balance and warnings built in)
  analysis.py   hotspots, gradients, zone and heater statistics (junction temperature)
  api.py        SolverOptions, simulate() -> Simulation (table, report, save), suggest_cell_mm()
  project.py    Project files (.pcbt.json): problem + options + view settings; legacy editor files
  examples.py   reference_problem(), example_board()
  plots.py      figures (draw_* into any Figure; plot_* / GIF writers for files)
  cli.py        python -m pcbthermal {run,solvers,transient,convergence,convert,gui,example}
  gui/          PySide 6 application (section 6)
tests/          110 pytest tests: geometry, FVM, models, API, checks, I/O, power profiles, GUI (offscreen) and a documentation gate
examples/       example boards, accuracy_study.py, stress_study.py, solver_equivalence.py
```

## 2. Python API

```python
from pcbthermal import Problem, SolverOptions, simulate, suggest_cell_mm

p = Problem.new(width_mm=100, height_mm=80, layers=4)               # empty board
p.add_zone(1, rect=(15, 15, 85, 65)).add_full_copper([2, 3, 4])
p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)   # theta_jb: junction-to-board K/W
p.add_via_array((30, 35, 40, 45), 3, 3, diameter=0.3)
p.add_sink(4, 30.0, rect=(25, 30, 45, 50))                          # extra h on the bottom layer

sim = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=suggest_cell_mm(p)))
print(sim.to_markdown())          # comparison table and every warning
print(sim.report())               # text report: hotspots, heaters (junction), zones
sim.save("results")               # summary.json, report.txt, field CSVs, PNG figures
sim.results["fvm"].T              # temperature field (layers, ny, nx) in degC
sim.warnings                      # input checks + model warnings
```

`SolverOptions` holds every setting (models, `cell_mm`, `linear_solver` direct/cg/sor, `lumped_rings`, `analytic_modes`,
`analytic_local_corrections`, `hotspot_c`) and validates them. The default linear solver is the **direct sparse solver**
(it gives the same temperatures as SOR, section 7.1). Projects save the problem, the options and the viewer state
together (`save_project` / `load_project`).

## 3. Models

Which model to use for which job (advantages, limits, decision guide): [`model_guide.md`](model_guide.md).

### 3.1 FVM (reference)

Cell-centred finite volumes, one node per layer and cell, slab thickness `t_pcb / N`.

Lateral sheet conductance of a cell (copper fill *f*, copper thickness *t*<sub>cu</sub>):
$S = f\,k_{cu}\,t_{cu} + k_{fr4,ip}\,(slab - f\,t_{cu})$, with the harmonic mean between cells:
$G_x = \frac{2S_1S_2}{S_1+S_2}\frac{dy}{dx}$. Vertical: $G_z = \frac{k_{fr4,th}\,dx\,dy}{d} + \sum_{vias}\frac{k_{cu}A_v}{d}$
with $A_v=\pi[(d_v/2)^2-(d_v/2-t_p)^2]$ (hollow) or $\pi(d_v/2)^2$ (filled). Ambient: $h_{top}dx\,dy$ on the top layer,
$h_{bot}dx\,dy$ on the bottom layer, sinks and edges. Heater power is spread over the covered cells by
coverage fraction, so the requested power is injected exactly on any grid.

Steady state $K\theta=Q$ ($\theta=T-T_{amb}$, $K$ sparse symmetric positive definite) with three interchangeable solvers:
`direct` (sparse LU, default, exact), `cg` (Jacobi-preconditioned conjugate gradients) and `sor` (vectorised red-black SOR, kept to
compare with the original program: stop by residual, or by step size like the original). The energy balance (heat out through top,
bottom, sinks and edges minus power in) is reported and is at round-off level.
Transient: `fvm.solve_transient` (power step, implicit Euler or Crank-Nicolson, time step doubling in ten stages),
validated against an exact exponential; on the command line (`transient --gif`) and in the GUI Animation tab.

### 3.2 Lumped (offset-contour network per heater)

A reduction of the FVM network. For every heater the board cells are grouped in rings by their **distance to the heater footprint**
(ring 0 is the footprint, outer rings grow geometrically up to the farthest cell), so any heater shape and the real board outline
are followed: no circular approximation. For every layer and ring the real geometry is aggregated (sheet conductance, vertical conductance
including vias, conductance to ambient, sinks, edges). Heat crosses the offset contours, whose length is $L_k=A_k/\Delta_k$ ($A_k$ ring area,
$\Delta_k$ ring thickness):

$$R_{k,k+1}=\frac{\Delta_k}{2S_kL_k}+\frac{\Delta_{k+1}}{2S_{k+1}L_{k+1}},\qquad
R_{0,1}=f_R(x)\,\frac{\varphi_b-\varphi_m}{2\pi S_0}+\frac{\Delta_1}{2S_1L_1}$$

The first term of $R_{0,1}$ is the interior of the heated footprint, from the logarithmic potential
$\varphi_i=\langle\ln|x_i-x'|\rangle$ of the uniformly heated footprint ($\varphi_b$: boundary cells, $\varphi_m$: mean; $1/(8\pi S)$ for a disc). When the layer
also loses heat vertically under the footprint (fin length $\lambda=\sqrt{S/g_{eff}}$ not much larger than the footprint radius $a$), the exact disc
solution with losses scales it by $f_R=4\,(I_0-2I_1/x)/(x I_1)$ and the peak by $f_P=4\,(2/x^2-1/(xI_1))$, with $x=a/\lambda$ and $I_0,I_1$ the modified Bessel
functions; $g_{eff}$ comes from the solution itself (three passes). The peak inside the footprint is $T_{mean}+Q_{lat}\,f_P\,(\varphi_m-\varphi_{min})/(2\pi S_0)$.
Each heater gives a small dense system; the problem is linear, so the field is the sum over heaters (mutual heating = the radial profile of one heater
read at the distance of the other).

### 3.3 Analytic (cosine series, weighted copper, local corrections)

Multilayer fin equation on the rectangle with insulated edges, expanded in $\cos(m\pi x/W)\cos(n\pi y/H)$; every mode is a small tridiagonal system
over the layers (module docstring of `analytic.py`). Exact on a uniform board. Refinements:

- **Copper fill weighted by influence, layer by layer**: $f_{eff,l}=\sum w_l f_l/\sum w_l$, $w_l=\sum_i P_i K_0(r_i/\lambda_l)$. A layer that carries a heater loses
  heat to its neighbours within a few millimetres, so its length is $\lambda_l=\sqrt{S_l/(h_l+n_l g)}$ (about 5 mm on the example board), not the length of the whole stack
  ($\approx$ 34 mm). This is what removed the error with partial copper (+9 to +16 % to about -2 %).
- **Local vias and sinks** (Green-function / Woodbury update): removed from the uniform problem and returned as lumped conductances $C$ on 2.5 to 5 mm tiles.
  With $G$ the modal response between tiles and $y_0$ the tile averages of the uniform solution, the tile temperatures solve $(I+GC)\,y=y_0$ and the heat
  $f=-Cy$ is added to the modes.
- **Warnings** when the copper around the heater is still strongly non-uniform, or edge convection is significant (the model assumes insulated edges).

### 3.4 Power profiles (time-dependent power)

A heater may carry a **square wave** (`SquareWave`: `p_on`, `period`, `duty`, `p_off`, average `p_off + duty (p_on - p_off)`); its `power` stays equal to the average, so the steady models and old files work unchanged.
Theory and measurements: `roadmap.md` section 1. What is implemented:

1. **Step response** `Z_i(t)` of every heater's own hottest point to a unit step of its power, from the reference model (FVM, else Lumped, else Analytic): `fvm.step_responses`, `lumped.step_responses`, `analytic.step_responses` (closed form per mode).
2. **Decision** (`profiles.decide`): by superposition the periodic peak and valley of heater *i* are `P_off Rth + ΔP Σ[Z(mT+tp) - Z(mT)]` and the valley the analogous sum; the oscillation is their difference in °C.
   Heaters are sorted by oscillation and averaged, smallest first, while the cumulative oscillation stays below the threshold (default 1 °C); the rest are simulated in time. Percentages are shown for information only.
3. **Run** (`profiles.run_windows`, one runner for all models through an adapter): the step is chosen from the shortest resolved period, the power of each step is the exact mean of the wave over the step (`SquareWave.mean_power`),
   averaged heaters keep their constant average power in the same run. Windows of the longest resolved period are repeated until the peak and minimum change by less than 0.1 °C ("until the cycle repeats"), for N cycles, or for a fixed time;
   more than 200,000 steps is refused with an explanation. Start: steady state of the average power, or a uniform temperature typed in °C.
   Adapters: FVM (implicit Euler or Crank-Nicolson with one factorisation), Lumped (one network per heater, own footprint plus the others' rise at its centroid), Analytic (`C a' + A a = q` per cosine mode,
   exact exponential step; vias and sinks are smeared, with a warning that quantifies the difference from the steady analytic model).
4. **Results** (`ProfileResult`): peak, minimum, oscillation, temperature of every heater versus time in the last window, peak map, frames of the last window, steady temperatures with the average power and with the peak power (the bound), windows, steps, warnings.
5. **Interfaces**: `SolverOptions.profile` (`ProfileOptions`) and `steady_power` (steady models use the "average" or "peak" power); `Simulation.decisions` / `profile_results`; CLI `run --duration --cycles --time-s --initial-c --threshold-c --steady-power`;
   GUI tab "Power profile" and results tab "Power profile"; files `profile_<model>.csv/.png`, `peak_map_<model>.png`.

Validation (`tests/test_profiles.py`): exact energy of the step-mean power; exact RC solution of a uniform board (periodic peak within 0.3 %, time stepping within 0.4 % with Crank-Nicolson);
mixed regimes against the fully resolved run (difference bounded by the neglected oscillation); the three models agree within 5 % on the example (FVM 135.3, Lumped 131.8, Analytic 134.9 °C peak).
Animation of the last window works in all three models; the Lumped frames are only indicative (sum of radial profiles). The step-power Animation tab remains FVM only.

## 4. Input checks

`check_problem(problem, cell_mm)` (also run by `simulate` and shown live in the GUI under the Run button) never blocks a run, it warns about inputs that
make a result doubtful: a heater partly outside the board (its power would be moved onto the part inside), no copper under a heater, a copper edge or hatching crossing a
footprint (Lumped and Analytic unreliable), a heater only a few cells wide, overlapping heaters, vias or zones outside the board and zero total power.

## 5. Command line

```sh
python -m pcbthermal example examples/example_board.pcbt.json --which example
python -m pcbthermal run examples/example_board.pcbt.json            # all models + report + plots in ./output
python -m pcbthermal run board.pcbt.json --model fvm --cell-mm auto --solver cg
python -m pcbthermal example profile.pcbt.json --which profile         # example with square-wave power
python -m pcbthermal run profile.pcbt.json --duration cycles --cycles 4 --initial-c 25
python -m pcbthermal solvers board.pcbt.json                         # direct vs CG vs SOR
python -m pcbthermal convergence board.pcbt.json                     # FVM grid refinement
python -m pcbthermal transient board.pcbt.json --t-end 600 --gif     # power step + animated GIF
python -m pcbthermal convert old_editor_export.json board.pcbt.json  # legacy editor JSON -> project
python -m pcbthermal gui [board.pcbt.json]                           # open the application
python -m pytest -q tests
```

## 6. Graphical application (PySide 6)

`python -m pcbthermal gui` (or `python -m pcbthermal.gui`). Dark and light themes, undo/redo, project files.

| Area | What it does |
| :-- | :-- |
| Board canvas | zoom (wheel), pan (middle button or Space), grid with snap, optional solver-mesh overlay, background photo with position/size/opacity |
| Tools | select/move, copper zone, heater, sink, via; rectangle by dragging, polygon mode by clicking vertices; corner handles reshape (rectangles stay rectangular) |
| Editing | move by drag or arrows, duplicate (Ctrl+D), delete, select all on layer, layer chooser (other layers dimmed), sinks only on outer layers |
| Left docks | board size, stack-up, environment, materials; element tree synchronised with the canvas |
| Right docks | model choice and solver settings (cell size with an Auto button), Run (F5, background thread, progress) and the live input checks; property inspector |
| Power profile | tab between Board and Results: heater list, editor (Constant / Square wave, period or frequency with units, duty, power on/off or average), derived values, decision table, run settings, Analyze |
| Results | Summary (models table, warnings, text report), Temperature, Gradients, Profiles (movable cut line), Components (heater and junction temperatures, zone statistics, hotspots), Models (comparison), **Animation** (real-time heat evolution: compute, play, scrub, export GIF), **Power profile** (temperature versus time, peak map, last-window frames) |
| Board overlay | paint the last temperature field on the board (key T); results are marked outdated when the design changes |
| Files | open/save projects, open legacy editor JSON, open examples, export results folder / TXT report / JSON summary / figures |

Dropped on purpose: the old "iterations GIF" (it showed solver iterations, not time; replaced by the Animation tab) and the pixel-corner board setup
(the board is its size in mm; a background image can be fitted to it).

## 7. Verification (2026-10-16)

| Check | Result |
| :-- | :-- |
| Energy balance, all models | below 1e-9 (about 1e-13 for the FVM) |
| Uniform plate (heater = board, 1 layer, insulated) | FVM equals $P/((h_t+h_b)A)$ to 1e-6 K |
| Requested power injected for any cell size | exact |
| Grid convergence Tmax of the example board, 4 / 2 / 1 / 0.5 / 0.25 mm | 82.996 / 85.342 / 85.814 / 85.874 / 85.955 °C (0.2 % from 1 mm on) |
| Analytic vs FVM, insulated edges, 1 / 2 / 4 layers | 104.25 vs 104.31, 90.35 vs 90.39, 76.08 vs 76.10 °C |
| Transient vs exact exponential | Euler error halves with the step, Crank-Nicolson divides by four; stored + lost heat = injected within 0.2 % |
| FVM size / speed | 320 000 cells in 4.6 s (direct), 3.3 s (CG) |
| Tests | 94 pass, among them 29 that check the documentation of every function |

### 7.1 Direct matrices versus SOR

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

All solvers that stop on the residual agree to 1e-8 K or better. The step-size rule of the original program (0.01 K per sweep, ω = 1.5) stops 2.7 to 16 K
from the solution with a visibly violated heat balance. The direct solver is the default.

### 7.2 Accuracy of the simplified models against the FVM (1 mm)

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

### 7.3 Stress cases

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

Reading: the **Analytic** model is exact on uniform boards and keeps within 2.3 % with partial copper, vias, sinks, corners, thin heaters and several heaters; it fails when a copper edge crosses
the heater (the checks warn). The **Lumped** model stays within about 4 % in most cases and 9 % at worst (corner and thin heaters) and also fails when a copper edge crosses the heater.
For those cases, and whenever geometry matters, use the FVM.

## 8. Known limits and next steps

- Radiation and natural convection are inside the constant `h`; temperature-dependent `h(ΔT)` is the next accuracy step.
- Power shapes other than a square wave (arbitrary or CSV profiles); components with junction/case resistances beyond `theta_jb` (planned: one Component element, `roadmap.md` section 3).
- Copper traces with Joule heating (IPC-2152); reduced-order models for design sweeps.
- A copper edge crossing a heater, and non-axisymmetric edge effects (corners), limit the Lumped and Analytic models.
- Methods found in the literature and not implemented: `candidate_methods.md`.
