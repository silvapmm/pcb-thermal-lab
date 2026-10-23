# 09. Parts: the junction temperature, the top path and the power that depends on temperature

![Parts](../figures/fig_09_part_runaway.png)

*Figure 9 (`figures/fig_09_part_runaway.png`): left, the worst case: all the power enters the board and the junction sits a series resistance `theta` above the hottest pad point; middle and right, the power that grows with temperature, `P(Tj) = P0 [1 + alpha (Tj - 25)]`, against what the board removes, `(Tj - T_amb) / R`: they cross at the fixed point (stable, `alpha R P0 < 1`) or never cross (thermal runaway, `alpha R P0 >= 1`). The numbers of the curves are illustrative.*

See also the sections of the package drawn from the real section: `research/component-heatsink/figures/fig_05_part_and_top_path_schematic.png` and `fig_06_package_sections.png`.

## 1. What it is

A **part** is a heater with a junction-to-pad resistance `theta_part` (and optionally a top path). The board is solved with the part's power and the junction temperature is read from it. The convention is **worst case first**: all the power reaches the board, then, if a top path is defined, the share that leaves through the top is taken out in a fixed-point loop.

## 2. The series chain

    Tj = T_max,footprint + P theta_part              (the hottest board point under the footprint is the pad temperature)

A junction node joined to the board by a uniform conductance would be about 3 K lower; the worst case keeps the hottest point. Derived quantities, for the same board response `R = (Tj - T_amb) / P` (linear for constant coefficients):

    margin = Tj,max - Tj                 power limit P_lim = (Tj,max - T_amb) / R = P (Tj,max - T_amb) / (Tj - T_amb)
    psi_JB estimate:   Tj = T_ring + psi_JB P,   T_ring = mean board temperature in the ring 0.5 to 1.5 mm outside the outline of the footprint

**Why `theta` must be a junction-to-pad number**: `theta_JA` includes the manufacturer's board and air, and `theta_JB` the spreading in the manufacturer's board; the program computes the spreading in **your** board, so those would be counted twice (JESD15-3 and the package notes in the sources).

## 3. The top path (heatsink on the package)

`analysis.part_split` closes the series-parallel network: a junction node joined to the board by `theta` and to the ambient by

    R_top = theta_JC(top) + interface / A + theta_SA

(`interface / A` the paste or pad resistance per area over the contact area). `api._solve_with_tc` gives the board `P - P_top` and shares the loop with the power coefficient, so FVM, FDM, Lumped, Analytic and the 3D solid all get it. The result is 0.4 to 0.8 K above a uniform-conductance node prototype. A bare mould changes the junction by about 3 K (3 % of the rise); a heatsink on top by a factor of two. Steady state only; without `theta_SA` nothing changes.

## 4. A power that depends on temperature

    P(Tj) = P0 [1 + alpha (Tj - 25 C)]

The program iterates `P_(k+1) = P0 [1 + alpha (Tj(P_k) - 25)]` around the board solve until the powers change by less than 1e-5 (relative). For a linear board (constant `R`, ambient 25 C) the fixed point is

    delta T = P0 R / (1 - alpha P0 R)

and in general `delta T = R P0 [1 + alpha (T_amb - 25)] / (1 - alpha R P0)`. The iteration converges when `alpha P0 R < 1`; **thermal runaway** (no stable point) is reported when the device passes 1500 C or the power grows 50 times. The closed form is reproduced within 0.05 K.

## 5. The datasheet numbers

| Number | What it is | Use here |
| :-- | :-- | :-- |
| `theta_JA` | junction to ambient on the maker's JEDEC board | not used (board counted twice) |
| `theta_JB` | junction to board, measured on the maker's board | not used directly (board dependent) |
| `theta_JC(top)` / `theta_JC(bottom)` | junction to the case top or, for exposed-pad packages, the pad | `theta_JC(bottom)` is the usable junction-to-pad value |
| `psi_JT`, `psi_JB` | characterisation parameters (not resistances) | consistency checks and the calculator (topic 23) |

JESD15-3: for a two-resistor model `theta_JB` and `theta_JC(top)` are the two resistances; `psi_JB` can substitute `theta_JB`; `psi_JT` is not allowed; accuracy "30 % or less". 75 to 95 % of the heat of a package goes through the PCB. A table of typical `theta` by package family is a library (Preferences), and the heater panel offers it.

## 6. How the program does it

`pcbthermal/analysis.py` (`heater_stats`, `part_split`), `api.py` (`_solve_with_tc`), `model.py` (`Heater.theta`, `tj_max`, `psi_jb`, `power_tc`, `role`, `junction_theta`), `docs/theory.md` section 9, `docs/models.md` sections 6 and 13.

## 7. Where it is tested

`docs/validation.md` section 9; `research/component-heatsink/` (prototype: the offset reproduces the CSD17308Q3 datasheet RthetaJA within 2 %); the closed-form fixed point to 0.05 K.

## 8. Related topics

08 (the same `h`), 11 (a block as the heatsink), 12 (the Foster chain for pulses), 13 (`theta_SA` scenarios), 14 and 23 (datasheet boards, the calculator).

## 9. Sources

* JESD15-3 two-resistor guideline: [JESD15-3] (text read). NIST report on 2R, DELPHI: [NISTIR7648]. TI definitions and the 75 to 95 % figure: [TI-SPRA953B]. Renesas: [Renesas-Thermal]. Richtek: [RichtekAN061]. Compact modelling accuracy: [SemiDigest2007], [EC2007Compact]; `R_JB` scatter: [EC1999RJB]; JESD51-14: [EC2024JESD5114]; the standards family: [EC2019JEDEC], [JESD51family].
* The 2R model lacks thermal capacity (RC ladders from transient measurements add it): [Siemens-CTM].
* ROHM's "two-resistor" note is **not** the JESD15-3 definition and is not used: [ROHM-2R-not-used].
* Datasheets read for the parts: [Datasheets]; MOSFET datasheet quantities: [Infineon-AN2012-03]; copper and via resistances: [TI-AN2020].
* Own computation: [L-parts].

*What was read and what was not verified:* equations from `docs/theory.md` section 9 (read in full); the sources marked R were read per `docs/research.md`; the standards were not opened (JESD51 family).
