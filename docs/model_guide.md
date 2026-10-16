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

### Why the FVM and the Analytic model give about the same numbers (and where they do not)

1. **They solve the same model.** Both treat every copper layer as a thin conducting sheet, the dielectric between layers as a vertical resistance, one constant `h` per face, the same material properties. The Analytic model is the **exact** solution of that model on a uniform sheet (a cosine series); the FVM is a **numerical** solution of the same equations. Two correct solutions of one model must agree: on the uniform cases they differ by 0.2 to 1 %, which is the FVM mesh error (cell 1 mm).
2. **The real board is not that model, and that error is shared.** The independent 3D finite-element solid (`model_guide.md`, "Accuracy against an independent 3D solid") shows the layered model itself is within 0.4 to 2.4 % of the true 3D conduction on these boards, and the literature reports 1 to 4 % between layered analytical models and finite elements and about 4 to 5 % against measurements on a real four-layer board [L5], [L6].
   Neither the FVM nor the Analytic model can be better than the layered model they share, so "FVM = more precise" does not hold in general. **No model of the program has been compared with a measurement of a physical board yet.**
3. **Part of the agreement was engineered.** The Lumped and Analytic models were tuned against the FVM (copper weighted with the heater influence, fin lengths, Bessel factors). The accuracy tables (`physics_core.md` 7.2, 7.3) measure agreement *with the FVM*, which is why the 3D check was added: it does not depend on that tuning.
4. **Where they differ, and why it matters.** The Analytic model assumes a uniform effective sheet around the heater, so it fails when the geometry is not uniform near it: 6 % with a 40 mm copper pad, **24 % with a 20 mm pad** and 25 % when a copper edge crosses the heater; the Lumped model degrades more gently. The FVM keeps within 2.4 % in the same cases because it resolves the copper cell by cell.
   For time dependence the FVM is the reference; the Analytic transient needs a per-heater calibration of the vias (`physics_core.md` 3.4).
5. **What each is for.** Analytic: instant, exact on uniform boards, good for understanding and as an independent check. FVM: any copper shape, exact energy balance, and the answer to confirm with when a warning appears.

### Literature on FDM, FVM and PCB thermal models

* [L1] Finite volume methods are built from an integral balance on each cell, so the discrete solution satisfies the energy balance globally and locally; finite differences work on point values of the differential equation (R. Eymard, T. Gallouët, R. Herbin, *Finite Volume Methods*, https://raphaeleh.github.io/PUBLI/bookevol.pdf; *Finite Volume Method in Heat Conduction*, Encyclopedia of Thermal Stresses, https://link.springer.com/rwe/10.1007/978-94-007-2739-7_896).
* [L2] Khouider, *Finite difference and finite volume methods for transport and conservation laws* (lecture notes), https://www.pims.math.ca/files/Khouider_1.pdf: conservation form is what makes finite volumes preserve the conserved quantity.
* [L3] A comparison of the two methods on 1D steady heat conduction (https://link.springer.com/chapter/10.1007/978-981-97-0037-0_9) is reported by a search summary as giving almost the same results, with FDM needing many more iterations; the chapter is behind a login and was **not read**, so no figure from it is used here.
* [L4] Commercial electronics-cooling tools use the finite volume method: Ansys Icepak, Siemens Flotherm (structured Cartesian grid) and Cadence Celsius (see `roadmap.md`, reference 13).
* [L5] *A modeling method for thermal steady-state simulation of the four-layer printed circuit board*, PMC11410250, https://pmc.ncbi.nlm.nih.gov/articles/PMC11410250/ (text read): Fourier-series solutions for the insulating layers combined with a lateral-only finite volume discretisation of the metal layers, the same architecture as our FVM plus Analytic pair; error against COMSOL about 1.8 to 2.5 % at the hot region and 4 to 5 % against measurements of the IC surface temperature on a real board, solver time under 9 minutes against about 50 minutes for COMSOL.
* [L6] Fourier-series analytical models of multilayer structures compared with finite elements: 1 to 4 % in the studies found by a search (https://researchonline.jcu.edu.au/86884/ and others); figures taken from search summaries, not from the full texts.

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
