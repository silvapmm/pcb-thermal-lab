# Which Model Should I Use?

PCB Thermal Lab 2.0.0 offers three models that solve the same problem at different cost and accuracy.
The numbers below come from the verification studies (`physics_core.md` section 7, `examples/accuracy_study.py`,
`examples/stress_study.py`); the reference is always the FVM.

## FDM or FVM? (names)

Both are ways of turning the heat equation into a matrix, and for a uniform grid with simple conduction they give the **same stencil**, so the numbers are close.

| | FDM (finite difference method) | FVM (finite volume method) |
| :-- | :-- | :-- |
| Idea | replace derivatives by differences between **node values** (Taylor expansion) | integrate the equation over a **cell** and balance the heat that crosses its faces |
| Unknown | temperature at a grid **node** | mean temperature of a **cell** |
| Conservation | not guaranteed: the power injected can depend on the grid and the nodes on the border need special care | exact: what leaves one cell enters the next, so power in = power out to machine precision |
| Material jumps (copper next to FR-4) | needs extra care at interfaces | the face conductance combines the two cells in series, naturally |
| In this project | the **original wxPython solver** (removed in 2.0.0): SOR, 8.17 W injected for 5.50 W requested on its default grid | the **current reference model** (`fvm`, "Finite volume (FVM), reference") |

So: when this documentation says FDM it means the old program; everything current is FVM. The FVM is not more accurate than the analytic model in general (see "Accuracy against an independent 3D solid"); it is the model with the freedom of geometry and an exact energy balance.
The linear solver (direct sparse, CG, SOR) is a separate choice: SOR is a way of *solving* the matrix, not a discretisation, and gives the same temperatures as the direct solver when it stops on the residual.

## At a glance

| | **FVM** (finite volumes) | **Lumped** (thermal network) | **Analytic** (cosine series) |
| :-- | :-- | :-- | :-- |
| What it is | the board cut into cells, one node per layer and cell, solved with sparse matrices | one small thermal network per heater, built from the real footprint and board outline | exact closed-form solution of a uniform multilayer board, with corrections for vias, sinks and copper |
| Accuracy | reference (grid-converged within 0.2 % from 1 mm cells) | within about 4 % in most cases, 9 % at worst | within about 2 % in most cases, exact on uniform boards |
| Time on the example board | 0.2 s (1 mm cells), 4.6 s for 320 000 cells | about 10 ms | about 50 ms |
| Output | full field of every layer, exact energy balance | approximate field, per-heater network | field of every layer, exact energy balance |
| Step-power animation | yes | no | no |
| Power profiles (square wave, time simulation) | yes, full field | yes, per-heater networks, frames indicative | yes, vias and sinks smeared (warned) |
| Needs a mesh | yes (cell size, "Auto" button) | no (internal raster) | no |

## Advantages and where to apply each

### FVM: the answer you sign off on

**Advantages**
- Handles any geometry: partial copper, hatched copper, copper edges anywhere, vias, sinks, several heaters, any layer count, polygonal shapes.
- Resolves the field, so hotspots, gradients, profiles, zone statistics and junction temperatures are meaningful.
- Conserves the injected power exactly (energy balance about 1e-13) and is mesh-converged: from 1 mm cells the maximum temperature is within 0.2 %.
- The only model with **transient response and animation**.
- Has three interchangeable matrix solvers (direct, conjugate gradients, SOR); all give the same temperatures when SOR stops on the residual.

**Apply it for**
- final temperatures, design sign-off and reports;
- any board that raises a warning (copper edge crossing a heater, heater near the board edge, no copper under a heater);
- via arrays, thermal pads, heat-sink footprints, thin or L-shaped heaters;
- heat-up and cool-down behaviour (time constants, animation);
- checking the two fast models on a new kind of board.

**Take care:** cost grows with cells × layers. Use the **Auto** cell size (about four cells across the smallest heater) and refine only if the answer changes.

### Lumped: fast exploration

**Advantages**
- Milliseconds per run, no mesh to tune.
- Built from the real geometry, so partial copper, vias, sinks and the board outline are seen where they are, and several heaters heat each other (superposition).
- Gives each heater's mean and peak temperature, and an approximate field for plots and hotspot lists.

**Apply it for**
- early design exploration and "what if" sliders;
- parameter sweeps with hundreds of runs (power, copper thickness, h, via count);
- a quick second opinion next to the FVM;
- ranking layout alternatives before running the FVM on the best ones.

**Avoid or double-check when**
- a copper edge crosses the heater (about -27 %: the circular contour assumption breaks);
- a heater sits close to a corner (about -9 %) or is long and thin (about +10 %);
- you need exact hotspot shapes (the field is a reconstruction).

### Analytic: understanding and independent verification

**Advantages**
- Instant, no mesh, and exact on boards with uniform copper (within 0.3 % of the FVM on the reference board).
- An **independent** computation (cosine series instead of finite volumes): when it agrees with the FVM, both are very likely right.
- Exposes the physics: the fin length `λ = sqrt(S / h)`, how far heat spreads, how much the layers share.
- Handles partial copper (within 2 %), vias and sinks through local corrections, corner heaters (+1 %) and multiple heaters.

**Apply it for**
- first estimates on boards with solid planes (typical power boards with a ground plane);
- verifying FVM results and mesh choices;
- explaining why a board is hot (spreading versus convection) and teaching;
- sweeps where the lumped model is not accurate enough.

**Avoid or double-check when**
- a copper edge crosses the heater (about -25 %: the model warns);
- edge convection matters (it assumes insulated edges; it warns when edge losses exceed 5 % of the face losses);
- the heater is not a rectangle (a polygon is replaced by the rectangle with the same area and centroid).

## Accuracy against an independent 3D solid
Independent 3D finite-element check (`examples/fem3d_validation.py`, scikit-fem, hexahedral elements, copper slabs of true thickness, anisotropic FR-4; 100 x 80 mm board, one 10 x 10 mm heater of 4 W, no vias, 0.5 mm cells in the models).
Maximum temperature of the top face; error is on the **temperature rise** against the 3D FEM (converged: element sizes in the table differ by less than 0.3 %):

| Case | 3D FEM (°C) | FVM | Lumped | Analytic |
| :-- | --: | --: | --: | --: |
| 4 layers, full copper | 90.6 | 90.3 (−0.4 %) | 89.2 (−2.2 %) | 90.8 (+0.2 %) |
| 2 layers, 40 x 40 mm top pad | 112.2 | 111.5 (−0.8 %) | 109.3 (−3.3 %) | 107.0 (−6.0 %) |
| 2 layers, 20 x 20 mm top pad | 136.4 | 133.7 (−2.4 %) | 128.6 (−7.1 %) | 109.8 (−23.9 %) |

Reading: the FVM is not "more accurate than the analytic model" in general. On a uniform board the analytic series is the exact solution of the same layered model the FVM approximates numerically (FVM error 0.4 % is mesh error), so both land on the 3D answer.
What the FVM has that the others lack is **freedom of geometry**: with partial copper the analytic model assumes a uniform sheet and fails first (the warning "a copper edge crosses or is near the heater" exists for this), the Lumped model is next.
The remaining 0.4 to 2.4 % of the FVM comes from representing each copper layer by one node and the dielectric between them as a one-dimensional vertical resistance (no lateral spreading inside the gap); vias and sinks are not in this table (they were not modelled in 3D).

## Decision guide

| Situation | Use |
| :-- | :-- |
| Final result, report, sign-off | FVM |
| Any warning about the input or a model | FVM |
| Heat-up behaviour, time constants, animation | FVM (Animation tab) |
| Several hundred design variants | Lumped, then FVM on the best |
| Board with solid planes, quick number | Analytic, confirmed by Lumped |
| New kind of board, trust check | all three; trust the FVM, a spread above about 5 % means "look closer" |
| Check that the FVM mesh is fine enough | `python -m pcbthermal convergence board.pcbt.json` |
| Learn what limits the temperature | Analytic (`fin_length_mm` in the result), then the FVM profiles |

## Recommended workflow

1. Draw the board and run **all three** models (the default). Look at the warnings first.
2. If the three agree within about 5 % and there are no warnings, the numbers are consistent.
3. If they differ, trust the FVM; the table shows each model's error against it.
4. For sweeps, use Lumped or Analytic, and confirm the interesting cases with the FVM.
5. Use the Animation tab when the temperature over time matters (duty cycles, thermal mass).
6. Validate the absolute numbers against a measurement of a real board when possible: all models share the same input (`h`, material properties),
   so a wrong `h` shifts them all alike.

## What none of the models covers yet

Temperature-dependent convection and radiation (a constant `h` is used), 3D effects inside components, copper trace Joule heating,
time-dependent power other than a square wave (pulse trains, arbitrary shapes). Square-wave profiles are supported, see `roadmap.md` section 1. See [`candidate_methods.md`](candidate_methods.md).
