# Final opinion of the reviewer on the 2.6.0 release candidate

This folder holds the written verdict of release gate step 5 for 2.6.0 (`CLAUDE.md`, "Agents and workflow"). It was made on the branch `docs/final-opinion-260`, created from `feature/integration-260` (tip `f403326c`), not from `develop`: an exception to the branch rule, because the 2.6.0 program exists only on the integration branch. The branch also carries two small corrections of the program found by this review (section 5), with their tests, for the maintainer to bring into the integration tree.

Contents: 1 what 2.6.0 contains, for a user; 2 the verdict on code for every investigation; 3 the open decisions; 4 the release opinion; 5 the defects found and fixed here; 6 what was read and what was not verified.

## 1. Summary for the maintainer: what 2.6.0 contains

**In one sentence**: 2.6.0 corrects the models where the independent reviews of 2.5 found them wrong (board outlines, the laminate at the edge, the via barrel, the Analytic edge and transient, the 3D solid slabs, small parts in the Lumped, the face turned down, fast power waves), adds the project package `.pcbtz` and a single Layer choice, and changes the numbers a user sees by a fraction of a kelvin on ordinary boards and by up to a few kelvin where the old model was wrong.

### 1.1 Model corrections and the size of each effect

| Correction | Models | What a user sees |
| :-- | :-- | :-- |
| Exact board cover (outline) | FVM, FDM, 3D solid | Boards with an outline only. The turn spread of a rotated square falls from 1.0 to 0.08 K at 1 mm; a part across the outline moves -0.55 / -0.45 / +0.12 K (FVM, 2 / 1 / 0.5 mm). Rectangles: bit-identical. |
| Cut-cell links and the edge film | FVM (and the 3D solid, sliver cells) | No more jump when an edge cell becomes a sliver (+3.6 K at 200 W/m2K before, under 0.1 K after; 3D solid +15.9 K before, -0.3 K after). Frozen FVM records move by at most 0.008 K except `part_across_outline` (-0.79 K at 2 mm). |
| Laminate band along the board edge | FVM, FDM | Thick boards with a cooled edge read cold before (-15 % of the rise at 3.2 mm, 200 W/m2K); now -2.4 % at most. Harness boards +0.001 to +0.82 K at 2 mm. |
| Via barrel longer by half the copper thickness; uncoupled when the hole touches no copper | FVM, FDM, Lumped, Analytic | Boards with vias run slightly hotter: example board +0.13 to +0.16 K in every model; at most 0.26 % of the rise on the frozen boards. A via just outside a copper edge no longer over-reads (+2.9 K before). |
| Analytic: per-layer edge, local transient | Analytic | Worst steady error on 48 unlike-layer boards 8.6 % to 4.1 %; time to 63 % with a heatsink from -66..+175 % to -8..+1 %. Example board time to 63 % of U1 -18.6 % (12.8 to 10.3 s). Steady frozen records move by at most 0.004 K. |
| 3D solid: slabs by thickness and face term | 3D solid | A 2 mm part on 3.2 mm bare laminate: +20 % to +3.9 % too hot. 39 records of 14 boards move (-0.0006 to -0.72 K, up to -1.44 K on `part_across_outline` together with the cut cells); two 0.5 mm records exceed the harness cap. |
| Lumped: capped first ring, finer raster for small parts, near-edge warning | Lumped | A 1 mm part on a 200 x 150 mm board: -25 % to about -5 %; time to 63 % of small parts 1.6..3.1 times to 0.92..1.03 times the FVM. No frozen board has such a part (no frozen record moves by these items). |
| Face turned down: `Nu = 0.475 Ra^(1/5)` | all, computed h, horizontal | -0.3 to -1.4 % of the rise (example 60.06 to 59.86 K). Typed coefficients (every frozen record) unchanged. |
| Fast power waves: closed-form swing and the `average + ripple` regime | FVM, FDM, Lumped, Analytic (profiles) | A wave faster than a few seconds was read 2 to 12 times too small. Example `profile_board`: U1 at 100 Hz from 0.39 K averaged to 2.01 K `average + ripple`; U2 (20 s) 84.9 K to 97.8 K (finer step-response cell). No frozen record (the harness has no profile). |

### 1.2 New features and interface

* Project package `.pcbtz` (project, background image and, if ticked, the import files in one checked ZIP; Save as, Export package, `convert`, every command of the command line), with the size preference `package.max_mb`.
* One Layer box for the board and every Results map, a clickable model name in the card of the map on the board (key M), the View (Current, Smooth) of the Display panel on the board.
* Bounds against hostile outlines (500 m span, 100 000 vertices, 20 million edge pairs, 10 million grid crossings) and plain-text names in the package messages.
* Before-close and before-release hooks of the import window (no visible change; the BOM role is deferred).

### 1.3 New warnings

The Lumped model near a side or corner; a small part in the Lumped that is not refined; a via that touches no copper on a layer; a via at a copper corner or track end (partial-copper text); the edge laminate above 200 W/m2K (FVM, FDM) and the Lumped/Analytic edge at `h_side * t >= 150`; the face-down Rayleigh number outside 100 to 1e9; a fast wave on bare laminate, on a board with a metal block, a one-shot table with a short stretch, a slow wave near a board side; the Analytic heatsink transient now quotes -8 % to +1 %; imported copper on an outline board keeps the earlier treatment.

### 1.4 The numbers a user will see

* **Example board** (`examples/example_board.pcbt.json`, 1 mm, `run`): FVM 85.38, Lumped 86.79, Analytic 84.72 degC (2.5.2: 85.23, 86.63, 84.58). The run shows one warning (the Lumped with 9 vias under U1), the same as 2.5.2.
* **Frozen numbers** (`tests/regression/data/v2.6.0.json` against `v2.5.0.json`, which 2.5.1 and 2.5.2 did not move): 145 of 251 steady records moved, by item (table `releases/regression-harness/reference/expected_shifts_2.6.0.json`, 0 alarms): Analytic 24 records (-0.0006 to +0.158 K), FDM 27 (+0.001 to +0.66 K), FVM 39 (-0.56 to +0.59 K, the extremes on `part_across_outline`), Lumped 15 (+0.016 to +0.158 K, the via barrel), 3D solid 40 (-1.44 to +0.013 K); two 3D records at 0.5 mm leave the harness (over the cap). Times to 63 %: example U1 Analytic -19.5 % (12.82 to 10.32 s), the others within about 1 %.
* **What stays limited** (stated in the documents and warned): the FDM has no cut-cell treatment; imported copper on an outline board keeps the old links and film; the copper edge inside the outline leaves 2 to 3 K at `h_side` 200; the Lumped near an edge stays 4 to 15 % cool; the Lumped and Analytic keep the edge film at the copper temperature (Analytic -5 % on 1.6 mm, -15 % on 3.2 mm at 200 W/m2K); a via at a copper corner reads 15 to 85 % of its effect low; the convection has never been compared with a measured copper board.

## 2. Does the research need code? Verdict per investigation

Legend: **impl** code implemented in 2.6.0 (where, test); **later** code needed in 2.6.1 or beyond (reason, evidence); **none** no code needed (the program as it is answers it); **dropped**; **earlier** implemented before 2.6.0, nothing new.

| Folder | Verdict | Where / why |
| :-- | :-- | :-- |
| `cut-cell-links/` | impl | `fvm.py` `_cut_edge_film`, `_lateral_links`, `geometry.face_apertures`; `tests/test_cut_cell_*`. Later: FDM cut cells (2.6.1 item 1), pixel mask for imported copper (item 2). |
| `rotated-square-3d/` | impl + later | exact cover (`geometry.exact_coverage`), 3D sliver cells (`solid3d.py`, `tests/test_solid3d_sliver_cells.py`); the 1.7 K aligned-edge residual of the 3D solid and the copper edge inside the outline (2.6.1 item 3) are open. |
| `bochkov-robin-check/` | none | confirms the adopted film (floor 0.25 is a safety net, `fvm.EDGE_FILM_FLOOR`). |
| `laminate-edge-band/` | impl | `laminate.edge_band`, `plan_gaps(edge=)`; `docs/validation.md` 36; tests of the band. Lumped/Analytic edge laminate: later, only warned (A29). |
| `laminate-2-6 (now laminate-slabs-and-local-rule)/` | impl (C), later (A local rule) | 3D slabs by thickness (`solid3d.py`); the source-aware local rule needs the three changes of its README 7 (A18). |
| `analytic-2-6 (now analytic-edge-and-transient)/` | impl | `analytic.py` per-layer edge, `analytic_local.py`; `tests/test_analytic_local.py`. The research tests were repaired in `releases/2.6.0/reproduction`. |
| `analytic-edge-spatial/` | earlier (2.5.0 Robin basis) | superseded in part by the per-layer edge; test restated in `releases/2.6.0/reproduction`. |
| `via-contact-geometry/` | impl + later | `viawell.barrel_length`, `rim_copper_shares`; `tests/test_via_barrel_and_rim.py`. Later: the sector well at a copper corner (A30). |
| `via-partial-copper/` | impl (warning, rim rule) / dropped (star coupling) | the star coupling (C) was not adopted (maintainer); what is left is A30. |
| `lumped-ring-uniform-deficit/` | impl | `lumped.py` capped first ring; `docs/validation.md` 31. |
| `lumped-near-edge/` | impl (warning, small-part raster) / later | `checks.check_lumped_near_edge`, `lumped.small_part_cell`; the image-potential correction not adopted (A27). |
| `published-cases-followup/` | impl via other folders | the near-edge warning and the barrel length came from its INTEGRATION; the face term was already in. |
| `face-down-convection/` | impl | `convection.py` 0.475 Ra^(1/5); the constant is an open decision (section 3). |
| `convection-laws/` | impl (face down) / later (measurement) | face up kept; board D measurement (G1) needed before revisiting. |
| `fast-wave-oscillation/` | impl | `stackimpedance.py`, `profiles.py`, `api.response_cell_mm`; `docs/validation.md` 37. Later: neighbours' waves, a via term in the column, partial copper under the part (section 3). |
| `bom-role-and-close-hook/` | impl (hooks) / later (BOM role, deferred by the maintainer) | hooks in `import_window.py`, `import_session.py`; BOM code kept on its branch. |
| `reduced-models-imported-passives/` | earlier (warning text) / later | the warning numbers must be re-measured after the capped first ring (Planned 'Fixes' 10). |
| `releases/2.6.0/reproduction/` | none | research tests only; 45 folders green after repairs, 0 unexplained. The studies themselves were not re-run (Planned 'Fixes' 9). |
| `gerber-real-boards/` | earlier / later | default mapping open since 2.5.0 (section 3); heater modes (Planned feature 4). |
| `gerber-models/`, `gerber-import/`, `gerber-cad-profiles/` | earlier / later | E items of `ROADMAP.md`; the hybrid vector features need shapely/GEOS (section 3). |
| `gerber-nets/` | later | electro-thermal coupling, no code in the program. |
| `memory-guard/` | earlier / later | `--log-level` and the measured peak in the summary (Planned 'Fixes' 11). |
| `paper-case-studies/` | earlier (warning) / later | source-aware laminate rule (A18). |
| `analytic-partial-copper/` | later | P3 (copper as a lateral defect) open; warning in the program. |
| `bare-spot-under-source/` | later | P1 to P3 wait for the maintainer. |
| `fin-channel/`, `fin-channel-sources/` | earlier (warning) / later | the channel correction (proposal B) waits. |
| `horizontal-plate-h/`, `plate-h-level/`, `theory-sources/` | none / decisions | answered by the program as it is; decisions in their INTEGRATION files. |
| `gap-subdivision/`, `laminate-nodes/`, `point-via-convergence/`, `sor-with-via-couplings/`, `young-omega-tiles/`, `zone-union/`, `via-edge-image/`, `lumped-analytic-vias/`, `lumped-via-groups/`, `lumped-zones-adoption/`, `via-real-board/`, `via-fill/`, `effective-conductivity/`, `outline/`, `stackup/`, `block-and-fins/`, `component-heatsink/`, `power-calculator/`, `solid3d-verification/`, `models-comparison/` | earlier | implemented in 2.4.x / 2.5.0; their open points are in `REVIEW.md`; `solid3d-verification` needs its tables refreshed with the slabs (2.6.1 item 5, documents only). |
| `theory/` | none | documents. |
| `releases/regression-harness/`, `releases/2.4.5/reproduction/`, `releases/2.5.0/reproduction/` | none | harness and passes; the 2.6.0 refreeze is done. |

## 3. Open decisions for the maintainer, with a recommendation

| Decision | Measured impact | Recommendation |
| :-- | :-- | :-- |
| Face-down constant: 0.475 (implemented), 0.52 (Incropera, not confirmed from an open source), or wait for board D | 0.52 against 0.475 is +9.5 % on the face-down convection term only; the whole change was -0.3 to -1.4 % of the rise | **Keep 0.475** until the Incropera page is read (status M) or board D is measured; add one computed-h board to `tests/regression` so that the next change of a law moves a frozen record. |
| Imported copper on an outline board: old links and film on the node | stated in a run note; no number measured on a real imported outline board | **Accept as a stated limit** until the pixel mask (2.6.1 item 2). |
| Film floor 0.25 as the program's own rule; film on rectangles | the floor acts only for a node outside the board by more than S/H; rectangles moved at most 0.008 K | **Accept** (the Bochkov condition is met; it is a safety net, written as the program's rule in `docs/theory.md` 2, the cut-cell film). |
| Analytic per-layer edge reads 5 to 10 % cool on small boards | the warning quotes the cool side | **Accept with the warning**; the common beta read 0 to +10 % on the same boards by two cancelling errors. |
| Default mapping of imported copper (faces on the reduced sheet, open since 2.5.0) | the faces were better on every comparison with the laminate rule on | **Confirm** the default. |
| Cost of the fine step-response cell for small parts | a 0.5 mm part on a 4-layer 100 x 80 mm board asks for 0.25 mm: guard estimate 6.9 GB, accepted ('ok' below 60 % of 16 GB); 22 s and 1.1 GB for a 2 mm part | **Cap it**: accept the finer cell only while the estimate stays under a fixed budget (for example 2 GB or 10 % of the memory) and otherwise keep the coarser cell with a line in the summary; with copper under the part the closed-form floor already covers the fast waves. A `fix/` for 2.6.1. |
| Add the neighbours' waves to the ripple | not measured; the ripple is local to the heater | **Later** (2.6.1 or 2.7.0) with a study; state it as a limit now (it is). |
| A via term in the column of the closed form | not measured | **Later**, after a study with an independent 3D solution. |
| Closed form for partial copper under the part | the floor applies only "on a part with copper under it" | **Later**; bare laminate already warns. |
| Fixed limits (1e6 mm, 1e100, outline bounds); only `package.max_mb` a preference | decided | none (recorded). |
| Markdown licence header on 288 `.md` files | none on numbers | **Do not add** to research and project Markdown (it clutters the rendered pages; the 'Author and license' statement covers them); decide once and write it in `CLAUDE.md` rule 4. |
| shapely/GEOS dependency and hybrid vector Gerber features | none in 2.6.0 | **Not in 2.6.x**; the own reader is enough; revisit with the E items (BSD-3 licence is compatible). |
| Get Papac, Gibou and Ratsch (2010) | the scheme is checked through the thesis (status N for the paper) | **Ask for the paper** (paywalled); not blocking. |
| 3D solid residual of 1.7 K, aligned against cut edge | a comparison model; documented in validation 33 | **Accept as a limit** of the comparison model; revisit with the copper-edge item (2.6.1 item 3). |
| Copper-corner via (sector well) | the via effect reads 15 to 85 % low, on the safe side; warned | **Later** (A30), after a study. |
| GitHub release for 2.6.0 (rule now in `CLAUDE.md`) | none | **Yes**, from the CHANGELOG section, after the tag is pushed. |

## 4. Release opinion

**Verdict: GO for 2.6.0, on condition that** the two corrections of section 5 (a crash on a via drawn before any copper, new in 2.6.0, and a crash on a block wholly off the outline, older) are brought into `feature/integration-260` and the whole battery passes on the final tree. Without the first correction it is a **no-go**: a user who draws a via before the zones gets an exception in the FVM, FDM and Lumped (2.5.2 ran the same board).

**Code** (diff `v2.5.2..f403326c`: 418 files, +48 243 / -791 lines; program files read where they interact):

* The cut-cell film, the laminate band and the via barrel meet in `fvm.Network`: the film uses the physical sheet after the laminate rule moved the laminate into its nodes, the band only adds flagged cells, the barrel couples the copper nodes through `viawell` (unaffected by the band). The FDM and the memory count call the same `laminate.edge_lengths`/`plan_gaps(edge=)`. Imported copper on an outline switches the cut cells off consistently. No inconsistency found.
* Lumped first ring + near-edge raster + small part: `lumped.cell_for` chooses one raster per board; a zoned part keeps 0.5 mm and the live list says so. No conflict found in the code; not measured beyond the tests.
* Fast-wave ripple + profile runner + memory guard: the response cell is enlarged until the guard says 'ok' for a transient; the ripple is added at the heater only. The cost question is section 3.
* Package + before-close hooks + display state: read, not exercised beyond the tests (`tests/test_package.py`, the hook tests).
* **Random boards with every feature together** (95 boards: outlines, `h_side` 0 to 600, 1 to 4 layers, vias anywhere, small parts, blocks, square waves, computed h; five models): two crashes (section 5), fixed. The Analytic heat balance is off on outline boards with a strong edge (8 of 100 boards above 0.1 % of the power, worst -120 %), **the same numbers in 2.5.2** (an older defect of the equivalent rectangle with the edge loss, recorded in section 6, not of 2.6.0); new in 2.6.0, the per-layer edge leaves a balance error of up to 4e-4 of the power on rectangles at `h_side` 600 (none above 1e-5 in 2.5.2): the GMRES tolerance, harmless.
* **Live check cost** (all checks, five models, `live=True`): 500 parts and 8000 vias on 4 layers 1.04 s (2.5.2: 0.62 s; the new `check_via_uncoupled` costs 0.45 s and has no time cap), with a round outline 3.2 s (2.5.2: 2.8 s); RP2040 0.07 s and CO60 (191 parts powered, 359 vias) 0.6 s at 1 and 0.5 mm. Acceptable; recommended: give the uncoupled-via pass the same time cap as the partial-copper pass (2.6.1).

**Program**: `python -m pcbthermal run` on the three example boards: the example board shows only the 2.5.2 Lumped via warning (not noisy); the reference board none; the profile board gives the ripple warning of U1 (2.01 K) once per model (three identical lines, mildly repetitive) and the Analytic heatsink transient warning. `--model compare --computed-h --cell-mm 2` gives four sensible warnings. The live list on the example boards has one line. Offscreen views (board with the map and the Display popover, every Results tab, the Power profile page with `average + ripple`, the three steps of the import window on the RP2040): no defect of 2.6.0 seen; the Power profile page scrolls sideways at 1600 x 950 with both docks open, the same in 2.5.2.

**Documents**: README, CHANGELOG, versions, guide and theory agree with the code on the items checked (the CLI numbers, the ripple example, the item list, the shifts). Corrected here: `docs/validation.md` 7 (power profiles) still quoted the 2.5 decisions of the profile example (U1 0.4 K averaged, U2 84.9 K) and old steady values; `docs/models.md` 19.2 repeated a paragraph of 1195 characters (also in 2.5.2). Left for the maintainer and the tester: the README badge still says 2710 tests and `docs/versions.md` 2.6.0 has the 'How 2.6.0 was tested: TODO (tester)' line (both filled after the battery). The documentation, help, version and licence tests pass (687).

**Investigations**: the register had no rows for `releases/2.5.0/reproduction/` and `releases/2.6.0/reproduction/`, its 2.6.0 status paragraph said that the reproduction pass had not run, several index statuses still said 'waits for the maintainer' for work implemented in 2.6.0, and `ROADMAP.md` carried four stale duplicate entries (A16, A17, A19, A20) and A28 as running: all corrected in this commit.

**Tests and hygiene**: licence headers and version tests pass; no generated output added outside `research/*/figures` and `docs/images` (the new JSON files are the frozen references and a test table); each new research folder has its `.gitignore`.

**Blocking defects**: the via crash (fixed here, section 5). **Not blocking**: the block off the outline (older, fixed here), the uncoupled-via pass without a time cap, the repeated ripple warning, the Analytic balance on outline boards (older).

## 5. Defects found and fixed on this branch

| Defect | Evidence | Fix | Test |
| :-- | :-- | :-- | :-- |
| A via whose rim touches no copper and no heater on any layer crashes the FVM, FDM and Lumped (`numpy.linalg.LinAlgError: Singular matrix` in `viawell.kron_barrel`). New in 2.6.0 (rim rule); 2.5.2 runs the board. | 40 x 30 mm, 4 layers, a 1 W part, one via at (20, 15) mm, no zones: FVM, FDM, Lumped fail; with a zone on one layer all run. | `viawell.kron_barrel` returns zero couplings when fewer than two wells are positive (the barrel nodes float otherwise). No frozen number moves (`tests/regression` at 2 mm: 153 passed). | `tests/test_via_barrel_and_rim.py::test_a_via_on_bare_laminate_on_every_layer_runs_in_every_model` (direct and SOR; the FVM and FDM equal the board without the via). |
| A metal block inside the box but wholly outside the outline crashes the FVM, FDM and 3D solid read-out (`zero-size array to reduction operation maximum`). Also in 2.5.2. | random board seed 13 of the review's fuzz; the 60 x 40 mm board cut at x = 20 mm with a block at (2..12, 5..15) mm. | `fvm.attach_block_results` and `solid3d.solve_steady` skip the read-out of a block with no cell on the board. | `tests/test_block_outline.py::test_a_block_wholly_off_the_outline_runs_and_heats_nothing` (five models). |

## 6. What was read and what was not verified

* **Read**: the CHANGELOG 2.6.0 section, `docs/versions.md` 2.6.0 and 'Planned', `research/REVIEW.md`, `research/README.md`, `research/ROADMAP.md`, `releases/2.6.0/reproduction/README.md`; the diffs of `fvm.py`, `fdm.py`, `laminate.py`, `viawell.py`, `viaconstriction.py`; `checks.check_input`; `api.response_cell_mm`; the frozen files `v2.5.0.json`, `v2.6.0.json` and the table `expected_shifts_2.6.0.json` (shifts computed here record by record).
* **Run**: the three example boards through the CLI; a compare run with computed h; the live-check timing (synthetic 500 parts / 8000 vias, CO60, RP2040) on 2.6.0 and on the tag v2.5.2; 95 random boards in five models on 2.6.0 and 100 in the Analytic on both trees; the offscreen views; `tests/test_via_barrel_and_rim.py`, `tests/test_point_via.py`, `tests/test_block_outline.py`, `tests/test_blocks.py`, `tests/regression` (2 mm), `tests/test_docs.py`, `tests/test_help.py`, `tests/test_license_header.py`, `tests/test_version.py`.
* **Not verified**: the whole battery (the tester's, running in parallel on the integration worktree); the frozen numbers at 1 and 0.5 mm; the research studies themselves (only their tests ran in `releases/2.6.0/reproduction`); `analytic.py`, `solid3d.py`, `stackimpedance.py`, `package.py` and the GUI diffs were not read line by line; the interaction of the package, the hooks and the display state beyond the tests; a real (cocoa) screen; the cause of the older Analytic balance error on outline boards with a strong edge (seeds 16 and 17 of the fuzz: -56 % and -120 % of the power, identical in 2.5.2): recorded as an unexplained result for a `fix/` after 2.6.0.
