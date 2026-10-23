# The part, its top path and its heatsinks: junction temperature, interfaces and metal blocks

Status: **mostly implemented** (θ junction-pad, junction limit, power coefficient, the top path, the interface sheet, the typical heatsink list, the metal block); the junction node (JESD15-3 two-resistor), the heatsink scenarios (θSA with the temperature rise, forced air, fin channel effect) and the Foster chain are **open** (see `INTEGRATION.md`). Investigated from 2026-10-16 to 2026-10-22; moved to this folder on 2026-10-23. The long running notes (what was read, section by section) are in `NOTES.md`.

## 1. The questions

1. What does a Component (a package with a junction resistance) add to a plain heater, on real parts with datasheet numbers?
2. Is a junction node worth it, or is a worst-case offset enough?
3. What does a top path (θJC(top), paste, heatsink) change, and how well does the program's fixed-point loop reproduce a junction-node network?
4. What do the interface material, the metal of a block under the board and the base of a heatsink matter?
5. How should a heatsink known only by its sink-to-ambient resistance behave (natural-convection scaling, forced air)?

## 2. Findings in short

* The junction-to-pad resistance adds a **worst-case offset** `Tj = T_board,max + P·θ`: 2.5 to 10 K on the four real parts (2 to 28 % of the rise above ambient, more on a 25 mm pad than on an 8 mm one), and 100 K on a 0603 resistor (θ = 1000 K/W, 88 to 94 % of the rise).
* A bare mould carries about **1 %** of the heat (0.6 to 1.4 %); a 12 K/W clip-on heatsink with paste takes **41 to 51 %** and lowers `Tj` by 16 to 40 K. So a junction node is only worth it with a heatsink on top.
* The program's fixed-point top path (`api._solve_with_tc`, steady state) is within **0.4 to 0.8 K** of a junction-node prototype on the four parts.
* Under the board the **interface** moves `Tj` by about 2 K and the **metal** by about 1 K; on top of a small package the interface and the base spreading matter more (steel 1 mm base adds 6 K/W of spreading against 0.9 for copper).
* With a heatsink known only by θSA, natural-convection scaling with the temperature rise changes `Tj` by 1 to 3 K from 0.5 to 4 W (fixed 12 K/W against a resistance of 24 K/W at 0.5 W to 15 K/W at 4 W) and forced air lowers it by 5 to 7 K; the factors are from a guide (Electronics Cooling, 1995), not verified against a datasheet (see the typical-heatsink list in `docs/models.md` and `docs/research.md` R3 in `NOTES.md`).
* Power rising with temperature (positive coefficient) can run away: 2 W at 25 °C with 0.67 %/K gives 210 °C and 4.5 W.

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `component_study.py` | Real parts (CSD17308Q3, TPS7A47, LMR36510, SS12, a 0603 resistor) at three levels: plain heater, junction offset, top path. |
| `package_prototype.py` | A MOSFET as a simple heater and as a junction node, outside the program. |
| `top_path_study.py` | The program's top path against the junction-node prototype on the four chips. |
| `chain_study.py` | Several levels in one chain: junction, pad, board, interface, metal block, package top, interface, heatsink. |
| `heatsink_study.py` | Top heatsink with different pastes and pads; block under the board by metal and interface. |
| `heatsink_convection_study.py` | A heatsink known only by its resistance: fixed, natural scaling, forced convection. |
| `base_spreading_study.py` | The extra resistance of a heatsink base for a small component (3D conduction). |
| `block_contact_study.py` | A plate model against a published spreading example; a big block touching the board only in a patch; temperature-dependent power. |
| `make_figures.py` | Draws the four figures (about 1.5 minutes). |
| `figures/` | `fig_01` to `fig_04`. |
| `NOTES.md` | The running research notes of `docs/research.md` (what was read, what was simulated, open questions). |
| `INTEGRATION.md`, `LOG.md` | What entered the program and what is open; what was read and how. |

## 4. How to run, and the results

Every study is run from the repository root, for example `.venv/bin/python research/component-heatsink/component_study.py` (each takes 2 to 40 seconds). The outputs below were produced on 2026-10-23.

### 4.1 Real parts at three levels (`component_study.py`)

A. What the junction-to-pad resistance adds (level 1 against level 0), natural convection, 60 x 60 mm board
| Part | P [W] | theta [K/W] | Pad | Level 0: board under part [degC] | Level 1: Tj [degC] | P*theta [K] | Share of the rise | Tj max |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 2 | 4.5 | 8 mm | 227.4 | 236.4 | 9.0 | 4 % | 150 |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 2 | 4.5 | 25 mm | 98.6 | 107.6 | 9.0 | 11 % | 150 |
| LDO TPS7A47 (QFN-20 5x5) | 1.5 | 1.7 | 8 mm | 176.7 | 179.2 | 2.5 | 2 % | 150 |
| LDO TPS7A47 (QFN-20 5x5) | 1.5 | 1.7 | 25 mm | 84.8 | 87.3 | 2.5 | 4 % | 150 |
| Buck LMR36510 (HSOIC-8) | 0.8 | 4.3 | 8 mm | 109.9 | 113.3 | 3.4 | 4 % | 150 |
| Buck LMR36510 (HSOIC-8) | 0.8 | 4.3 | 25 mm | 59.3 | 62.8 | 3.4 | 9 % | 150 |
| Schottky SS12 (SMA) | 0.5 | 20 | 8 mm | 85.6 | 95.6 | 10.0 | 14 % | 150 |
| Schottky SS12 (SMA) | 0.5 | 20 | 25 mm | 50.9 | 60.9 | 10.0 | 28 % | 150 |
| Resistor 0603, 0.1 W | 0.1 | 1000 | 8 mm | 38.9 | 138.9 | 100.0 | 88 % | - |
| Resistor 0603, 0.1 W | 0.1 | 1000 | 25 mm | 31.6 | 131.6 | 100.0 | 94 % | - |

B. Wrong number from the datasheet: theta_JB instead of theta_JC(bottom) (pad 25 mm)
| Part | theta_JC(bot) [K/W] | Tj | theta_JB [K/W] | Tj with theta_JB | Difference |
| :-- | --: | --: | --: | --: | --: |
| LDO TPS7A47 (QFN-20 5x5) | 1.7 | 87.3 | 11.9 | 102.6 | +15.3 K (+25 % of the rise) |
| Buck LMR36510 (HSOIC-8) | 4.3 | 62.8 | 13.6 | 70.2 | +7.4 K (+20 % of the rise) |

C. Sensitivity to the theta entered (+-30 %, pad 25 mm)
| Part | Tj nominal | Tj at -30 % | Tj at +30 % |
| :-- | --: | --: | --: |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 107.6 | 104.9 (-2.7 K) | 110.3 (+2.7 K) |
| LDO TPS7A47 (QFN-20 5x5) | 87.3 | 86.6 (-0.8 K) | 88.1 (+0.8 K) |
| Buck LMR36510 (HSOIC-8) | 62.8 | 61.7 (-1.0 K) | 63.8 (+1.0 K) |
| Schottky SS12 (SMA) | 60.9 | 57.9 (-3.0 K) | 63.9 (+3.0 K) |
| Resistor 0603, 0.1 W | 131.6 | 101.6 (-30.0 K) | 161.6 (+30.0 K) |

D. A top path (level 2): bare mould (theta_JC(top) + convection on the body) and with a 12 K/W clip-on heatsink + 1 K/W paste (pad 25 mm)
| Part | Level 1 Tj | Bare mould Tj (heat through top) | With heatsink Tj (heat through top) | theta_JC(top) [K/W] |
| :-- | --: | --: | --: | --: |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 107.6 | 104.6 (0.6 %) | 67.4 (49 %) | 30 (assumed) |
| LDO TPS7A47 (QFN-20 5x5) | 87.3 | 83.2 (1.4 %) | 55.5 (51 %) | 27 |
| Buck LMR36510 (HSOIC-8) | 62.8 | 60.6 (1.3 %) | 46.9 (41 %) | 54 |
| Schottky SS12 (SMA) | 60.9 | 59.1 (1.1 %) | 42.9 (49 %) | 60 (assumed) |

![Parts with and without a top path](figures/fig_01_parts_with_and_without_top_path.png)

*Figure 1: `figures/fig_01_parts_with_and_without_top_path.png`.*

### 4.2 The program's top path against a junction node (`top_path_study.py`)

Top path: theta_JC(top) of the part + 0.5 K cm2/W paste + 12.0 K/W heatsink; pad 25 mm, computed h, FVM at 0.5 mm
| Part | Tj without top path | Tj program | Top share program | Tj node prototype | Top share prototype |
| :-- | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 107.6 | 69.8 | 48 % | 69.0 | 47 % |
| LDO TPS7A47 (QFN-20 5x5) | 87.4 | 56.6 | 51 % | 55.8 | 50 % |
| Buck LMR36510 (HSOIC-8) | 62.8 | 47.8 | 41 % | 47.1 | 40 % |
| Schottky SS12 (SMA) | 60.9 | 43.7 | 49 % | 43.3 | 48 % |

![Program top path against the node prototype](figures/fig_02_program_top_path_vs_node_prototype.png)

*Figure 2: `figures/fig_02_program_top_path_vs_node_prototype.png`.*

### 4.3 The prototype (`package_prototype.py`)

```
A. The datasheet's own test: RthJA on the test board (1 W)
   datasheet: typical 46, maximum 58 K/W on 1 in2; maximum 165 K/W on the minimum pad

   board                        model        Tj   RthJA   Tfoot
   1 in2 pad (25.4 mm)          offset     71.7    46.7    67.2
   1 in2 pad (25.4 mm)          node       70.1    45.1    66.8
   5 mm pad (minimum, assumed)  offset    189.2   164.2   184.7
   5 mm pad (minimum, assumed)  node      187.8   162.8   184.3

B. A real use: 2 W in the FET on the 1 in2 pad, without and with a heat heatsink on the package top
   case                                         model        Tj  Tj<=150?  top share
   no top path                                  offset    112.5       yes       0.0 %
   no top path                                  node      109.4       yes       0.0 %
   bare mould: 30 K/W + 15 W/m2K on 3.3 mm (assumed) node      108.9       yes       0.7 %
   heat heatsink 12 K/W, theta_JC(top) = 40 (assumed) node       73.6       yes      45.8 %
   heat heatsink 12 K/W, theta_JC(top) = 20 (assumed) node       63.4       yes      58.2 %
   heat heatsink 12 K/W, theta_JC(top) = 5 (assumed) node       51.1       yes      72.6 %
   good heat heatsink 4 K/W, theta_JC(top) = 20 (assumed) node       57.6       yes      65.1 %

C. Sensitivity to the junction-to-pad resistance (2 W, 1 in2 pad, no top path)
   theta =  1.1 K/W   Tj =  101.9 degC   footprint  101.1
   theta =  4.5 K/W   Tj =  109.4 degC   footprint  102.6
   theta =  8.0 K/W   Tj =  116.5 degC   footprint  103.0
```

### 4.4 Several levels in one chain (`chain_study.py`)

MOSFET CSD17308Q3 (SON 3.3x3.3), 2 W, pad 25 mm, h = 14.6 / 10.3 W/m2K; top chain = theta_JC(top) 30 + paste 4.6 + heatsink 12 = 46.6 K/W
| Case | Tj [degC] | heat through the top | heat through the block |
| :-- | --: | --: | --: |
| board only | 105.0 | 0 % | 0 % |
| + block 30x30x3 mm, paste 0.5 | 95.6 | 0 % | 27 % |
| + block, gap pad 5 K cm2/W | 96.7 | 0 % | 28 % |
| + top heatsink with paste | 68.1 | 46 % | 0 % |
| + both (block with paste and top heatsink) | 65.2 | 43 % | 16 % |

LDO TPS7A47 (QFN-20 5x5), 1.5 W, pad 25 mm, h = 14.0 / 9.9 W/m2K; top chain = theta_JC(top) 27 + paste 2.0 + heatsink 12 = 41.0 K/W
| Case | Tj [degC] | heat through the top | heat through the block |
| :-- | --: | --: | --: |
| board only | 84.0 | 0 % | 0 % |
| + block 30x30x3 mm, paste 0.5 | 72.0 | 0 % | 28 % |
| + block, gap pad 5 K cm2/W | 74.4 | 0 % | 28 % |
| + top heatsink with paste | 55.1 | 49 % | 0 % |
| + both (block with paste and top heatsink) | 51.6 | 43 % | 16 % |

### 4.5 Top heatsink pastes and pads, block metals and interfaces (`heatsink_study.py`)

E. Heatsink on top of the package (12 K/W), different interface materials (pad 25 mm)
| Part | no heatsink | good paste (1.5 W/mK apparent, 50 um) [0.33 K cm2/W] | paste, typical default (2 W/mK, 100 um) [0.50 K cm2/W] | soft gap pad (3 W/mK, 0.5 mm) [1.67 K cm2/W] | gap pad (1 W/mK, 0.5 mm) [5.00 K cm2/W] | hard gap pad (1 W/mK, 1 mm) [10.00 K cm2/W] |
| :-- | --: | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 (SON 3.3x3.3) | 107.6 | 68.4 (48 %) | 69.0 (47 %) | 73.1 (42 %) | 81.0 (32 %) | 87.5 (23 %) |
| LDO TPS7A47 (QFN-20 5x5) | 87.3 | 55.6 (51 %) | 55.8 (50 %) | 57.4 (47 %) | 61.2 (41 %) | 65.1 (34 %) |
| Buck LMR36510 (HSOIC-8) | 62.8 | 47.0 (41 %) | 47.1 (40 %) | 47.8 (38 %) | 49.5 (33 %) | 51.4 (28 %) |
| Schottky SS12 (SMA) | 60.9 | 43.2 (48 %) | 43.3 (48 %) | 44.4 (45 %) | 46.9 (38 %) | 49.4 (30 %) |

F. MOSFET CSD17308Q3 (SON 3.3x3.3), 2 W, 3 mm block 30 x 30 mm under the board: Tj [degC] by metal (rows) and interface (columns); block face in natural convection
| Metal | no block | good paste (1.5 W/mK apparent, 50 um) [0.33] | paste, typical default (2 W/mK, 100 um) [0.50] | soft gap pad (3 W/mK, 0.5 mm) [1.67] | gap pad (1 W/mK, 0.5 mm) [5.00] | hard gap pad (1 W/mK, 1 mm) [10.00] |
| :-- | --: | --: | --: | --: | --: | --: |
| aluminium | 107.6 | 98.4 | 98.5 | 98.9 | 99.6 | 100.3 |
| copper | 107.6 | 98.3 | 98.4 | 98.8 | 99.6 | 100.3 |
| brass | 107.6 | 98.4 | 98.5 | 98.9 | 99.6 | 100.4 |
| carbon steel | 107.6 | 98.6 | 98.7 | 99.1 | 99.7 | 100.4 |
| stainless 304 | 107.6 | 99.3 | 99.3 | 99.6 | 100.1 | 100.7 |

![Block metal and interface](figures/fig_04_block_metal_and_interface.png)

*Figure 4: `figures/fig_04_block_metal_and_interface.png`.*

### 4.6 Heatsink scenarios: natural scaling and forced air (`heatsink_convection_study.py`)

MOSFET, top heatsink 12 K/W catalogue value at a 75 K rise, default paste; fixed resistance against natural-convection scaling (Tj in degC, sink resistance in K/W)
| Power [W] | fixed 12 K/W | natural scaling: Tj | sink R used | heat through the top |
| --: | --: | --: | --: | --: |
| 0.5 | 35.8 | 36.9 | 23.8 | 41 % |
| 1 | 46.5 | 48.2 | 20.6 | 42 % |
| 2 | 68.1 | 70.4 | 17.8 | 43 % |
| 3 | 89.6 | 92.3 | 16.4 | 44 % |
| 4 | 111.1 | 113.9 | 15.4 | 44 % |

Same heatsink (12 K/W natural, 2 W) in forced convection (factors of the volumetric performance)
| Air | sink R used [K/W] | Tj [degC] | heat through the top |
| :-- | --: | --: | --: |
| natural | 17.8 | 70.4 | 43 % |
| 1 m/s | 6.8 | 65.7 | 49 % |
| 2.5 m/s | 4.4 | 64.5 | 51 % |
| 5 m/s | 2.7 | 63.6 | 52 % |

Size to resistance (volumetric performance 500-800 cm3 K/W natural): heatsink volume for a given resistance
| Volume [cm3] | natural R [K/W] | 1 m/s | 2.5 m/s | 5 m/s |
| --: | --: | --: | --: | --: |
| 5 | 100 to 160 | 30 to 50 | 16.0 to 30.0 | 10.0 to 16.0 |
| 10 | 50 to 80 | 15 to 25 | 8.0 to 15.0 | 5.0 to 8.0 |
| 20 | 25 to 40 | 8 to 12 | 4.0 to 7.5 | 2.5 to 4.0 |
| 50 | 10 to 16 | 3 to 5 | 1.6 to 3.0 | 1.0 to 1.6 |

![Heatsink convection scenarios](figures/fig_03_heatsink_convection_scenarios.png)

*Figure 3: `figures/fig_03_heatsink_convection_scenarios.png`.*

### 4.7 The base of a heatsink (`base_spreading_study.py`)

Extra resistance of a 40 x 40 mm heatsink base (catalogue 12 K/W) for a small component, K/W (mean over the source); share of the top chain in brackets
| Base | 3.3 mm source (chain 46.6 K/W) | 5 mm source (chain 41 K/W) |
| :-- | --: | --: |
| aluminium 1 mm | 1.69 (3.6 %) | 1.32 (3.2 %) |
| aluminium 3 mm | 0.75 (1.6 %) | 0.54 (1.3 %) |
| aluminium 6 mm | 0.54 (1.2 %) | 0.38 (0.9 %) |
| copper 1 mm | 0.90 (1.9 %) | 0.70 (1.7 %) |
| copper 3 mm | 0.40 (0.9 %) | 0.29 (0.7 %) |
| copper 6 mm | 0.29 (0.6 %) | 0.20 (0.5 %) |
| carbon steel 1 mm | 6.31 (13.5 %) | 4.90 (12.0 %) |
| carbon steel 3 mm | 2.83 (6.1 %) | 2.04 (5.0 %) |
| carbon steel 6 mm | 2.05 (4.4 %) | 1.44 (3.5 %) |

### 4.8 A block larger than its contact, and power rising with temperature (`block_contact_study.py`)

1. Plate against Lee et al.: maximum constriction resistance 0.69 K/W (paper 0.66), total 1.69 K/W (paper 1.66)

2. MOSFET 2 W, Al block 40 x 40 x 3 mm under the board, contact only in a centred patch (default interface 5 K cm2/W)
| Contact patch | Tj [degC] |
| :-- | --: |
| whole block (40 x 40) | 87.8 |
| 25 x 25 mm | 96.6 |
| 12 x 12 mm | 97.0 |
| 6 x 6 mm | 99.5 |
| none | 124.3 |

2b. The same with an air gap outside the patch (conduction + radiation; gap in mm, block bare aluminium, emissivity 0.1)
| Gap outside the contact | patch 25 mm | 12 mm | 6 mm | none |
| :-- | --: | --: | --: | --: |
| insulated (board face hidden, as above) | 96.6 | 97.0 | 99.5 | 124.3 |
| 0.5 mm  (h = 57 W/m2K) | 92.2 | 93.2 | 95.7 | 101.7 |
| 1 mm  (h = 29 W/m2K) | 93.7 | 94.5 | 97.3 | 106.1 |
| 2 mm  (h = 15 W/m2K) | 94.8 | 95.5 | 98.2 | 110.5 |
| 5 mm  (h = 6 W/m2K) | 95.7 | 96.3 | 98.9 | 115.6 |

3. MOSFET 2 W (at 25 C) with the power rising with temperature (pad 25 mm, no top path)
| alpha [%/K] | Tj [degC] | power at Tj [W] |
| --: | --: | --: |
| 0.00 | 107.6 | 2.00 |
| 0.33 | 138.6 | 2.75 |
| 0.50 | 165.8 | 3.41 |
| 0.67 | 210.0 | 4.48 |

### 4.9 The junction temperature in the program (validation)

`python research/component-heatsink/component_study.py`, `research/component-heatsink/block_contact_study.py` (power coefficient) and `tests/test_component.py`. Five parts of the datasheets read on 2026-10-17 (`docs/models.md` section 6) on a 60 × 60 mm, 2-layer board with a copper pad under the part on both faces (vias under footprints of 3 mm and more), computed natural convection, FVM at 0.5 mm. Level 0 is the plain source (the hottest board point under the part); level 1 adds θ.

| Part | P [W] | θ [K/W] | Pad | Board under part | Tj | P·θ | Share of the rise |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 2 | 4.5 | 8 mm | 227.4 °C | 236.4 °C | 9.0 K | 4 % |
| MOSFET CSD17308Q3 | 2 | 4.5 | 25 mm | 98.6 °C | 107.6 °C | 9.0 K | 11 % |
| LDO TPS7A47 | 1.5 | 1.7 | 8 mm | 176.7 °C | 179.2 °C | 2.5 K | 2 % |
| LDO TPS7A47 | 1.5 | 1.7 | 25 mm | 84.8 °C | 87.3 °C | 2.5 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 8 mm | 109.9 °C | 113.3 °C | 3.4 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 25 mm | 59.3 °C | 62.8 °C | 3.4 K | 9 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 8 mm | 85.6 °C | 95.6 °C | 10.0 K | 14 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 25 mm | 50.9 °C | 60.9 °C | 10.0 K | 28 % |
| Resistor 0603 | 0.1 | 1000 (derived) | 8 mm | 38.9 °C | 138.9 °C | 100 K | 88 % |
| Resistor 0603 | 0.1 | 1000 (derived) | 25 mm | 31.6 °C | 131.6 °C | 100 K | 94 % |

* **Sensitivity** (pad 25 mm): θ ±30 % moves `Tj` by ±0.8 K (LDO), ±1.0 K (buck), ±2.7 K (MOSFET), ±3.0 K (diode) and ±30 K (resistor, where the derived number is the whole answer).
* **The number chosen matters more than its accuracy**: `θJB` instead of `θJC(bot)` gives 102.6 against 87.3 °C (LDO) and 70.2 against 62.8 °C (buck).
* **`ψJB` route** (`Tj = T_ring + ψJB·P`, ring 0.5 to 1.5 mm outside the body, pad 25 mm): LDO 93.7 °C and buck 65.1 °C against 87.4 and 62.8 °C with `θJC(bot)`; with `θJB` as θ 102.7 and 70.2 °C.
* **Datasheet check** (CSD17308Q3, 1 W on its own board of 1 in² of 2 oz copper, computed natural convection): `RθJA` 46.7 K/W against the datasheet's typical 46 and maximum 58; on a minimum pad of 5 mm (assumed size) 164 against the maximum 165 K/W.
* **Power temperature coefficient** against the closed form `ΔT = P0 R/(1 − tc P0 R)` on a linear board (the FVM, Lumped and Analytic models, `tests/test_component.py`): agreement to 0.05 K; for the MOSFET 2 W at 25 °C (107.6 °C without feedback) the junction reaches 138.6, 165.8 and 210 °C for 0.33, 0.5 and 0.67 %/K, with the power rising to 2.75, 3.41 and 4.48 W; a coefficient of 3 %/K has no stable point and the program says so.
* **Top path** (`python research/component-heatsink/top_path_study.py`, `tests/test_component.py`; θJC(top) of the part, 0.5 K·cm²/W paste, 12 K/W clip-on heatsink, pad 25 mm): the heatsink takes 41 to 51 % of the heat and lowers `Tj` of the chips by 15 to 38 K. Against the junction-node prototype of `research/component-heatsink/package_prototype.py` (uniform conductance under the footprint) the program is 0.4 to 0.8 K higher and the top share differs by one point.

| Part | Tj without top path | Tj program | Top share | Tj node prototype | Top share |
| :-- | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 107.6 | 69.8 | 48 % | 69.0 | 47 % |
| LDO TPS7A47 | 87.4 | 56.6 | 51 % | 55.8 | 50 % |
| Buck LMR36510 | 62.8 | 47.8 | 41 % | 47.1 | 40 % |
| Schottky SS12 (SMA) | 60.9 | 43.7 | 49 % | 43.3 | 48 % |

  The series-parallel closure is exact (`Tj − T_amb = R_top·P_top`, `P_top + P_board = P`, test to 1e-4) and the FVM, FDM, Lumped and Analytic models agree on `Tj` within 10 % of its rise.
* **Limits of the approach**: worst case without `theta_sa` (no heat through the top of the package); `θ` is a single number for the whole junction; the junction is the hottest board point under the footprint plus `P·θ` (about 3 K above a junction node with a uniform conductance, which is the conservative side).

## 5. Limits of this study

* No measurement of a physical board or part: all numbers are model against model, with datasheet inputs; entries marked *assumed* (θJC(top) of the MOSFET and the Schottky, the pad of some parts, a bare-mould coefficient of 15 W/m²K) are not from a datasheet.
* The top path is steady state only; the junction has no capacity (no Foster chain); the interface has no area of its own other than the contact area field.
* The natural-convection scaling and the forced-air factors come from a guide and a few catalogue values, not from a verified heatsink model; the fin channel effect is not modelled.
* Five parts only; a 0603 resistor shows how strongly a large θ moves the result (100 K at 0.1 W).

## 6. Sources

See `NOTES.md` (the references of every section, from JEDEC-based application notes of TI, Renesas, Richtek, ROHM and Microchip to the heatsink catalogues) and `docs/models.md` for the typical-heatsink list. Where a source was only seen in a search summary, `NOTES.md` says so.
