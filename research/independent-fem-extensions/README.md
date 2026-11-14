# Extensions of the independent finite-element comparison tool (plan)

**Status: planned, nothing solved.** This folder reopens `research/independent-fem-edge` (its `lib/` is imported, never copied or edited here) for
`research/ROADMAP.md` A43 and the item 'FEM extensions (A43)' of `docs/versions.md` 'Planned: 2.8.0'. Every cost below is an ESTIMATE
(`scripts/study_plan_costs.py`, 3000 bytes per unknown assumed from the order of magnitude of `independent-fem-edge` README 5; the first run of
study 1 replaces it by a measured number). No number of the program is quoted that a script of this folder has not printed.

## 1. What the tool is today, and what is missing

Read from `independent-fem-edge/lib` (`board.py`, `fem.py`, `cases.py`): a steady, hexahedral Q1 conduction solver on a graded plan mesh extruded
through the layers (copper, graded gaps), copper by polygon or callable on element centroids, vias as conforming cylinders (`r_drill`, `r_in`, `k_fill`),
heaters on the top copper (volume or surface source), Robin films on faces and walls, symmetry planes, CG with the scaled AMG above 60 000 unknowns.

**Correction to the brief.** The brief says a Crank-Nicolson integrator exists. In this tool it does NOT: `fem.py` has no capacity matrix and no density or
specific heat (the README 7.6 item 6 says 'it needs a time integrator'). The Crank-Nicolson of the repository is the program's (`fvm.transient_*`),
which is what would be checked, so it cannot be the reference. Study 5 therefore builds the capacity matrix too.

| Capability | In the tool | Missing for (a) cluster under a tab | Missing for (b) transient |
| :-- | :-- | :-- | :-- |
| solid barrel | yes (`k_fill` 385) | - | - |
| hollow plated barrel (`r_in`, resin core) | field exists, no case, never compared | a case at the program's wall (25 um) with the O-grid fine enough for the wall (3 elements through it) | - |
| copper tab block with a heat source on it | no (heaters are on the top copper layer) | a block region: extra z slabs over a plan polygon (copper tab, then solder) with the source in the tab volume | - |
| solder layer | no | a slab of conductivity `k_solder` (about 50 W/mK, an assumption stated per case) under the tab, with an optional void fraction | - |
| plate underneath with an interface | no (only films) | a bottom slab (aluminium) with an interface slab, film below | - |
| stripes, masks (validation 40, 45) | stripes aligned with mesh lines yes; masks need sampling | centroid classification on a mask callable for imported-copper truths (study 3) | - |
| L outline | polygon plan yes (T exists) | an L case (study 4) | - |
| capacity `C = rho c V` | no | - | element `rho c` (copper 8960 x 385, FR-4 1850 x 1100, solder, aluminium), lumped or consistent mass |
| time integrator | no | - | Crank-Nicolson (and implicit Euler as a check), one factorisation (or AMG-CG per step), power as a function of time |
| square-wave read-out | no | - | the periodic-state read-out: the 5th period peak, minimum and the heater-mean curve |

## 2. Studies, in order

Each study names the synthetic board of ours that exercises it, what it answers, the expected cost and the independent checks. 'Runs now' means under
2 GB (estimate; the maintainer's machine is shared, so heavier runs wait for the lock to clear).

### Study 1. Hollow plated barrel against the program's barrel (answers: is `d + 0.5 t_cu` and the Peaceman well right for a wall of 25 um, or only for the solid cylinder of `independent-fem-edge` 3(b)?)
Board: 10 x 10 mm, 4 layers (gaps 0.487 mm, the board of 3(a)), one via of 0.3 mm drill at 0.16 and 3 mm from the wall, 0.5 W on a pad, quarter symmetry
where the geometry allows it; `r_in = r_drill - 25 um`, resin core `k_fill` 0.3, against `k_fill` 385 as the control, program at 1, 0.5, 0.25 mm. Also a 3 x 3
array at 1 mm pitch. Output: the via effect E (as 3(b)) for the three fills and the two programs.
Cost: 1a about 360 000 unknowns, 1.1 GB, a few minutes: **runs now**. 1b about 1.2 million, 3.6 GB: waits.
Checks: (i) the hollow barrel with `k_fill` = `k_cu` must equal the solid one to 1e-6 (same mesh); (ii) closed form of the barrel conductance
`k_cu pi (r_o^2 - r_i^2) / L` against the FEM barrel in a 1D column (all other conduction removed), within 2 %; (iii) wall resolved with 2, 3 and 4 elements: the
change of E below 0.5 %; (iv) energy balance of the tool (< 1e-6) and the mesh halving 0.2 / 0.1 / 0.05 mm as in 3(b).

### Study 2. Part on a tab over a via cluster, plate underneath (answers: is the program's cluster (the footprint of cells, Peaceman wells, and the Lumped dense group) within what percent of the finite elements, for the board that matters most?)
Board (figure 1): 20 x 20 mm, 4 layers, a 6 x 6 mm copper tab (0.2 mm) with solder (0.1 mm, `k` 50, stated) under it, 1 W in the tab, a 5 x 5 via cluster at 0.8 mm
pitch under the tab, 1.0 mm aluminium plate under the board through a 0.1 mm interface (`k` 3), films 10 W/m2K on the free top, 10 on the plate. Variants: no vias
(control), vias hollow, vias with a partly missing rim (the rim rule), the tab 3 x 3 mm. Program: FVM and FDM at 0.5 and 0.25 mm, with the block and heatsink path
as the program models them (a metal block of thickness, a heater on the tab footprint), the 3D solid and the Lumped. The two sides must model the same
contact: the model comparison states which program inputs encode the tab and the solder (a heater with `base_interface` for the solder, the block for the tab).
Cost: 0.1 mm quarter about 360 000 unknowns, 1.1 GB: **runs now**; 0.05 mm 1.4 million, 4.3 GB and 0.025 mm 5.8 million, 17 GB: **wait** (two levels are needed
for the Richardson check, so the 0.1 mm result alone is flagged unconverged).
Checks: (i) no-via variant against a 1D series closed form under the tab plus the 3D layered helper `tests/helpers/layered3d.py` read only as a cross-check
(it is the program-side independent solver, not the tool); (ii) energy balance; (iii) refinement 0.2 / 0.1 / 0.05 mm with the observed order (as `refine.py`);
(iv) the solder slab removed and set to `k_cu` must equal the tab-only run.

### Study 3. Stripes and imported masks (answers: do the truths of validation 40 and 45 hold against a tool of different construction?)
Boards of validations 40 and 45 reproduced as FEM boards: stripes aligned to the mesh (exact), then a mask callable sampled at 8 x 8 points per element
(the copper fraction of the element decides k by volume mixing, parallel in-plane, series through). Cost: about 520 000 unknowns, 1.6 GB: **runs now** for the
aligned stripes; the 45-degree mask needs a finer plan mesh and waits. Checks: a checker mask at fill 0.5 against the exact mixing formula; stripes
against the 1D parallel-series closed form; refinement.

### Study 4. The L outline (answers: the reflex corner of an L, as the T already covers)
Two layers, 20 mm arms, copper to the wall and inset 1.2 mm, 200 W/m2K. Cost: about 600 000 unknowns, 1.8 GB, borderline: **runs now, one level**; the
refinement level waits. Low priority (README 7.6 item 4). Checks: mirror-image symmetry of the L, energy balance, refinement.

### Study 5. The transient reference and the square-wave profiles (answers: the program's time to 63 %, step responses and fast-wave swing against a reference of a different construction)
Tool additions (in `lib/`, written here, tested small): element capacity with `rho c`, lumped mass (positivity of the scheme) and consistent mass as an option,
Crank-Nicolson with implicit Euler as a check, one sparse factor of `C/dt + theta K` kept for a fixed `dt` (or AMG-CG per step above the direct limit), a
power function of time, the periodic read-out (period 5 peak, minimum, heater mean curve). Boards: the step response on case 2 (no cluster first), and a square wave
of 1 W at 1 Hz and 20 Hz with 10 % and 50 % duty on a 30 x 20 mm two-layer board with a 6 mm part, which is the board of `research/fast-wave-oscillation`
(its independent Cartesian reference exists there; this tool is the second, differently built, check).
Cost: the mesh of 2a with 400 steps: the factor once, then 400 solves of about 360 000 unknowns: minutes and about 1.1 GB if the factor fits (else AMG-CG per step,
about an hour): **the small board and the first steps run now; the cluster board and the 20 Hz run (steps of 5 ms over 5 periods) wait for a quiet machine**.
Checks: (i) the single-cell lumped RC exact exponential (a 1-element column with a film); (ii) a 1D slab against the eigenseries; (iii) the plateau equals the
steady solve of the same board; (iv) the energy balance in time (stored plus lost equals input); (v) halving `dt` (CN second order: error ratio 4) and the mesh.

## 3. Order and cost summary

| # | Study | unknowns (est.) | memory (est.) | time (est.) | runs now |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | hollow barrel, one via | 0.36 M | 1.1 GB | minutes | yes |
| 2 | tab over cluster, 0.1 mm | 0.36 M | 1.1 GB | minutes | yes (unconverged); finer levels wait |
| 3 | stripes, aligned | 0.52 M | 1.6 GB | minutes | yes; 45-degree masks wait |
| 4 | L outline | 0.6 M | 1.8 GB | minutes | one level |
| 5 | transient and square wave | 0.36 M and 400 solves | 1.1 GB if factored | minutes to an hour | small board yes; the rest waits |

## 4. Figures planned

| Figure | Script | Shows |
| :-- | :-- | :-- |
| fig_01_cluster_cross_section.png (drawn) | `make_diagrams.py` | the section of case 2 with the heat paths (not to scale) |
| fig_02_hollow_barrel.png (drawn) | `make_diagrams.py` | plan and section of the hollow barrel, the program's length `d + 0.5 t_cu` |
| fig_03_barrel_via_effect | `make_figures.py` (to write) | E against fill and cell, program columns against the FEM |
| fig_04_cluster_error | `make_figures.py` | program error against the FEM of case 2 against cell, per model |
| fig_05_temperature_section | `make_figures.py` | the FEM temperature field in the vertical section through the cluster |
| fig_06_step_response | `make_figures.py` | the step response and the 63 % time, program against FEM |
| fig_07_square_wave | `make_figures.py` | the periodic swing, program against FEM |

## 5. Limits and what was not verified

* The costs are estimates; the constant of bytes per unknown is assumed, not measured here.
* The conductivities of the solder (50 W/mK), the interface (3 W/mK) and the plate are our assumptions for a synthetic board, not a datasheet; the studies
  compare the program with the FEM on the SAME inputs, so the assumption cancels in the comparison, not in an absolute number.
* The program's input for a tab and a solder layer must be settled in the first reading of the program (study 2); if no input expresses it, the comparison is
  restricted to the block and the interface path, and the note says so.
* The tool compares the layered model's idealisation with a resolved board; the transient reference is of the same physics (no radiation, constant properties).
* Not read or run here: nothing from `independent-fem-edge/lib` was run; the code was read for the capabilities table.

## 6. What was read and what was not verified

Read in full: `independent-fem-edge/INTEGRATION.md`, `lib/board.py` and `lib/cases.py` headers and signatures, the README sections 3(b), 7.6; the brief
(`releases/2.8.0/opinions/2026-11-14-overnight-plan.md`, A43 text) and `docs/validation.md` headings 28, 40, 43, 45. Not read: the bodies of `fem.py` and `mesh2d.py`
beyond their signatures. No source outside the repository was opened in this planning pass; the formulas named in the checks (series and parallel mixing, the
1D slab eigenseries, the exact RC exponential) are textbook and are to be written with their citations when the studies run.
