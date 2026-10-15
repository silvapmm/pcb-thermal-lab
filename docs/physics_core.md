# Physics Core (`pcbthermal`): Models, Formulas, Verification

New, GUI-independent physics package that replaces the solvers in `core/`
(reviewed in [`thermal_models.md`](thermal_models.md)). Branch `feature/physics-core`,
2026-10-16. Everything runs from the command line and the three models share one
problem description, so their results can be compared directly.

- SI units everywhere inside the package (m, W, K, W/mK, W/m²K, J/kgK, kg/m³).
- JSON files use millimetres and 1-based layer numbers (layer 1 = top).
- Dependencies: NumPy, SciPy (solvers), Matplotlib (plots only, `plots.py`).

## 1. Layout

```
pcbthermal/
  model.py      Board, Materials, Zone, Heater, Via, Sink, Problem; JSON readers/writer;
                reference_problem(); problem_from_legacy() for the old editor format
  geometry.py   shoelace area, centroid, vectorised point-in-polygon, cell coverage fractions
  fvm.py        reference model: finite volumes, steady (sparse direct / CG) and transient
  lumped.py     ring-network LPTN solved exactly
  analytic.py   multilayer cosine-series (modal) solution
  results.py    SteadyResult, TransientResult (energy balance built in)
  plots.py      field maps, profiles, comparison, convergence, transient
  cli.py        python -m pcbthermal {run,transient,convergence,convert,example}
tests/          30 pytest tests (geometry, FVM verification, model agreement, I/O, CLI)
examples/reference_board.json
```

## 2. Command line

```sh
python -m pcbthermal example examples/reference_board.json      # write the reference board
python -m pcbthermal run examples/reference_board.json          # all three models + plots in ./output
python -m pcbthermal run board.json --model fvm --cell-mm 1 --solver cg --out results
python -m pcbthermal transient board.json --t-end 600 --theta 0.5   # Crank-Nicolson step response
python -m pcbthermal convergence board.json                      # FVM grid refinement table + plot
python -m pcbthermal convert editor_export.json board.json       # legacy editor JSON -> native JSON
python -m pytest -q tests                                        # run the test suite
```

`run` prints a table (Tmax, Tmean, ΔT, Rθ, power in, energy-balance error, run time) and writes
`summary.json`, `field_<model>_layer1.csv`, `fields_<model>.png`, `comparison.png` and
`profiles.png`.

Native JSON (millimetres):

```json
{ "board":   {"width_mm":100, "height_mm":100, "thickness_mm":1.6, "layers":2,
              "copper_thickness_mm":0.035, "ambient_c":25, "h_top":10, "h_bottom":15, "h_side":10,
              "k_copper":385, "k_fr4_through":0.3, "k_fr4_inplane":0.9, "via_plating_mm":0.025},
  "zones":   [{"layer":1, "polygon_mm":[[0,0],[100,0],[100,100],[0,100]], "fill":1.0}],
  "heaters": [{"layer":1, "power_w":5, "polygon_mm":[[40,40],[60,40],[60,60],[40,60]]}],
  "vias":    [{"x_mm":50, "y_mm":50, "diameter_mm":0.3, "filled":false}],
  "sinks":   [{"layer":1, "polygon_mm":[[30,30],[70,30],[70,70],[30,70]], "h_extra":50}] }
```

`h_side: null` makes the edges insulated. `copper_thickness_mm` may be a list (one value per layer).

## 3. FVM model (reference)

Cell-centred finite volumes on an `nx × ny` grid (cell `dx × dy`), one node per layer and cell.
A node represents a slab of thickness `slab = t_pcb / N`.

**Lateral sheet conductance** of a cell in layer *l* (copper fill *f*, thickness *t*<sub>cu</sub>):

$$S = f\,k_{cu}\,t_{cu} + k_{fr4,ip}\,(slab - f\,t_{cu}) \quad [\mathrm{W/K}]$$

Between neighbouring cells the harmonic mean is used (two half cells in series):

$$G_x = \frac{2 S_1 S_2}{S_1+S_2}\frac{dy}{dx},\qquad G_y = \frac{2 S_1 S_2}{S_1+S_2}\frac{dx}{dy}$$

**Vertical conductance** between layers (dielectric of thickness $d = (t_{pcb}-\sum t_{cu})/(N-1)$,
via barrels in parallel with the dielectric):

$$G_z = \frac{k_{fr4,th}\,dx\,dy}{d} + \sum_{v\in cell}\frac{k_{cu}\,A_v}{d},\qquad
A_v = \pi\left[(d_v/2)^2-(d_v/2-t_p)^2\right]\ (\text{hollow}),\ \ \pi (d_v/2)^2\ (\text{filled})$$

**Ambient conductances** per cell: top $h_{top}\,dx\,dy$ on layer 1, bottom $h_{bot}\,dx\,dy$ on layer N
(both on layer 1 for a single layer), sinks $h_{extra}\,dx\,dy\cdot cov$, edges
$h_{side}\,dy\cdot slab$ (or $dx\cdot slab$) on boundary cells.

**Sources**: each heater power is spread over the covered cells with weights equal to the
coverage fraction (sub-sampled 8×8), so the injected power is exactly the requested power for any
grid. A heater smaller than the sampling goes to its centroid cell.

**Heat capacity**: $C = \left(f\rho_{cu}c_{cu}t_{cu}+(slab-f t_{cu})\rho_{fr4}c_{fr4}\right)dx\,dy$.

**Steady state** (rise $\theta = T-T_{amb}$): sparse symmetric positive definite system

$$K\,\theta = Q$$

solved by sparse LU (`method="direct"`, default) or Jacobi-preconditioned CG (`"cg"`). The residual
and the **energy balance** (heat out through top, bottom, sinks and sides minus power in) are
reported; the balance is at round-off level (about 1e-13).

**Transient** (power step from ambient): θ-method

$$\left(\tfrac{C}{\Delta t}+\theta K\right)x^{n+1} = \left(\tfrac{C}{\Delta t}-(1-\theta)K\right)x^{n} + Q$$

with θ = 1 (implicit Euler, robust) or 0.5 (Crank-Nicolson, second order). Both are unconditionally
stable. Output times are log-spaced by default; one LU factorisation is reused per interval. The 63 %
time constant is interpolated from the curve.

## 4. Analytic model

Exact modal solution of the multilayer fin equation for a **uniform** board with insulated edges:

$$S_l\nabla^2\theta_l - h_l\theta_l - g\,(2\theta_l-\theta_{l-1}-\theta_{l+1}) = -q_l$$

Expanding in $\cos(m\pi x/W)\cos(n\pi y/H)$ turns it, for every mode, into a small tridiagonal system

$$\left[\mathrm{diag}(S_l k_{mn}^2+h_l)+g\,\mathcal{L}\right]a_{mn}=q_{mn},\qquad k_{mn}^2=(m\pi/W)^2+(n\pi/H)^2$$

($\mathcal L$ is the path-graph Laplacian over the layers, $g=k_{fr4,th}/d$ plus vias smeared over the board).
The heater projection is closed-form for rectangles (non-rectangular heaters use the rectangle with the same
area and centroid). Mode $(0,0)$ is the uniform board $P/(hWH)$. The characteristic fin length is
$\lambda=\sqrt{S/h}$ (about 34 mm on the reference board): heat spreads over roughly λ around the source.

## 5. Lumped model (ring network)

Heater footprint = disc of equal area; board = disc of equal area; the annulus between them is split into
geometrically growing rings (default 8). Nodes: layers × (rings + 1).

$$G_{lat}=\frac{2\pi S}{\ln(r_{k+1}/r_k)}\ (\text{area-mean radii}),\qquad
G_{vert}=\frac{k_{fr4,th}A_k+k_{cu}A_{vias,k}}{d}$$

Convection, sinks and edges attach to the rings in proportion to their area. A dense solve gives the node
temperatures; the peak inside the footprint adds the exact uniform-disc relation
$T_{peak}-T_{mean}=Q_{lat}/(8\pi S)$.

## 6. Verification (2026-10-16)

Reference board: 100×100 mm, 2 layers, 35 µm copper full planes, 5 W / 20×20 mm heater centred on layer 1,
h<sub>top</sub>=10, h<sub>bot</sub>=15, edges h=10 (FVM, cell 1 mm).

| Check | Result |
| :-- | :-- |
| Energy balance, all models | below 1e-9 (round-off, about 1e-13) |
| Uniform plate (heater = whole board, 1 layer, insulated) | FVM equals $P/((h_t+h_b)A)$ to 1e-6 K |
| Requested power injected for any cell size (10 to 1 mm, 4 mm heater) | exact |
| Grid convergence Tmax: 10 / 5 / 2 / 1 / 0.5 / 0.25 mm | 88.24 / 89.61 / 90.07 / 90.13 / 90.15 / 90.155 °C |
| Analytic vs FVM, insulated edges, 1 / 2 / 4 layers | 104.25 vs 104.31, 90.35 vs 90.39, 76.08 vs 76.10 °C |
| Lumped vs FVM, 1 / 2 / 4 layers | +4 to +6 % on ΔT |
| Old merged-sheet assumption (perfect vertical coupling) | 79 °C, 12 % too low (FR-4 under the heater is 13 K/W) |
| FVM size / speed | 320 000 cells in 4.6 s (direct), 3.3 s (CG) |
| Transient, reference board | steady 90.07 °C, 63 % time constant about 19 s, reaches steady state |

Accuracy of the simplified models against the FVM (ΔT error):

| Case | Lumped | Analytic |
| :-- | --: | --: |
| Reference, centred heater | +6.0 % | +0.3 % |
| Small heater 5 mm, 3 W | +6.6 % | +0.5 % |
| 8 layers | +5.9 % | +1.0 % |
| Heater near a corner | -18.2 % | +1.2 % |
| 25 hollow vias under the heater | +9.7 % | +13.3 % |
| Sink 40×40 mm (+100 W/m²K) | +18.2 % | +44.8 % |
| Copper only 40×40 mm around the heater | +22.5 % | +57.2 % |

Reading: the **Analytic** model is excellent on uniform boards (it is an exact solution) and degrades when properties
are not uniform (partial copper, sinks, local vias). The **Lumped** model is a fast ±6 % estimate for centred
heaters but ignores board edges and non-uniform copper. The **FVM** is the reference: use it whenever geometry matters.

## 7. Known limits and next steps

- Radiation and natural convection are inside the user's `h` (constant). A temperature-dependent
  $h(\Delta T)$ with a Picard iteration is the natural next step.
- The FR-4 in-plane conductivity default (0.9 W/mK) is 3× the through-plane value (0.3), typical of glass-woven FR-4.
- Components, enclosures and 3D effects are not modelled.
- Lumped: add edge effects and local copper (ring model assumes a heater far from the edges and uniform copper).
- Analytic: local vias, sinks and partial copper are only averaged; consider a hybrid using the FVM correction.
- Time-dependent power (pulses, duty cycles) in `solve_transient`.
- Adaptive mesh refinement near heaters.
