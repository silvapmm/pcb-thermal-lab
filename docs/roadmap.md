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

**Limits to show to the user.** Accuracy: the 2R is the simplest standardised model; DELPHI is quoted as within about 10 % on junction temperature and main fluxes [5]; an often-quoted 2 to 20 % for the 2R could not be traced to a source and is not used: we will measure it on our boards.
Single junction temperature (no die hot spots, no multi-die). `θJB` depends on the test board (standardised 1S2P). No heat capacity in the standard models: the Package is **quasi-static**, valid for periods well above the package time constants; dynamic compact models were still being standardised [5]
and an RC ladder from measured transient curves is the way to add it [6].

### 1.4 Heat sink on a component

Top cooling of a Package: none (package top with the computed `h` or a fixed resistance), **heat sink** (`junction → θJC,top → case → θCS → sink node → θSA → ambient`, the usual `θJA = θJC + θCS + θSA` [3], [4]) and later a heat sink described by geometry.

* **θSA depends on the temperature rise** (agreed): the natural-convection `h` grows roughly as `ΔT^(1/4)` and radiation faster, so a datasheet value is valid at its own operating point; datasheets give power against temperature rise and the resistance is `ΔT/P`.
  Design: the user enters `θSA` and the `ΔT_ref` at which it was specified; the program scales the convective part with `(ΔT/ΔT_ref)^(−1/4)` in the same iteration that computes `h`; without `ΔT_ref` the number is constant. To check before shipping: the exponent against a real curve, and the convection/radiation split.
* **Heat-sink capacity** `C_hs` (J/K, mass × specific heat; aluminium about 0.9 J/(g K)) as an optional node capacity from the first version (agreed): with it fast waves see only `θJC + θCS` in parallel with `θJB` because the sink stays near its mean temperature;
  without it the sink answers instantly and the junction ripple of fast waves is overestimated (conservative). The package's own capacity (die and mould) comes later from the manufacturer's `Zth,JC(t)` curve as a Foster chain [8].

### 1.5 Power profiles with a Package

The profile drives `P` as now. The **average-or-resolve decision** keeps measuring the board (that is what costs computing time) but the program also reports `T_j(t)` at every time step: with the board temperature nearly constant, `T_j(t) = T_board,mean + P(t)·R_eff`, `R_eff = θJB ‖ (θJC,top + θCS + …)`, which is a cheap post-processing of the instantaneous power
and is **not averaged away** (on the example, 13.3 W on / 4 W average with `R_eff` ≈ 4.8 K/W gives a junction about 64 K above the board while the board only oscillates 0.4 K; illustrative values). Without package capacity this is an upper bound for fast waves.

### 1.6 Staging and validation

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
