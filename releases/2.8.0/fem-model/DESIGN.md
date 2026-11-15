# The finite-element model `fem`: design for 2.8.0

**Status**: design only (branch `docs/fem-model-design`); nothing of `pcbthermal/`, `tests/` or `requirements.txt` is changed by it. **Decision taken by the maintainer** ('let us go to 2.8.0 and implement the FEM that we created'): the independent finite-element tool of `research/independent-fem-edge` and `research/independent-fem-extensions` becomes a model of the program, exposed **exactly as the FDM and the 3D solid are today**: a checkbox 'Finite elements (FEM), comparison' in the Models box of the Simulation settings, off by default, never the reference of a decision. This reverses the 2.7.0 opinion 'a comparison reference, not a sixth model' (`releases/2.7.0/final-opinion/fem-reference-opinion.md` 2, `fem-worth-it.md` 6); this file does not argue that decision, it makes it safe. Where a fact measured here corrects a statement of those opinions it is said (section 1.4).

Every number below is either printed by a script of the repository (named with it) or by `releases/2.8.0/fem-model/scripts/measure_fem_cost.py` (this folder; run it to reproduce section 5.3). Nothing was run on a measured board.

## Contents

1. What the model is for, and what it is not
2. The physics, as the research tool implements it (explicit form)
3. From a `Problem` to a mesh: the missing piece
4. Dependencies and licences
5. Program architecture
6. The compare workflow and 'which model to trust'
7. Time simulation: a second stage
8. Validation plan
9. Frozen numbers
10. Documents, tests and diagrams to produce
11. Work breakdown into branches
12. Risks
13. Questions for the maintainer
14. What was read, measured and not verified

## 1. What the model is for, and what it is not

### 1.1 Where it adds something no current model has

The five models share two ideas that the finite elements do not: one value per cell (or node) per copper layer, and links between cell values. The 3D solid already drops the first one for the laminate (real slabs) but keeps one cell through each copper slab and the cell-centred links. The research tool is a **continuous nodal field on hexahedra conforming to the material interfaces** (`research/independent-fem-edge/lib/fem.py`): trilinear (Q1) bricks, Galerkin weak form, 2 x 2 x 2 Gauss, the Robin film as the natural boundary integral on the real face. Concretely, what it resolves that no current model does:

| Situation | Current models | The FEM | Evidence |
| :-- | :-- | :-- | :-- |
| **Through-thickness gradient inside a thick metal layer or block** (the surface hotter than the column mean) | one value through each copper slab (FVM, FDM, Lumped, Analytic, and the 3D solid's copper slab); case 2 of Muzychka, Culham and Yovanovich (2003) reads 2.0 / 4.6 / 3.7 / 2.9 K below the published surface centroids after `fix/face-film-half-slab` | several elements through the plate: the top-face nodes ARE the surface; the paper's surface is the target (to be measured, 8.2) | `docs/validation.md` 55.1 (the column-mean term 2.06 / 4.70 / 3.82 / 2.94 K of the independent 3D reference) |
| **Hollow plated barrel** (25 um wall, open, resin or copper core) | a lumped barrel area in a well (FVM, FDM), a rod of the barrel area (3D solid), constriction formulas (Lumped, Analytic) | a conforming cylinder: O-grid levels at the drill and at the inner radius, 2 to 4 elements across the wall | `research/independent-fem-extensions` 8.1 (wall area 0.993 of the annulus at 8 sides per quarter; via effect converged to 0.02 % across the wall) |
| **The edge film on the real wall** | half-cell film in series, cut-cell apertures and the centroid film (FVM, 3D solid), the node on the edge (FDM) | `h N_i N_j` integrated on the wall face, every wall slab, no half cell | `research/independent-fem-edge` 3, `docs/validation.md` 46 |
| **Curved outline and a via drill** | the cover fraction of a cut cell | nodes on the circle (inscribed 4 n-gon, chord error O(h^2)) | `research/independent-fem-edge` 2 (order 2.45 / 2.12 on the disc) |
| **A partial slab** (a tab, solder, a plate smaller than the board, an interface) | blocks as a node layer (FVM, FDM) or slabs (3D solid) | elements removed outside the polygon, films on the new free faces | `research/independent-fem-extensions` 8.2 (`lib/stack_ext.py`) |

### 1.2 Where it does not add anything (said in the tooltip and the user guide)

* **Imported copper** (Gerber masks): the copper of a real board is a raster of pixels; a mesh conforming to every pixel edge is out of reach (`fem-worth-it.md` 2: millions of elements). The FEM reads a mask as the copper fill of each element (as the 3D solid does), so on an imported board it is a 3D solid with a different stencil, not a better answer. It warns.
* **Slanted or curved copper edges that are not mesh lines**: classified per element (fill fraction), same remark.
* **Ordinary boards**: on a plain four-layer board with full copper the FEM, the 3D solid and the FVM agree to 0.2 % (5.3: 29.306 / 29.271 / 29.253 K). It costs 1.1 to 2.8 times the 3D solid's time on the same plan size (5.3).
* **Time simulation**: not in the first stage (section 7). Steady state only, like the 3D solid.
* **The Lumped and Analytic questions** (rings, modes) and the decisions of the power profiles: the FEM is a comparison model, never the reference of `profiles.decide` (as `COMPARISON_MODELS` today).

### 1.3 Name, key and labels

| Where | Text |
| :-- | :-- |
| model key (`api`, CLI, project, harness) | `fem` |
| checkbox (Simulation settings, Models box, after the 3D solid) | `Finite elements (FEM), comparison` |
| `results.MODEL_LABELS`, Results model combo, report tables, `plots.model_label` | `FEM` |
| card of the map on the board (`gui/fieldscale.MODEL_SHORT`) | `FEM` |
| memory guard messages (`memory.MODEL_LABELS`) | `finite elements (FEM)` |
| CLI | `--model fem`; `--model compare` = `fvm, lumped, analytic, fdm, solid3d, fem` |

### 1.4 What the measurements of this design correct in the 2.7.0 opinions

* 'It would need scikit-fem': it does not. The solver is ours (NumPy, SciPy); scikit-fem is used by one optional cross-check test of the research folder only (`fem-reference-opinion.md` 1 already said so).
* 'SuperLU reached 5.2 GB at 138 000 unknowns': true for the direct solve. With conjugate gradients and a pyamg preconditioner the tool takes **6.8 to 7.8 kB per unknown** from 48 000 to 291 000 unknowns, which is **less than the 3D solid per unknown** on the same boards (9.2 to 14.1 kB; table 5.3). The memory argument against an in-program FEM does not hold once pyamg is used; the time argument partly holds (5.3).
* 'No mesh generator for an arbitrary outline with arbitrary copper': still true, and it is the largest piece of new work (section 3). The design does not add a mesh generator; it builds structured meshes from the program's geometry and refuses or approximates what they cannot hold, with the reason (3.4).

## 2. The physics, as the research tool implements it (explicit form)

Symbols as `docs/theory.md` 0. The domain `Ω` is the board as a solid (copper slabs, laminate gaps, metal blocks and their interface pads); `θ = T − T_amb`.

**Field equation** (steady, orthotropic, piecewise constant per element):

    −∇·(K ∇θ) = q   in Ω,      K = diag(k_x, k_y, k_z)                                                   (F.1)

with, per element: copper `k_x = k_y = k_z = k_cu`; laminate `k_x = k_y = k_ip`, `k_z = k_th` (`Materials.k_fr4_inplane`, `k_fr4_through`; an advanced stack-up gives each gap its own `Dielectric`); a mixed element (a copper edge or an imported mask not on a mesh line) the volume average of the fill `f`, `k_x = f k_cu + (1 − f) k_ip`, `k_z = f k_cu + (1 − f) k_th` (the 3D solid's rule of `docs/theory.md` 4, so that the two differ only by the method where the geometry is not resolved); a block element `k_metal`, an interface pad `K_PAD = 1 W/mK` with the thickness `R'' · 1 W/mK` (as `solid3d.K_PAD`).

**Boundary conditions** (Robin, natural):

    −K∇θ·n = h_f θ        on every outer face f                                                          (F.2)

* top and bottom faces of the board: `h_top`, `h_bottom` (manual, or computed by the Picard loop of `api._solve_computed_h`, unchanged: it reads the face means from the result), **also under a part** (the program's convention: the part is a source in the copper, the face still convects; the research option `source_mode="surface"` is used only by the published-case tests);
* a heatsink without thickness: `h_top + h_extra` (or `h_bottom + h_extra`) on the face elements inside its polygon;
* the walls: `h_side` on **every wall slab** (copper and laminate), on the real outline (aligned or snapped, 3.2);
* a metal block: its exposed face `h_exp = h_face r_fin + h_extra`, its walls `h_wall = h_face + h_extra` (`blocks.wall_h`), the board face it covers has no film;
* an open via barrel: the inner wall is adiabatic (the hole is removed from the mesh, `independent-fem-extensions` 1, correction 4).

**Weak form and discretisation** (Q1, `fem.Model`):

    Σ_e ∫_e ∇N_i·K_e ∇N_j dV  θ_j  +  Σ_f ∫_f h_f N_i N_j dA  θ_j  =  Σ_e ∫_e q_e N_i dV                    (F.3)

2 x 2 x 2 Gauss on each brick (exact for an affine brick with constant K), 2 x 2 on each face (the consistent face mass). **The film term is inherent**: there is no half-cell resistance to add in series with `h` (contrast `docs/theory.md` 1.2a and 4.1): the face nodes carry the face temperature. The matrix is symmetric positive definite; the heat balance `Σ_f ∫ h θ dA = Q` is an identity of a consistent assembly and is printed for every solve (it checks the assembly and the solve).

**Sources**: the power `P` of a part is a uniform volumetric source in the copper elements of its layer under its polygon, `q = P / (A t_cu)` with `A` the exact area under the polygon (exact when the polygon edges are mesh lines; otherwise the elements take the share of their area under the polygon, 3.3). The top path of a part (`api._top_path_split`), the power temperature coefficient and the computed coefficients wrap the model as they wrap the others (they read `T`, `t_max` and the face means of the result).

**Vias**: a conforming cylinder of radius `r_drill` through the board slabs (not through a block or a pad), the plating `r_drill − r_in = Board.via_plating` in copper, the core open (removed), resin or copper (`Via.fill_k`). Where the conforming patch cannot be built (3.3), the barrel falls back to the 3D solid's rod: the barrel copper area spread over the elements of the drill disc (`k_z` parallel mix), with a warning.

**What is NOT modelled** (stated in the theory and the tooltip): radiation as a separate term (it is inside the computed `h`, as in every model), temperature-dependent conductivity, contact resistance between copper and laminate, the solder and the part body (the part is a source in the copper, as in every model; the research variant B measured the idealisation at about 1 % of the rise, `independent-fem-extensions` 8.2), the fin channel effect of a finned block (same fin ratio as the other models), time (section 7).

## 3. From a `Problem` to a mesh: the missing piece

The research tool has a solver and builders written **by hand per case** (`lib/cases.py`). The program needs a builder that takes any `Problem` and either builds a structured hexahedral mesh or refuses with the reason. This is new code (module `pcbthermal/femmesh.py`, section 5.1) and the main risk of the work. It is built from the research functions `grid1d`, `tensor`, `embed_ogrid`, `extrude`, `Quad2D.remove` and the partial-slab builder of `independent-fem-extensions/lib/stack_ext.py`.

*Figure to be drawn (10.3, D2; not yet made): Problem -> break lines -> graded tensor plan -> via patches -> extrusion through the slabs -> partial slabs of blocks -> element materials and faces; the refusals at each step.*

### 3.1 The plan mesh

1. **Break lines** in x and y: the board box; every vertex x (and y) of an **axis-aligned** edge of a zone, a heater, a heatsink, a metal block and of a rectilinear outline. Lines closer than `h_plan / 4` are merged (the feature edge wins over the box line).
2. **Spacing**: `grid1d` between the breaks, element size `h_fine` within `2 d_gap` of a heater edge and of a via patch, growing by at most 1.3 to `h_plan` elsewhere. `h_plan` is the run's cell (`SolverOptions.cell_mm`), `h_fine = h_plan / 2` (option `fem_refine`, 5.2). So the user's one control (the cell) keeps its meaning: the size of the map and the coarse element.
3. **Via patches**: for each via whose drill is at least a fifth of `h_fine` and whose square window (side `max(4 r_drill, h_fine)`) contains no break line and no other via, `embed_ogrid` with circles at `r_in` (if a core), `r_drill` and two rings across the plating, `n_side` 8. The others (dense arrays at a pitch below the window, vias on a feature line, more than `FEM_MAX_PATCHES` = 200 patches) take the rod fallback (3.3) and are counted in one warning.
4. **Outline**: a rectilinear outline (every side parallel to an axis) is exact: its vertices are break lines and the elements outside are removed. A **slanted or curved outline** is refused in the first stage (greyed reason 'the FEM needs a rectangular or axis-aligned outline in this version'); the second stage (branch 9 of section 11) snaps the nodes of the cut elements onto the outline (body-fitted projection of the nearest node row, element quality checked: a Jacobian below 0.1 of the regular one makes the run refuse). The rotated square and the disc of the research are mapped meshes that the projection must reproduce (test, 8.1).

### 3.2 Through the thickness

| Slab | Elements | Why |
| :-- | :-- | :-- |
| copper layer of `t_cu` | 1 if `t_cu <= 105 um`, else `ceil(t_cu / 70 um)` up to 8 | one element is the research setting (35 um); a thick copper plane or a plate drawn as a layer (case 2: 10 mm) needs several, which is the point of 1.1 |
| laminate gap of `d` | `fem_gap_elements` (default 6), graded 1.4 towards the copper | the research default; 6 / 12 / 24 move the strong-edge rise by +0.012 to +0.055 K (`independent-fem-edge` README, the audit note before section 7) |
| a one-layer board's laminate | as a gap below the copper, bottom face convecting | as `laminate.py` and `solid3d` |
| interface pad of a block | 1, `K_PAD` | as the 3D solid |
| metal block of thickness `t_b` | `clip(ceil(t_b / 1 mm), 2, 8)` | at least two so that the block face reads its surface |

The extrusion spans the plan of the board for the board slabs; block and pad slabs are partial (extruded over the block polygon, the rest removed, films added on their new free faces: `stack_ext`).

### 3.3 What is exact, what is averaged, what is refused

| Feature | First stage (2.8.0) | Later |
| :-- | :-- | :-- |
| rectangular board, axis-aligned zones, heaters, heatsinks, blocks | exact | |
| rectilinear outline | exact | |
| slanted or curved outline | **refused** with the reason | node projection (stage 2) |
| copper polygon or heater not on mesh lines | element fill (exact area per element, `geometry.exact_coverage` on the tensor axes) | |
| imported masks | element fill by `copper.sample_coverage` on the element rectangles; **warning** (1.2) | |
| a via with room for a patch | conforming hollow cylinder | |
| a via without room (array, on a line, above 200) | rod of the barrel area, warning with the count | patches that share their windows |
| a via with no board under it | ignored (as every model, `docs/theory.md` 2.6) | |
| metal block, heatsink with thickness | partial slabs | |
| finned block | fin ratio on the exposed face (as the others) | |
| power profile on a part | the steady power of `steady_copy` (as the 3D solid) | section 7 |

### 3.4 A mesh that cannot be built

Every refusal raises `ValueError` with the reason (the pattern of `solid3d`): `api` then skips the FEM with an alert line when other models are ticked and raises when it is the only one (the 3D solid's handling, `api._simulate`). The same reason greys nothing in the panel (the panel cannot know the geometry cheaply), but the **live check** (`checks.check_input` with `models` containing `fem`) states it before the run (5.6).

## 4. Dependencies and licences

Read from the installed metadata in a scratch virtual environment outside the repository (`pip install pyamg scikit-fem` into the scratchpad; the project `.venv` and `requirements.txt` untouched):

| Package | Version | Licence (metadata) | Requires (runtime) | Needed for |
| :-- | :-- | :-- | :-- | :-- |
| **pyamg** | 5.4.1 | `MIT License` (classifier `License :: OSI Approved :: MIT License`) | `numpy>=1.23.5`, `scipy>=1.15.0` (build-only: meson-python, meson, ninja, pybind11) | the preconditioner of the conjugate-gradient solve above `FEM_DIRECT_MAX` unknowns; a binary wheel for macOS arm64 / Python 3.13 installed without a compiler |
| scikit-fem | 12.0.2 | BSD-3-Clause (`LICENSE` file of the wheel; classifier `License :: OSI Approved :: BSD License`) | `numpy`, `scipy` (extras: matplotlib, **meshio**) | **nothing in the program**; one optional cross-check test (8.1) |
| numpy, scipy | 2.5.4, 1.18.1 | BSD-3-Clause (numpy: and 0BSD, MIT, Zlib, CC0 parts) | | already required |

No GPL or non-commercial package is involved: **no gmsh (GPL-2-or-later with an exception), no Triangle (non-commercial), no TetGen (AGPL), no meshpy (bundles both), no pygmsh (needs gmsh), no shapely needed** (the program's own `geometry.py` gives the areas). meshio (MIT) is only an extra of scikit-fem and is not installed. The design deliberately uses only structured meshes so that no mesh generator is needed.

**Install story (recommended; a question in 13)**: `pyamg` becomes a line of `requirements.txt` (MIT, small, two dependencies already present), with its row in the README table of libraries **in the same commit** (CLAUDE.md 'Licences'). The import stays lazy (`fem.available()`): a program without pyamg starts, and the FEM checkbox is **greyed with the reason** 'needs the package pyamg (pip install pyamg)'. The alternative (pyamg optional, `requirements-fem.txt`) gives the same greyed checkbox on a default install, which hides the model from most users. scikit-fem goes into no requirements file of the program: the cross-check test does `pytest.importorskip("skfem")` and the research folder's `requirements.txt` keeps it.

**Bundled executable**: pyamg's compiled extension (`amg_core`, pybind11) is MIT; a bundle must carry its licence text with the others. No new LGPL obligation (PySide 6 is the only one, unchanged).

## 5. Program architecture

### 5.1 Modules (no GUI imports)

| Module | Content | From |
| :-- | :-- | :-- |
| `pcbthermal/femcore.py` | `Model` (Q1 assembly, Robin and flux faces, `solve` direct / CG + AMG, `face_integral`, `volume_integral`), `available()` | `independent-fem-edge/lib/fem.py`, **ported line for line** (licence header and Doxygen already there), plus a cancel check between assembly chunks and a residual check of the CG solve |
| `pcbthermal/femmesh.py` | plan axes from a Problem, via patches, extrusion, partial slabs, element materials, faces; the refusals of 3.4; `unknowns(problem, cell_mm)` counted **without building** (for the memory guard) | `mesh2d.py`, `board.py`, `stack_ext.py`, `hollow.py` (ported), plus the new Problem reader |
| `pcbthermal/fem.py` | `solve_steady(problem, cell_mm, memory_fraction, gap_elements, refine)` -> `SteadyResult`; the read-outs of 5.4 | new |

Three modules because `fem.py` alone would pass 1500 lines and the mesh is the part that will grow (stage 2). `femcore` imports nothing of `pcbthermal` (so the research tests can run it), `femmesh` imports `model`, `geometry`, `copper`, `blocks`, `viawell` (for `via_plating`, thermal areas).

### 5.2 API

* `api.COMPARISON_MODELS = ("fdm", "solid3d", "fem")`; `TIME_MODELS` unchanged (no `fem`); `_run_model`: `if name == "fem": return fem.solve_steady(problem, cell_mm=o.cell_mm, memory_fraction=o.memory_fraction, gap_elements=o.fem_gap_elements)`. Every place that special-cases `solid3d` as 'steady-only comparison model that may be skipped' (`api.py` lines 961, 1030, 1060 on this tree; `cli.py` 38, 57, 100, 353; `gui/panels.py` 1560 to 1760; `gui/preferences.py` 94; `gui/fieldscale.py` 167; `results.py` 14; `copper.model_warnings`; `checks.py`) takes `fem` the same way: the rule is **'do what the code does for `solid3d`'**, and a test greps that every tuple listing `solid3d` lists `fem` (10.2).
* `SolverOptions` gets two fields, both saved only when not the default (as `laminate_s_max_mm`): `fem_gap_elements: int = 6` (2 to 24) and `fem_refine: float = 2.0` (the ratio `h_plan / h_fine`, 1 to 4). No tolerance field: the CG tolerance is fixed (relative residual 1e-10) and the direct limit is a constant. `memory_fraction` is the machine preference already used.
* **Project format** (a compatibility defect avoided, measured on this tree): `SolverOptions.from_dict` validates `models` against the known keys, and `project.load` wraps it in `guard("solver")`, so `{"models": ["fvm", "fem"]}` raises `ValueError: models must be a non-empty subset of ('fvm', 'lumped', 'analytic', 'fdm', 'solid3d')` and **2.7.1 would refuse to open a 2.8.0 project saved with the FEM ticked**. So `to_dict` writes `models` without `fem` (if `fem` is the only model, `models` is `["fvm"]`) and adds `"comparison_models": ["fem"]`, a key older readers drop (`from_dict` keeps only known fields); `from_dict` puts it back. `fem_gap_elements` and `fem_refine` are dropped by older readers the same way. Tests: a 2.8.0 file opened by the v2.7.1 tag (`PCBT_COMPAT_V245`-style subprocess test on `git archive v2.7.1`), and the round trip.
* `defaults.json` `solver.models`: `default_options` already filters unknown keys, so a user file naming `fem` is harmless to an older program.

### 5.3 The memory guard law

Measured by `releases/2.8.0/fem-model/scripts/measure_fem_cost.py` (each solve in a fresh process; peak `ru_maxrss`, interpreter included; plain boards, full copper on every layer, a 10 x 10 mm source of 1 W, films 10 W/m2K, six elements per gap; load average 2.2 on the 10-core 16 GB machine):

| model | board | layers | size mm | solver | unknowns | rise K | s | peak GB | kB per unknown |
| :-- | :-- | --: | --: | :-- | --: | --: | --: | --: | --: |
| fem | 60 x 40 | 2 | 1.0 | direct | 22509 | 32.136 | 0.7 | 0.32 | 14.0 |
| fem | 60 x 40 | 4 | 1.0 | direct | 57523 | 29.306 | 3.9 | 1.06 | 18.5 |
| fem | 100 x 80 | 4 | 2.0 | direct | 48093 | 18.173 | 3.0 | 0.87 | 18.1 |
| fem | 60 x 40 | 4 | 1.0 | cg | 57523 | 29.306 | 2.8 | 0.44 | 7.6 |
| fem | 100 x 80 | 4 | 2.0 | cg | 48093 | 18.173 | 3.8 | 0.38 | 7.8 |
| fem | 100 x 80 | 4 | 1.0 | cg | 188163 | 17.277 | 10.0 | 1.35 | 7.2 |
| fem | 100 x 80 | 2 | 0.5 | cg | 291249 | 21.188 | 9.6 | 1.97 | 6.8 |
| solid3d | 60 x 40 | 4 | 1.0 | solid3d | 38400 | 29.271 | 1.0 | 0.35 | 9.2 |
| solid3d | 100 x 80 | 4 | 1.0 | solid3d | 128000 | 17.237 | 5.6 | 1.80 | 14.1 |
| solid3d | 100 x 80 | 2 | 0.5 | solid3d | 320000 | 21.179 | 8.5 | 3.06 | 9.6 |

Readings: (1) the FEM, the 3D solid and (separately run, same board with `h_bottom` 10) the FVM 29.253 K agree on the plain 60 x 40 four-layer board within 0.2 % (the FEM point maximum against two cell values); (2) with CG + AMG the FEM is linear in the unknowns at about **7 to 8 kB per unknown** and below the 3D solid per unknown; it has 1.5 times the 3D solid's unknowns at the same plan size on four layers (`L + 6 (L − 1) + 1` node planes against `slab_rule`), and 0.9 times on two layers at 0.5 mm; (3) the direct solve is 14 to 18.5 kB per unknown already at 22 000 to 58 000 and grows (46 kB at 59 000 in the research's whole-study process; 5.2 GB at 138 000, `independent-fem-edge` 2), so it is kept only up to `FEM_DIRECT_MAX` = 30 000 unknowns; (4) the time is 1.1 to 2.8 times the 3D solid's on these boards.

**Law** (the form of `memory.CONTINUOUS`, a new row `"fem"`): `peak = base + safety · factor · k1 · N` with `p = 1`, `a = 0` (the AMG cost does not grow with the thickness of the graph at these sizes), `k1 = 7.8 kB` fitted on at least six boards that include vias (patches), a metal block, an outline and a one-layer board (branch 3 of section 11 measures them; the four plain points above are not enough), and the safety factor of the 3D solid (1.30) until the fit says otherwise; the direct branch (N <= 30 000) uses the measured 18.5 kB. The count `femmesh.unknowns` is exact and cheap (axes and slab counts, no mesh), so the guard is exact like the 3D solid's. `memory.TIME_LAWS["fem"]` from the same runs. No `CEILING` of unknowns besides the memory: a large board is refused by the memory with 'the cell that fits' (`memory.cell_that_fits`). Without pyamg the model is greyed (4), so the guard never has to estimate a direct solve of 300 000 unknowns.

### 5.4 The result and the read-outs (defined, because the FEM has more than one temperature per cell)

The `SteadyResult` keeps the layout of the other models, so every view, table, report and `analysis.heater_stats` work unchanged: `T` of shape `(layers, ny, nx)` on the run's cell grid (`grid="cells"`, `dx`, `dy` = the run cell). Three read-outs, named the same everywhere (theory, tooltip, report):

| Read-out | Definition | Where it goes |
| :-- | :-- | :-- |
| **column** (default) | for a cell of the run grid and a copper layer: the volume mean of the trilinear field over that cell and that copper slab (Gauss quadrature of the elements under the cell) | `T`, `t_max`, `t_mean`, `layer_mean`, the part rows: **like for like with the node value of the FVM, FDM and 3D solid**, so that a difference between models is the method, not the definition |
| **surface** | for a cell: the area mean of the field over the cell on the outer face of the outer copper layers (top of layer 1, bottom of layer L) | `arrays["T_surface"]` (2, ny, nx), `extras["t_max_surface"]`; the Layer box offers 'Surface (top)' and 'Surface (bottom)' after the layers (like 'Metal block' today) |
| **point** | the hottest node of the whole mesh, and the hottest node under each part's footprint on its face | `extras["t_max_point"]`, `t_max_location` keeps the column cell; the part rows add 'face peak' for the FEM |

`t_max` is the column read-out (the question in 13 asks whether the maintainer wants the surface as the headline instead). Case 2 of Muzychka is the case where column and surface differ by 2 to 5 K; on an ordinary board with 35 um copper they differ by microkelvin (`docs/validation.md` 55.2: 5e-7 of `h`). The heat balance, the face means used by the computed-h loop (`layer_mean[0]`, `layer_mean[-1]`) and `power_out` come from the face integrals (exact).

### 5.5 Process, cancel, progress

`jobs.job_simulate` runs `api.simulate` in the calculation process, so nothing changes there; the FEM reports progress 'mesh', 'assembly', 'solve' through the existing callback; a cancel terminates the process as for every model (no cooperative cancel needed). The assembly is chunked (20 000 elements), so a cancel is never blocked in a long Python loop of the parent.

### 5.6 Warnings and the live check

Live (`checks.check_input` when `fem` is ticked): slanted or curved outline (refused in stage 1); the count of vias that fall back to a rod; imported copper read as element fill; a heater or zone edge not on a mesh line ('element fill under the part'); a part smaller than two fine elements. After the run (`SteadyResult.warnings`): the rod count, the CG iterations and residual when the solve needed more than 500 iterations, the balance when it is off 1 by more than 1e-6, and 'steady state only' when the project has profiles (the existing 3D solid text, extended). Every text names the control of the window or the option of the command line through `uicontext` (as today).

### 5.7 Command line, reports, plots

`cli.py`: `RUN_MODELS += ("fem",)`, `--model fem`, `compare` expanded to all six; `--fem-gap-elements` and `--fem-refine` options (named like the laminate options); the exit code 3 of a memory refusal unchanged. Reports and plots take the label from `results.MODEL_LABELS`; the report adds the surface and point read-outs for the FEM rows (one line each).

### 5.8 Interface (exactly as the 3D solid and the FDM)

* Simulation settings, Models box: `"fem": QCheckBox("Finite elements (FEM), comparison")` after the 3D solid, off by default (also in `defaults.json` `solver.models`, which does not list it), tooltip in the same pattern: *'The board as a 3D solid of finite elements (hexahedra through every copper layer and gap, conforming via barrels, the film on the real faces). Steady state only; within about 0.2 % of the FVM and the 3D solid on ordinary boards; reads the surface of thick copper and blocks and resolves hollow vias; slower than the 3D solid. Skipped above the memory limit.'* (numbers replaced by the measured ones of branch 6).
* Greyed with the reason as tooltip when `femcore.available()` is false ('needs the package pyamg').
* Memory verdicts beside the checkbox exactly as for the 3D solid (`panels.py` 1713 to 1760: a refusal blocks only that model when others are ticked).
* Results: the model combo of Temperature, Gradients and Profiles lists `FEM`; the Models tab (bar chart of `plots.draw_comparison` and the summary table) includes it; the card name `FEM`; the model menu of the card (key M) lists it; not in the Animation or the Power profile time views (steady only, the 3D solid's handling).
* Preferences: `MODELS` of the default-models list gains `fem`; the Solver page gains the two FEM options with tooltips.
* User guide, tooltips table, About box (the library list gains pyamg), keyboard list unchanged.

## 6. The compare workflow and 'which model to trust'

**What exists today** (read on this tree): ticking several models runs them on the same project; the Results show each model's maps through the model combo, the **Models tab** draws a bar chart of `Tmax` and `Tmean` per model (`plots.draw_comparison`) and the summary table lists every model's hottest point, mean and part rows; `--model compare` runs every model and prints the same table. There is **no difference map and no table of differences** between two models.

**What the design adds** (branch 7 of section 11; display only, no number moves):

1. **Differences table** in the Models tab and the report: for each model, `Δ` of the hottest point and of every part's mean and peak against a chosen reference model (default FVM; the FEM column also with its surface read-out), in K and in % of the reference rise.
2. **Difference map**: a 'Difference' entry of the Temperature tab's View, enabled when two or more field models ran: `T_model − T_reference` on the run grid, layer from the Layer box, diverging colour map centred on 0, its own colour bar; the Lumped and Analytic on an outline board are left out with the reason (their field is stretched).
3. **Which model to trust here**: one informational line in the Results summary, built by `checks.trust_hint(problem, models)` from rules that already have evidence; it names the model and the reason, never a number it cannot back:

| Situation (detected) | Hint | Evidence |
| :-- | :-- | :-- |
| a copper layer or block thicker than 0.5 mm, or a plate thickness term of `check_thick_plates` above 5 % | 'FEM (surface read-out): the other models give the column mean' | `docs/validation.md` 55.1; branch 6 measures the FEM on case 2 |
| hollow vias carrying a large share of the heat (a via under a part) | 'FEM or FVM; the FDM reads the via effect 1 to 9 % low at 0.25 mm' | `independent-fem-extensions` 8.1 |
| a part smaller than the warning of `check_small_part_laminate` | 'FEM or 3D solid at the finest cell that fits' | `docs/validation.md` 21.3 |
| a strong edge (`h_side` above 200 W/m2K) | 'FEM; the FVM reads 0.4 to 6.2 % cool' | `docs/validation.md` 46 |
| a slanted or curved outline | 'FVM (cut cells); the FEM refuses it in this version' | 3.3 |
| imported copper | 'FVM or FDM: they read the copper; the FEM and the 3D solid read the cell fill' | `copper.model_warnings` |
| otherwise | 'FVM; the comparison models agree within about 1 % on such boards' | `docs/validation.md` 3 |

The hints are one function with a table of rules and a test per rule (10.2); they are reviewed when a rule's evidence changes.

## 7. Time simulation: a second stage

The research transient (`independent-fem-extensions/lib/transient.py`: consistent mass, Crank-Nicolson with a Rannacher start, implicit Euler as the check, the frequency-domain periodic state) is validated (time to 63 % and plateaus within 0.5 % of independent references; a fast swing of a small source 0.5 to 3.5 % low, 8.3). Bringing it in means a step response, the animation and the profile runner for the FEM, a capacity on every element, a time law in the guard (a factor stored per stage) and the frozen times to 63 %. **It does not ship in 2.8.0** (recommendation; a question in 13): the FEM is steady only in 2.8.0, like the 3D solid, and the transient is a later item of 'Planned' with its own branch. The steady model is designed so that `femcore.Model.assemble` already returns what the transient needs (A, f), so nothing is redone.

## 8. Validation plan

### 8.1 The port is the research tool (first test, before anything else)

`tests/test_fem_port.py`: on the research cases that a `Problem` can express (the strong-edge plate with and without a via, the 20 mm square aligned, the T, the hollow barrel of study 1, the L), the program's `femcore.Model` with the research mesh reproduces the research `fem.Model` **to 1e-9 relative on every node** (same nodes, same elements: the port must be exact); and `femmesh` building the same board from a `Problem` reproduces the research builder's hottest rise and heater mean to 1e-9 where the meshes coincide, to the discretisation order where they do not (stated per case). The research `lib/` is imported read-only by the test (as `tests/test_*` import research scripts today), so a later edit of either side breaks the test.

### 8.2 Closed forms and published cases (in the battery)

| Check | Reference | Target |
| :-- | :-- | :-- |
| 1D column (a source over the whole face, films up and down) | `exact.series_stack` (the research closed form, copied into `tests/helpers/`) | 1e-9 relative |
| 1D fin with a Robin end | `exact.fin_robin` | 1e-5 of the peak |
| manufactured solution on a box, orthotropic K, Robin on six faces | exact | order 2.0 on three meshes |
| energy balance | identity | 1e-9 on every solve |
| rotation invariance (stage 2) | the same board turned | 1e-9 |
| Seri Lee plate (centre, edge, corner) | the paper (S) and the own series | within the research's 0.6676 / 1.2840 / 2.2744 K/W |
| **Muzychka, Culham and Yovanovich (2003) case 2** (a 50 x 50 x 10 mm plate of `k` 150 W/mK as one layer, expressed as `docs/validation.md` 55.1 expresses it for the FVM; `h` 400 under) | the published centroids 97.40 / 103.82 / 101.28 / 99.94 °C and the independent 3D reference 97.39 / 103.81 / 101.27 / 99.93 (`docs/validation.md` 1123) | the FEM surface read-out within 0.1 K of the reference; the column read-out equal to the FVM's column mean within 0.1 K (55.1) |
| case 3 (the cross) and the Culham coupon | `docs/validation.md` 55.1 and the coupon of `tests/test_layered_vs_3d.py` | within the 3D reference's band |
| scikit-fem cross-check (optional, skipped without it) | `skfem.ElementHex1` on the same mesh | 1e-10 |

### 8.3 Against the program's models

On the 20 harness boards at 2 / 1 / 0.5 mm: the FEM column against the FVM and the 3D solid (a table in `docs/validation.md`, new section 'Finite elements in the program'), and the converged FEM (three plan sizes, Richardson, `refine.py`) on six of them against the FVM at 0.25 mm. Before quoting a difference, both sides must model the same board: same `Materials`, same films (`Problem.new` gives `h_bottom` 15, the research builders 10: the first comparison of this design was 14 % apart until that was equalised), same copper fill rule, same plating, same anisotropy, same edge films.

### 8.4 Stress and the battery

`tests/test_gui_stress.py` gets the FEM in the 'every example with every model' scenario, in the random-actions monkey (the model list) and a scenario with pyamg hidden (`monkeypatch` of `femcore.available`) that checks the greyed checkbox. Cost: the 20 boards at 2 mm are 1 000 to 48 000 unknowns (counted on uniform plans of 2 mm: the four 100 mm boards 48 093 or 23 409, the 60 mm boards 8 649, the 20 mm boards 1 089), so about 1 to 4 s each and under a minute for the frozen-number run; the unit tests of the FEM about 1 minute. The whole battery grows by an estimated 3 to 5 minutes (to be measured on branch 6).

## 9. Frozen numbers

* A new model key **adds** records; no existing record moves. The harness (`releases/regression-harness/lib/regress_harness.py` and its byte-identical copy in `tests/regression/`, `test_harness_copy.py`) gets `"fem"` in `MODELS`, a `FEM_CAP` of unknowns (like `SOLID_CAP` = 150 000) and a guard so that a run on an older tag that has no `fem` key records the FEM as `skipped` ('model absent in this version'), not as a failure (the baseline of the next release runs v2.7.1).
* Until the refreeze of 2.8.0 the FEM records live in a **pending file** `tests/regression/data/pending/fem-model.json` (`with_pending` adds records with `records.update`, so a pending file can add records as well as move them; `make_pending.py` writes it). Which boards: **all 20 at 2 mm and 1 mm**, at 0.5 mm only those under `FEM_CAP` (the four 100 mm boards at 0.5 mm are about 750 000 unknowns on four layers and are `skipped` with the reason); the outline boards (`example_cut_to_T`, `round_outline`, `t_outline`, `part_across_outline`) are **skipped in stage 1** with the reason 'outline not rectilinear' except `t_outline` (rectilinear: kept). Each record holds `t_max` (column), `t_max_surface`, the part means and the balance, under the one tolerance policy.
* `study_diff.py --strict` at the release sees the FEM records as added (no baseline): `expected_shifts_2.8.0.json` lists them as 'new model'.

## 10. Documents, tests and diagrams to produce

The rule of CLAUDE.md 'Before every commit' applies to every branch; this table says which branch writes what, so that nothing is left for 'later'. **Who**: the executor writes code and the scripts of the figures; the maintainer writes the documents and the user guide; the reviewer checks every number against a script and the theory against the code.

### 10.1 Documents

| Document | Content | Branch (11) |
| :-- | :-- | :-- |
| `docs/theory.md` new chapter '4a Finite elements' in the explicit style of chapter 4 (the eight parts: idea in a picture, unknowns, equations F.1 to F.3, assembly, solution, limits in words, where it is checked, sources) and the read-outs (5.4) | figures D1 to D5 | 2 (core), 4 (read-outs), 6 (checked numbers) |
| `docs/theory.md` 0 (symbols), the table 'Where each part lives', 2.7 (the memory law row), 12 (sources: Zienkiewicz-Taylor, Hughes for Q1 (status to be set by reading), Muzychka 2003 R) | | 3, 6 |
| `docs/models.md` section 2.8 'Finite elements (FEM)' and the table 2.5 'Which model for which job' (rows for thick metal, hollow vias, strong edge) | D6 | 6 |
| `docs/validation.md` new section 'Finite elements in the program' (8.1 to 8.3 tables) | D4 | 6 |
| `docs/versions.md` 2.8.0 chapter (what, where in the code, how tested) and 'Planned' (stage 2 outline projection, transient, via patches sharing windows) | | each branch |
| `README.md`: feature list, the model table, the **library table row for pyamg** (licence MIT, version), test count | | 3 (pyamg row), 6 |
| `CHANGELOG.md` Unreleased | | each branch |
| `CLAUDE.md`: Project Overview (six models), Structure (`femcore.py`, `femmesh.py`, `fem.py`), Commands (`--model fem`), the test count, a Decisions Log entry per branch, and the entry that reverses the 2.7.0 decision | | each branch |
| user guide `pcbthermal/help/index.html`: the Models table, the FEM paragraph, a chapter **'Which model to use'** with the decision picture D6 and the trust hints of 6, the Difference view, the read-outs; `tests/test_help.py` words (`Finite elements (FEM)`, `surface read-out`, `column read-out`, `Difference`, `pyamg`) | D6 | 6, 7 |
| `pcbthermal/help/calculator.html`: one sentence (the Power Calculator runs the FVM, not the FEM) | | 6 |
| tooltips (`gui/tips.py`, the checkbox, the two options, the Layer entries 'Surface (top/bottom)', the Difference view, the reference-model box) and `tests/test_tooltips.py` | | 5, 7 |
| About box (`gui/help.py`: libraries) | | 3 |
| `research/independent-fem-edge/INTEGRATION.md` and `research/independent-fem-extensions/INTEGRATION.md`: 'What enters the program' rewritten (it said 'nothing'), the REVIEW and index rows | | 2 |

### 10.2 Tests

`tests/test_fem_port.py` (8.1), `tests/test_fem_closed_forms.py` (8.2), `tests/test_fem_published.py` (Lee, case 2, the cross), `tests/test_fem_mesh.py` (break lines, merging, patches, refusals, rectilinear outline, partial slabs, the count of `unknowns` equal to the built mesh), `tests/test_fem_readouts.py` (column equals FVM node on a uniform board; surface minus column equals the closed form on the 1D column), `tests/test_fem_memory.py` (the law against measured peaks, the refusal message, the greyed checkbox without pyamg), `tests/test_fem_project_compat.py` (the `comparison_models` key; the v2.7.1 tag opens a 2.8.0 file, subprocess on `git archive`, behind an environment variable like `PCBT_COMPAT_V245`), `tests/test_model_lists.py` (every tuple that lists `solid3d` lists `fem`), `tests/test_trust_hints.py`, `tests/test_difference_view.py`, the stress scenarios (8.4), the frozen records (9). `tests/test_docs.py` and `tests/test_license_header.py` cover the new modules.

### 10.3 Diagrams (CLAUDE.md 'Diagrams and illustrations (always)')

Drawn by `research/theory/scripts/make_diagrams.py` (shapes of `research/diagram_kit.py`), or by `make_figures.py` when they come from data, at the next free numbers of `research/theory/figures/`, copied to `docs/images/` under the same name, with a topic file in `research/theory/topics/` (sources by key) in the same pass:

| Id | Picture | Kind | Used in |
| :-- | :-- | :-- | :-- |
| D1 | **the mesh through the thickness**: a section of a four-layer board with the copper elements, the graded gap elements, a block with its pad and partial slabs, the films on every face and wall | diagram | theory 4a, models 2.8 |
| D2 | **the mesh builder**: break lines, graded plan, via patch, extrusion, partial slab, refusals | diagram | theory 4a, this file 3 |
| D3 | **the film term**: the FEM face (`h N_i N_j` on the real face, the node on the face) against the cell-centred half-cell film (`1/(1/h + Δ/(2k))`) | diagram (from `independent-fem-edge` figure 6) | theory 4a and 1.2a |
| D4 | **the hollow via barrel**: O-grid plan with the circles at `r_in` and `r_drill`, the rings across the plating, a section with the heat paths through the wall | diagram + the via-effect data of `independent-fem-extensions` 8.1 | theory 4a, validation |
| D5 | **surface against column mean, Muzychka case 2**: the plate section with the four sources, the through-thickness profile under S2, the column mean, the surface, the FVM node, the published centroid | figure from data (`research/muzychka-case2-analytic` and branch 6's FEM run) | theory 4a, validation, user guide |
| D6 | **which model to use**: the decision picture (questions: thick metal? hollow vias under a part? small part? strong edge? outline? imported copper? time?) leading to a model and its read-out | diagram | user guide 'Which model to use', models 2.5 |
| D7 | **the three read-outs**: a cell column with the column mean, the surface cell mean and the point maximum | diagram | theory 4a, user guide, tooltips |
| D8 | **the difference map** on the example board (FEM minus FVM) | screenshot from `examples/make_screenshots.py` | user guide, README |

Every picture is looked at before it is committed; a number on a picture is one the documents already hold.

## 11. Work breakdown into branches

Each branch from `development`, executor -> reviewer -> maintainer (documents, the whole battery), merged with `--no-ff`, **one at a time** (they share `api.py`, `memory.py`, `checks.py`, `gui/panels.py` and `docs/theory.md`). Sizes: S up to 2 working days of an agent, M 3 to 5, L 6 to 10, review and battery included.

| # | Branch | What | Size | Numbers move? | Ships in 2.8.0 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | `docs/fem-model-design` (this) | the design, the cost script | S | no | (documents) |
| 2 | `feature/fem-core` | `femcore.py` (port), `tests/test_fem_port.py` 8.1 core part, closed forms 8.2; no API key yet (not selectable) | M | no | yes |
| 3 | `feature/fem-mesh-and-guard` | `femmesh.py` (rectangle, axis-aligned features, rectilinear outline, partial slabs, element fill, imported masks, via patches with the rod fallback), `unknowns`, the memory law fitted on six boards, pyamg in `requirements.txt` and the README table, About box | L | no | yes |
| 4 | `feature/fem-model` | `fem.py` (`solve_steady`, read-outs 5.4), `api` key, `SolverOptions` fields with the `comparison_models` save rule and the v2.7.1 compatibility test, CLI, report rows, warnings and live check, theory 4a, the pending frozen records | L | **adds** frozen records only | yes |
| 5 | `feature/fem-gui` | the checkbox (greyed reason), the memory verdicts, the Results combos and card, the Layer entries 'Surface (top/bottom)', Preferences, tooltips, the stress scenarios | M | no | yes |
| 6 | `docs/fem-validation` (with the reviewer) | the validation section (8.2 and 8.3 tables, Muzychka case 2 against the paper), the published-case tests, models 2.8, the user guide chapter 'Which model to use', diagrams D1 to D7, the tooltip numbers measured | M | no | yes |
| 7 | `feature/compare-differences` | the differences table, the difference map, the reference-model box, `checks.trust_hint` with its tests, D8 | M | no | yes |
| 8 | `feature/fem-transient` | section 7 | L | adds times | **no** (later) |
| 9 | `feature/fem-outline-projection` | stage 2 of 3.1: slanted and curved outlines by node projection, rotation-invariance test | L | adds records | later |

**Realistic size**: branches 2 to 7, the 2.8.0 part, are about **20 to 30 agent working days** in series (review rounds and the whole battery included; the mesh builder of branch 3 is the uncertain one). The earlier '5 to 8 weeks' (`fem-worth-it.md` 3) assumed an unstructured mesher; that is avoided here, but the review rounds of this project usually double the first estimate, so plan **4 to 6 weeks of calendar** for the steady model in the program, and do not tie the release date to it (13).

**Order of delivery, so that something useful lands first**: branch 2 lands a tested solver with no user-visible change; branch 4 (after 3) is the first useful delivery: `--model fem` on the command line for rectangular boards, with the frozen records; branch 5 puts it in the window; branch 7 is useful for every model even without the FEM (it can be done before 2 if the FEM slips). The transient and the outline projection wait.

## 12. Risks

1. **The mesh builder** (branch 3): hostile geometry (hundreds of break lines from a busy drawn board, near-coincident lines, a via on a break line, tiny parts) can make the plan mesh large or of poor quality. Mitigations: the line merging rule, the patch admission rule with the rod fallback, the memory guard on the exact count, a cap of break lines per axis (10 000) with a refusal, and the fuzz of the GUI stress test.
2. **A sixth model the user cannot place**: mitigated by the comparison label, the off default, the trust hints (6) and the 'Which model to use' chapter; the FVM stays the reference of every decision and of the Power Calculator.
3. **Read-out confusion** (column, surface, point): one definition, one name, in every text (5.4); the headline stays the column so that differences between models are not differences of definition.
4. **Imported boards**: the FEM adds nothing there (element fill) and the warning must say so, or users will take its number as better.
5. **Project compatibility**: without the `comparison_models` rule, 2.7.1 refuses 2.8.0 projects (measured, 5.2); the compatibility test holds it.
6. **pyamg**: a compiled dependency; a platform without a wheel cannot install it; the model is then greyed, nothing else breaks. Its version is pinned by a minimum, not exactly.
7. **Cost**: 1.1 to 2.8 times the time of the 3D solid on the measured boards; the four-layer 100 mm boards at 0.5 mm (about 744 000 unknowns on a uniform plan, about 7.5 GB by the law of 5.3 with the safety 1.3) fit the default limit of a 16 GB machine (0.60, 9.6 GB) only just, and take minutes: the harness skips them (`FEM_CAP`), and the user gets the verdict 'slow' or the refusal with the cell that fits.
8. **Two copies of the solver** (research `lib/` and `femcore.py`): the port test (8.1) fails if they drift; the research folders keep their copy as the reference of their READMEs.
9. **The 'independent reference' is now inside the program**: once the FEM is a model, comparing a model with it is no longer an independent check of the program's code base in the sense of `fem-worth-it.md` 0 (shared geometry readers, shared `Problem`). The research `lib/` stays as the independent reference (its own builders, no `pcbthermal` import), and the validation keeps comparing against it, not only against the program's FEM.

## 13. Questions for the maintainer (one block)

1. **Scope of 2.8.0**: the steady FEM only (branches 2 to 7), the transient (8) and slanted or curved outlines (9) later? (Recommended.)
2. **Release date**: 2.8.0 waits for the FEM (4 to 6 weeks of calendar for the steady model), or 2.8.0 ships the confidence items already planned and the FEM goes into 2.9.0? (The design works either way; the order of 11 lets the difference view ship alone.)
3. **pyamg**: a required line of `requirements.txt` (recommended: MIT, small, the model is greyed only on a platform without a wheel), or an optional extra (the checkbox greyed on a default install)?
4. **Headline read-out of the FEM**: `t_max` = the column mean (recommended: like for like with the other models; the surface shown beside it), or the surface?
5. **Name**: 'Finite elements (FEM), comparison', key `fem`, short name `FEM`?
6. **Outline boards in stage 1**: refuse slanted and curved outlines with the reason (recommended), or accept them with a staircase of elements and a warning (cheaper, but worse than the FVM's cut cells, which would make the comparison misleading)?
7. **The compare additions** (difference table, difference map, trust hints): in 2.8.0 for every model (recommended), even if the FEM slips?

## 14. What was read, measured and not verified

* **Read in full**: `research/independent-fem-edge/lib/fem.py` and `lib/board.py`, its `INTEGRATION.md`, README sections 0 to 2 and the memory and run notes of 5 and 7; `research/independent-fem-extensions/INTEGRATION.md`, README 1, 3, 4, 7.2, 8.1, 8.3, 8.5; `releases/2.7.0/final-opinion/fem-reference-opinion.md` and `fem-worth-it.md`; `docs/theory.md` 4; `docs/validation.md` the Muzychka case 2 paragraph and 55.1 to 55.3; `api.py` (`SolverOptions`, `_run_model`, `_simulate`, the time-simulation selection), `solid3d.py` header and constants, `memory.py` header and constants, `project.py` (the load of the solver options), `jobs.py` (signatures), `results.SteadyResult`, `plots.draw_comparison`, `gui/panels.py` (the Models box), `tests/regression/test_frozen_numbers.with_pending`, the list of harness boards (`regress_boards.py`).
* **Read in part**: `mesh2d.py` (signatures, `tensor`, `embed_ogrid`), `transient.py` (header), `results_view.py` (the Models tab), `cli.py` (the model lists).
* **Measured here**: the table of 5.3 (`measure_fem_cost.py`); the agreement of the FEM, the 3D solid and the FVM on the plain 60 x 40 four-layer board (29.306 / 29.271 / 29.253 K; the FVM run separately with the same inputs); the refusal of a `models` list with `fem` by `SolverOptions.from_dict` on this tree (the 2.7.1 code path); the licences and dependencies of pyamg 5.4.1 and scikit-fem 12.0.2 from their installed metadata in a scratch environment; the unknown counts of the 20 harness boards at 2 mm on uniform plans (a lower bound: break lines and via patches add elements).
* **Not verified**: the memory law with vias, blocks and outlines (four plain points only: branch 3 fits it); the cost of via patches on a board with many vias; the mesh builder itself (it does not exist); the FEM on Muzychka case 2 with several elements through the plate (the research tool was not run on it here: branch 6); the v2.7.1 tag opening a file with `comparison_models` (the rule follows from `from_dict` dropping unknown keys, read in the code, not run on the tag); the timing of the whole battery with the FEM.
