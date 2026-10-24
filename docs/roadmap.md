# Roadmap

Two lists: **what has already been implemented** and **what we want to implement**. Details of what exists are in [`models.md`](models.md) (models and features), [`theory.md`](theory.md) (equations), [`validation.md`](validation.md) (numbers) and [`versions.md`](versions.md) (where it is in the code and how it is tested); investigations that are still open, with the evidence read so far, are in [`research.md`](research.md).
Rule: when something is implemented it moves from the second list to the first in the same commit, and any source read is added to the bibliography of the document that uses it.

## What has been implemented

* **Models**: finite volumes (FVM, the reference), thermal network by rings (Lumped), Fourier series (Analytic), node-centred finite differences (FDM) and the 3D solid; steady state in all, time simulation in FVM, FDM, Lumped and Analytic; five direct/iterative linear solvers checked against each other (`models.md`, `theory.md`).
* **Heat transfer**: computed convection and radiation per face (natural and forced, emissivity, horizontal or vertical mounting, calibration multiplier), typed coefficients, edge loss.
* **Power profiles**: square waves and CSV tables, the average-or-resolve decision per heater, animation of a power step.
* **Parts (heaters)**: junction-to-pad `θ` in the worst case, junction limit with margin and power limit, `ψJB` ring estimate, power temperature coefficient with runaway detection, typical `θ` by package family, the top path (`θJC(top)`, body helper, contact area, interface sheet, `θSA`), power from a measured temperature or a datasheet parameter (Power calculator).
* **Typical heatsinks on a package**: a library of catalogue θSA (heatsink and air flow, with source and test conditions) in Preferences and two lists in the heater panel; the top-path boxes appear with θSA.
* **Heatsinks**: extra coefficient typed as `h` or as `θSA`; metal block (all five models in steady state, FVM, FDM and 3D solid in time too) with thickness, metal presets, interface sheet (paste, gap pad, direct contact), plate fins with efficiency, exposed-surface coefficient; validated against the 3D solid within 1.8 %.
* **Board**: variable stack-up (copper per layer, material and thickness per gap, simple and advanced modes, typical stack-ups for 1 to 12 layers checked against JLCPCB and PCBWay tables), outline polygon of any shape (FVM, FDM, 3D solid on the real shape; Lumped and Analytic on the rectangle of the same area), advanced stack-up in all five models.
* **Vias and power calculator**: the via fill (open, epoxy resin, conductive paste, copper) and the power of a part from a board temperature, the junction or the top of the package (θ and ψJT), with the sensitivity to the copper measured (`validation.md` sections 18 and 19).
* **Power calculator** documented in `docs/calculators.md` with its validation against two datasheet boards (CSD17308Q3, JEDEC 2s2p with an exposed-pad QFN).
* **Power calculator band**: best case / nominal / worst case from the uncertainty of the copper, heat transfer, θ, ψJT and the reading, combined as the root of the sum of squares; the case chosen is the power written in the part.
* **Preferences**: material libraries and defaults of a new board, new elements, materials and solver in a JSON file with a user override (`Preferences`).
* **Application**: PySide 6 editor with undo, polygon drawing and vertex handles, right-click menu (add or delete a vertex, add elements), rulers, properties in titled boxes, Stack-up tab with the cross-section and the simple stack-up fields, results views with animation, calculations in a cancellable separate process, HTML user guide, tooltips on every control.
* **One-layer boards and the Lumped rings** (`validation.md` section 21): laminate nodes under the copper of a one-layer board (FVM, FDM, Lumped; series film in the Analytic), rings narrower than a cell merged; nine boards compared before and after against the 3D solid.
* **Model corrections after a review** (`validation.md` section 20): the time constant and the step responses of a board with an outline leave out the cells off the board, the 3D solid keeps the laminate of a one-layer board, the transient mean counts only the board, and a power loop that does not settle is reported.
* **Quality**: documentation gate on every function, stress tests of the application, the 3D check of the layered models, studies in `examples/` that reproduce every table of `validation.md`.

## What we want to implement

In the order of value for the effort.

### Heatsink air flow (follows from `docs/research.md` R3)

- **Other speed (estimated)** in the heatsink flow list: `θSA(v) = θSA(natural) × f(v)` with f from the volumetric guide (1, 0.31, 0.18, 0.10 at 0, 1, 2.5, 5 m/s), always marked as an estimate (about 15 % for a large heatsink, up to 50 % for a small one).
- **Flow linked to the board air speed** by default, with an override for a heatsink that has its own fan or air channel.
- **Heatsinks with a fan** (catalogue assemblies, for example 40 mm sets of about 1.1 K/W) as entries of the library.
- **Heatsink from its geometry** (fin height, thickness, pitch, metal) with the channel effect between fins (Elenbaas, Bar-Cohen and Rohsenow) and the temperature-rise dependence of natural convection, compared with the catalogue θSA.
- **Junction node (JESD15-3 two-resistor)**: only worth it with a heatsink on top (a bare mould changes the result by about 3 K, a heatsink by a factor of two); first in the FVM, top path only.

### Component element (the part of the plan not done)

Evidence for all of this is in `research.md` (sections E3 to E8 and R2 to R8).

* **Junction node** (JESD15-3 two-resistor model, block-and-plate attachment to the footprint) in the FVM and FDM first, then Lumped and Analytic (scalar Woodbury update). Worth it only with a heatsink on the top: with a bare package it changes the junction by 3 K (3 % of the rise), with a clip-on heatsink by a factor of two.
* **Heatsink on the package with its own capacity** `C_hs` (J/K) and the Foster chain of the package from the manufacturer's `Zth(t)` curves, for pulsed operation; `ΔTj = Zth(tp, D)·P` as a check of the time simulation.
* **Heatsink scenarios**: natural convection scaling `θsa ∝ ΔT^-0.25` from a reference rise, forced-convection factors tied to the air speed (0.31, 0.18, 0.10 at 1, 2.5, 5 m/s), orientation; fin spacing effect on the convection (Elenbaas / Bar-Cohen and Rohsenow channel correlation: the fins are validated only for a uniform coefficient, `validation.md` section 15), a comparison with the θSA of catalogue extrusions, pin fins.
* **Heatsink on a component as a plate layer** with spreading (only worth it for a thin base of a poor conductor such as steel: 5 to 13 % of the top chain against 1 to 4 % for aluminium and copper).
* **Interface with its own area** (contact patch) and the **air gap** outside it, and a side view with the vertical information (stack-up, component height, gap).
* **Virtual JEDEC test**: the datasheet's own board built in the program, to predict `θJA`, `ΨJT`, `ΨJB` and compare with the datasheet (TPS7A47, CSD17308Q3), and to recover a missing package resistance from a `θJA` on a stated board.
* **Passive areas** as component types (cooled area, contact to a fixed temperature, material patch) and a **component library** (typical `θJC`, `θJB`, `ψJB`, size and mass by family or part number; presets for processors with lid and paste).
* **Power calculator, less error from the board** (`docs/calculators.md` section 2.4): the **uncertainty band** with a best / nominal / worst selector is implemented; an optional **known-power reference** (the same reading at a known power scales the model: ±5 % with ±1 K of reading error against −19 to −27 % without) is kept for later (it matters less once the copper comes from Gerber or KiCad files); the two-point fit of power and copper is a study only. The **virtual JEDEC test** of the datasheet's own board is done for two cases (`docs/calculators.md` section 2.1); more datasheet cases would need their boards described.
* **Heater as a pure source or a component**: the Type selector (heat source with an interface under it / component) and the package library that fills several typical values at once are done in the GUI; still to tune with the maintainer: clearer names for the datasheet lines, the boxes in the order of the heat flow with the live Tj and heat share, and the datasheet table mapped in the help (`docs/research.md`).
* LEDs: the fraction of the electrical power that becomes heat; temperature-dependent power beyond the linear coefficient.

### Import of copper and parts

* **Board import from KiCad** (`.kicad_pcb` is text): outline, copper zones and tracks per layer, vias with drills, the stack-up table, footprints with reference, position and size (parts to be given a power). Pure-Python S-expression parser, no KiCad needed.
* **Gerber and Excellon import** of the copper per layer (candidate library `gerbonara` [1]): rasterise on a fine grid and store the copper fill fraction per cell, which is what the FVM already uses; drills with plating become vias. Limits to state: the fill fraction hides trace connectivity (half-filled may be one long trace or two disconnected pieces); the Analytic model keeps the layer average plus local corrections; solder-mask openings matter for emissivity, not conduction. Needs a layer-assignment step in the GUI and a validation against a board also drawn by hand.
* **Power list from a CSV/BOM** (`reference, power_w, theta, tj_max`) applied to footprints by designator; power from a circuit simulation.
* **Orthotropic copper** from the raster (conductivity along x and along y of a cell with traces).

### Board and stack-up

* Stack-up: an outer dielectric (solder mask) above the top copper and below the bottom copper, a material per copper layer (alloys, plated copper), a library of fabricator stack-ups (Eurocircuits and Sierra Circuits publish no table that could be read).
* Outline: arc and spline outlines, refinement near curves, holes and cut-outs inside the board (list of polygons with even-odd fill), a warning for a neck narrower than three cells, the Lumped network on any outline with geodesic rings (the Analytic series on an outline is probably not worth it).
* Pad-size effect on Lumped and Analytic for a part near the edge of a cut board (10 to 18 % cool today, `validation.md` section 13).

### Solvers and validation

* **Multigrid** (optional, low priority): measured on the example board, algebraic multigrid (`pyamg`) pays only above about 500 000 unknowns (987 000 unknowns: 8.0 s against 12.8 s for CG; the direct solver does not fit in memory); it would stay an optional dependency chosen above a threshold. All solvers agree to 1e-8 K.
* **A measurement of a physical board** (absolute accuracy; also calibrates the convection multiplier, `pcbthermal calibrate`): none of the models has been compared with a physical board yet. The disclaimer that the results are a design aid, to be validated by measurement, should appear in the About box, the user guide and every report.
* **What the corrections of section 21 leave** (`validation.md` section 21): a bare copper pad on a one-layer board is still hard for the Lumped (−11 to −17 % against the 3D solid) and the Analytic (−11 to −36 %), whose ring-mean and uniform-sheet ideas cannot hold a small pad on a poor laminate; the FDM samples the pad edge on its nodes (−7 to −10 %). The input checks warn about a one-sided pad; the FVM (within 3.5 %) and the 3D solid are the models for such boards.
* Done: the 3D solid against Yovanovich's spreading table and a grid-convergence study, the fins against a 2D fin (`validation.md` sections 15 and 16). Open: a transient comparison against the 3D solid; a thick-copper case; the 3D solid with the package.

### Ideas from similar projects and tools (research of 2026-10-21 and 22)

What other open-source projects and commercial tools do, and what would be worth taking. Sources were read as web summaries (the repositories were not cloned or run): none of the projects below has the models, the profiles, the junction, the computed convection or the 3D check of this one; they are mostly KiCad plug-ins with one 2D model.

| Project / tool | What it does | Idea for us |
| :-- | :-- | :-- |
| [Dietschi10/KiCad_Thermal_Sim](https://github.com/Dietschi10/KiCad_Thermal_Sim) | KiCad plug-in: 2D in-plane conduction on every copper layer, coupling through FR-4 and vias, manual heat sources, optional DC current (I²R) heating and a Joule-loss map | **KiCad import** and **Joule heating of the copper** |
| [mgburr/pcb-sim-toolkit](https://github.com/mgburr/pcb-sim-toolkit) | Python toolkit that imports KiCad boards: 2D finite-difference steady state, junction temperature per component, with SPICE and signal integrity | components with positions and powers read from the board file |
| [krosa-laboratory/kicad-electrothermal-sim](https://github.com/krosa-laboratory/kicad-electrothermal-sim) | 2.5D/3D DC IR-drop and electro-thermal co-simulation (sparse MNA and FEM) on native KiCad 6 to 9 files, temperature maps planned | **electro-thermal coupling**: current density → I²R heat → temperature → resistivity |
| [kbralten/KiPIDA](https://github.com/kbralten/KiPIDA) | KiCad 9 plug-in: DC power integrity, current density and thermal rise with a 2.5D resistive mesh | the same coupling, and a current-density map |
| [SPIKE](https://github.com/krishna-swaroop/SPIKE) | Desktop workbench (power and signal integrity, thermal, extensions): layer maps, cooling presets, command line | cooling presets; an extension mechanism |
| [SchrodingersGat/KITS](https://github.com/SchrodingersGat/KITS) | KiCad thermal simulation tool (MIT) | listed only |
| Ansys Icepak, Flotherm, Cadence Celsius, Simcenter | Import of ODB++/Gerber/IPC-2581, orthotropic conductivity per layer, conjugate heat transfer with airflow, component libraries (2R/DELPHI) | ECAD import; copper as polygons, not as a percentage (JLCPCB's advice too); a component library |
| Elmer FEM / OpenFOAM routes ([jrainimo write-up](https://jrainimo.com/build/2024/11/oss-thermal-simulation-of-pcbs/)) | Export the copper geometry (STEP/XAO) to a free 3D solver | export of the model for an external 3D check |
| [Tomachie/FYPA](https://github.com/Tomachie/FYPA) (fork of [anarthrous-eda/FYPA](https://github.com/anarthrous-eda/FYPA), AGPL-3.0) | PDN (voltage drop) analysis of Altium and Gerber boards: a 2D FEM Laplace solve per copper layer, OpenGL viewer with probes and tables, editor mode with a sidecar file, result cache, PASS/FAIL checks with a CI exit code, regulator model, ParaView export, release workflow | design checks with pass/fail and a CI exit code, result cache, sidecar edits, regulator losses from efficiency, probes, ParaView export, release automation |
| [atx/padne](https://github.com/atx/padne) (the FEM solver FYPA vendors; NLnet-funded) | KiCad-native 2.5D FEM of the DC voltage drop and current density; text directives in the schematic on `DESIGNATOR.PAD` endpoints; Qt GUI and ParaView export; also meant for "heating elements" | read part parameters from the schematic fields; the current solution gives the I²R heat source |
| [wavenumber-eng/altium_monkey](https://github.com/wavenumber-eng/altium_monkey) (AGPL-3.0) | Python reading/writing of Altium PcbDoc, SchDoc, PrjPcb | an import path for Altium boards; design-review checks in CI |
| JLCPCB / RayPCB guides | Thermal vias: 4 vias about 40 K/W, 16 about 10 K/W; power from the datasheet maximum, V × I, or a circuit simulation | a thermal-via array generator and a check against those numbers |

The ideas, in the order of value for the effort (all future work):

1. **Electro-thermal coupling**: Joule heating of the copper (current in, current out → I²R in planes and traces, `IPC-2152` trace-rise check), copper resistivity rising 0.39 %/K, solved by the fixed-point loop that already exists for the power coefficient; a DC solve per copper layer gives the heat source and the voltage drop (padne, FYPA).
2. **Thermal via tools**: an array generator (pitch, diameter, area), the resistance of an array next to the 4/16-via figures of the guides, a via-count sweep.
3. **Parameter sweeps and comparison of two designs** (copper area, number of vias, power, ambient, air speed) with plots of Tj against the parameter and an A/B table; a short optimisation reusing the power-limit logic.
4. **Design checks with PASS/FAIL and an exit code** (`--fail-on fail` in `run`), a **report** (one HTML or PDF page with the settings, maps, table of parts with margins and warnings), and a **result cache** keyed by the problem, options and code version.
5. **Regulator and converter losses from efficiency**: `P_out (1/η − 1)` for a switching converter and `(V_in − V_out) I_out` for an LDO, in the power calculator.
6. **Parameters in the design files**: read power, θ and Tj max from fields of the KiCad symbol, with our own settings in a sidecar file so the CAD files are never modified.
7. **Probes and pin tables** (temperature of every layer at a clicked point; sortable tables of parts and vias), **export for ParaView** and for an external 3D check (STEP/XAO or a mesh).
8. **Cooling presets and enclosure**: an air-speed preset by fan, a closed box with an internal air temperature rise (a first step towards conjugate heat transfer, no CFD).
9. **Local mesh refinement or a triangular mesh** near parts and along curved outlines (large work, only if the boards that matter are large), and **release automation** (CI with lint, documentation gate and tests; a standalone program on a version tag).

**Licences**: FYPA, padne and altium_monkey are AGPL-3.0; this project is MIT (see the `LICENSE` file; the licences of the libraries it uses are in the README). Their code must not be copied here; their ideas and file formats can be used (Gerber, Excellon, KiCad and Altium formats are public or reverse-documented) and any import has to be written independently.

### Deferred

Neural-network surrogates; reduced-order models (only if transients become too slow); a per-cell or enclosure-aware radiation model; editing power tables inside the application (the CSV round trip is the workflow).

## References

1. gerbonara, https://pypi.org/project/gerbonara/ (documentation https://gerbolyze.gitlab.io/gerbonara); listed only, not evaluated here (apertures, regions and clear polarity to check); licence checked on 2026-10-23: Apache-2.0 (PyPI, version 1.6.3), compatible with an MIT project that only imports it. Its companion shapely is BSD-3-Clause.
2. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf; Texas Instruments SLUAAT8, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, `D + (1 − D) z(t)`).
3. The datasheets, JEDEC standards and application notes behind the Component element (JESD15-3, JESD51 family, TI SPRA953B and AN-2020, Renesas, Richtek, Infineon, Vishay and others) are listed at the end of `research.md`.
4. Fabricator stack-up tables used in `docs/validation.md` section 14 are listed in its Literature section (JLCPCB, PCBWay, Eurocircuits, Sierra Circuits).
