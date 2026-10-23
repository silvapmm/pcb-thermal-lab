# 27. From datasheet numbers to the model: what each test measures, and the junction node

![Package sections](../../component-heatsink/figures/fig_06_package_sections.png)

*Figure 6 of `research/component-heatsink` (`research/component-heatsink/figures/fig_06_package_sections.png`): sections of a package, with the paths of the heat and the points where the datasheet metrics are measured.*

Also `research/component-heatsink/figures/fig_02_program_top_path_vs_node_prototype.png` (the program's top path against the junction-node prototype) and `fig_05_part_and_top_path_schematic.png`. Investigation: `research/component-heatsink/` (`package_prototype.py`, `component_study.py`); text: `docs/research.md` E3 to E8, R4 and the open "heater as a source or a component". **Status: the junction-to-pad resistance and the top path are implemented; the junction node, `psi` as an output and the Foster chain are not.**

## 1. What each datasheet test measures

| Metric | Test | Physical meaning | Usable here? |
| :-- | :-- | :-- | :-- |
| `theta_JC(top)`, `theta_JC(bot)` | cold plate on the top or bottom face, one heat path | resistance inside the package from the junction to that face (meaningful for a mostly 1D path, `theta_JB / theta_JC` above about 10; an overmolded BGA gave 0.82 against 1.79 K/W by two methods) | **yes**, a package property; the solder, paste or heatsink on that face is ours |
| `theta_JB` | double ring cold plate, heat forced through the board (JESD51-8); board temperature 1 mm from the package edge, or on the lead foot for leaded parts | package resistance **plus part of the test board** for area-array parts | **partly**: only when `theta_JC(bot)` is not given; it over-estimates when our board already spreads the heat |
| `theta_JA` | still air, JEDEC board 1s0P (JESD51-3) or 2s2p (JESD51-7), at least 76 x 114 mm | package + test board + convection together | **not as an input** (manufacturers say so); **yes as a validation target** (topic 14) |
| `psi_JT`, `psi_JB` | same environment as `theta_JA`, with the real heat partition | `delta T / P` between the junction and a measured temperature, **not** a resistance (`psi_JT` typically 0.5 to 2 K/W against `theta_JC` of 4 to 15) | as a post-processing estimate |

**Which resistance goes between the junction and our board.** For the exposed-pad parts of the datasheets read, `theta_JC(bot)` (4.3 and 1.7 K/W) is much smaller than `theta_JB` (13.6 and 11.9 K/W): `theta_JB` includes the spreading in the datasheet's own board, `theta_JC(bot)` stops at the pad. Our model spreads the heat in the real board, so `theta_JB` there would count the spreading twice; JESD15-3 allows replacing `theta_JB` by `theta_JC(bottom)` for exposed-pad packages.

## 2. The 2R model (JESD15-3), three nodes and two resistances

Junction, case and board; two resistances; the die at one temperature; ambient isothermal; power into the junction; single-die packages. DELPHI (JESD15-4) adds surface nodes and shunt resistors for more accuracy, but manufacturers rarely publish them. The standard states that the error of a 2R prediction cannot be known beforehand, that it grows with the difference from the JEDEC test environment, and that published studies show errors on the junction temperature **rise** of about 30 % or less (a guide, not a bound); DELPHI within about 10 %, typically 5 % against detailed models. 2R works best when the heat goes mostly into the board or a heatsink. Block-and-plate construction: an isothermal block the size of the package between two plates whose resistances are `theta_JC,top` and `theta_JB`; the board-side plate has the footprint area, a uniform conductance `1/(theta A)`, which is the program's weighted `G_i = w_i / theta_JB`.

## 3. Three levels of approximation

* **A. Source plus psi** (no new physics): after the simulation `T_j = T_board,ref + psi_JB P` (or `T_top + psi_JT P`), with `T_board,ref` the simulated temperature 1 mm outside the body. Richtek measured 79.9 C with the body-diode method against 79.98 C from `psi_JB` and the board temperature.
* **B. Package (2R)**: a junction node, built as the block-and-plate; needed when a heatsink or a strong top path exists. Error about 30 % or less.
* **C. DELPHI / detailed**: out of scope until the data exist.

## 4. Is the junction node worth it? (prototype on a CSD17308Q3, SON 3.3 x 3.3 mm, `Rth_JC` 4.5 K/W, datasheet board)

| Test | Datasheet | Offset (program) | Node |
| :-- | --: | --: | --: |
| `Rtheta_JA` on 1 in2 of 2 oz copper (1 W) | 46 typical, 58 max | 46.7 | 45.1 |
| `Rtheta_JA` on a 5 mm pad (size assumed) | 165 max | 164.2 | 162.8 |
| Tj at 2 W, 1 in2, no top path | | 112.5 C | 109.4 C |
| 2 W with a 12 K/W heatsink, `theta_JC(top)` 40, 20, 5 K/W (assumed) | | cannot represent | 73.6, 63.4, 51.1 C; 46, 58, 73 % through the top |

* The physics and the one-resistance approach already reproduce the datasheet (`Rtheta_JA` within 2 %).
* **Without a top path the node changes little**: 3 K (3 % of the rise) lower, conservative.
* **With a heatsink on top the answer changes by a factor of two** (112 against 51 to 74 C): that is what justifies the node.
* It depends strongly on `theta_JC(top)`, which this datasheet does not give.

## 5. What real datasheets give (parameter sets differ by part)

(a) `theta_JC,top` + `theta_JB` (TI converters, LDOs: the full 2R set); (b) one resistance to the board or terminal (`theta_JC(bot)` of a MOSFET, `theta_J-L` of a diode, `Rth j-sp` of an LED) and no top path; (c) only `theta_JA` on a stated board (some diodes: the package resistance is `theta_JA` minus what **our** model gives to the stated board); (d) only a power rating at a temperature (resistors: `(T_max - T_rating) / P_rating`, for example 100 K / 0.1 W = 1000 K/W, an order of magnitude to check). `theta_JA` is never an input. Copper weight matters (MOSFET boards are 2 oz, the default is 35 um). LEDs: the heat is `Vf If` minus the light, which is not a datasheet number.

## 6. Other things that may be missing

Packages with several dies (a per-die junction needs one `theta` per die); pulsed operation (topic 12); the ambient inside an enclosure is the user's; the solder under the pad is part of the board side, a fraction of a K/W, ignored.

## 7. Related topics

09, 12, 14, 24, 25.

## 8. Sources

* [JESD15-3] (read), [NISTIR7648], [TI-SPRA953B], [Renesas-Thermal], [RichtekAN061], [SemiDigest2007], [EC2007Compact], [EC2019JEDEC], [EC1999RJB], [EC2024JESD5114], [Siemens-CTM]; the datasheets [Datasheets] and [Infineon-AN2012-03]; [JESD51family] (not read).
* Own computation: [L-parts], [L-calc].

*What was read and what was not verified:* from `docs/research.md` E3 to E8 (read in full); the standards were not opened; the LED row of the datasheet table is from a search summary.
