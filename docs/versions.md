# Version history

What was implemented in every version (with the module where it lives and how it is tested) and what we still want to implement (last chapter, "Planned"). The release notes are `CHANGELOG.md`; the physics is in `models.md` and `theory.md`, the numbers in `validation.md`. **Newest first.** Dates are those of the release tags. Each bullet reads: feature (code; tests).

---

## Unreleased

* **Via diameter labelled as the drill** (`gui/tips.py` key `drill diameter`, the *Drill diameter* field, `Via.diameter`, the guide, `docs/models.md`): the text now says what the model uses; no number changes.

* **Top path only on a component**: `Heater.has_top_path()` (a component with `theta > 0` and `theta_sa > 0`) is the one condition used by `top_resistance()` and so by the report row and the split of the power; a pure source that carries `theta` and `theta_sa` from a file or the API ignores them (it used to show `r_top > 0` with no heat through the top, and with an interface under it a hidden top path that cooled the part by 39 K in the test case) (`tests/test_top_path_role.py`).

* **Metal block beyond the board outline**: the block is cut at the outline in the FVM, FDM and 3D solid (`blocks.extra_layers` receives the board cover; `solid3d.py`), so a block over the cut-away part no longer drains into the cells pinned to the ambient (it read 38 K cold on the test board: FVM 66.8 against 104.7 degC); the input check measures the block against the outline and says it is cut there. Lumped and Analytic take the block whole on the rectangle of the same area (`tests/test_block_outline.py`).

---

## 2.4.2 - 2026-10-29: interface review, calculator uncertainty, corrections

User-visible changes first.

* **Power Calculator, design uncertainty**: the *Board description* list (none, CAD, hand, estimated) adds copper coverage, copper weight, inner planes and vias to the best / nominal / worst band (`inverse.power_band`, `defaults.json` `calculator.design_*`, `gui/calculator.py`; `test_calculator_design.py`, `test_inverse.py`). Level none is the old band.
* **Inner copper 0.5 oz or 1 oz** for the typical stack-ups; 1 oz keeps every dielectric (`model.stackup_template`, `Board.template_inner_oz`, Stack-up tab; `test_inner_copper.py`).
* **Natural convection form** of a vertical board, general (default) or laminar (`Board.natural_form`, Environment panel, CLI `--natural-form`; `test_natural_form.py`).
* **Thick-plate warning** when `q'' t / (2 k)` of a copper layer or block exceeds 5 % of the rise (`checks.check_thick_plates`; `test_thick_plate.py`).
* **Numbers in the interface**: decimal point whatever the system language, a comma typed in a field read as the point, engineering notation outside 0.01 to 10000 (`numfmt.py`, `theme.fix_number_locale`, `plots.engineering_ticks`; `test_numfmt.py`, `test_gui.py`).
* **Interface review**: docks of a usable width and a Run footer always in sight, scroll areas for the wide pages, docks remembered; list of input warnings that selects the element; keyboard focus kept after an edit; theme hint colour; readable Preferences; solver-grid icon; no tooltip on command buttons; table of models without a scroll bar; texts for a first-time user; the name Power Calculator (`gui/`; `test_gui.py`, `test_tooltips.py`, `test_defaults.py`, `test_inspector_sections.py`).
* **Fixes that move results**:
  * one-layer boards get two laminate nodes (FVM, FDM, Lumped) or a series film (Analytic) (`laminate.py`; `test_laminate.py`);
  * the 3D solid keeps the laminate of a one-layer board (`solid3d.py`; `test_solid3d.py`);
  * the Lumped merges rings narrower than a cell (`lumped.py`; `test_models_agree.py`);
  * the cells off an outline are no longer a path to the air in the time constant, step responses and transient mean (`fvm.board_time_constant`, `mean_weights`; `test_outline.py`);
  * the whole outline edge is counted (`geometry.edge_length_on_board`; `test_outline.py`);
  * the side walls of a finned block no longer carry the fin ratio (`blocks.wall_h`; `test_block_side_loss.py`);
  * the top-path split is solved as a root, not a loop (`api._top_path_split`; `test_top_path.py`);
  * a power loop that does not settle warns (`test_component.py`);
  * the Analytic heat balance with a block (`test_block_models.py`).
* **3D solid limited to 250 000 unknowns**, checked before building, with the cell that fits; the panel shows the exact count; a cancel kills a process that survives SIGTERM (`solid3d.MAX_CELLS`, `unknowns`, `check_size`, `gui/compute.py`; `test_solid3d.py`, `test_compute.py`, `test_gui_stress.py`).
* **Independent 3D solver as a test reference** (`tests/helpers/layered3d.py`; `test_layered_vs_3d.py`).
* **Documents**: screenshots regenerated, times and memory replaced by the measured table, research text folded into `research.md`, `theory.md`, `models.md`, `validation.md`; the investigations moved to `research/`; the program roadmap folded into the chapter "Planned" below (`test_docs.py`, `test_help.py`, `test_version.py`).

---

## 2.4.1 - 2026-10-22: licensing

The MIT licence stated alike in `LICENSE`, README and the About box, and a note that results are a design aid not validated against a physical board (`gui/help.py`; `test_help.py`, `test_version.py`). No change to the models.

## 2.4.0 - 2026-10-22: parts, stack-up, outline, tools

* **Parts**: junction temperature from a datasheet resistance (`model.Heater.theta`, worst case), Tj max with margin and power limit, ψJB estimate, power temperature coefficient with runaway detection, package-family typical values, heater as source or component (`analysis.py`, `api._solve_with_tc`; `test_component.py`).
* **Top path** (heatsink on the package) in every model: junction node split as a root (`analysis.part_split`, `api._top_path_split`; `test_top_path.py`), typical heatsink library, contact area and body helper, interface as one dielectric sheet (`Heater.heatsink`, `contact_area`, `pad_*`; `test_heatsink_part.py`, `test_inspector_sections.py`).
* **Advanced stack-up** in all five models (copper per layer, dielectric per gap, sheets combined) with the cross-section tab and typical stack-ups of 1 to 12 layers (`model.Board`, `data/stackups.json`, `gui/stackup.py`; `test_stackup.py`, `test_templates.py`).
* **Board outline** of any shape in FVM, FDM and 3D solid; Lumped and Analytic run on the rectangle of the same area with a warning (`Board.outline`, `Problem.equivalent_rectangle`, `geometry.py`; `test_outline.py`); presets, vertex table, rounded corners, right-click menu (`test_context_menu.py`, `test_templates.py`).
* **Metal blocks** computed with fins, in all five models (Lumped and Analytic in steady state) (`blocks.py`, `lumped._heater_network`, `analytic._block_tiles`; `test_blocks.py`, `test_block_models.py`, `test_fin_model.py`); fins checked against a 2D solution and the 3D solid against Yovanovich's table (`validation.md` 15, 16).
* **Via fill** (open, resin, paste, copper) (`Via.fill_k`, `VIA_FILLS`; `test_via_fill.py`).
* **Calculation in a separate process** with Cancel (`jobs.py`, `gui/compute.py`; `test_compute.py`).
* **Power Calculator**: power from a measured temperature by the board model or a datasheet parameter, tabs per route, best / nominal / worst band, Help window, validated against datasheets (`inverse.py`, `gui/calculator.py`; `test_inverse.py`, `test_calculator_validation.py`; `calculators.md`).
* **Preferences and defaults in JSON** (shipped `defaults.json` plus the user's differences) (`defaults.py`, `gui/preferences.py`; `test_defaults.py`).
* **Help and tooltips**: HTML user guide, About box, a tooltip on every control (`help/index.html`, `gui/tips.py`; `test_help.py`, `test_tooltips.py`).
* **Editor**: rulers and scale bar, drag keeps elements on the board, tool keys, tab shortcuts, orientation top up / top down / vertical (`gui/canvas.py`, `convection.board_h`; `test_gui_stress.py`, `test_orientation.py`).
* Changed: a new layer count loads the typical stack-up; the edge loss no longer counts the board edge twice on a block.

## 2.3.0 - 2026-10-17: FDM in time, metal blocks, the 3D solid

* FDM animation, step responses and power profiles (`fdm.py`; hottest point within 0.7 degC of the FVM).
* Metal block (a Heatsink with a thickness) as an extra node layer in FVM and FDM (`blocks.py`; `test_blocks.py`, within 1.8 % of the 3D solid); Sink renamed Heatsink (old files open).
* 3D solid model with a slab per copper layer and gap, real via copper, blocks, steady state (`solid3d.py`; `test_solid3d.py`, within 0.2 % of an independent finite-element solid).
* Studies: copper that dissipates needs no element; what a package resistance and a top path add (`validation.md` 3.1).

## 2.2.0 - 2026-10-16: tables, the FDM, 3D check

* Power tables and CSV files (`model.TableProfile`, `profile_io.py`, `run --profile`; `test_profiles.py`).
* Analytic transient with vias and heatsinks, one modal system per heater (`analytic.py`; within 2.5 degC of the FVM).
* FDM comparison model (`fdm.py`; `test_fdm.py`, within about 1 % of the FVM); direct solves about 40 % faster (`fvm.ORDERING`).
* `calibrate_convection` and `pcbthermal calibrate` (`api.py`, `cli.py`); independent 3D finite-element check (offline).
* Stress test of the application (`test_gui_stress.py`); fixed a result shown as current after an edit and an abort with two background calculations.

## 2.1.0 - 2026-10-16: power profiles and computed heat transfer

* Square-wave power profiles per heater, average or resolved automatically, in the three models; Power profile tab, CLI options (`profiles.py`, `model.SquareWave`, `gui/profile_page.py`; `test_profiles.py`, `test_gui_profile.py`).
* Computed convection and radiation per face from the board temperature (`convection.py`, `api._solve_computed_h`; `test_convection.py`).
* Descriptive model names in the interface; temperature differences in degC.

## 2.0.0 - 2026-10-16: the rebuilt program

* Physics package `pcbthermal` with the `Problem` builder, `SolverOptions`, `simulate` and `.pcbt.json` projects (`model.py`, `api.py`, `project.py`; documentation gate `test_docs.py`).
* FVM reference with direct, CG and SOR solvers (`fvm.py`; energy balance, SOR equals direct to 1e-8 K); Lumped ring network (`lumped.py`); Analytic multilayer series (`analytic.py`).
* Input checks and Auto cell size (`checks.py`); transient and GIF animation (`fvm.solve_transient`, `gui/animation.py`); PySide 6 application (`gui/`; `test_gui.py`); command line (`cli.py`); the version defined in `pcbthermal/__init__.py` (`test_version.py`).

## 1.0.0 - 2025 (tag `legacy-wxpython-1.0.0`)

The original wxPython program, "PCB Thermal Simulator Tool": editor and three solvers with modelling errors (false SOR convergence, heater power depending on the grid, no lateral conduction in FR-4, solid vias, an invalid lumped network; `validation.md` section 6). Removed in 2.0.0.

---

## Planned

What we want to **implement** in the program, each item once, with the evidence and the branch. What we want to investigate is in `research/ROADMAP.md`. When an item is implemented it leaves this chapter in the same commit and is recorded above. A **fix** goes on `fix/<topic>` off `develop` (executor, reviewer, maintainer); a **feature** on `feature/<topic>`, with documents, user guide, tooltips and the whole battery; **after the investigation X** waits for the study in `research/ROADMAP.md`. One `pytest` at a time (16 GB machine).

### Next, in order (maintainer)

1. **Zone union** (`fix/zone-union`). Zones of a layer are combined by the maximum per sample point (`geometry.zone_fill`), losing the copper of two zones that abut in a cell (5 to 15 % cool on real copper). Test: the strips case. Evidence: `research/gerber-models/README.md` 4.39.
2. **Memory limit and guard** (`pcbthermal/memory.py`; fix or feature to decide: a wrong unknown count in the panel is a fix, a new Preferences setting with a guard is a feature and makes the version 2.5.0, fixes only 2.4.2). Physical RAM, the memory of each model from its unknowns (coefficient per slab class, growth about N^(4/3)), a verdict ok / refuse in `api.simulate`, the jobs, the interface and the CLI. **Default limit 70 % of the physical memory, editable in Preferences** (`solver` section of `defaults.json`); a "slow" warning below it; the fixed 3D limit of 250 000 becomes RAM-based with an absolute ceiling; the unknown count shown for the layered models (it ignores the laminate nodes and the block layers: 2 400 shown, 9 600 real) is corrected in the same item. Test: simulated RAMs of 8, 16 and 64 GB; the 502 mm board refused in under 60 s; a failed RAM read falls back to the fixed ceiling. Evidence: `research/solid3d-verification/docs/for-the-project-documents.md`, its fig_09. Related: reuse the factorisation in the computed-h loop of the 3D solid.
3. **Wait for the investigation**: the point via (below), the fin warning and the items after the investigations. The faster split stays as it is.

### Fixes waiting for a study

* **Point via** (`fix/point-via`, after investigation A5). In the FVM and FDM a via in one cell acts like a hole of radius 0.198 dx (Peaceman), so on cells finer than about 0.5 mm the copper-fill gain drifts (-4.78 to -3.34 K from 1 to 0.0625 mm against -4.45 K resolved); plan: a Peaceman well index while the equivalent radius exceeds the via radius, otherwise spread over the cells of the disc. The 3D solid clips a via larger than its cell (`via_frac = min(..., 1)`; a 0.5 mm fill keeps 32 % at 0.25 mm cells): spread before clipping and warn. Needed for Gerber boards. Test: gain within 0.3 K of the reference from 1 to 0.125 mm. Evidence: `research/via-fill/README.md`.
* **Fin warning** (`fix/fin-warning`, after investigation C3). The 4 mm threshold in still air against a channel correlation (Elenbaas; Bar-Cohen and Rohsenow, to be read first). Test: the 6.5 mm gap example. Evidence: `research/block-and-fins`.
* **Faster top-path split** (`feature/faster-top-path-split`, not wanted now). Start each power-coefficient pass from the previous split; semi-smooth Newton. Cost today: a median of 7 board solves per part, up to 57 with several parts, error at most 0.004 K. Evidence: `research/component-heatsink/README.md` 4.2 and 4.9.
* **Inner copper 30 um** (`feature/inner-copper-30um`, only if wanted): the JLCPCB 1 oz product. Evidence: `research/stackup` 4.6.
* **After the investigations A1, A2, A3, A6, A7** (`research/ROADMAP.md`): subdividing the gap of multilayer boards (-2 to -8 % in the FVM on 2-layer boards; moves every 2 and 3-layer result); the Analytic on one-layer boards with partial copper and Lumped and Analytic on a bare pad (-11 to -36 %; `validation.md` 21); the 3D solid with a rotated square; the Lumped and Analytic overstating the via copper-fill gain by 35 to 52 %; laminate nodes for patterned copper.

### Features

* **Size of the models**: multigrid (`pyamg`, only above about 500 000 unknowns; optional); a hard limit for FVM and FDM if the guard does not cover them.
* **Metal block**: the capacity of the fins (a time simulation of a finned block responds too fast), fin end faces (0.7 to 0.9 % of the rise), adjacent blocks, a cell shared by two blocks, time simulation with a block in Lumped and Analytic. Evidence: `research/block-and-fins/INTEGRATION.md`.
* **Time and pulses**: the top path in the time simulation, a Foster chain / heat capacity of the junction and the heatsink with `dTj = Zth(tp, D) P` as a check; the pad-size effect of Lumped and Analytic near the edge of a cut board (`research/outline/README.md` 4.2). Evidence: `research.md` E3 to E5, R2.
* **Heatsinks and the part**: other air speed as an estimated factor of the natural value, flow linked to the board air speed, heatsinks with a fan, scenarios (`theta_sa` scaling with the rise, orientation, geometry with the channel effect), the junction node in the FDM, Lumped and Analytic, the heatsink as a plate layer with an interface of its own area, clearer names and live Tj for the source/component heater, passive areas and a component library (LEDs, processors with lid and paste). Evidence: `research.md` E3 to E8, R2 to R9.
* **Calculator**: a virtual JEDEC test to predict θJA, ΨJT, ΨJB and recover a missing package resistance (and fix the bottom layer of the JEDEC 2s2p board); the known-power reference (+-5 % with +-1 K reading error against -19 to -27 % without). Evidence: `docs/calculators.md` 2.1 and 2.4.
* **Import**: Gerber and Excellon copper per layer (rasterised fill fraction; needs the point-via fix for fine cells), the `copper_mapping` option (`research/gerber-models/INTEGRATION.md`), KiCad `.kicad_pcb`, a power list from a CSV or BOM by designator, orthotropic copper from the raster. Evidence: `research/gerber-import`, `gerber-models`, `gerber-nets`. **When the Gerber import is implemented** (maintainer's wish): also read the other layers, such as the solder paste, so that a part can be drawn by clicking the paste polygon of its pads and giving it a power (the heater footprint comes from the file); the missing piece is which part is which, that is its reference designator, to be read from a pick-and-place (centroid) file or from ODB++ or IPC-2581 when the project has one, and typed by hand otherwise; first find a real project that holds this data to try the import on, and run the studies of `research/gerber-import` and `research/gerber-nets` again in the research environment before and after (item E11 of `research/ROADMAP.md`).
* **Board, stack-up and outline**: solder mask above and below the copper, a material per copper layer, a library of fabricator stack-ups; arc and spline outlines, holes and cut-outs, a warning for a neck narrower than three cells, the Lumped network on any outline; the disclaimer (a design aid, to be validated by measurement) also in every report. A heatsink on the laminate side of a one-layer board stays unsupported.
* **Interface checks** (not urgent): confirm the layout in a real macOS window; left over: the Simulation footer eats a low window, a half-cut "32000 unknowns", narrow pages scroll sideways with a cut inner tab bar, the Defaults page of Preferences at 760 px, log axes below 0.01 crowd their labels, the model plot shows the keys, the "mm" of the ruler overlaps a label, a decimal comma pasted from the context menu is not converted, a click on a warning between an edit and the check may pick the wrong element, thousands separator in large counts.

### Ideas taken from similar projects (all features, in the order of value for the effort)

Read as web summaries (KiCad plug-ins such as KiCad_Thermal_Sim, pcb-sim-toolkit, kicad-electrothermal-sim, KiPIDA; commercial tools; FYPA, padne and altium_monkey, which are AGPL-3.0: ideas and public formats only, no code copied).

1. Electro-thermal coupling: Joule heating of the copper (`Problem.electrical`), IPC-2152 trace-rise check, copper resistivity with temperature, by the existing fixed-point loop.
2. Thermal via tools: an array generator, the resistance of an array against the 4 / 16 via figures of the fabricator guides, a via-count sweep.
3. Parameter sweeps and comparison of two designs with plots and an A/B table.
4. Pass/fail checks with an exit code (`--fail-on fail`), an HTML or PDF report, a result cache.
5. Regulator and converter losses from efficiency in the Power Calculator.
6. Parameters read from the CAD symbol fields, our settings in a sidecar file.
7. Probes and pin tables, export for ParaView and for an external 3D check (STEP/XAO or a mesh).
8. Cooling presets and a closed box with an internal air rise (no CFD).
9. Local mesh refinement or a triangular mesh; release automation (CI, standalone program on a tag).

### Deferred

Neural-network surrogates; reduced-order models (only if transients become too slow); a per-cell or enclosure-aware radiation model; editing power tables inside the application (the CSV round trip is the workflow).

### Sources of this chapter

gerbonara (https://pypi.org/project/gerbonara/, Apache-2.0, checked; its companion shapely is BSD-3-Clause); Nexperia AN11261 and TI SLUAAT8 on RC thermal models and repetitive pulses; the datasheets, JEDEC standards and notes behind the Component element are listed at the end of `research.md`; the fabricator stack-up tables in the Literature section of `validation.md` section 14.
