# Extensions of the independent finite-element comparison tool (plan)

**Status: planned and reviewed (section 7: GO for the plan as corrected here), nothing solved.** This folder reopens `research/independent-fem-edge`
(its `lib/` is imported, never copied or edited here) for `research/ROADMAP.md` A43 and the item 'FEM extensions (A43)' of `docs/versions.md`
'Planned: 2.8.0'. Every cost below is an ESTIMATE printed by `scripts/study_plan_costs.py` (unknowns counted on plan meshes built by the tool's own
mesh functions; memory from the peaks the tool measured, section 3); the first run of each study replaces it by a measured number. No number of the
program is quoted that a script of this folder has not printed.

## 1. What the tool is today, and what is missing

Read from `independent-fem-edge/lib` (`fem.py`, `mesh2d.py`, `board.py` in full; `cases.py` for the builders; the review read the bodies, the first
pass of the plan only the signatures). There is no `asm.py`: the assembly is `fem.Model._assemble_elements` and `_assemble_faces`.

* `fem.Model`: a steady, isoparametric trilinear (Q1) hexahedral solver; per element a diagonal conductivity `(kx, ky, kz)` and a volumetric source
  `q`; Robin faces `h (T - T_amb)` with a consistent face mass and a per-node ambient; a prescribed face flux; 2 x 2 x 2 Gauss. Solve: SuperLU in
  symmetric mode up to `direct_max` (default **60 000** unknowns), above it CG with a pyamg smoothed-aggregation preconditioner (pyamg only in
  `independent-fem-edge/.venv-research`). Unused nodes are dropped, so elements can be removed freely (a hole, a slab that covers only part of the plan).
* `mesh2d`: graded tensor axes (`grid1d`), O-grid patches whose circles are mesh levels (`ogrid`, `embed_ogrid`), the disc, `Quad2D.remove`.
* `board.Board`: a plan mesh extruded through ALL slabs of the stack (copper layers, graded gaps); copper per layer by polygon (even-odd per polygon,
  union of polygons; a plane with antipads needs a callable) on quad centroids; vias as cylinders by plan centroid **through every slab of the
  extrusion**; heaters only in the top copper layer (volume source, or a prescribed flux with no film under it); films on the top, bottom and every wall slab.

**Corrections of the first plan.** (1) The brief says a Crank-Nicolson integrator exists in the tool: it does NOT. `fem.py` has no capacity matrix,
no density or specific heat, no time loop (confirmed by reading the whole file); the Crank-Nicolson of the repository is the program's theta method
(`fvm.transient_*`), which is what is checked, so it cannot be the reference. (2) `Board` cannot express a slab that covers only part of the plan
(tab, solder, a plate smaller than the board): every slab spans the whole plan, so those slabs are a new builder that extrudes and then removes the
elements outside their polygon, and adds the films on the new free faces (top and sides of the tab, bottom and sides of the plate) by hand. (3) The
via loop of `Board.build` would also turn the new tab, solder, interface and plate slabs into copper: the builder must restrict the barrel to the board
slabs. (4) An open barrel cannot be `k_fill = 0` (the core nodes would have no stiffness and the matrix would be singular): the core quads are removed
from the plan (a hole through the board, adiabatic inner wall, as the program's open barrel). (5) Under a 2 GB budget the default `direct_max` of
60 000 is too high (2.73 GB was measured at 59 000 unknowns): pass `direct_max=30000`.

| Capability | In the tool | Missing for the studies |
| :-- | :-- | :-- |
| solid barrel | yes (`k_fill` 385, 3(b)) | - |
| hollow plated barrel | fields `r_in`, `k_fill` exist, never run | O-grid levels at `r_in` and 3 to 4 rings across the 25 um wall; open barrel as a hole (correction 4) |
| tab and solder over a polygon, source in the tab | no | partial slabs (correction 2), source in the tab elements, films on the tab |
| plate under the board through an interface | no (films only) | partial slabs under the board (correction 2); via barrel kept out of them (correction 3) |
| stripes | aligned with mesh lines: yes | a builder |
| imported masks | no | a mask callable on centroids of a mesh that RESOLVES the features (section 2, study 3) |
| L outline | polygon plan yes (the T exists) | a builder |
| capacity `C = rho c` | no | element mass (lumped and consistent) |
| time integrator | no | implicit steps and a frequency-domain solve (study 5) |

![The section of study 2](figures/fig_01_cluster_cross_section.png)
*Figure 1 (fig_01_cluster_cross_section.png): the section of study 2 with the heat paths, not to scale.*

![The hollow barrel](figures/fig_02_hollow_barrel.png)
*Figure 2 (fig_02_hollow_barrel.png): plan and section of the hollow barrel and the program's barrel length `d + 0.5 t_cu`.*

## 2. Studies (corrected by the review; order and green light in section 4)

'Runs now' means: the estimated peak of one solve is under 2 GB (`study_plan_costs.py`), the script builds the mesh, prints the unknowns and the
estimate, and refuses above the budget; one heavy run at a time on the shared machine.

### Study 1. Hollow plated barrel against the program's barrel
Question: is `d + 0.5 t_cu` with the Peaceman well right for a plated wall of 25 um, or only for the solid cylinder of `independent-fem-edge` 3(b)?
And the FDM via effect 4 to 16 % low at 0.25 mm (A43): every program row carries the FDM column.
Board: exactly the 3(b) board (`cases.strong_edge`: 10 x 10 mm, 4 layers 35 um, gaps 0.487 mm, FR-4 0.3 / 0.3, 0.5 W on 3 x 2 mm, h_top 10,
h_bottom 200, h_side 200 and 1000, half domain), the via of 0.3 mm drill at 0.16 and 3 mm from the wall, so that the solid cylinder of 3(b) is the
control already computed. Barrel `r_in = r_drill - 25 um` with three cores: open (the hole), resin `k_fill` 0.3, copper `k_fill` 385. Program: FVM
and FDM at 1, 0.5 and 0.25 mm with `Via(diameter 0.3 mm, fill_k 0 / 0.3 / 385)`, `board.via_plating` 25 um (the same annulus: the program's drill
includes the plating). 1b: a 3 x 3 array at 1 mm pitch, the middle row on the symmetry line. Output: E (as 3(b)) for the three cores, both programs.
Checks: (i) `k_fill = k_cu` with `r_in` set equals the solid cylinder on the same mesh (round-off: the matrix is the same); (ii) the closed form of
the barrel conductance `k_cu pi (r_o^2 - r_i^2) / L` against a FEM column with the laminate set to a negligible conductivity, within 1 %; (iii) the
wall with 2, 3 and 4 elements: E moves less than 0.5 %; (iv) the plan meshes 0.2 / 0.1 / 0.05 mm with the observed order (`refine.py`), and the
balance (a real check with CG, an identity with the direct solve).

### Study 2. Part on a tab over a via cluster, plate underneath
Question: how far are the program's cluster (FVM and FDM footprint of cells with Peaceman wells, the 3D solid, the Lumped dense group, the
Analytic tiles) from the finite elements on the board that matters most, and how much does the program's idealisation of the part itself add?
Board (figures 1 and 3): 20 x 20 mm, 4 layers 35 um, 1.6 mm, FR-4 0.3 / 0.9, full copper on every layer; **a 4 x 4 cluster at 0.8 mm pitch** (the
first plan had 5 x 5: a 5 x 5 array puts nine vias on the two symmetry planes of the quarter, and some via centres of a 4 x 4 or 6 x 6 array at other
pitches fall on the program's cell lines, the stated limit of the 3D solid; 4 x 4 at 0.8 mm centred at (10, 10) mm sits off every line of the 1, 0.5,
0.25 and 0.125 mm grids and off both symmetry planes), drill 0.3 mm, hollow with resin `fill_k` 0.3; 1 W; the part 6 x 6 mm (7..13 mm, on cell lines)
and a 4 x 4 mm variant (8..12 mm; the first plan's 3 x 3 mm edge at 8.5 mm is not on the 1 mm grid); a 1.0 mm aluminium plate (k 204 W/mK, rho c
2.44 MJ/m3K, the program's defaults, so that both sides take the same values) under the whole board through a 0.1 mm interface of 3 W/mK; h_top =
h_bottom = 10, h_side 10.
* **Variant A, the program's problem** (solved by both sides): the heat is a uniform volume source in the top copper over the footprint (the
  program's heater), the top face convects also under it (as in the program); the plate and the interface as above. The part temperature is
  `T_max(footprint) + P t_s / (k_s A)` on both sides (solder 0.1 mm, 50 W/mK: 0.056 K at 6 x 6 mm), so the comparison is of the board.
* **Variant B, the part resolved** (finite elements only): a 0.2 mm copper tab with the source in its volume and 0.1 mm of solder (50 W/mK) under
  it; no film on the board under the tab, films on the tab top and sides. B minus A is the error of the program's part idealisation (uniform flux plus
  a series offset instead of a nearly isothermal tab spreading through the solder); A against the program is the error of its discretisation.
* Variant with a partial rim: the copper of layer 2 ends on a line through one column of the cluster (expressible by a zone in the program and by a
  polygon in the tool), so that the rim rule acts.
Program inputs (section 5.1): `Heater` on layer 1, role 'source', `base_pad_thickness` 0.1 mm, `base_pad_k` 50; 16 `Via`; one `Heatsink` block on the
last layer (thickness 1 mm, k 204, rho_cp 2.44e6, `pad_thickness` 0.1 mm, `pad_k` 3, `h_extra` 0). Models: FVM and FDM at 0.5 and 0.25 mm, the 3D
solid, the Lumped and the Analytic (steady).
Checks: (i) a 1D column of the new stack (one plan element, insulated walls, uniform source) against the series closed form `exact.series_stack`
extended to the tab, solder, interface and plate slabs, to 1e-9 (the first plan named `tests/helpers/layered3d.py`, which cannot take a plate, and a
1D closed form under the tab, which a spreading problem does not obey); (ii) the solder at `k_cu` equals the tab directly on the copper; (iii) the
balance; (iv) the plan meshes 0.2 / 0.1 mm now and 0.05 mm on a quiet machine: the 0.1 mm value with two levels is flagged unconverged until then.

### Study 3. Stripes and imported masks (validation 40 and 45)
The boards of validations 40 and 45 as FEM boards. Stripes aligned with mesh lines are exact (the centroid decides). **Correction**: the first plan
mixed the copper by its fraction in each element (volume mixing, parallel in the plane, series through); that is the program's own cell fill and would
share the assumption under test. The truth must RESOLVE the copper: elements of at most a quarter of the narrowest feature, centroid classification,
and a mesh sequence. Checks: stripes against the 1D parallel and series closed forms on a strip board; a 2D checkerboard sheet (copper and laminate
sheets alone, no laminate below) against Dykhne's `sqrt(S1 S2)` (from memory, status M: the source must be opened before it is relied on); refinement.
The masks at 45 degrees need a fine plan everywhere and wait.

### Study 4. The L outline
Two layers, 20 mm arms, copper to the wall and inset 1.2 mm, 200 W/m2K, the heater of the T (`cases.t_outline`) moved into one arm. Low priority
(README 7.6 item 4 of `independent-fem-edge`: the T covers the reflex corners). Checks: mirror symmetry of the L about its diagonal, balance, refinement.

### Study 5. The transient reference (design decided in section 7.3)
Question: the program's time to 63 %, step responses and square-wave swing against a reference of a different construction, on the cases the
existing references cannot take.
* **Existing references, no new code** (`research/fast-wave-oscillation/lib`): `axisym_stack.Reference` (axisymmetric finite volumes diagonalised
  once: the step response and the periodic state of a square wave in closed form per mode) and `review_rect3d` (Cartesian 3D finite volumes of the
  rectangle in the frequency domain, partial copper, vias as copper columns). They already cover the plain and partial-copper boards and the square
  waves of `docs/validation.md` 37. The first plan's board ('30 x 20 mm two-layer with a 6 mm part, the board of fast-wave-oscillation') was wrong: that
  folder's board is 60 x 40 mm, 1.6 mm, parts of 2, 5 and 10 mm.
* **Tool addition, small** (`lib/transient.py` here, importing `fem.Model`): element capacity `rho c` (copper 8960 x 385, FR-4 1850 x 900 = the
  program's `Materials`, solder, aluminium 2.44e6), lumped mass (row sums, positive for Q1 bricks) and consistent mass as a check; (a) implicit steps,
  `(M/dt + theta K) T = ...`, Crank-Nicolson with two implicit-Euler steps after every power switch (Rannacher's start: Crank-Nicolson is not
  L-stable, and the thin copper elements are stiff modes that ring after each edge of a square wave), implicit Euler as the check, `dt` growing
  geometrically for a step response (one factor per `dt` level up to 30 000 unknowns, CG with a fixed AMG hierarchy above); (b) the periodic state of a
  square wave from the harmonic sum of complex solves `(K + i k w M) T_k = F_k` (no time step, no start-up; complex SuperLU only up to 30 000 unknowns).
* **Time step and mesh at 20 Hz** (corrected): the first plan's 5 ms steps cannot resolve a 10 % duty at 20 Hz (5 ms on: one step). Steps of at most
  1/20 of the shortest stretch (0.25 ms) or the frequency form (b). The penetration depth in FR-4 at 20 Hz is 0.06 mm (`fast-wave-oscillation`
  README 3): the gap needs about 20 graded elements with a first element of a few um, not the 6 elements of ratio 1.4 (first 0.17 mm) of the steady boards.
* Program side: the Lumped and Analytic transients refuse a metal block (`blocks.require_no_blocks`), so on the study 2 board only the FVM and FDM
  have a step response.
Checks: (i) a column with a film and lumped mass against the exact exponential; (ii) a 1D slab against its eigenseries (Carslaw and Jaeger, to be
cited with the page when the study runs); (iii) the plateau equals the steady solve; (iv) the energy in time (stored plus lost equals the input);
(v) halving `dt` (ratio 4 for Crank-Nicolson); (vi) **the disc board against `axisym_stack`** (same physics, a method of a different family: the
check of the new integrator before any program comparison); (vii) the periodic state by (a) and by (b) on the same mesh.

![The mapping of study 2](figures/fig_03_program_mapping.png)
*Figure 3 (fig_03_program_mapping.png): the part resolved (variant B), the same board as the program takes it (variant A), and the program inputs.*

![The transient design](figures/fig_04_transient_design.png)
*Figure 4 (fig_04_transient_design.png): which transient reference covers which case and where they are checked against each other.*

## 3. Cost summary

Printed by `.venv/bin/python research/independent-fem-extensions/scripts/study_plan_costs.py` (a few seconds, no solve). Memory: 8.5 kB per unknown
for CG + AMG (the upper value measured by the tool: 2.78 GB at 327 000 unknowns; a fresh process 0.93 GB at 138 000), 46 kB per unknown for the
direct solve (2.73 GB at 59 000), the direct solve only up to 30 000 unknowns. The first plan assumed 3000 bytes per unknown (2.8 times too low) and
counted about three times too many unknowns (2a: 360 000 assumed, 160 000 counted at 0.1 mm).

| Case | unknowns (est.) | GB (est.) | solver | under 2 GB |
| :-- | :-- | :-- | :-- | :-- |
| 1a hollow barrel, d 0.16 / 3.0 mm, hf 0.2 | 27 462 / 28 566 | 1.26 / 1.31 | direct | yes |
| 1a same, hf 0.1 | 58 190 / 62 215 | 0.49 / 0.53 | cg+amg | yes |
| 1a same, hf 0.05 | 146 832 / 160 540 | 1.25 / 1.36 | cg+amg | yes |
| 1b 3 x 3 array, hf 0.2 / 0.1 / 0.05 | 88 596 / 142 600 / 273 240 | 0.75 / 1.21 / 2.32 | cg+amg | yes / yes / WAIT |
| 2 tab over cluster, plate, quarter, hf 0.2 / 0.1 | 91 272 / 160 357 | 0.78 / 1.36 | cg+amg | yes |
| 2 same, hf 0.05 / 0.025 | 343 048 / 1 210 009 | 2.92 / 10.29 | cg+amg | WAIT |
| 3 stripes aligned, 20 mm square, quarter | 23 085 | 1.06 | direct | yes |
| 4 L outline, hf 0.2 / 0.1 | 40 500 / 110 250 | 0.34 / 0.94 | cg+amg | yes |
| 5 fast-wave board, quarter, hf 0.4 / 0.2 / 0.1 | 27 600 / 59 248 / 142 968 | 1.27 / 0.50 / 1.22 | direct / cg+amg / cg+amg | yes |

## 4. Order and green light (decided by the review, section 7.4)

1. **Study 1** (a builder only, no tool change): 1a at 0.2, 0.1, 0.05 mm and 1b at 0.2 and 0.1 mm **run now**; 1b at 0.05 mm waits.
2. **Study 2, variant A, then B**: the partial-slab builder and its 1D check first; 0.2 and 0.1 mm **run now** (flagged unconverged); 0.05 mm waits
   for a quiet machine (about 3 GB), 0.025 mm (about 10 GB) is not planned.
3. **Study 5**: the tool addition and checks (i) to (vii) on small meshes **run now**; the fast-wave board at hf 0.4 / 0.2 / 0.1 **runs now** (frequency
   form only at 0.4); the step response of the study 2 board at 0.2 mm runs now, at 0.1 mm after study 2 has passed its checks.
4. **Study 3**, aligned stripes **run now**; masks wait.
5. **Study 4**, both levels **run now**, last.
The code of later studies may be written while an earlier one runs (writing is not a heavy job).

## 5. Limits and what was not verified

* The costs are estimates from built plan axes and the tool's earlier peaks; nothing was solved in this pass.
* The solder (50 W/mK), the interface (3 W/mK, 0.1 mm) and the plate are our choices for a synthetic board, not a datasheet; the comparison takes
  the SAME inputs on both sides, so the choice does not enter the program error, only the absolute number.
* The transient reference has the physics of the layered program (constant properties, no radiation).
* `axisym_stack` and `review_rect3d` are reused as they were reviewed in `research/fast-wave-oscillation`; they are not re-reviewed here.

### 5.1 What the program can express (read from `pcbthermal/model.py` and `blocks.py`)

* **A heat source**: `Heater` on any copper layer, a polygon, a power spread uniformly in the copper node(s) of its footprint; the face under it
  still convects. **No input for a copper tab or any body above the top copper.**
* **Solder or paste under a source**: `Heater.role = 'source'` with `base_pad_thickness` and `base_pad_k` (or `base_interface` in K cm2/W). It is a
  **read-out offset only**: `junction_theta() = (t / k) / A` is added to the hottest board temperature under the footprint (`analysis.part_split`); it
  does not spread, has no capacity and does not change the board field.
* **A plate under (or on) the board**: `Heatsink` with `thickness > 0` on the first or last layer: one node layer (isothermal through its thickness),
  lateral conduction `k t`, capacity `rho_cp t`, contact `c A [f / R'' + (1 - f) / (R'' + d / k)]` with `R'' = pad_thickness / pad_k` (or `contact_r`)
  and `f` the copper fill of the board layer; exposed face `h_face x fin ratio + h_extra`, sides `h_face + h_extra`; the board face under it loses
  nothing; cut at the outline. The Lumped and Analytic take it in the steady state only.
* **Vias**: `Via(x, y, diameter, fill_k)`, through every layer (no blind via), plating `board.via_plating` inside the drill; barrel length
  `d + 0.5 t_cu`; rim shares from the zones.
* So the FEM problem that is THE SAME as the program's is variant A of study 2; variant B is a different, more real problem whose difference from A
  is the program's part idealisation, reported as such and never as a discretisation error.

## 6. What was read and what was not verified

Read in full: `independent-fem-edge/lib/fem.py`, `mesh2d.py`, `board.py`, the builders of `cases.py` used here, its README sections 1, 2, 3(b), 5,
6, 7.6; `pcbthermal/model.py` (Heater, Via, Heatsink, Materials) and `pcbthermal/blocks.py` (header and the functions named); the headers of
`research/fast-wave-oscillation/lib/axisym_stack.py` and `review_rect3d.py` and that folder's README sections 1 to 3. Not opened: Dykhne's
checkerboard result and the slab eigenseries of Carslaw and Jaeger (from memory, status M, to be cited with pages when the studies run); Rannacher's
start-up is a known remedy (M). Nothing was solved; `study_plan_costs.py` builds plan axes only.

## 7. Review

Independent review of the plan (the planning pass read only signatures; the review read the code bodies and the program inputs). **Verdict: GO for
the plan as corrected in sections 1 to 5; no run has been made, so there is nothing to confirm numerically yet.**

### 7.1 Findings, by severity

1. **Defect of the plan, study 5**: the tool has no capacity and no integrator (confirmed); the plan's 20 Hz run (5 ms steps) could not resolve a
   5 ms on-time; the gap mesh of the steady boards (first element 0.17 mm) cannot resolve a 0.06 mm penetration depth; the plan's board was not the
   fast-wave board (60 x 40 mm, not 30 x 20). Corrected in section 2.
2. **Defect of the plan, study 3**: volume mixing of the copper in an element is the program's own cell fill; as a truth it would share the
   assumption under test. Corrected: resolved copper.
3. **Defect of the plan, study 2 (mapping)**: the program cannot express a tab, and its solder input is a read-out offset; a FEM with the tab
   compared directly with the program would mix the idealisation of the part with the discretisation. Corrected: variants A and B (section 2, figure 3).
4. **Defect of the plan, study 2 (geometry)**: a 5 x 5 cluster puts vias on the symmetry planes; the 3 x 3 mm tab is off the 1 mm grid. Corrected:
   4 x 4 at 0.8 mm, tabs 6 x 6 and 4 x 4 mm.
5. **Defect of the plan, costs**: 3000 bytes per unknown against 6.7 to 8.5 kB measured with CG + AMG and 46 kB with the direct solve; the unknown
   counts about three times high. Section 3 now holds counts from built axes. Consequence: the direct limit of the tool (60 000) exceeds a 2 GB budget.
6. **Tool limits not in the plan**: partial slabs, the via loop through every slab, the singular open barrel (section 1, corrections 2 to 5).
7. **Check that did not apply**: `tests/helpers/layered3d.py` cannot take a plate, and a 1D closed form does not hold under a tab on a 20 mm board;
   replaced by the 1D column of the new stack against `exact.series_stack`.

### 7.2 The memory constant against the tool's measurements

`independent-fem-edge` README: CG + AMG 0.93 GB at 138 000 unknowns (fresh process, 6.7 kB per unknown) and 2.78 GB at 327 000 (whole-study process
peak, 8.5 kB); direct 2.73 GB at 59 000 (46 kB) and 5.2 GB at 138 000 (stopped). The plan's 3000 B is 2.2 to 2.8 times low for CG + AMG and 13 to 15
times low for the direct solve. The assembly keeps triplets of 64 entries per element (about 1.5 kB per element) besides the matrix and the AMG
hierarchy, which is where the per-unknown cost comes from. 8.5 kB is used as the upper value.

### 7.3 Transient: a new integrator in the tool, or a closed form plus the FEM for steady states?

Neither alone. (b) alone, a closed form or a 1D modal reference with the FEM only for steady states, cannot give the time to 63 % or the swing of a
board with spreading, a plate or vias: a 1D column has no lateral spreading, and the board's slow time constant is set by its lateral spreading and
its films. (a) alone would build a second copy of what `research/fast-wave-oscillation` already has (an axisymmetric modal reference and a Cartesian
frequency-domain reference, both reviewed) for the plain and partial-copper boards. **The cheapest defensible design**: reuse those two references
for what they cover; add to the FEM only the capacity matrix with an implicit step (Rannacher-started Crank-Nicolson, implicit Euler as the check) and
the frequency-domain periodic solve, about 150 lines on top of `fem.Model`; check it against closed forms and against `axisym_stack` on the disc
board (the FEM has the disc mesh), and only then use it for the cases no other reference takes (the plate and the cluster of study 2, conforming
hollow vias). The time integrator is of the same family as the program's, which is acceptable because the reference is converged in `dt` (halving)
and in the mesh: the independence is in the spatial method.

### 7.4 Decisions (delegated by the maintainer)

* **Order**: 1, 2 (A then B), 5, 3, 4 (section 4). Study 1 needs no tool change and answers the first item of A43; study 2 is the board that
  matters most; the transient reference is the other wave-2 priority, and its code may be written while 1 and 2 run.
* **Synthetic values accepted**: solder 50 W/mK (bulk tin-lead is about 50, SAC305 about 58 to 60, from memory, M), interface 0.1 mm at 3 W/mK
  (0.33 K cm2/W, inside the range of pastes and thin pads, M); the solder offset is 0.056 K at 6 x 6 mm, so its value barely enters; the plate takes
  the program's aluminium defaults (k 204, rho c 2.44 MJ/m3K). Both sides take the same inputs.
* **Cleared to run now (under 2 GB, one at a time, the mesh guard printing the estimate)**: study 1a at 0.2 / 0.1 / 0.05 mm; 1b at 0.2 / 0.1 mm;
  study 2 (A and B, and the rim variant) at 0.2 / 0.1 mm; study 5 tool checks (i) to (vii), the fast-wave board at hf 0.4 / 0.2 / 0.1 mm and the step
  response of the study 2 board at 0.2 mm; study 3 aligned stripes; study 4 at 0.2 / 0.1 mm.
* **Wait for a quiet machine**: 1b at 0.05 mm (2.3 GB), study 2 at 0.05 mm (2.9 GB); masks at 45 degrees. Not planned: study 2 at 0.025 mm (10 GB).
* **For the maintainer, not decided here**: whether variant B (the part resolved) should lead to a program feature (a tab or a spreading term
  under a part); that is a proposal only after the numbers exist.

### 7.5 Not verified by the review

Nothing was run: no mesh was assembled or solved; the cost table counts plan axes (the O-grid patch and the tab region are added by rule, not
built). `axisym_stack` and `review_rect3d` were read by their headers, not re-run. The pyamg environment (`independent-fem-edge/.venv-research`) was
not checked on this machine.
