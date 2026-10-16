# Physics Core (`pcbthermal`): Models, API, GUI, Verification

GUI-independent physics package and PySide 6 application that replaced the original wxPython program
(its solvers are reviewed in [`thermal_models.md`](thermal_models.md), its results are compared in
[`legacy_vs_new.md`](legacy_vs_new.md)). Branch `feature/physics-core`, 2026-10-16.

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
  lumped.py     ring-network model, one network per heater, superposed
  analytic.py   multilayer cosine-series model with local via/sink corrections
  results.py    SteadyResult, TransientResult (energy balance and warnings built in)
  analysis.py   hotspots, gradients, zone and heater statistics (junction temperature)
  api.py        SolverOptions, simulate() -> Simulation (table, report, save)
  project.py    Project files (.pcbt.json): problem + options + view settings; legacy editor files
  examples.py   reference_problem(), example_board()
  plots.py      figures (draw_* into any Figure; plot_* / GIF writers for files)
  cli.py        python -m pcbthermal {run,solvers,transient,convergence,convert,gui,example}
  gui/          PySide 6 application (see section 5)
tests/          53 pytest tests (geometry, FVM, models, API, I/O, GUI offscreen)
examples/       example_board.pcbt.json, reference_board.pcbt.json, accuracy_study.py
```

## 2. Python API

```python
from pcbthermal import Problem, SolverOptions, simulate

p = Problem.new(width_mm=100, height_mm=80, layers=4)               # empty board
p.add_zone(1, rect=(15, 15, 85, 65)).add_full_copper([2, 3, 4])
p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)   # theta_jb: junction-to-board K/W
p.add_via_array((30, 35, 40, 45), 3, 3, diameter=0.3)
p.add_sink(4, 30.0, rect=(25, 30, 45, 50))                          # extra h on the bottom layer

sim = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=1.0))
print(sim.to_markdown())          # comparison table, warnings
print(sim.report())               # text report: hotspots, heaters (junction), zones
sim.save("results")               # summary.json, report.txt, field CSVs, PNG figures
sim.results["fvm"].T              # temperature field (layers, ny, nx) in degC
```

`SolverOptions` holds every setting (models, `cell_mm`, `linear_solver` direct/cg/sor, `lumped_rings`,
`analytic_modes`, `analytic_local_corrections`, `hotspot_c`) and validates them. Projects save
the problem, the options and the viewer state together (`save_project` / `load_project`).

## 3. Models

### 3.1 FVM (reference)

Cell-centred finite volumes, one node per layer and cell, slab thickness `t_pcb / N`.

Lateral sheet conductance of a cell (copper fill *f*, copper thickness *t*<sub>cu</sub>):
$S = f\,k_{cu}\,t_{cu} + k_{fr4,ip}\,(slab - f\,t_{cu})$, with the harmonic mean between cells:
$G_x = \frac{2S_1S_2}{S_1+S_2}\frac{dy}{dx}$. Vertical: $G_z = \frac{k_{fr4,th}\,dx\,dy}{d} + \sum_{vias}\frac{k_{cu}A_v}{d}$
with $A_v=\pi[(d_v/2)^2-(d_v/2-t_p)^2]$ (hollow) or $\pi(d_v/2)^2$ (filled). Ambient: $h_{top}dx\,dy$ on the top layer,
$h_{bot}dx\,dy$ on the bottom layer, sinks and edges. Heater power is spread over the covered cells by
coverage fraction, so the requested power is injected exactly on any grid.

Steady state $K\theta=Q$ ($\theta=T-T_{amb}$, $K$ sparse symmetric positive definite) with three interchangeable solvers:

- `direct`: sparse LU (default, exact),
- `cg`: Jacobi-preconditioned conjugate gradients,
- `sor`: vectorised red-black SOR, kept to compare with the method of the original program (stop by
  residual, or by the step size like the original).

The energy balance (heat out through top, bottom, sinks, edges minus power in) is reported and is at round-off level.
Transient (power step, implicit Euler or Crank-Nicolson, time step doubling in ten stages) is `fvm.solve_transient`: validated against an exact
exponential, on the command line (`transient --gif`) and in the GUI Animation tab.

### 3.2 Lumped (ring network per heater)

The model is the azimuthal average of the FVM network. For every heater the cells are binned in rings by the distance to the
heater centroid (ring 0 = footprint, outer rings grow geometrically). For every layer and ring, the real geometry is aggregated:

$$G_{lat}=\frac{2\pi f_{arc}\,\bar S}{\ln(r_{k+1}/r_k)},\qquad
G_{vert}=\sum_{cells}G_z,\qquad G_{amb}=\sum_{cells}(g_{top}+g_{bot}+g_{sink}+g_{edge})$$

$r$ is the rms radius of a ring and $f_{arc}$ the fraction of the circle inside the board (adiabatic edges: a heater in a
corner spreads over a quarter circle). Each heater gives a small dense system. The problem is linear, so the field is the
sum over heaters (mutual heating = radial profile of one heater interpolated at the other's distance). The peak in a
footprint adds $Q_{lat}/(8\pi S)$ (exact for a uniform disc).
Copper, vias, sinks and edges are seen where they really are, which fixed the 24 % error of the first version.

### 3.3 Analytic (cosine series with local corrections)

Multilayer fin equation on the rectangle with insulated edges, expanded in $\cos(m\pi x/W)\cos(n\pi y/H)$; every mode
is a small tridiagonal system over the layers (see the module docstring). Exact for a uniform board. Refinements:

- **Copper fill weighted by influence**: $f_{eff}=\sum w f/\sum w$, $w=\sum_i P_i K_0(r_i/\lambda)$, $\lambda=\sqrt{S/h}$.
- **Local vias and sinks** (Green-function / Woodbury update): vias and sinks are removed from the uniform problem and returned
  as lumped conductances $C$ on 2.5 to 5 mm tiles. With $G$ the modal response between tiles and $y_0$ the tile averages of the
  uniform solution, the tile temperatures solve $(I+GC)\,y=y_0$ and the injected heat $f=-Cy$ is added to the modes.
- **Warnings**: strong copper non-uniformity around the heaters, or significant edge convection (the model assumes insulated edges).

## 4. Command line

```sh
python -m pcbthermal example examples/example_board.pcbt.json --which example
python -m pcbthermal run examples/example_board.pcbt.json            # all models + report + plots in ./output
python -m pcbthermal run board.pcbt.json --model fvm --cell-mm 0.5 --solver cg
python -m pcbthermal solvers board.pcbt.json                         # direct vs CG vs SOR
python -m pcbthermal convergence board.pcbt.json                     # FVM grid refinement
python -m pcbthermal transient board.pcbt.json --t-end 600 --gif     # power step + animated GIF
python -m pcbthermal convert old_editor_export.json board.pcbt.json  # legacy editor JSON -> project
python -m pcbthermal gui [board.pcbt.json]                           # open the application
python -m pytest -q tests
```

## 5. Graphical application (PySide 6)

`python -m pcbthermal gui` (or `python -m pcbthermal.gui`). Dark and light themes, undo/redo, project files.

| Area | What it does |
| :-- | :-- |
| Board canvas | zoom (wheel), pan (middle button or Space), grid with snap, optional solver-mesh overlay, background photo with position/size/opacity |
| Tools | select/move, copper zone, heater, sink, via; rectangle by dragging, polygon mode by clicking vertices; corner handles reshape (rectangles stay rectangular) |
| Editing | move by drag or arrows, duplicate (Ctrl+D), delete, select all on layer, layer chooser (other layers dimmed), sinks only on outer layers |
| Left docks | board size, stack-up, environment, materials; element tree synchronised with the canvas |
| Right docks | model choice and solver settings with the Run button (F5, background thread, progress); property inspector (name, layer, power, θ junction-board, fill, extra h, via position and diameter, rectangle position and size) |
| Results | Summary (models table, warnings, text report), Temperature (all layers or one, colour map, range, hotspot contour), Gradients, Profiles (movable cut line, all models), Components (heater and junction temperatures, zone statistics, hotspot list), Models (comparison), Animation (real-time heat evolution: compute, play, scrub, export GIF) |
| Board overlay | paint the last temperature field on the board (key T); results are marked outdated when the design changes |
| Files | open/save projects, open legacy editor JSON, open examples, export results folder / TXT report / JSON summary / figures |

Features of the original program that were dropped on purpose: the "iterations GIF" (it showed solver iterations, not physical
time; it was replaced by the real-time Animation tab) and the pixel-corner board setup (the board is defined by its size in mm and
a background image can be fitted to it).

## 6. Verification (2026-10-16)

| Check | Result |
| :-- | :-- |
| Energy balance, all models | below 1e-9 (about 1e-13 for the FVM) |
| Uniform plate (heater = board, 1 layer, insulated) | FVM equals $P/((h_t+h_b)A)$ to 1e-6 K |
| Requested power injected for any cell size | exact |
| Grid convergence Tmax (reference board), 10 / 5 / 2 / 1 / 0.5 / 0.25 mm | 88.24 / 89.61 / 90.07 / 90.13 / 90.15 / 90.155 °C |
| Analytic vs FVM, insulated edges, 1 / 2 / 4 layers | 104.25 vs 104.31, 90.35 vs 90.39, 76.08 vs 76.10 °C |
| FVM size / speed | 320 000 cells in 4.6 s (direct), 3.3 s (CG) |
| Transient, reference board | steady 90.07 °C, 63 % time constant about 19 s |
| Tests | 53 pass: geometry, FVM, model agreement, API, I/O, SOR, GUI (drawing, editing, undo, simulation) |

### 6.1 Solver comparison: direct matrices vs SOR (example board, cell 1 mm)

```
Board 'example-4layer', cell 1 mm
solver                                                Tmax C  |dT| vs direct   residual   sweeps   time s
direct (sparse LU)                                   85.8143        0.00e+00    1.1e-13        -     0.26
cg (Jacobi)                                          85.8143        8.01e-12    1.1e-12        -     0.09
SOR, residual 1e-9, omega auto                       85.8143        1.10e-08    9.9e-10     2247     0.77
SOR, residual 1e-6, omega auto                       85.8143        1.09e-05    9.9e-07     1532     0.53
SOR, step 0.01 K, omega 1.5 (original program)       69.6449        1.65e+01    1.4e-01      562     0.19
```

Direct, CG and SOR with the residual criterion reach the same solution (differences down to 1e-8 K). The step-size rule of
the original program (0.01 K per sweep, omega 1.5) stops 4.7 K (2 mm cells) to 16.5 K (1 mm cells) away from the solution, with a visibly violated
heat balance, and the error grows when the mesh is refined, which is the false convergence found in the review of the old solver.

### 6.2 Accuracy of the simplified models against the FVM

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

Reading: the **Lumped** model is within about 10 % everywhere and within 1 % on the example board; its limit is the circular-spreading
assumption. The **Analytic** model is exact (below 1.5 %) on uniform boards and handles vias, sinks, corners and several layers;
it overestimates by 9 to 16 % when the copper on the heater layer is partial (it then shows a warning), where the FVM is the reference.

## 7. Known limits and next steps

- Radiation and natural convection are inside the constant `h`. Temperature-dependent `h(ΔT)` (Picard iteration) is the natural next step.
- Time-dependent power (pulses, duty cycles) in the transient and the GUI; components with junction/case resistances (JEDEC) beyond `theta_jb`.
- Copper traces with Joule heating (IPC-2152) and temperature-dependent copper resistivity.
- Reduced-order models for fast design sweeps; surrogate models for layout optimisation.
- Analytic: partial copper under the heater needs the FVM.
