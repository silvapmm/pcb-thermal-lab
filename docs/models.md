# Models: what they are, how they work, which one to use

PCB Thermal Lab solves the steady and time-dependent temperature of a PCB with **four models of the same physical description**. This document
explains the description, each model, the features built on top of them (power profiles, computed heat transfer coefficients), and gives a decision
guide. The numbers that back every statement are in [`validation.md`](validation.md); what is planned is in [`roadmap.md`](roadmap.md).

## 1. The physical description

A board has `N` copper layers (layer 1 = top), a total thickness, copper zones (polygons with a fill factor), heaters (power over a footprint on one layer),
plated vias, sinks (extra heat transfer on an outer face) and boundary conditions: ambient temperature and a heat transfer coefficient `h` on the top, bottom and edges.

* SI units inside the package; project files and the builder API use millimetres and 1-based layers.
* **Layered model**: every copper layer is a thin conducting sheet with in-plane sheet conductance
  `S = f·k_cu·t_cu + k_fr4,ip·(slab − f·t_cu)` (`f` copper fill, `slab = thickness/N`); the dielectric between two layers is a vertical conductance `k_fr4,th/d`
  per unit area (anisotropic FR-4: 0.3 W/mK through, 0.9 in plane); a via adds `k_cu·A_via/d` between all layers with `A_via = π[(d_v/2)² − (d_v/2 − t_plating)²]` (hollow) or `π(d_v/2)²` (filled);
  the top and bottom faces lose heat with `h_top`, `h_bottom`, sinks add `h_extra`, edges `h_side`.
* **Heater power** is injected exactly (it does not depend on the grid). Total heat out through the faces and edges equals the power in; every result reports that energy balance.
* Dependencies: NumPy, SciPy, Matplotlib; PySide 6 for the application; scikit-fem only for the offline 3D check. Virtual environment: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## 2. The four models

| | **FVM** | **FDM** | **Lumped** (thermal network, LPTN) | **Analytic** (Fourier series) |
| :-- | :-- | :-- | :-- | :-- |
| Role | reference | comparison | fast estimate | fast estimate, independent check |
| What it is | board cut into cells, one node per layer and cell, sparse matrices | the same equations on grid **points** (node-centred finite differences) | one small network per heater, built from the real footprint and outline | exact closed-form solution of a uniform multilayer board, with corrections for vias, sinks and copper |
| Time on the example board | 0.13 s (1 mm cells) | 0.12 s | about 10 ms | about 50 ms |
| Output | full field per layer | full field per layer (at nodes) | approximate field | field per layer |
| Power profiles in time, step animation | yes | no | profiles yes, animation no | yes (vias calibrated per heater) |
| Needs a mesh | yes (cell size, Auto) | yes | no | no |

### 2.1 FVM (finite volumes), the reference

Cell-centred finite volumes (`fvm.py`). One node per layer and cell; between neighbouring cells the conductance uses the harmonic mean of the two sheet
conductances (`G_x = 2 S₁S₂/(S₁+S₂)·dy/dx`), so a copper/FR-4 jump is a series combination. The steady problem is the sparse symmetric positive definite system `K θ = Q`
(`θ = T − T_amb`) solved with a **direct sparse LU** (default, with a symmetric minimum-degree ordering: half the fill and about 40 % less time than the default ordering), conjugate gradients, or red-black SOR (kept for
comparison). Transient: `C dθ/dt + K θ = Q`, theta-method (implicit Euler or Crank-Nicolson), time step doubling in ten stages so that only ten factorisations are needed.

*Use it* for final temperatures, any geometry (partial or hatched copper, copper edges anywhere, via arrays, thin or L-shaped heaters), whenever a warning appears, and to
confirm the fast models. Cost grows with cells × layers; the **Auto** cell size (about four cells across the smallest heater) is a good start.

### 2.2 FDM (finite differences), the comparison

Node-centred finite differences (`fdm.py`) of the same layered model: nodes on the board edges (`nx+1` by `ny+1`), edge nodes with half control volumes, the conductivity between
two nodes is the mean of the nodal values (arithmetic or harmonic), vias go to the nearest node. How the copper and the heater footprint reach the nodes is selectable:

* `sampling="area"` (default): the covered fraction of the control volume around each node. It removes the grid-to-grid scatter of point sampling and is exact for geometry that does not lie on the grid.
* `sampling="point"`: the classic "is the node inside the polygon" test (left and bottom edge in, right and top edge out).

Same equations as the FVM, so on boards without vias the two agree to about 0.1 % (table in `validation.md`). Differences: the FDM treats a via (a point feature) at the nearest node, which costs
about 2 % on the example board at 1 mm; near a copper edge that crosses a heater it is 3.5 % below the FVM. It is steady state only (no time simulation or animation).
*Use it* to check the FVM's discretisation or to see what a classic scheme gives; for design work the FVM is preferred (smoother with the grid, conservative by construction).
FDM is **not** the removed wxPython solver, which also had modelling errors (see `validation.md`).

**FDM or FVM, in one table**

| | FDM (finite differences) | FVM (finite volumes) |
| :-- | :-- | :-- |
| Idea | replace derivatives by differences between **node values** | integrate the equation over a **cell** and balance the heat through its faces |
| Unknown | temperature at a grid node | mean temperature of a cell |
| Conservation | by construction only with care at boundaries and interfaces | exact: what leaves one cell enters the next |
| Material jumps | need care at interfaces | the face conductance is the series of the two half cells |
| Point features (vias, sources) | sampled at the nearest node | averaged over the cell |

The linear solver (direct, CG, SOR) is a separate choice from the discretisation.

### 2.3 Lumped (thermal network)

A reduction of the FVM network (`lumped.py`). For every heater the cells are grouped in rings by their **distance to the heater footprint** (ring 0 is the footprint, outer rings grow geometrically),
so any heater shape and the real board outline are followed. For every layer and ring the geometry is aggregated; heat crosses offset contours of length `L_k = A_k/Δ_k`:
`R_{k,k+1} = Δ_k/(2 S_k L_k) + Δ_{k+1}/(2 S_{k+1} L_{k+1})`. The interior of the heated footprint comes from the logarithmic potential of the uniformly heated footprint, with the exact disc solution with vertical
losses (modified Bessel functions `I₀, I₁`: factors `f_R = 4(I₀ − 2I₁/x)/(x I₁)` for the resistance and `f_P = 4(2/x² − 1/(x I₁))` for the peak, `x = a/λ`, `λ = √(S/g_eff)`). Each heater gives a small dense
system; the problem is linear so the board is the sum over heaters (mutual heating is one heater's profile read at the distance of the other).
*Use it* for fast exploration and sweeps; it is weak when a copper edge crosses the heater, at corners (−8.7 %) and for thin heaters (+9.5 %).

### 2.4 Analytic (Fourier series)

The multilayer fin equation on the rectangle with insulated edges, expanded in `cos(mπx/W) cos(nπy/H)`: every mode is a small tridiagonal system over the layers (`analytic.py`). Exact on a uniform board. Refinements:

* **copper weighted by influence, layer by layer**: `f_eff,l = Σ w f_l / Σ w` with `w = Σ_i P_i K₀(r_i/λ_l)` and the layer's own fin length `λ_l = √(S_l/(h_l + n_l g))` (about 5 mm for a layer that carries a heater, not the 34 mm of the whole stack);
* **local vias and sinks** by a Green-function (Woodbury) update on 2.5 to 5 mm tiles: `(I + G C) y = y₀`;
* **warnings** when the copper around the heater is strongly non-uniform or edge convection is significant.

*Use it* for instant answers on boards close to uniform, to understand a design, and as an independent check. It fails when the copper is not uniform near the heater (24 % low with a 20 mm pad, 25 % when an edge crosses it);
the input checks warn.

### 2.5 Which model for which job

| You want | Use |
| :-- | :-- |
| the number you sign off, any geometry, hotspots, junction temperatures, time behaviour | **FVM** |
| a quick exploration or a parameter sweep | **Analytic** (uniform-ish boards) or **Lumped** (partial copper, several heaters), then confirm with the FVM |
| to see whether the grid or the scheme matters | compare **FVM** and **FDM** at two spacings |
| to know whether a fast model can be trusted on your board | run all four (`--model compare`); a spread above about 5 % means "use the FVM" |

Workflow: explore with Analytic/Lumped, refine with the FVM at the **Auto** cell size, change the cell size once to confirm convergence, read the warnings.

## 3. Input checks

`check_problem` (also run by `simulate` and live in the application under the Run button) never blocks a run; it warns about inputs that make a result doubtful: a heater partly outside the board
(its power would be moved onto the part inside), no copper under a heater, a copper edge or hatching crossing a footprint (Lumped and Analytic unreliable), a heater only a few cells wide, overlapping
heaters, vias or zones outside the board and zero total power.

## 4. Power profiles (time-dependent power)

A heater may carry a **square wave** (`SquareWave`: `p_on`, `period`, `duty`, `p_off`) or a **table** (`TableProfile`: times and powers, repeating or one-shot, read from and written to CSV files:
`profile_io.py`, format and a worked example in [`examples/csv_profiles/README.md`](../examples/csv_profiles/README.md)). The heater's `power` stays equal to the average, so steady models and old files work unchanged.

1. **Step response** `Z_i(t)` of every heater's own hottest point to a unit step of its power, from the reference model (FVM, else Lumped, else Analytic).
2. **Decision, per heater** (`profiles.decide`): by superposition the periodic response of a piecewise-constant power is `T(u) = Σ_j P_j [G(σ₂) − G(σ₁)]` with
   `G(σ) = Σ_{m≥0} [Z(σ + mT) − Z(mT)]` plus the tail `σ/T·(R_th − Z(MT))`; for a square wave `peak = P_off R_th + ΔP·G(t_p)`. The oscillation (peak minus valley) is in **°C**. Heaters are sorted by oscillation and
   *averaged* (smallest first) while their cumulative oscillation stays below the threshold (default 1 °C); the others are *resolved* in time. One-shot tables are always resolved. Percentages are shown for information only.
3. **Run** (`profiles.run_windows`, one runner for the models through an adapter): the step is a tenth of the shortest stretch, each step's power is the **exact mean** of the profile over the step, averaged heaters keep their
   constant power in the same run, the window is the least common multiple of the periods, and windows repeat until peak and minimum change by less than 0.1 °C ("until the cycle repeats"), for N cycles, or for a fixed time;
   more than 200,000 steps is refused with an explanation. Start: the steady state of the average power (the first power for a one-shot table) or a uniform temperature typed in °C.
4. **Results**: peak, minimum, oscillation, temperature of every heater versus time, peak-temperature map, frames of the last window, steady temperatures with the average and with the peak power (the bound).
5. **Analytic transient with vias and sinks**: one modal system per heater with the smeared via (or sink) conductance scaled so that its steady response equals the locally corrected steady model (factor 65 above the via
   array of the example, 1 for the distant heater); a single global factor cooled the distant heater by 18 %.

Interfaces: `SolverOptions.profile`, `steady_power` ("average" or "peak"); CLI `run --profile U1=file.csv --duration --cycles --time-s --initial-c --threshold-c --steady-power`; the "Power profile" tab with
**Import CSV…** / **Export CSV…**; outputs `profile_<model>.csv/.png`, `peak_map_<model>.png`.

## 5. Heat transfer coefficients: typed or computed

`Board.h_mode` is `"manual"` or `"computed"`. Computed (`convection.py`): each face gets `h = calibration × (h_n³ + h_f³)^(1/3) + h_radiation`, with natural convection on a horizontal plate
(up: `Nu = 0.54 Ra^(1/4)` to Ra = 1e7 then `0.15 Ra^(1/3)`; down: `0.27 Ra^(1/4)`; length = area/perimeter) or Churchill and Chu for a vertical board; forced laminar `Nu = 0.664 Re^(1/2) Pr^(1/3)` (mixed above Re = 5e5);
radiation `ε σ (T_s² + T_a²)(T_s + T_a)` to surroundings at the air temperature; air properties from Sutherland-type fits checked against textbook values. `h` depends on the mean face temperature, so `simulate`
repeats the model until the coefficients change by less than 0.01 W/m²K (3 or 4 solves). Settings: emissivity per face (default 0.9), orientation, air speed, a global multiplier of the convection (not of the radiation).
`api.calibrate_convection` / `pcbthermal calibrate board.json --measured 85 [--heater U1]` fits that multiplier to one measured steady temperature. Time simulation and animation use the steady-state coefficients with the average power.
Limits: isothermal-plate correlations are uncertain by 20 to 30 % on a board with hot spots; the edge coefficient is not computed; the radiation view factor is 1.

## 6. Python API and command line

```python
from pcbthermal import Problem, SolverOptions, simulate, suggest_cell_mm

p = Problem.new(width_mm=100, height_mm=80, layers=4)
p.add_zone(1, rect=(15, 15, 85, 65)).add_full_copper([2, 3, 4])
p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)      # theta_jb: junction-to-board K/W
p.add_via_array((30, 35, 40, 45), 3, 3, diameter=0.3)
p.add_sink(4, 30.0, rect=(25, 30, 45, 50))                               # extra h on the bottom layer

sim = simulate(p, SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=suggest_cell_mm(p)))
print(sim.to_markdown())      # models, error against the FVM, energy balance, warnings
sim.save("results")           # report, JSON, CSV fields, figures
```

```sh
python -m pcbthermal gui [board.pcbt.json]                      # application
python -m pcbthermal run board.pcbt.json [--model all|compare|fvm|fdm|lumped|analytic] [--cell-mm auto]
python -m pcbthermal run board.pcbt.json --computed-h --air-speed 1 --emissivity 0.85
python -m pcbthermal run board.pcbt.json --profile U1=u1.csv --profile U2=u2.csv
python -m pcbthermal calibrate board.pcbt.json --measured 85 --heater U1
python -m pcbthermal transient board.pcbt.json --t-end 300 --gif   # power step animation (FVM)
python -m pcbthermal solvers|convergence|convert|example ...        # solver comparison, grid study, legacy file, example boards
```

`simulate` runs the selected models (the FDM is steady state only), the input checks, the power-profile decision and time simulation, and returns a `Simulation` (table, report, `save`).

## 7. The application (PySide 6)

Board canvas with zoom/pan, grid snap, polygons, vias, sinks, undo/redo, background photo, dark and light themes; docks for the board, environment (typed or computed `h`), materials, element tree, models and settings,
live input checks and the property inspector; tabs **Board**, **Power profile** (heater list, constant / square wave / table with CSV import and export, decision table, run settings) and **Results** (summary, temperature,
gradients, profiles, components, model comparison, step-power animation, power-profile results). The temperature of the last run can be painted on the board (key T). The version is shown in the title bar, status bar and About box.
