# Version history in detail

What was implemented in every version, where it lives in the code, how it is tested and what it left out. The short list is `CHANGELOG.md`; the physics is in
`models.md`, the numbers in `validation.md`, the plans in `roadmap.md`. Dates are those of the release tags. **Newest first**: the next version is at the top, the original program at the bottom.

## How to read this file

For each version: the **headline**, a table of **what was implemented** (feature, code, tests/evidence), **what changed** for existing users and the **limits** that remained.


---

## Unreleased: model corrections after a review

* **One-layer boards** (`laminate.py`, new; `fvm.py`, `fdm.py`, `analytic.py`, `api.py`): `laminate.nodes(board)` gives the laminate nodes of a one-layer board (`LAMINATE_NODES = 2`), `laminate.extra_layers` their arrays; the FVM and FDM append them as node layers after the board layer (before the metal blocks, whose indices now start after them; `block_info` carries its `board_layer`), move the bottom film to the last one and join them with `extra_links`; SOR folds those links into its vertical conductances; the Lumped model gets them through the FVM network; the Analytic model runs on `laminate.series_bottom_problem(problem)`; `extras["bottom_face_mean"]` feeds `api._solve_computed_h`. Tests: `tests/test_laminate.py` (closed form of a uniform board, agreement with the 3D solid, solvers, transient, computed coefficients) and the closed-form tests of `test_fvm.py` and `test_profiles.py` (the single-node RC forms switch the laminate nodes off). Studies: `research/solid3d-verification/scripts/study_one_layer_board.py` (part 2, with the independent solver copied to `research/solid3d-verification/lib/layered3d.py`), `research/models-comparison/scripts/study_complex_boards.py`.
* **Analytic heat balance with a block** (`analytic.py`): the face heat of the tiles under a block is taken off the `top` or `bottom` total of `power_out`. Test: `tests/test_block_models.py`.
* **Lumped rings** (`lumped.py`): `ring_edges()` builds the edges and merges those closer than `RING_MIN_WIDTH = 1` cell. Test: `tests/test_models_agree.py`. Study: `research/models-comparison/scripts/study_lumped_rings.py`.

* **Outline boards** (`fvm.py`, `fdm.py`, `lumped.py`): the 1 W/K pin of the cells or nodes off the board is a separate array `g_pin`; `fvm.board_time_constant(net)` (`ΣC / (ΣG_amb − Σg_pin)`) replaces the plain `C.sum() / g_amb.sum()` in `estimate_time_constant`, `step_responses_from_network` (FVM and FDM) and the Lumped step responses; `fvm.mean_weights(net)` gives the board area of every cell (FVM) or node (FDM), used for the transient mean and to keep the off-board cells out of the transient maximum. Tests: `tests/test_outline.py` (time constant and step responses on a round board, transient mean). Study: `research/outline/scripts/study_outline_time_constant.py`.
* **3D solid, one layer** (`solid3d.py`): a one-layer board gets `n_diel` FR-4 slabs of `slab − copper` under the copper (the laminate of the layered models; vias in parallel as in a gap). Test: `tests/test_solid3d.py` (`test_a_one_layer_board_keeps_its_laminate`). Study: `research/solid3d-verification/scripts/study_one_layer_board.py`.
* **Edge of an outline** (`geometry.edge_length_per_cell`, `geometry.edge_length_on_board`): each sample of the outline is nudged `1e-3` of the smaller cell side towards the inside (the inside is on the left of a counter-clockwise polygon) before it is given to a cell, so a side on a grid line is not given to the cell off the board; the length that still falls in a cell off the board (a sliver of board that none of the 4 × 4 cover samples reaches, on slanted and curved sides) goes to the nearest cell on the board, split equally between equally near cells. The FVM, the FDM and the 3D solid use `edge_length_on_board`, so the counted edge is the perimeter whatever the position of the outline on the grid (the FDM, whose node cover is smeared over the neighbours, was not affected). Tests: `tests/test_outline.py` (edge counted by the FVM and the FDM equals the polygon perimeter for a rectangle, an L, a T, its mirror image, squares turned by 3 to 45 degrees, a disc and an ellipse; the T and its mirror image give the same maximum in the FVM and the 3D solid; time constant of the T, a disc, an ellipse and a turned square against the closed form; a turned square against the same square on the grid; the helper moves lengths only to neighbours of the lost cells). Studies: `research/outline/scripts/study_edge_on_grid_lines.py` and `study_disc_reference.py` (on the research branch).
* **Part power loop** (`api._solve_with_tc`): a warning when the powers do not settle in 80 iterations. Test: `tests/test_component.py`.
* **Plate check** (`research/component-heatsink/scripts/block_contact_study.py`): 0.5 mm cells and halves rounded up; documents corrected (`theory.md` sections 7, 8 and 11, `research.md`, `validation.md`).
* Found and not changed: the Lumped model does not converge with the ring count (`validation.md` section 20, `roadmap.md`).

## Unreleased: the investigations in `research/`

The studies of `examples/` moved to `research/<topic>/` (eight folders; the Gerber research stays on its own branch), with documents and figures; no change to the program except the case count in a tooltip (62 → 74) and test paths. See `research/INDEX.md`.

---

## 2.4.1 - 2026-10-22: licensing

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| MIT License stated consistently (copyright 2025-2026 Pedro Silva, PMS Labs) in `LICENSE`, README, About box and `CLAUDE.md`; note that results are a design aid not validated against a physical board | `LICENSE`, `README.md`, `gui/help.py` | `test_help.py`, `test_version.py` |

No change to the models or the interface. Limits: a paid or proprietary model is not decided; versions up to 2.4.0 stay MIT.

---

## 2.4.0 - 2026-10-22: parts, stack-up, outline, tools

Work of the branches `feature/component-element` and `feature/junction-node` (merged through `develop`).

### Parts (the Component element, first delivery)

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| Heater as a **part**: junction-to-pad resistance `theta` (worst case: all the power enters the board), `Tj = hottest board point under the part + P theta` (old key `theta_jb` still opens) | `model.Heater`, `analysis.heater_stats` | `test_component.py` |
| **Tj max**: margin, **power limit**, warning | `analysis.py`, `api._part_warnings` | power limit puts Tj exactly at the limit |
| **psi_JB**: second estimate from the board temperature in the ring 0.5 to 1.5 mm around the part | `analysis._ring_mean` | |
| **Power temperature coefficient**: `P = P0 (1 + c (Tj - 25))` solved with the board, thermal runaway detected | `api._solve_with_tc` | matches the closed form to 0.05 K in three models |
| Package-family typical values, hints, datasheet guide, warning when theta looks like a theta_JA | `model.PACKAGE_THETA`, `gui/panels.py` | `validation.md` section 9 |
| **Top path** (heatsink on the package): `theta_jc_top`, `interface`, `theta_sa`; the part becomes a junction node, the board gets only the power the top does not take; fixed-point loop around any model | `analysis.part_split`, `api._solve_with_tc` | within 0.4 to 0.8 K of the junction-node prototype (`research/component-heatsink/scripts/top_path_study.py`) |

### Variable stack-up (simple and advanced)

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| Per-layer copper thickness and per-gap dielectric (thickness, k through, k in-plane, density, specific heat) in **all five models**; the simple stack-up is unchanged | `model.Board`, `Dielectric`, `DIELECTRICS`; `fvm.py`, `fdm.py`, `analytic.py`, `solid3d.py`, `blocks.py` | `test_stackup.py`: equal gaps within 3 % of simple, trends in every model, models agree, JSON round trip |
| **Stack-up tab**: cross-section drawn to scale (true proportions or readable), thickness in µm and mm, total thickness, a click shows the layer; layer table; simple/advanced switch; laminate presets | `gui/stackup.py` | `test_gui_stress.py::test_advanced_stackup_in_the_application` |

### Board outline (any shape)

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| Board outline polygon: cell cover, edge loss along the outline, blank cells in plots, parts off the board deliver power to the nearest board cell; FVM, FDM and 3D solid (lumped and analytic run on the rectangle of the same area, see below) | `model.Board.outline`, `geometry.edge_length_per_cell`, `fvm.py`, `fdm.py`, `solid3d.py`, `plots.py` | `test_outline.py`: a rectangle as polygon is identical, a smaller outline equals the smaller board, energy closes, models within 3 % |
| Outline presets, vertex table, outline tool | `gui/panels.py`, `gui/canvas.py` | |
| Right-click menu: add/delete a vertex, duplicate, delete, add an element on an empty spot | `gui/canvas.BoardView.build_context_menu`, `geometry.insert_vertex/nearest_vertex` | `test_context_menu.py` |
| Properties panel in boxes; heatsink manual input as h or θSA; Direct contact interface; simple stack-up and materials in the Stack-up tab | `gui/panels.Inspector.rebuild`, `gui/stackup.StackupPage.add_parameters` | `test_inspector_sections.py` (also: advanced mode hides the simple-only rows; side panels scroll), `test_tooltips.py`, `test_heatsink_part.py` |
| Lumped and Analytic on an outline: rectangle of the same area (box and positions scaled by sqrt(area ratio), parts keep their size, field stretched back), warning in the Results summary, no time simulation for them | `model.Problem.equivalent_rectangle`, `api._run_model`, `api.simulate`, `gui/main_window._confirm_rectangle`, `research/outline/scripts/outline_rectangle_study.py` | `test_outline.py` (area, sizes, beats the bounding box), `test_gui_stress.py` (cancel and confirm); `docs/validation.md` section 13 |

### Application

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **Calculation in a separate process**: Cancel button (Ctrl+.), window never freezes, nothing left running after closing | `jobs.py`, `gui/compute.py` | `test_compute.py` |
| **Power calculator** (power from a measured temperature, by the board model or a datasheet parameter) | `inverse.py`, `gui/calculator.py` | `test_inverse.py` |
| **Help menu**: HTML user guide (in the program or the browser), About box (version, author, project link, libraries) | `help/index.html`, `gui/help.py` | `test_help.py` |
| **Tooltips on every control**, checked by a test | `gui/tips.py` | `test_tooltips.py` |
| Rulers and scale bar on the board, drag keeps every element on the board (a via no longer jumps off), shape position and size fields, tool keys S Z H C V O, tab shortcuts Ctrl+1..4, hidden unused heat transfer fields, units on every field | `gui/canvas.py`, `gui/document.py`, `gui/panels.py`, `gui/main_window.py` | `test_gui_stress.py` |

### Typical stack-ups, interface presets and curved boards (2026-10-21, second batch)

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **Typical stack-ups by layer count** (1, 2, 4, 6, 8, 10, 12; generic for odd counts) in an editable JSON file, loaded when the layer count changes and by a button on the Stack-up tab | `data/stackups.json`, `model.load_stackup_templates`, `stackup_template`, `Board.apply_template`, `gui/document.py` | `test_templates.py`: file consistency (counts, symmetric builds, real thicknesses, known materials), every template runs in all five models, a user file works, a bad file is refused |
| Interface material presets for the heatsink on a package (paste, gap pads) | `gui/panels.py`, `model.INTERFACES` | `test_templates.py` |
| Heatsink: θSA from the datasheet sets the extra h over the polygon | `gui/panels.py` | `test_templates.py` |
| Board orientation reduced to what the layer numbering already says (layer 1 = top faces up; horizontal or vertical only), validated against the textbook correlations | `convection.board_h`, `tests/test_orientation.py` | `test_orientation.py` |
| Rounded-corner preset, Subdivide button, `geometry.rounded_rectangle` | `gui/panels.py`, `geometry.py` | `test_templates.py`: area error 0.13 % at 8 edges, temperature converges |
| Documentation of the heat paths, the stack-up contents and curved boards | `docs/models.md` sections 12 to 14, the user guide | |

### Third batch (2026-10-21): computed heatsinks, contact area, prepreg

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **Cooling model** of the Heatsink element: *Coefficient* (extra h or θSA) or *Metal block, computed* (the program does the rest); fields appear for the chosen model | `gui/panels.py` | `test_heatsink_part.py` |
| **Fins on a metal block**: height, thickness, pitch; area gain with fin efficiency, in the FVM, FDM and 3D solid (lumped and analytic: steady state only); warning for fins too close in still air | `blocks.fin_ratio`, `blocks.exposed_h`, `Heatsink.fin_*`, `solid3d.py`, `checks.py` | textbook formula to 1e-12, the five models, FVM/FDM/3D within 1 % (`validation.md` 12 D) |
| **Contact area** of a part's interface (lid or exposed top; empty = footprint) and the **body helper** (θJC(top) = t/(kA) from thickness and material), for processors and chips with a heatsink | `Heater.contact_area`, `gui/panels.py` | `test_heatsink_part.py` |
| **Gaps of several sheets** (prepreg and core): `combine_sheets` (series through, parallel in plane), `"sheets"` in the templates | `model.combine_sheets` | exact formulas in `test_heatsink_part.py` |
| **The interface is one dielectric sheet** between the heatsink and the board or the package, with its own material and thickness (`pad_thickness`, `pad_k`; resistance t/k; the typed resistance still works) | `Heatsink.interface_resistance`, `Heater.interface_kcm2`, `gui/panels.py _pad_rows`, `blocks.py`, `solid3d.py` | `test_heatsink_part.py`: same temperatures as the equivalent resistance, thicker sheet hotter, JSON, validation |
| Sensitivity of the temperature to the stack-up numbers (dielectric k, thickness, copper) | `research/stackup/scripts/stackup_outline_study.py` | `validation.md` 12 C |
| Orientation worded by faces (top up / top down / vertical) | `gui/panels.py` | |
| Documentation: `docs/models.md` sections 15 to 18 (computed block, paste and processors, prepreg, orientation) | | |

### Fourth batch (2026-10-22): forms, verification, models and blocks

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| Metal block in the Lumped (ring layer) and Analytic (tile graph, Schur complement) steady states, 1 to 2 % off on average; no time simulation for them with a block; fields that do not apply are greyed (top path without θ and θSA, settings of models that are not selected) | `lumped._heater_network`, `analytic._block_tiles`, `blocks.require_no_blocks`, `api.simulate`, `gui/panels.SolverPanel._update_availability`, `Inspector.rebuild` | `test_block_models.py`, `test_blocks.py`, `test_inspector_sections.py`, `research/block-and-fins/scripts/block_equivalent_study.py` |
| Fins validated against an independent 2D solution of one fin (24 cases within 0.08 %) | `research/block-and-fins/scripts/fin_validation.py` | `test_fin_model.py`, `validation.md` section 15 |
| 3D solid verified against Yovanovich's spreading-resistance table (0.7 to 0.8 %) and a grid-convergence study (GCI 1.14 %) | `research/solid3d-verification/scripts/solid3d_verification.py` | `test_solid3d_verification.py`, `validation.md` section 16 |

### Fifth batch (2026-10-22): vias and the power calculator

| Feature | Code | Tests / evidence |
| :-- | --: | --: |
| Via fill: open, epoxy resin, conductive paste, electroplated copper (`Via.fill_k`, `Via.thermal_area`, `VIA_FILLS`, the *Fill* list; old files unchanged) | `model.py`, `fvm.py`, `fdm.py`, `analytic.py`, `solid3d.py`, `gui/panels.py` | `test_via_fill.py`; `validation.md` section 18 |
| Power from the top of the package (`point="top"`, θ and ψJT) in the API, the job and the calculator | `inverse.py`, `jobs.py`, `gui/calculator.py` | `test_inverse.py`; `validation.md` section 19 |

| Preferences: libraries and defaults in JSON (shipped `defaults.json` + user `user_defaults.json` with only the differences), editor window, start-up notice; via fill by name with an editable typical value | `defaults.py`, `data/defaults.json`, `model.reload_libraries/new_problem`, `gui/preferences.py`, `gui/panels.py`, `gui/main_window.py` | `test_defaults.py` |

| Power calculator reworked (name, parameters inside the window, hints, result with temperatures and board resistance), validated against datasheet boards; empty board at start-up | `gui/calculator.py`, `inverse.py`, `gui/app.py`, `research/power-calculator/scripts/calculator_validation.py`, `docs/calculators.md` | `test_calculator_validation.py`, `test_inverse.py` |

| Power calculator: tabs per route, constant window size, Help window, uncertainty band with best / nominal / worst selector (`inverse.power_band`, `calculator` defaults) | `inverse.py`, `jobs.py`, `gui/calculator.py`, `help/calculator.html`, `defaults.json` | `test_inverse.py` (band), `test_defaults.py` (window, selector, routes) |

| Heater type (heat source with an interface under it / component), package family fills θ, θJC(top), Tj max from the library in Preferences | `model.Heater.role/base_*/junction_theta`, `analysis.part_split`, `gui/panels.py`, `defaults.json` | `test_component.py`, `test_inspector_sections.py` |

| Typical heatsink list for the top of a package (library `heatsinks`: heatsink and air flow, θSA from catalogues, 11 entries); the top-path boxes appear with θSA; the study of flow factors against catalogues is in `research.md` R3 | `defaults.json`, `model.HEATSINKS`, `Heater.heatsink`, `gui/panels.py` | `test_inspector_sections.py` |

### Changed behaviour

- Changing the number of layers in the application now loads the typical stack-up of the new count (copper, dielectrics and total thickness in the advanced mode; total thickness and outer copper in the simple mode): a 4-layer board is 1.586 mm, a 10-layer board 2.0 mm.

- The edge loss of the FVM and FDM no longer adds the board edge conductance to the layers of metal blocks (the block's own edge is in its exposed surface): the old code counted it twice. The effect on the examples is below the validation tolerances.
- `Board.thickness` stays the typed value in the simple stack-up; use `Board.total_thickness()` for the real total.

---

## 2.3.0 - 2026-10-17: FDM in time, metal blocks, the 3D solid

(Rewritten at the maintainer's request to include the work first planned for 2.4.0.)

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **FDM in time**: power-step animation, step responses and profile simulation on the nodes (same theta-method as the FVM) | `fdm.py`, `fvm.transient_from_network` | hottest point within 0.7 °C of the FVM |
| **Metal block** (a Heatsink with a thickness): extra node layer in the FVM and FDM, lateral conduction, mass, contact over the copper it overlaps through an interface resistance, material and interface presets | `blocks.py`, `gui/panels.py` | `test_blocks.py`; within 1.8 % of the 3D solid |
| **Sink renamed Heatsink** everywhere (old files with `sinks` still open) | `model.py` | |
| **3D solid** model: the board as a real solid with a slab per copper layer and per dielectric gap, vias with their real copper area, metal blocks; steady state | `solid3d.py` | `test_solid3d.py`; within 0.2 % of an independent finite-element solid on three boards |
| Studies: copper that dissipates needs no element; what a package resistance and a top path add on five real parts | `research/solid3d-verification/scripts/copper_dissipation.py`, `research/component-heatsink/scripts/component_study.py`, `test_copper.py` | `validation.md` section 3.1, `roadmap.md` 1.9b |

---

## 2.2.0 - 2026-10-16: tables, the FDM, 3D check, clean documentation

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **Power tables and CSV files** (`TableProfile`, repeating or one-shot, import/export, `run --profile`) | `model.TableProfile`, `profile_io.py`, `examples/csv_profiles/` | `test_profiles.py`, stress tests with bad CSV files |
| Analytic transient with vias and heatsinks (one modal system per heater, scaled to the local steady response); animation of the power step also for the Analytical model | `analytic.py` | curve within 2.5 °C of the FVM (10 °C before) |
| **FDM** comparison model (node-centred finite differences, area sampling by default) | `fdm.py` | `test_fdm.py`; FDM within about 1 % of the FVM |
| About 40 % faster direct solves (symmetric sparse ordering) | `fvm.ORDERING` | `research/models-comparison/scripts/solver_equivalence.py` |
| `calibrate_convection` and `pcbthermal calibrate` | `api.py`, `cli.py` | |
| Independent 3D finite-element check with vias and heatsinks (offline, scikit-fem) | `research/solid3d-verification/scripts/fem3d_validation.py` | `validation.md` section 3 |
| Documentation cut to `models.md`, `validation.md`, `roadmap.md` | `docs/` | `validation.md` is regenerated by `research/models-comparison/scripts/validation_study.py` |
| Stress test of the application (every example with every model, every view, odd boards, edits during a run, random actions) | `tests/test_gui_stress.py` | found one real bug: a result arriving after an edit was shown as current |

Fixed: that bug; the abort when two background calculations ran at the same time (SuperLU is not safe in two threads: they now wait for each other); node fields in the plots, hotspot list and overlay.

---

## 2.1.0 - 2026-10-16: power profiles and computed heat transfer

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| **Power profiles** (square wave) per heater, in the three models; the decision average-or-resolve per heater from the oscillation in °C (default 1 °C, shared error budget); mixed regimes in one run; start from the steady state of the average power or a typed temperature; duration until the cycle repeats / N cycles / fixed time; 200,000-step cap | `profiles.py`, `model.SquareWave` | `test_profiles.py`, `test_gui_profile.py` |
| "Power profile" tab and results tab; CLI `run --duration --cycles --time-s --initial-c --threshold-c --steady-power`, `example --which profile` | `gui/profile_page.py`, `gui/profile_results.py`, `cli.py` | |
| **Computed heat transfer coefficients**: natural and forced convection plus radiation per face from the mean face temperature, emissivity, orientation, air speed and a convection multiplier; solved by iteration in all models | `convection.py`, `api._solve_computed_h` | `test_convection.py`; a constant `h` overestimates the rise by 10 % at 22 W (`roadmap.md` section 2) |
| Model names in the GUI ("Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)"); temperature differences in °C | `gui/` | |

Limits: the analytic transient smeared vias and heatsinks over the board (warned).

---

## 2.0.0 - 2026-10-16: the rebuilt program

First release of the new physics package and GUI.

| Feature | Code | Tests / evidence |
| :-- | :-- | :-- |
| GUI-independent physics package `pcbthermal` with a public API (`Problem` builder in mm, `SolverOptions`, `simulate`) and project files `.pcbt.json` | `model.py`, `api.py`, `project.py` | 94 tests, a documentation gate (`test_docs.py`) requiring Doxygen docstrings on every function |
| **FVM**, the reference: cell-centred finite volumes, sparse direct/CG/SOR solvers, exact heater power on any grid | `fvm.py`, `geometry.py` | energy balance of every result; SOR equals the direct solve to 1e-8 K when it stops on the residual |
| **Lumped** thermal network: rings by distance from the real footprint, one network per heater, Bessel correction for vertical losses | `lumped.py` | example board within 1 to 2 % of the FVM |
| **Analytic** multilayer Fourier series with copper weighting and local via/heatsink corrections | `analytic.py` | example board within 2 %; warnings when its assumptions fail |
| Anisotropic FR-4 (0.3 through, 0.9 in plane), hollow plated via barrels | `model.py` | |
| Input validity checks, shown live (heater off the board, no copper under a part, ...) and **Auto** cell size | `checks.py`, `api.suggest_cell_mm` | `test_api.py` |
| Transient response (implicit Euler, Crank-Nicolson), animation in the GUI and `transient --gif` | `fvm.solve_transient`, `gui/animation.py` | exact exponential reference |
| PySide 6 application: editor with undo/redo, inspector, background image, dark/light themes, results tabs, export | `gui/` | `test_gui.py` |
| Command line `run`, `solvers`, `transient`, `convergence`, `convert`, `gui`, `example` | `cli.py` | |
| Version defined only in `pcbthermal/__version__`, shown in the title bar, status bar, reports and project files | `__init__.py` | `test_version.py` |

Limits: steady-state power only (no profiles), constant heat transfer coefficients, no component junction model beyond an offset.

---

## 1.0.0 - 2025 (tag `legacy-wxpython-1.0.0`)

Original wxPython program, "PCB Thermal Simulator Tool".

| Feature | Notes |
| :-- | :-- |
| Interactive editor (zones, heaters, vias, sinks) | wxPython; removed in 2.0.0 |
| Three solvers: Analytic, Lumped, FDM (SOR) | had modelling errors: false convergence of the SOR stop rule, heater power depending on the grid, no lateral conduction in the FR-4, solid vias, a dimensionally wrong analytic term, an invalid lumped network (`validation.md` section 6) |
