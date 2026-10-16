# Roadmap

What is planned and why, with the evidence gathered so far. Nothing in this document is implemented yet. What exists is described in [`models.md`](models.md) and checked in [`validation.md`](validation.md).
Agreed order: **Component element (Package, heat sink)** → passive areas → Foster chain → **Gerber import** and **variable stack-up** (extras) → optional multigrid.

## 1. Component element

### 1.1 Why

Today a part is a heater: all its power enters the board under the footprint and `theta_jb` only adds an offset to the reported junction temperature. A real single-die part generates heat at the junction, which leaves by **two parallel paths**:
down through the package pad and solder into the board (`θJB`) and up through the package top (`θJC,top`) into the air or a heat sink. The current models cannot represent the top path: they send all the heat into the board (hotter board, hotter junction) and cannot represent
a heat sink on the part. Estimate on the reference board (5 W, board resistance 13 K/W, `θJB` 6 K/W): board only, junction rise 5 × (13 + 6) = 95 K; with a top path of 25 K/W the heat splits 57 % board / 43 % top and the junction rises about 54 K (series-parallel estimate, not a measurement).

### 1.2 One element with a type

Decided: a single **Component** element with a type and the properties that type needs. Today's heater is the type *Source* with nothing else set, so existing projects keep working. Types: *Source* (power into the board),
*Package* (JEDEC 2R, below), and passive areas: *Cooled area* (extra `h` or a resistance to ambient over the polygon; today's "sink" is the simplest case), *Contact* (pad or enclosure touching the board: a conductance to a fixed temperature),
*Material patch* (different conductivity or thickness, for example a via field described by its density). Passive types have no power; *Source* and *Package* take a constant power, a square wave or a CSV table.

### 1.3 Package: the JEDEC two-resistor model

The 2R compact model (JESD15-3) has three nodes (junction, case, board) and two resistances (junction-to-board, junction-to-case), the die at one temperature, ambient isothermal, power entering the junction; it applies to single-die packages [1], [2].
DELPHI (JESD15-4) adds surface nodes and shunt resistors for higher accuracy; manufacturers rarely publish those resistances, so it stays out of scope until a data source exists [2].

**Which datasheet numbers may be used.** `θJC,top` and `θJB` are resistances: the user enters them. `ΨJT` and `ΨJB` are **not** true resistances (only part of the heat flows between the two measured points; ΨJT is typically 0.5 to 2 K/W against θJC of 4 to 15 K/W; ΨJB is within about 15 % of θJB)
and are never accepted as resistors [3], [4]. The program can *report* `ΨJT = (T_j − T_top)/P` and `ΨJB = (T_j − T_board)/P` from its own solution, to compare with the datasheet as a consistency check, and should find 75 to 95 % of the heat leaving through the board for a plastic package [3].

**Structure** (the same series-parallel network in the three models; only the attachment to the board differs):

```
          P (constant, wave or table)
           |
          [T_j]--- θJC,top ---[T_case]--- R_top ---> ambient    (R_top = 1/(h A_top) with the computed h, or a heat sink)
           |
           θJB (spread over the footprint cells with weights w_i)
           |
        board cells under the package
```

* **FVM**: one extra unknown `T_j`; the footprint cells couple to it with `G_i = w_i/θJB` (`w_i` coverage weights, `Σ w_i = 1`: TI's "block of footprint size" practice [3], without an artificial short); `T_j` couples to ambient with `G_top = 1/(θJC,top + R_top)`.
  The augmented matrix stays symmetric positive definite.
* **Lumped**: `T_j` is a node attached to ring 0 of the heater layer and to ambient. **Analytic**: a scalar Woodbury update on the footprint-average modal response: `θ̄_fp = θ̄_0 + g_ff f`, `f = G_b (T_j − θ̄_fp)`, `T_j = (P + G_b θ̄_fp)/(G_b + G_top)`.
* **Top surface cooling** is not part of the standard; TI closes the circuit with an ambient resistance from the convective and radiative loss of the package top [3]: the computed `h` already in the program applied to the package area and temperature, or a heat sink.

**Limits to show to the user.** JESD15-3 itself states that the error of a 2R prediction "cannot be known a priori", that it may over- or under-predict, that it grows with the difference between the application and the JEDEC test environment, and that published studies show errors on the junction **temperature rise** "in the neighbourhood of 30 % or less", a guide and not a bound [18];
DELPHI is quoted within about 10 % (typically 5 % against detailed models) [5], [19]. The 2R model works best when the heat goes mostly into the board or a heat sink [19]. Single junction temperature (no die hot spots, no multi-die). `θJB` depends on the test board (below). No heat capacity in the standard models: the Package is **quasi-static**,
valid for periods well above the package time constants; dynamic compact models were still being standardised [5] and an RC ladder from measured transient curves is the way to add it [6].

### 1.4 Heat sink on a component

Top cooling of a Package: none (package top with the computed `h` or a fixed resistance), **heat sink** (`junction → θJC,top → case → θCS → sink node → θSA → ambient`, the usual `θJA = θJC + θCS + θSA` [3], [4]) and later a heat sink described by geometry.

* **θSA depends on the temperature rise** (agreed): the natural-convection `h` grows roughly as `ΔT^(1/4)` and radiation faster, so a datasheet value is valid at its own operating point; datasheets give power against temperature rise and the resistance is `ΔT/P`.
  Design: the user enters `θSA` and the `ΔT_ref` at which it was specified; the program scales the convective part with `(ΔT/ΔT_ref)^(−1/4)` in the same iteration that computes `h`; without `ΔT_ref` the number is constant. To check before shipping: the exponent against a real curve, and the convection/radiation split.
* **Heat-sink capacity** `C_hs` (J/K, mass × specific heat; aluminium about 0.9 J/(g K)) as an optional node capacity from the first version (agreed): with it fast waves see only `θJC + θCS` in parallel with `θJB` because the sink stays near its mean temperature;
  without it the sink answers instantly and the junction ripple of fast waves is overestimated (conservative). The package's own capacity (die and mould) comes later from the manufacturer's `Zth,JC(t)` curve as a Foster chain [8].

### 1.5 Power profiles with a Package

The profile drives `P` as now. The **average-or-resolve decision** keeps measuring the board (that is what costs computing time) but the program also reports `T_j(t)` at every time step: with the board temperature nearly constant, `T_j(t) = T_board,mean + P(t)·R_eff`, `R_eff = θJB ‖ (θJC,top + θCS + …)`, which is a cheap post-processing of the instantaneous power
and is **not averaged away** (on the example, 13.3 W on / 4 W average with `R_eff` ≈ 4.8 K/W gives a junction about 64 K above the board while the board only oscillates 0.4 K; illustrative values). Without package capacity this is an upper bound for fast waves.

### 1.6 What real datasheets give (read on 2026-10-16)

Parameters found in datasheets of typical parts (all read from the PDF text, except the LED row, taken from a search summary):

| Part | Thermal parameters given | Conditions stated | Source |
| :-- | :-- | :-- | :-- |
| Power MOSFET, TI CSD17308Q3 (SON 3.3 × 3.3) | `RθJC` 4.5 K/W (max); `RθJA` 58 K/W (max, 1 in² pad) and 165 K/W (max, minimum pad); power 2.7 W at 25 °C ambient, 28 W with the case at 25 °C; `Tj` −55 to 150 °C; transient thermal impedance curves | board 1.5 × 1.5 in, 1.52 mm FR-4, **2 oz** (71 µm) copper pad of 1 in² (6.45 cm²); `RθJC` "by design", `RθJA` "determined by the user's board design" | [10] |
| Power MOSFET, Infineon OptiMOS (application note) | `RthJC` (bottom) 1.1 K/W; `Ptot` 136 W at `Tc` 25 °C and 3.0 W at `Ta` 25 °C with `RthJA` 50 K/W; **`ZthJC(tp, D)` curves** and the rule `ΔTj = Zth(tp, D) · Ptot`; "Zth consists of Rth and Cth" | 40 × 40 × 1.5 mm FR-4, **6 cm² of 70 µm copper** on one layer for the drain, board vertical in still air | [11] |
| DC-DC converter, TI LMR36510 (HSOIC-8, exposed pad) | `RθJA` 42.9, `RθJC(top)` 54, `RθJB` 13.6, `ΨJT` 4.3, `ΨJB` 13.8, `RθJC(bot)` 4.3 K/W; a graph of `RθJA` against copper area | JEDEC board; the datasheet says the table "is not valid for design purposes" and that `RθJA` depends on power, airflow, PCB area, copper heat-sink area, number of thermal vias and neighbours | [12] |
| LDO, TI TPS7A47 (QFN-20, exposed pad) | `RθJA` 32.5, `RθJC(top)` 27, `RθJB` 11.9, `ΨJT` 0.3, `ΨJB` 11.9, `RθJC(bot)` 1.7 K/W; "`θJA` is the sum of `θJCbot` plus the PCB copper contribution" | JEDEC board; `θJA` "only a relative measure of package thermal performance" | [13] |
| Schottky diode, SMA (SX SS12…SS120) | `RθJ-A` 65 and `RθJ-L` (junction to terminal) 20 K/W; `Tj` −55 to 125 or 150 °C; no `RθJC`, no `Zth` | PCB with 0.2 × 0.2 in (5 × 5 mm) copper pads | [14] |
| Schottky diode, SMC (SS54) | `RθJA` 15 K/W only; `Tj` −55 to 125 °C | "junction to ambient", pad not stated | [15] |
| Power metal-strip resistor, Vishay WSL | **power rating at 70 °C** (0.1 W for 0603, 0.125 W for 0805 …), derating curve to zero at the maximum temperature (170 °C); no thermal resistance | rating at 70 °C, board mounting | [16] |
| LED, high power (Samsung and others; search summary, not read) | `Rth j-sp` junction to solder point: a "real" value (about 5 K/W) and a lower "electrical" one (about 3 K/W); `Tj` max 150 °C | the LED dissipates `Vf·If` minus the light emitted, which the datasheet does not give as a number | [17] |

**What this means for the Component element**

1. **The parameter sets differ by part type**, so the Package form needs optional fields and presets by type, not one fixed set: (a) `θJC,top` + `θJB` (TI converters and LDOs, the full 2R set); (b) **one** resistance to the board or terminal (`θJC(bot)` of a MOSFET, `θJ-L` of a diode, `Rth j-sp` of an LED) and no top path;
   (c) only `θJA` on a stated board (some diodes); (d) only a **power rating at a temperature** (resistors: a thermal resistance can be derived as `(T_max − T_rating)/P_rating`, for example 100 K / 0.1 W = 1000 K/W for the 0603 at its 70 °C rating, an order of magnitude to be checked against the manufacturer's mounting note).
2. **`θJA` must never be an input** of the board model: manufacturers say so themselves ([12], [13]); it is useful only as a plausibility check (our `T_j − T_ambient` on a board like the datasheet's should approach `P·θJA`) and `RθJA` against copper area (the CSD17308Q3 gives 58 and 165 K/W for 6.45 cm² and the minimum pad) is a good **validation case** for the model.
3. **Which resistance goes between the junction and our board.** In the exposed-pad parts above `θJC(bot)` (4.3 and 1.7 K/W) is much smaller than `θJB` (13.6 and 11.9 K/W): `θJB` is measured on the JEDEC board and **includes the spreading of the heat in that board**, while `θJC(bot)` stops at the pad. Our model already spreads the heat in the real board under the footprint, so using `θJB` there would count the board's spreading twice. Proposal: the Package takes the
   **junction-to-pad resistance** (`θJC(bot)`, `θJ-L`, `Rth j-sp`) when the datasheet gives it, and `θJB` otherwise, with a note on which one was used; the `ΨJB` consistency check (section 1.3) will show whether the choice is sensible for a given part. To settle with a real part.
4. **Transient curves** `Zth(tp, D)` (MOSFETs) contain `Rth` and `Cth`: they are the input of the later Foster chain, and the datasheet shortcut `ΔTj = Zth(tp, D)·P` is a good check of our time simulation.
5. **Copper weight matters**: the MOSFET boards are 2 oz (71 µm) or 70 µm, our default is 35 µm; the datasheet `RθJA` values cannot be compared without matching the copper of the board.
6. **LEDs**: the heat is `Vf·If` minus the optical output; the Component needs a "fraction of the electrical power that becomes heat" (or the heat power directly), which is not a datasheet number.
7. The simple **Source** (a heater with a power) stays the default and needs none of this.

### 1.7 How the datasheet tests convert to our model (researched 2026-10-16)

**What each test measures** (JESD51 family [18], [20], [21], [22]):

| Metric | Test | What it is physically | Transferable to our board model? |
| :-- | :-- | :-- | :-- |
| `θJC(top)`, `θJC(bot)` | cold plate on the top or bottom face, one heat path (JESD51-14 dual interface or the cold-plate method) | resistance **inside the package** from the junction to that face; meaningful for packages with a predominantly 1D path (the `θJB/θJC` ratio above about 10, power packages); an overmolded BGA gave 0.82 against 1.79 K/W by the two methods [22] | **yes**, it is a package property; the solder, thermal paste or heat-sink interface on that face is ours |
| `θJB` | double ring cold plate, heat forced through the board (JESD51-8); board temperature 1 mm from the package edge (area-array parts) or on the lead foot (leaded parts) | package resistance **plus part of the test board** for area-array parts, none for leaded parts [18], [23] | **partly**: use it only when `θJC(bot)` is not given, and expect it to over-estimate if the part's heat spreading is already in our board [18] |
| `θJA` | still air, 0.3 m cube, JEDEC board 1s0P (JESD51-3) or 2s2p (JESD51-7), at least 76 × 114 mm with at least 50 µm on the top copper (JESD51-2, -3, -7) [20] | package + test board + convection together | **no as input** (manufacturers say so [12], [13], [23]); **yes as a validation target**, see the virtual test below |
| `ΨJT`, `ΨJB` | same environment as `θJA`, with the real heat partition | `ΔT/P` between the junction and a measured top or board temperature, **not** a resistance [3], [18] | as a **post-processing estimate**, see level A |

**Three levels of approximation, from cheapest to richest**

* **A. Source plus ψ (no new physics).** The heat enters the board under the footprint as today; after the simulation the program estimates `T_j = T_board,ref + ΨJB·P` (or `T_j = T_top + ΨJT·P` when a top temperature exists), where `T_board,ref` is the simulated board temperature on the reference point of the test (a ring 1 mm outside the package body).
  This is the method the manufacturers themselves recommend with a measured temperature on the real board; Richtek measured 79.9 °C with the body-diode method against 79.98 °C from `ΨJB` and the measured board temperature, and 79.9 °C from `θJA(EVB)` [23]; `ΨJT` is the better estimate when the power is uncertain because the top is closer to the junction temperature than the board is [23].
  Valid while the application is close to the test conditions (no heat sink, similar board); it needs `ΨJB` (given by IC makers, not by most MOSFET and diode makers) and it does not change the board field.
* **B. Package (JESD15-3, section 1.3).** A junction node with the two resistances, built as the standard's **block-and-plate**: an isothermal block the size of the package, insulated on its sides, between two plates whose resistance equals `θJC,top` and `θJB`; the plate on the board has the footprint area, i.e. a uniform conductance `1/(θ·A)` per unit area,
  which is exactly our `G_i = w_i/θJB`; the heat source sits in the block (a volume or area source, never a point); the block's own resistance must be two orders of magnitude below the plates' [18]. **Exposed-pad parts: the standard allows replacing `θJB` by `θJC(bottom)`** [18] (4.3 against 13.6 K/W and 1.7 against 11.9 K/W for the two TI parts of section 1.6), which settles which number goes between the junction and our board.
  Needed when a heat sink or a strong top path exists. Expected error on the rise: 30 % or less in the standard's words [18].
* **C. DELPHI / detailed.** Needs resistances manufacturers do not publish; out of scope until a data source exists.

**The virtual JEDEC test (validation and a way to recover a missing number).** Build the datasheet's own board in the program (JESD51-3 1s0P or JESD51-7 2s2p, 76.2 × 114.3 mm, the copper and the pad area the datasheet states), natural convection (computed `h`, still air), the package with the user's resistances, and compute
`θJA = (T_j − T_amb)/P`, `ΨJT` and `ΨJB`; they should land near the datasheet values (to be checked on the TPS7A47: `θJA` 32.5, `ΨJT` 0.3, `ΨJB` 11.9 K/W with `θJC(bot)` 1.7 K/W; and on the CSD17308Q3: `RθJA` 58 and 165 K/W for 6.45 cm² and the minimum pad of 2 oz copper). The test is the **calibration of the Component**: if it fails by more than the 30 % of the 2R,
the parameters or the board data are wrong. It also converts the parts that only give `θJA` on a stated board (the SMA diode: `θJA` 65 K/W on 5 × 5 mm pads): the package resistance is `θJA` minus the resistance that **our model** gives to the stated board, the same relation TI states (`θJA = θJC(bot)` plus the contribution of the PCB copper [13]).

**What the Component form asks, by case**: (1) the datasheet gives `θJC(top)` and `θJC(bot)` or `θJB` → Package with the top path; (2) one resistance to the pad, lead or solder point (`θJC(bot)`, `θJ-L`, `Rth j-sp`) → Package without a top path; (3) only `θJA` on a stated board → the package resistance from the virtual test; (4) only `ΨJB`/`ΨJT` → level A; (5) only a power rating at a temperature → derived resistance with a warning.
The board reference temperature of a `ΨJB` estimate and the 1 mm ring are outputs of the board field, not inputs.

### 1.8 Staging and validation

Stages: (1) Component element and Package, static, in the three models; (2) top path from the computed `h`; (3) heat sink; (4) passive areas; (5) Foster chain for package transients.
Validation: `θJB → 0` and no top path reproduce the current heater; `G_top → 0` gives heater plus the offset `P θJB`; exact series-parallel solution on a uniform board (`T_j` and power split to 1e-9); energy balance with the extra node; the models against each other;
**ΨJT and ΨJB against a real datasheet** (to be chosen, with its test conditions; no numbers invented); power split in the 75 to 95 % board range; an independent 3D solid (the validation script already handles vias and sinks).

## 2. Import of Gerber files (extra)

Read the copper of every layer from manufacturing files instead of drawing zones by hand.

* **Input**: Gerber RS-274X per copper layer, Excellon drill file (vias), outline layer. Candidate library: `gerbonara` (read, modify, write Gerber, Excellon, IPC-356) [7]; not evaluated or installed (licence, apertures, regions, clear polarity to check). Alternative: parse only what is needed.
* **Mapping**: rasterise each layer on a fine grid and store the **copper fill fraction per cell**, which is what the FVM already uses (`S = f k_cu t_cu + k_FR4 (slab − f t_cu)`); the editor keeps polygons for hand-drawn zones and gets an "imported raster" source; drills with plating become vias.
* **Limits to state**: the fill fraction hides trace connectivity (half-filled may be one long trace or two disconnected pieces, so the effective in-plane conductivity is direction dependent), improves with a finer grid (more cells); the Analytic model keeps only the layer average plus local corrections;
  solder-mask openings matter for emissivity, not conduction.
* **Open**: file variants of KiCad/Altium/Eagle, a layer-assignment step in the GUI, plane splits and anti-pads; component positions come from a pick-and-place file (a later extra).
* **Validation**: import a board whose copper was also drawn by hand, compare areas per layer and the FVM result.

## 3. Variable stack-up (extra; keep the model ready for it)

Today: one total thickness, copper thickness per layer (already a list) and **equal dielectric gaps** (`Board.dielectric_thickness()` shares what is left of the thickness among the gaps; each layer node is a slab `thickness/layers`). Real stack-ups have different copper weights, core and prepreg thicknesses and sometimes materials.

* **Parameters** per layer and per gap: copper thickness, **dielectric thickness and material per gap** (FR-4 core, prepreg, high-Tg, polyimide, metal-core insulation, ceramic), through-plane and in-plane `k`, density, specific heat. The board thickness becomes the **sum** of the stack (a check, not an input); a stack-up table in the GUI.
* **Model impact**: FVM: a layer node represents copper plus half of each adjacent dielectric; vertical conductance per gap `k_through/d_gap` (different per gap); vias cross all gaps. Lumped and Analytic: the vertical coupling becomes a vector over gaps (`slab`, `d_diel`, `g_diel` in `_effective_sheet` are scalars today and the
  tridiagonal modal matrix takes one coupling per gap). Time simulation: capacities from real thicknesses and materials. Edge cooling from each layer's real thickness.
* **Why**: through-board resistance is `Σ d_i/k_i`, so a thin prepreg under the heater layer and a thick core elsewhere differ a lot from equal gaps; a metal-core board is another regime. Expect first-order changes in `T_j` with a thin top prepreg and an inner plane.
* **Compatibility**: with equal gaps the new code must reproduce the current results exactly (regression test). The stack-up table also feeds the Gerber import (copper thickness, plating).

## 4. Multigrid solver (optional, low priority)

Measured on the example board, seconds per steady solve (the direct column predates the symmetric ordering that made it about 40 % faster):

| Unknowns | Sparse direct | CG, Jacobi | CG, algebraic multigrid (`pyamg`) |
| --: | --: | --: | --: |
| 32 000 | 0.24 | 0.08 | 0.12 |
| 128 000 | 2.3 | 0.6 | 0.7 |
| 262 000 | 4.6 | 2.3 | 2.1 |
| 512 000 | 16.2 | 6.5 | 4.2 |
| 987 000 | not run (memory) | 12.8 | 8.0 |

All agree to 1e-8 K. The gain appears above about 500 000 unknowns; `pyamg` would stay an optional dependency chosen automatically above a threshold. Plain CG already captures most of the benefit for moderate sizes.

## 5. Further validation

Done: the 3D solid with vias and sinks on four boards (`validation.md` section 3). Next, in order of value: **a measurement of a physical board** (absolute accuracy; also calibrates the convection multiplier, `pcbthermal calibrate`);
a transient comparison against the 3D solid; a thick-copper case; the 3D solid with the Package once it exists.

## 6. Deferred

Neural-network surrogates; trace Joule heating (IPC-2152 style); reduced-order models (only if transients become too slow); a per-cell or enclosure-aware radiation model; editing power tables inside the application (the CSV round trip is the workflow).

## References

1. JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline*, https://www.jedec.org/standards-documents/docs/jesd-15-3 (single-die packages, metrics of JESD51-8 and JESD51-12; the standard itself was not read, only its JEDEC page and citations).
2. J. Stori, K. Brady, T. Thurman, *Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2*, NISTIR 7648, 2008, https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf (read: JESD15 family, 2R with three nodes and two resistances, DELPHI with shunt resistors).
3. Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, 2012, https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/171/4745.TI_5F00_PackageThermalMetrics_5F00_spra953b.pdf (read: definitions of θJC, θJB, ΨJT, ΨJB, the 3-resistor estimate, the θJB redistribution problem, 75 to 95 % of the heat through the PCB).
4. Renesas, *Thermal Characterization of Packaged Semiconductor Devices*, https://www.renesas.com/en/document/whp/thermal-characterization-packaged-semiconductor-devices (read: ΨJB within about 15 % of θJB, ΨJT, mould compound emissivity about 0.95, `θJA = θJC + θCS + θSA`).
5. *Compact Thermal Modeling: Impacting the Industry*, Semiconductor Digest, 2007, https://sst.semiconductor-digest.com/2007/03/compact-thermal-modeling-impacting-the-industry/ (read: DELPHI within 10 %, boundary-condition independence, dynamic models in standardisation).
6. Siemens, *Experiment vs. Simulation, Part 4: Compact Thermal Models*, https://blogs.sw.siemens.com/simulating-the-real-world/2013/04/05/experiment-vs-simulation-part-4-compact-thermal-models/ (read: standard 2R and DELPHI lack thermal capacitance; RC ladders from transient measurements add it).
7. gerbonara, https://pypi.org/project/gerbonara/ (documentation https://gerbolyze.gitlab.io/gerbonara); listed only.
8. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf; Texas Instruments SLUAAT8, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, `D + (1 − D) z(t)`).
9. Not used as a source for the 2R model: ROHM's application note "two-resistor model" (https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf) defines junction-to-board and board-to-ambient resistances, which is not the JESD15-3 definition.
10. Texas Instruments, CSD17308Q3 datasheet (SLPS262C), https://www.ti.com/lit/ds/symlink/csd17308q3.pdf (read: thermal information, `RθJC`, `RθJA` and the pad area graph).
11. Infineon, *OptiMOS Power MOSFET Datasheet Explanation*, AN 2012-03, https://www.infineon.com/assets/row/public/documents/24/42/infineon-mosfet-optimos-datasheet-explanation-applicationnote-en.pdf (read: `Ptot`, `RthJA` conditions, `ZthJC`).
12. Texas Instruments, LMR36510 datasheet (SNVSBD7B), https://www.ti.com/lit/ds/symlink/lmr36510.pdf (read: thermal information and the application note on `RθJA`).
13. Texas Instruments, TPS7A47 datasheet, https://www.ti.com/lit/ds/symlink/tps7a47.pdf (read: thermal information and the power dissipation section).
14. SX Semiconductor, SS12 to SS120 SMA Schottky rectifiers, https://www.ickey.cn/static-pf/datasheet/22/76/cc08/2276cc08322b3110623485720f87bf21.pdf (read: thermal resistance and its PCB note).
15. SS54 Schottky barrier rectifier (SMC), Farnell/element14 datasheet V1.1, https://components101.com/sites/default/files/component_datasheet/SS54%20Schottky%20Diode.pdf (read).
16. Vishay, WSL power metal strip resistors, https://www.vishay.com/docs/30100/wsl.pdf (read: power rating at 70 °C and the derating curve).
17. Samsung LED, high power LED datasheets (for example https://download.led.samsung.com/led/file/automotive/Samsung_C_Gen3_1W_WH_SPHWH1A1N1A0_DS_Rev.1.6.pdf); the thermal figures come from a search summary and the files were **not read**.
18. JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline* (text read, mirror at http://www.simu-cad.com/userfiles/images/ZaiXianXiaZai/ef8f29116ed54c67a8a8d77502611043.pdf): definitions of `θJB` and `θJCtop`, replacing `θJB` by `θJCbottom` for exposed-pad packages, `ψJB` as a substitute, `ψJT` not allowed, the block-and-plate construction, accuracy "30 % or less".
19. Electronics Cooling, *Compact thermal modeling in electronics design* (2007), https://www.electronics-cooling.com/2007/05/compact-thermal-modeling-in-electronics-design/ (read: 2R about 30 % or less, DELPHI within 10 %, typical errors under 5 % against detailed models, lack of `θJB` data from some manufacturers).
20. Electronics Cooling, *JEDEC Thermal Standards: Developing a Common Understanding* (2019), https://www.electronics-cooling.com/2019/11/jedec-thermal-standards-developing-a-common-understanding/ (read: JESD51-2, -3, -5, -6, -7, -8, -9, -14, JESD15-3 and -4; test boards of at least 76 × 114 mm).
21. Electronics Cooling, *Use of junction-to-board thermal resistance in predictive engineering* (1999), https://www.electronics-cooling.com/1999/01/use-of-junction-to-board-thermal-resistance-in-predictive-engineering/ (read: `RJB` depends on the board, about 10 % scatter, errors under 25 % in a CFD study).
22. Electronics Cooling, *The Applicability of JESD51-14 for the Determination of Junction to Case Thermal Resistance* (2024), https://www.electronics-cooling.com/2024/04/the-applicability-of-jesd51-14-for-the-determination-of-junction-to-case-thermal-resistance/ (read: single-path packages, `Rjb/Rjc` above about 10, an overmolded BGA 0.82 against 1.79 K/W).
23. Richtek, *Application and Definition of Thermal Resistances on Datasheet*, AN061 (2020), https://www.richtek.com/Design%20Support/Technical%20Document/~/media/AN%20PDF/AN061_EN.ashx (read: `θJB` on the lead foot for leaded parts, `θJA/θJC/θJB` not applicable to another board, the `ΨJB` and `ΨJT` estimates and their measured check).
