# 23. The Power calculator: the board model run backwards

![Calculator schematic](../../power-calculator/figures/fig_04_calculator_schematic.png)

*Figure 4 of `research/power-calculator` (`research/power-calculator/figures/fig_04_calculator_schematic.png`): the calculator as a chain from a measured temperature to the power of the part.*

Also `research/power-calculator/figures/fig_05_reading_points_and_copper.png` (the reading points and why the copper dominates the error) and the planned extensions in topic 14. Investigation: `research/power-calculator/README.md`; documentation of the calculator: `docs/calculators.md`. **Status: implemented** (route 1: from the drawn board; route 2: from a datasheet parameter).

## 1. What it is

Given a measured temperature of a part (junction, case or board point), the calculator finds the **power** of the part. The board model is run backwards: the board is **affine in the power** (two runs fix the line), so the unknown power is the intersection of that line with the reading. The reason it is not a datasheet-only formula: `Tj = T_board + psi P` needs `Tj`.

* **From the top of the package**: `Tj = T_top + psi_JT P`, then the junction rise gives `P` through the board resistance and `theta`.
* **Uncertainty band**: best, nominal and worst power from the one-at-a-time effects of the copper (+-25 %), the heat transfer (+-30 %), `theta` (+-20 %), `psi_JT` (+-30 %) and the reading (+-1 K), the downward and the upward deviations each combined as the root of the sum of squares; the selector decides which power is written into the part.
* **Design term** (how well the drawing matches the board): four more one-at-a-time sources, the copper coverage of the outer zones, the copper weight, the inner planes and the via plating, with assumed amplitudes (40, 50, 50, 50 %) times the multiplier of the *Board description* level (None 0, real fabrication files 0.2, drawn by hand 0.5, the default, estimated 1), added by the same rule (`inverse.power_band`, `docs/calculators.md` 1.1c). It brings 2 of the 4 drawing errors of the study inside the band at *Drawn by hand* (a hatched pour, missing vias) and not a copper weight half the real one nor missing inner planes, even at *Estimated*; the amplitudes are judgements, not fitted to data.

## 2. Validation

Against datasheets: the CSD17308Q3 on its own board gives 0.983 W for 1 W (-1.7 %), the JEDEC 2s2p exposed-pad QFN +3.0 % (package data assumed), and the same board without vias 0.48 W (the exposed pad needs the vias). The copper dominates the error (11 to 45 % of the power when the drawn copper differs from the real); the datasheet shortcut `theta_JA - psi_JT` is therefore not offered.

## 3. Limits

Only as good as the drawn board (copper, vias, stack-up, air) and the measurement (a thermocouple that touches the board cools it; an infrared spot is too large for a small part; emissivity of a package top about 0.9, of bare copper 0.05 to 0.1); steady state with constant power; no top-path model in this calculator (use the part's `theta_SA` fields with the simulation).

## 4. Related topics

09, 14 (the known-power reference, the virtual JEDEC test), 21 (vias), 15 (copper from files).

## 5. Sources

* Definitions and estimates of `theta_JC`, `theta_JB`, `psi_JT`, `psi_JB`: [TI-SPRA953B], [Renesas-Thermal], [RichtekAN061]; why `theta_JA` and `psi_JT` change in other applications: [ROHM-65AN114E]; the JEDEC board: [ROHM-64AN113E]; the standards: [JESD51family], [EC2019JEDEC]; one-page references: [Microchip-Thermal].
* Inverse methods and measurement: [Chen-style], [ArXiv2307.08354], [OSTI21026063], [IITPalakkad], [PohankaRaudensky].
* Datasheets: [Datasheets]. Own computation: [L-calc].

*What was read and what was not verified:* from `docs/calculators.md` and `research/power-calculator/README.md` (read in full); the measurement literature is from search summaries.
