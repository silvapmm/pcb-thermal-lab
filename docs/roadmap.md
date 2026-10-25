# Roadmap

What we want to investigate is in `research/ROADMAP.md` (kept on the branch `research/gerbers` until the investigations are merged).

This document is only the list of what we want to **implement in the program**: new functionality, defects to fix, improvements of the models, the interface and the tools. Each item is stated once, with a pointer to the evidence. What already exists is described in [`versions.md`](versions.md) (where it is in the code and how it is tested), [`models.md`](models.md), [`theory.md`](theory.md) and [`validation.md`](validation.md); the notes of the Component element that are still open are in [`research.md`](research.md).
Rule: when something is implemented it leaves this list in the same commit (it is recorded in `versions.md` and `CHANGELOG.md`), and any source read is added to the bibliography of the document that uses it.

Each item says what kind of work it is: **fix** (a `fix/<topic>` branch off `develop`: executor, reviewer, maintainer), **feature** (a `feature/<topic>` branch, same flow plus documents, user guide, tooltips and the whole battery) or **after the investigation X** (the feature is decided by a study listed in `research/ROADMAP.md`).

## 1. Defects of the program to correct

* **Metal block beyond the board outline** (fix). The FVM (`fvm.py`, `g_pin[:, ~active]`) and the 3D solid (`pin[:, ~active]`) pin every layer, the block layer included, to the ambient outside the outline: a 40 × 30 × 3 mm block on a cut 60 × 40 mm board reads 40.7 K (FVM) and 41.1 K (3D solid) against 90.0 K (FDM), 55 % cold, and the warning of `checks.py` ("only the part inside is modelled") is false for these two models. Plan: let the block keep its own cells off the board (or clip it) and correct the warning; regression test with those numbers. Evidence: `research/block-and-fins/README.md` section 7 (branch `research/gerbers`).
* **Point via of the FVM and FDM does not converge with the cell** (fix). A via in one cell of a five-point stencil acts like a hole of radius `0.198 Δx` (Peaceman), so on cells finer than about 0.5 mm the copper-fill gain of a via array drifts (−4.78 to −3.34 K from 1 to 0.0625 mm against −4.45 K with resolved barrels). Plan: connect the via through a Peaceman well index while the equivalent radius exceeds the via radius, otherwise spread it over the cells of its disc; test against `tests/helpers/layered3d.py` with resolved barrels. Matters for Gerber boards, which need fine cells. Evidence: `research/via-fill/INTEGRATION.md` 1.
* **3D solid clips a via larger than its cell** (fix). `via_frac = min(Σ A_via / A_cell, 1)` loses the excess (a 0.5 mm copper fill keeps 32 % at 0.25 mm cells). Plan: spread the via area over the cells of its disc before clipping and warn if a cell is still over 1. Evidence: `research/via-fill/INTEGRATION.md` 2.
* **Zones of a layer combined by the maximum per sample point** (fix). Today the maximum per cell loses the copper of two zones that abut inside a cell (5 to 15 % cool on real copper). The second correction of the same study, the laminate slab under a single copper layer in the 3D solid, is already in the program. Needs the whole battery. Evidence: `research/gerber-models/README.md` 4.39.
* **`Heater.top_resistance()` and `analysis.part_split` disagree** (fix, small). The first uses `theta`, the second `junction_theta()`: with `role="source"`, an old `theta=5` and `theta_sa=10` the report shows `r_top=15` while no heat goes through the top. Reachable only through the API or a JSON file (the GUI zeroes both when the role changes). Make both use `junction_theta()`. Evidence: `research/theory/docs/for-the-project-documents.md`.
* **Via diameter label** (fix; decision of the maintainer pending). The tooltip (`gui/tips.py`, key `diameter`) and the docstring of `Via.diameter` say "finished hole diameter" but the model uses the drill diameter (plating inside it). Either change the label to "drill diameter" (no number changes; the Gerber reader gives drills) or read the finished hole and add the plating outside (changes every result with vias by up to 15 % of the via resistance). Evidence: `research/via-fill/INTEGRATION.md` 3.
* **Fins**: the channel effect between close fins is not in the model and the warning leaves a gap (feature or fix, with the maintainer's choice). The warning is below 4 mm of air gap in still air; a 6.5 mm gap, near the optimum spacing of a short array, has a channel coefficient that a remembered correlation puts 10 to 30 % below the typed one. Options: a channel correlation (Elenbaas; Bar-Cohen and Rohsenow) for still air, or a higher warning threshold. The correlation has to be read from the sources first (`research/ROADMAP.md`). Evidence: `research/block-and-fins/INTEGRATION.md`, `validation.md` section 15.

## 2. Memory and size of the models

* **Memory guard** (feature, branch `feature/memory-guard`). New `pcbthermal/memory.py` reads the physical RAM and estimates the memory of each model from the unknowns (FVM and FDM direct about 4.4 KB per unknown, 3D solid about 15 KB, CG about 10 % of the direct; measured, editable in Preferences); verdicts ok / slow (above 50 % of the RAM) / refuse (above 90 %) used by `api.simulate`, the jobs, the interface (memory next to the unknown count, with the cell and the CG solver suggested) and the CLI. The fixed 3D limit (250 000 unknowns) becomes RAM based with an absolute ceiling for the time; a Preferences box with the fractions, the KB per unknown and a forced RAM value. Tests with simulated RAMs of 8, 16 and 64 GB, the 502 mm board that hung, a failed RAM read, and an estimate never below the measured memory on a small case. The small alternative (a fixed ceiling of about 4 million unknowns for FVM and FDM) was offered and not chosen. After the clean-machine timing of the direct solves (`research/ROADMAP.md`) the times in `CHANGELOG.md`, `docs/versions.md`, `docs/models.md` and the reasoning of the 250 000 limit are corrected. Evidence: `research/REVIEW.md`, "Agreed for after the review".
* **Large 3D and layered models** (feature). Reuse the factorisation across the computed-h loop of the 3D solid (the coefficients change only the diagonal of the faces, so the previous LU is a near-exact preconditioner for CG), a nested-dissection ordering, and a hard limit for the FVM and FDM if the guard does not cover them (measured: 1 million unknowns 97 s and 4.4 GB, 2 million 273 s and 8.4 GB).
* **Faster top-path split** (feature). `api._top_path_split` costs a median of 7 board solves per part and up to 57 with several coupled parts, the error at most 0.004 K (accepted as is on 2026-10-25): start each pass of the power-coefficient loop from the previous split instead of from `[0, P]`, and a semi-smooth Newton method whose Jacobian comes from differences of the maximum temperature under each part.
* **Multigrid** (feature, optional, low priority). Algebraic multigrid (`pyamg`) pays only above about 500 000 unknowns (987 000 unknowns: 8.0 s against 12.8 s for CG; the direct solver does not fit in memory); an optional dependency chosen above a threshold.

## 3. Model improvements

* **Metal block**: thermal capacity of the fins (only the base plate `ρc t` is in `C`, so a time simulation of a finned block responds too fast; the fins' capacity with a lag along the fin); fin end faces (about 0.7 to 0.9 % of the rise on the block of `validation.md` 12 D); adjacent blocks (two blocks that touch count their common wall as exposed to the air); a cell shared by two blocks (the layer keeps the last one drawn, overlapping blocks are not combined); a time simulation with a block in the Lumped and Analytic models. Evidence: `research/block-and-fins/INTEGRATION.md`, `theory.md` section 7.
* **Top path in the time simulation** (steady state only today) and a **Foster chain / heat capacity** of the junction and the heatsink for pulsed operation, with `ΔTj = Zth(tp, D)·P` as a check of the time simulation; the Foster chain of the package from the manufacturer's `Zth(t)` curves. Evidence: `research.md` E3 to E5 and R2.
* **Pad-size effect in the Lumped and Analytic models** for a part near the edge of a cut board (10 to 18 % cool today, `validation.md` section 13).
* **Subdivide the gap of every multilayer board** (after the investigation "gap of a multilayer board"). Two nodes through the gap of a 2-layer board give −2 to −8 % in the FVM against the independent solver (−3.9 % with the same pad on both faces); the change moves every 2 and 3-layer result and needs the reviewer. Evidence: `validation.md` 21.1.
* **Analytic model on one-layer boards with partial copper, and Lumped and Analytic on a bare pad** (after the investigation of why they are hot or cool there): −11 to −17 % (Lumped) and −11 to −36 % (Analytic) on a bare pad against the 3D solid today; the input checks warn and the FVM is the model for such boards. Evidence: `validation.md` section 21.
* **3D solid with a rotated square at a high side coefficient** (after the investigation: +1.15 K above the aligned square).
* **Lumped and Analytic vias** (after the investigation of why): they overstate the copper-fill gain by 35 to 52 % on a via array under a part (−6.0 to −6.8 K against −4.45 K). Evidence: `research/via-fill/README.md` 7.3.

## 4. Heatsink air flow and the Component element

Evidence for all of this is in `research.md` (E3 to E8 and R2 to R9).

* **Other speed (estimated)** in the heatsink flow list: `θSA(v) = θSA(natural) × f(v)` with f from the volumetric guide (1, 0.31, 0.18, 0.10 at 0, 1, 2.5, 5 m/s), always marked as an estimate (about 15 % for a large heatsink, up to 50 % for a small one).
* **Flow linked to the board air speed** by default, with an override for a heatsink that has its own fan or air channel.
* **Heatsinks with a fan** (catalogue assemblies, for example 40 mm sets of about 1.1 K/W) as entries of the library.
* **Heatsink scenarios**: natural convection scaling `θsa ∝ ΔT^-0.25` from a reference rise, orientation, and a **heatsink from its geometry** (fin height, thickness, pitch, metal; pin fins) with the channel effect, compared with the catalogue θSA of extrusions.
* **Junction node** (JESD15-3 two-resistor model, block-and-plate attachment to the footprint) in the FVM first (top path only), then FDM, Lumped and Analytic (scalar Woodbury update). Worth it only with a heatsink on top: a bare mould changes the junction by 0.4 to 3 K, a clip-on heatsink by a factor of two.
* **Heatsink on a component as a plate layer** with spreading (5 to 14 % of the top chain for a thin steel base, 1 to 4 % for aluminium and copper), **interface with its own area** (contact patch) and the **air gap** outside it, and a side view with the vertical information (stack-up, component height, gap).
* **Virtual JEDEC test**: the datasheet's own board built in the program, to predict `θJA`, `ΨJT`, `ΨJB` and compare with the datasheet, and to recover a missing package resistance from a `θJA` on a stated board. For the power calculator: fix the reading of the bottom layer of the JEDEC 2s2p board (ROHM reads a 70 µm plane, the study draws traces) and move the datasheet rows to a finer cell. Evidence: `docs/calculators.md` 2.1.
* **Power calculator, known-power reference**: the same reading at a known power scales the model (±5 % with ±1 K of reading error against −19 to −27 % without); applies only to parts with a controllable dissipation. Evidence: `docs/calculators.md` 2.4.
* **Heater as a pure source or a component**: clearer names for the datasheet lines, the boxes in the order of the heat flow with the live Tj and heat share, and the datasheet table mapped in the help (`research.md`, "the heater as a pure source or as a component").
* **Passive areas** as component types (cooled area, contact to a fixed temperature, material patch) and a **component library** (typical `θJC`, `θJB`, `ψJB`, size and mass by family or part number; presets for processors with lid and paste); LEDs (the fraction of the electrical power that becomes heat) and temperature-dependent power beyond the linear coefficient.

## 5. Import of copper and parts

* **Gerber and Excellon import** of the copper per layer (candidate library `gerbonara` [1]): rasterise on a fine grid and store the copper fill fraction per cell, which is what the FVM already uses; drills with plating become vias. Needs a layer-assignment step in the GUI and a validation against a board also drawn by hand. The fill fraction hides trace connectivity (half-filled may be one long trace or two disconnected pieces); solder-mask openings matter for emissivity, not conduction. Evidence: `research/gerber-import`, `research/gerber-models`, `research/gerber-nets` (branch `research/gerbers`). Fine cells depend on the point-via correction of section 1.
* **Copper mapping as an option** (`SolverOptions.copper_mapping`: `fill` by default, `lambda`, `cell_problem`, `flow`), designed in `research/gerber-models/INTEGRATION.md`. A diagonal-face (nine-point link) variant did not pass its held-out test and is not proposed.
* **Board import from KiCad** (`.kicad_pcb` is text): outline, copper zones and tracks per layer, vias with drills, the stack-up table, footprints with reference, position and size (parts to be given a power). Pure-Python S-expression parser.
* **Power list from a CSV/BOM** (`reference, power_w, theta, tj_max`) applied to footprints by designator; **orthotropic copper** from the raster (conductivity along x and along y of a cell with traces).

## 6. Board, stack-up and interface

* Stack-up: a third inner copper option of 30 µm (what JLCPCB's own 1 oz builds use) if a fabricator table confirms it; the 0.5 oz and 1 oz (35 µm) options cover the published tables.
* Stack-up: an outer dielectric (solder mask) above the top copper and below the bottom copper, a material per copper layer (alloys, plated copper), a library of fabricator stack-ups (Eurocircuits and Sierra Circuits publish no table that could be read).
* Outline: arc and spline outlines, refinement near curves, holes and cut-outs inside the board (list of polygons with even-odd fill), a warning for a neck narrower than three cells, the Lumped network on any outline with geodesic rings.
* The disclaimer that the results are a design aid, to be validated by measurement, in the About box, the user guide and every report.
* **A heatsink on the laminate side of a one-layer board is not supported** (a limit, not a wish; the program says so).

## 7. Ideas from similar projects and tools (research of 2026-10-21 and 22)

Sources were read as web summaries (the repositories were not cloned or run): none of the projects has the models, the profiles, the junction, the computed convection or the 3D check of this one; they are mostly KiCad plug-ins with one 2D model.

| Project / tool | What it does | Idea for us |
| :-- | :-- | :-- |
| [Dietschi10/KiCad_Thermal_Sim](https://github.com/Dietschi10/KiCad_Thermal_Sim) | KiCad plug-in: 2D in-plane conduction on every copper layer, coupling through FR-4 and vias, manual heat sources, optional DC current (I²R) heating and a Joule-loss map | KiCad import, Joule heating of the copper |
| [mgburr/pcb-sim-toolkit](https://github.com/mgburr/pcb-sim-toolkit) | Imports KiCad boards: 2D finite-difference steady state, junction temperature per component | components with positions and powers read from the board file |
| [krosa-laboratory/kicad-electrothermal-sim](https://github.com/krosa-laboratory/kicad-electrothermal-sim) | 2.5D/3D DC IR-drop and electro-thermal co-simulation on KiCad 6 to 9 files | electro-thermal coupling: current density → I²R heat → temperature → resistivity |
| [kbralten/KiPIDA](https://github.com/kbralten/KiPIDA) | KiCad 9 plug-in: DC power integrity, current density and thermal rise, 2.5D resistive mesh | the same coupling, a current-density map |
| [SPIKE](https://github.com/krishna-swaroop/SPIKE) | Desktop workbench (power and signal integrity, thermal, extensions) | cooling presets; an extension mechanism |
| [SchrodingersGat/KITS](https://github.com/SchrodingersGat/KITS) | KiCad thermal simulation tool (MIT) | listed only |
| Ansys Icepak, Flotherm, Cadence Celsius, Simcenter | ODB++/Gerber/IPC-2581 import, orthotropic conductivity per layer, conjugate heat transfer, component libraries (2R/DELPHI) | ECAD import; copper as polygons, not as a percentage; a component library |
| Elmer FEM / OpenFOAM routes ([jrainimo write-up](https://jrainimo.com/build/2024/11/oss-thermal-simulation-of-pcbs/)) | Export the copper geometry (STEP/XAO) to a free 3D solver | export of the model for an external 3D check |
| [Tomachie/FYPA](https://github.com/Tomachie/FYPA) (AGPL-3.0) and [atx/padne](https://github.com/atx/padne) (the FEM solver FYPA vendors) | DC voltage-drop analysis of Altium, Gerber and KiCad boards: 2D FEM per copper layer, viewer with probes, sidecar file, result cache, PASS/FAIL checks with a CI exit code, regulator model, ParaView export, text directives in the schematic | pass/fail checks, cache, sidecar edits, regulator losses from efficiency, probes, ParaView export, parameters read from schematic fields, the current solution as the heat source |
| [wavenumber-eng/altium_monkey](https://github.com/wavenumber-eng/altium_monkey) (AGPL-3.0) | Python reading/writing of Altium PcbDoc, SchDoc, PrjPcb | an import path for Altium boards; design-review checks in CI |
| JLCPCB / RayPCB guides | Thermal vias: 4 vias about 40 K/W, 16 about 10 K/W; power from the datasheet maximum, V × I, or a circuit simulation | a thermal-via array generator and a check against those numbers |

The ideas, in the order of value for the effort (all features):

1. **Electro-thermal coupling**: Joule heating of the copper (current in, current out → I²R in planes and traces, `IPC-2152` trace-rise check), copper resistivity rising 0.39 %/K, solved by the fixed-point loop that already exists for the power coefficient; a DC solve per copper layer gives the heat source and the voltage drop.
2. **Thermal via tools**: an array generator (pitch, diameter, area), the resistance of an array next to the 4/16-via figures of the guides, a via-count sweep.
3. **Parameter sweeps and comparison of two designs** (copper area, number of vias, power, ambient, air speed) with plots of Tj against the parameter and an A/B table; a short optimisation reusing the power-limit logic.
4. **Design checks with PASS/FAIL and an exit code** (`--fail-on fail` in `run`), a **report** (one HTML or PDF page with the settings, maps, table of parts with margins and warnings), and a **result cache** keyed by the problem, options and code version.
5. **Regulator and converter losses from efficiency**: `P_out (1/η − 1)` for a switching converter and `(V_in − V_out) I_out` for an LDO, in the power calculator.
6. **Parameters in the design files**: read power, θ and Tj max from fields of the KiCad symbol, with our own settings in a sidecar file so the CAD files are never modified.
7. **Probes and pin tables** (temperature of every layer at a clicked point; sortable tables of parts and vias), **export for ParaView** and for an external 3D check (STEP/XAO or a mesh).
8. **Cooling presets and enclosure**: an air-speed preset by fan, a closed box with an internal air temperature rise (a first step towards conjugate heat transfer, no CFD).
9. **Local mesh refinement or a triangular mesh** near parts and along curved outlines (large work, only if the boards that matter are large), and **release automation** (CI with lint, documentation gate and tests; a standalone program on a version tag).

**Licences**: FYPA, padne and altium_monkey are AGPL-3.0; this project is MIT (see the `LICENSE` file; the licences of the libraries it uses are in the README). Their code must not be copied here; their ideas and file formats can be used (Gerber, Excellon, KiCad and Altium formats are public or reverse-documented) and any import has to be written independently.

## 8. Housekeeping

* Merge the research branches into `develop` as their reviews finish (the order and the open reviews are in `research/ROADMAP.md`), and fold each folder's `docs/for-the-project-documents.md` into the project documents.

## 9. Deferred

Neural-network surrogates; reduced-order models (only if transients become too slow); a per-cell or enclosure-aware radiation model; editing power tables inside the application (the CSV round trip is the workflow).

## References

1. gerbonara, https://pypi.org/project/gerbonara/ (documentation https://gerbolyze.gitlab.io/gerbonara); licence checked on 2026-10-23: Apache-2.0 (PyPI, version 1.6.3), compatible with an MIT project that only imports it. Its companion shapely is BSD-3-Clause.
2. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf; Texas Instruments SLUAAT8, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, `D + (1 − D) z(t)`).
3. The datasheets, JEDEC standards and application notes behind the Component element (JESD15-3, JESD51 family, TI SPRA953B and AN-2020, Renesas, Richtek, Infineon, Vishay and others) are listed at the end of `research.md`.
4. Fabricator stack-up tables used in `docs/validation.md` section 14 are listed in its Literature section (JLCPCB, PCBWay, Eurocircuits, Sierra Circuits).
