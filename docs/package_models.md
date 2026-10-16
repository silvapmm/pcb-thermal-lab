# Package (component) thermal models: the evidence behind the plan

Research notes (2026-10-16) that support the *Package* type of the future Component element (`roadmap.md` section 3). Every claim is tied to a source; things we could not verify are marked as such.
Nothing here is implemented yet.

## 1. What the standards define

| Item | What it is | Source |
| :-- | :-- | :-- |
| JESD15-3 | The **two-resistor (2R) compact thermal model**: three nodes (junction, case, board) and two resistances (junction-to-board, junction-to-case); the die is at a single temperature; ambient is isothermal in steady state and power enters the junction node. Single-die packages only. Built from the metrics of JESD51-8 (θJB) and JESD51-12 (θJC,top). | [1], [2] |
| JESD15-4 | The **DELPHI** compact model: more nodes on the package surface, resistors between die and surface nodes and *shunt* resistors between surface nodes; for higher accuracy than 2R. | [2], [3] |
| JESD15 family | JESD15 overview, 15-1 compact thermal modelling overview, 15-2 terms and definitions, 15-3 two-resistor, 15-4 DELPHI. The standards do not prescribe a machine-readable representation of the network. | [2] |
| Origin | Compact models were developed in Europe (ESPRIT / DELPHI project, 1993 to 1996) and are implemented in most system-level thermal tools. | [4], [5] |

## 2. The metrics a datasheet gives, and which ones may be used as model resistors

| Metric | Definition | Use in our model | Source |
| :-- | :-- | :-- | :-- |
| θJC (top) | `(T_J - T_C)/P`, measured with the case surface held on a cold plate or heat sink; depends mainly on thickness, area and conductivity of the materials in that path | **yes**: resistance junction to top case (`θJC,top`) | [6], [7] |
| θJB | `(T_J - T_B)/P`, all heat forced into the board by a ring cold plate; depends on the test board (standardised on 1S2P) | **yes**: resistance junction to board (`θJB`) | [6], [7] |
| ΨJT | `(T_J - T_T)/P` with the package powered on a board; **not a true resistance**: only part of the power flows through the top; typically 0.5 to 2 °C/W for plastic packages against θJC of 4 to 15 °C/W; near zero with an embedded slug | **no**; use only to *check* the model | [6], [7] |
| ΨJB | same idea for the board; not a true resistance; always below θJB, within about 15 % for small and medium packages; 75 to 95 % of the heat leaves through the PCB | **no**; use only to *check* | [6], [7] |

Consequences for the design:
- The user enters **θJB and θJC,top as resistances** (the datasheet's θ values, not ψ). The program must not accept ψ as a resistor; the labels and tooltips say so.
- The program can **report ψJT = (T_j - T_top)/P and ψJB = (T_j - T_board)/P** from its own solution, which can be compared with the datasheet ψ values as a consistency check on the inputs.
- The share of the power going into the board should land in the 75 to 95 % range quoted by TI for typical plastic packages [6]; a value far outside it is flagged as a warning.

## 3. Known limits (must be shown to the user)

1. **Accuracy.** The 2R model is the simplest standardised model [2]. For DELPHI one source states a predictive accuracy of junction temperature and major heat fluxes within 10 %, "a major improvement" over the 2R model [8]. A search summary also quoted 2 to 20 % deviation of 2R from detailed models, growing with forced airflow; we could **not** trace that figure to a primary source, so it is *not* used in the program text. Our own validation (section 5) will quantify the error on our boards instead.
2. **Boundary-condition dependence.** The 2R model is not boundary-condition independent in general; DELPHI models are constructed to be [8].
3. **Single junction temperature.** One die, one temperature: no hot spots on the die, no multi-die packages [1], [2].
4. **Redistribution of θJB over the footprint.** TI notes that the difficulty of using θJB in a board-level model is how to spread the single resistance that ends on the board over the package footprint; for area-array packages representing the connection as a point is wrong, shorting the board surface under the package with a very high conductivity plate introduces errors, and a better practice is a solid block of footprint size whose conductivity gives the right θJB [6].
   Our implementation: the footprint cells are connected to `T_j` through `G_i = w_i / θJB` (`w_i` = coverage weight of the cell, `Σ w_i = 1`), which is the "block of footprint size" approach: cells keep their own temperatures and no artificial short is introduced.
5. **θJB depends on the test board** (standardised 1S2P) [7]; on very different boards the datasheet value is an approximation. The editor tooltip says so.
6. **No heat capacity.** The standard 2R and DELPHI models have no thermal capacitance; dynamic compact models were still under standardisation in 2007 [8], and an RC ladder derived from measured transient curves is the way to add it [9]. Therefore the Package is **quasi-static**: valid for periods much longer than the package time constant; for shorter pulses a Foster RC chain from the manufacturer's `Zth,JC(t)` curve is needed (planned stage 4), and the program warns about the shortest valid period.
7. **Top surface cooling is not part of the standard.** JESD15-3 gives the junction-to-case resistance; what happens from the case node to the air is left to the application: TI's 3-resistor model closes it with an ambient resistance Ra "calculated from the convective heat loss and radiation loss from the top of the package" [6]. This is exactly the computed `h` of `roadmap.md` section 2 applied to the package top (area and temperature of the package), or a fixed heat-sink resistance in K/W entered by the user.

## 4. How it maps to the three models

The structure is the same series-parallel network in all three; only how it attaches to the board differs.

```
          P (constant or square wave)
           |
          [T_j]--- θJC,top ---[T_case]--- R_top ---> ambient     (R_top = 1/(h A_top) or a heat sink in K/W)
           |
           θJB (spread over the footprint cells with weights w_i)
           |
        board cells under the package
```

- **FVM:** one extra unknown `T_j`; `G_b = 1/θJB` couples it to the footprint cells (`G_i = w_i G_b`); `G_top = 1/(θJC,top + R_top)` couples it to ambient. The augmented matrix stays symmetric positive definite, so the direct solver, CG and the time stepping are unchanged.
- **Lumped:** `T_j` is a node attached to ring 0 of the heater layer through `G_b` and to ambient through `G_top`.
- **Analytic:** a scalar Woodbury update on the footprint-average modal response: `θ̄_fp = θ̄_0 + g_ff f`, `f = G_b (T_j - θ̄_fp)`, `T_j = (P + G_b θ̄_fp)/(G_b + G_top)` (derivation in `roadmap.md` 3.2).
- **Profiles:** the wave drives `P`; the average-or-resolve decision uses the step response of `T_j`. With no heat capacity `T_j` follows `P` instantly.

## 5. Validation plan (what makes the implementation trustworthy)

1. **Limits:** `θJB → 0` and no top path gives the existing heater model exactly; `G_top → 0` gives the heater plus the offset `P θJB` (the current `theta_jb` behaviour).
2. **Exact series-parallel solution** on a board with a uniform sheet (known board resistance): `T_j` and the power split to 1e-9.
3. **Energy balance** to machine precision with the extra node (power out through the board + through the top = power in).
4. **Three models against each other** on the example board, as for heaters (Lumped within about 4 %, Analytic within about 2 %).
5. **Consistency with datasheet ψ:** for one real package with published θJB, θJC,top, ψJT and ψJB (to be chosen and cited; no numbers are invented), the program's ψJT and ψJB should be close to the datasheet values on a board similar to the test board.
6. **Power split in the 75 to 95 % board range** for a plastic package with no heat sink, as in [6].
7. **Independent 3D check** (`roadmap.md` section 5), later, for a package modelled as a solid.

## 6. Open points

- Which real package to use for the ψ consistency check (needs datasheet values with their test conditions).
- Whether to offer DELPHI later: it needs the extra surface-node resistances that manufacturers rarely publish, so it stays out of scope until a data source exists.
- Default top-surface emissivity (plastic mould compound is about 0.95 according to [7]) and how to treat metal-lid packages.

## References

1. JEDEC, JESD15-3, *Two-Resistor Compact Thermal Model Guideline* — https://www.jedec.org/standards-documents/docs/jesd-15-3 (scope: single-die packages, metrics of JESD51-8 and JESD51-12; full text not read, summary from the JEDEC page and patent citations).
2. J. Stori, K. Brady, T. Thurman, *Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2*, NISTIR 7648, 2008 — https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf (text read; describes JESD15 family, 2R with three nodes and two resistances, DELPHI with shunt resistors).
3. JEDEC, JESD15-4, *DELPHI Compact Thermal Model Guideline* (via [2]).
4. Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, 2012 (compact models from the EC ESPRIT/DELPHI work; see [6]).
5. *Compact Thermal Modeling: Impacting the Industry*, Semiconductor Digest, 2007 — https://sst.semiconductor-digest.com/2007/03/compact-thermal-modeling-impacting-the-industry/
6. Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, July 2012 — https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/171/4745.TI_5F00_PackageThermalMetrics_5F00_spra953b.pdf (text read: definitions of θJC, θJB, ΨJT, ΨJB, the 3-resistor estimate, the θJB redistribution problem, 75 to 95 % of the heat through the PCB, ΨJT 0.5 to 2 °C/W against θJC 4 to 15 °C/W).
7. Renesas, *Thermal Characterization of Packaged Semiconductor Devices* (white paper TB379/WHP) — https://www.renesas.com/en/document/whp/thermal-characterization-packaged-semiconductor-devices (text read: definitions and usage of θJC, θJB, ΨJB, ΨJT; ΨJB within about 15 % of θJB; mould compound emissivity about 0.95).
8. Semiconductor Digest [5] (text read): DELPHI within 10 % of junction temperature and major fluxes; boundary-condition independence; dynamic compact models under standardisation.
9. Siemens, *Experiment vs. Simulation, Part 4: Compact Thermal Models*, 2013 — https://blogs.sw.siemens.com/simulating-the-real-world/2013/04/05/experiment-vs-simulation-part-4-compact-thermal-models/ (text read: standard 2R and DELPHI lack thermal capacitance; RC ladders from transient measurements add it).
10. ROHM, *Two-Resistor Model for Thermal Simulation*, application note 60AP001E — https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf (note: ROHM's "two-resistor model" uses junction-to-board and board-to-ambient resistances, which is **not** the JESD15-3 definition; it is not used as a source for our model).
