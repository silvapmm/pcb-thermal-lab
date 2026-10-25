# The metal block and its fins: models and verification

Status: **implemented** in the program (see the program's `docs/versions.md` and `docs/validation.md`). Studies: `fin_validation.py` and `block_equivalent_study.py`; figures: `make_figures.py`.

## 1. The questions

1. Is the formula that replaces the fins of a metal block by an area gain and an efficiency right?
2. Can the Lumped and Analytic models represent a metal block (a heat spreader under the board), and with what error against the FVM, which solves it natively?

### 1.1 Diagrams and illustrations

![The metal block and its fins as schematics](figures/fig_04_block_and_fins_schematic.png)

*Figure 4 (`figures/fig_04_block_and_fins_schematic.png`): The metal block and its fins as schematics: 1, the block under the board and the heat path; 2, the same path as thermal resistances (the board faces in parallel); 3, the efficiency of a fin as a function of mL, with the range of the 24 validated cases shaded; 4, the three ways of representing a block in the Lumped and Analytic models, with their mean error against the FVM.*

![Figure 5](figures/fig_05_block_section.png)

*Figure 5 (`figures/fig_05_block_section.png`): the section of a board on a finned metal block (the part, the board, the interface patch, the block, the fins) and one plate fin with the temperature falling along it; the efficiency range and the 0.08 % are those of section 2.*

## 2. Findings in short

* The fin formula (`blocks.fin_ratio`) agrees with a 2D conduction solution of one fin to within 0.08 % in 24 cases (four metals, three coefficients, two fin sizes, efficiencies 0.27 to 0.997). What is **not** validated is the coefficient itself on a real fin array (channel effect between fins).
* An equivalent coefficient (with a contact area and an annular fin) is 9 to 11 % off on average in the Lumped and Analytic models; the block as one more layer of the ring network (Lumped) and as a Schur-complement tile graph in the Green-function correction (Analytic) is 1.9 % and 1.1 % off on average (maxima 4.7 % and 4.3 %), on 74 cases.
* The FVM, FDM and 3D solid agree within 1 % on a finned block, because they use the same fin ratio.
* The temperature drop across the block's own thickness (the layered models keep one node per layer) is checked by the program's thick-plate warning (`checks.check_thick_plates`, `docs/validation.md` section 22) with the flux that really enters the block: over these same 74 cases it is 0.07 % of the rise at the median and 0.34 % at most, none above the 5 % limit, so the warning does not fire on them (numbers taken from that section; this folder's scripts were not changed to reproduce them).

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `scripts/fin_validation.py` | The fin formula against a 2D finite-volume solution of one fin (24 cases). |
| `scripts/block_equivalent_study.py` | Three approaches to the block in the Lumped and Analytic models against the FVM, on 74 cases. |
| `scripts/make_figures.py` | Draws the three figures (runs both studies and reads what they print). |
| `scripts/make_diagrams.py` | Draws the schematic diagram and the illustration (figures 4 and 5; no data, no program; uses `research/diagram_kit.py`). |
| `figures/` | `fig_01` to `fig_05`; figures 4 and 5 are the diagram and the illustration (`make_diagrams.py`). |

## 4. How to run, and the results

```sh
.venv/bin/python research/block-and-fins/scripts/fin_validation.py            # under a second
.venv/bin/python research/block-and-fins/scripts/block_equivalent_study.py    # about 15 seconds
.venv/bin/python research/block-and-fins/scripts/make_figures.py
```

### 4.1 The fins against a 2D fin

`python research/block-and-fins/scripts/fin_validation.py` (and `tests/test_fin_model.py`). The program replaces the fins by an area gain and an efficiency (`blocks.fin_ratio`): per unit of base area `(1 − t/p) + 2 Hc η/p`, `Hc = H + t/2`, `η = tanh(m Hc)/(m Hc)`, `m = √(2h/(k t))` (straight fin, convecting tip taken as an adiabatic tip at the corrected length; Incropera and DeWitt). Here the same fin is solved as a two-dimensional conduction problem (width `t`, height `H`, root at 1 K, convection `h` on both faces and on the tip, 12 × 240 finite volumes), which keeps the transverse temperature drop and the real tip.

| Metal | k (W/mK) | h (W/m²K) | fin | efficiency | 2D (W/m/K) | formula (W/m/K) | difference |
| :-- | --: | --: | :-- | --: | --: | --: | --: |
| aluminium | 204 | 10 | 1.5 × 15 mm | 0.995 | 0.3133 | 0.3133 | +0.00 % |
| aluminium | 204 | 100 | 1 × 30 mm | 0.777 | 4.7395 | 4.7397 | +0.00 % |
| copper | 386 | 30 | 1 × 30 mm | 0.954 | 1.7466 | 1.7466 | +0.00 % |
| carbon steel | 50 | 100 | 1 × 30 mm | 0.497 | 3.0311 | 3.0315 | +0.01 % |
| stainless | 14 | 100 | 1.5 × 15 mm | 0.593 | 1.8668 | 1.8683 | +0.08 % |
| stainless | 14 | 100 | 1 × 30 mm | 0.274 | 1.6702 | 1.6710 | +0.05 % |

All 24 cases of the script (four metals, h = 10, 30, 100 W/m²K, two fin sizes, efficiencies from 0.27 to 0.997) are within 0.08 %. So **the fin formula is right for a fin with a uniform coefficient**; what is not validated is the coefficient itself.

**What is not validated** (the honest limits): (1) the coefficient on a real fin array is not the flat-plate `h` of the board face: between close fins the air in a channel is slower and the fins preheat each other, which Elenbaas (1942) and Bar-Cohen and Rohsenow (1984) describe with an optimum spacing and a channel Rayleigh number; the program ignores this and only warns below 4 mm of air gap in still air, so a closely spaced array is optimistic; (2) the 3D solid uses the same fin ratio, so it does not test the fins independently; (3) no comparison with a measured heatsink or a manufacturer's θSA curve was made (the searches found fin-efficiency equations and worked examples but no datasheet with the dimensions needed). To do: a channel correlation (roadmap) and a comparison with θSA of catalogue extrusions.

![Fin formula against the 2D solution](figures/fig_01_fin_formula_against_2d.png)

*Figure 1: `figures/fig_01_fin_formula_against_2d.png`.*

### 4.2 The block in the Lumped and Analytic models

`python research/block-and-fins/scripts/block_equivalent_study.py` compares the Lumped and Analytic models with the FVM, which has the block, on 74 cases: four block and pad geometries (a 30 × 30 pad in a 60 × 60 block, 50 × 40 in 90 × 70, pad equal to the 40 × 40 block, 20 × 20 in 80 × 60), blocks of 1, 3 and 6 mm of aluminium, 3 mm of copper, 1 and 3 mm of steel, interface 1, 5 and 20 K·cm²/W, and two finned blocks (15/1.5/8 mm). Error: difference of the maximum temperature divided by the FVM rise, in percent (negative = too cool).

| Approach | Lumped mean / max | Analytic mean / max |
| :-- | --: | --: |
| earlier equivalent coefficient (isothermal block over the whole polygon) | 15.6 / 31.4 | 17.3 / 31.5 |
| equivalent coefficient on the copper contact area plus an annular fin for the block outside it | 8.8 / 18.8 | 11.0 / 19.7 |
| **implemented**: Lumped: block layer in the ring network; Analytic: tile graph (Schur complement) in the Green-function correction | **1.9 / 4.7** | **1.1 / 4.3** |

* Why the coefficient approaches fail: they are too hot, and more so with a thicker or better-conducting block (+13 % for 1 mm, +19 % for 6 mm of aluminium on the 30 × 30 pad): the block spreads the heat of the centre of the pad to the whole pad, which a uniform coefficient cannot do. The implemented versions keep the lateral conduction `k t` of the block.
* The finned blocks are at −1.5 % (Lumped) and −0.1 % (Analytic). Typical cases: 30 × 30 pad in a 60 × 60 block, 3 mm of aluminium, 5 K·cm²/W: FVM rise 90.0 K, Lumped −2.2 %, Analytic −1.1 %.
* Limits: steady state only (the capacity of the block is in the ring sums but no transient with a block was tested, and the time simulation refuses it); a rectangular block and rectangular copper pads were tested, a block over scattered copper not; the Analytic keeps its own weak spots (copper that is far from uniform around the heater).
* Sources: static condensation / Schur complement as used by finite-element codes (MFEM documentation, https://docs.mfem.org/4.6/staticcond_8hpp_source.html) and Kron reduction of a network (https://arxiv.org/pdf/2204.05554); the annular-fin efficiency tested in the coefficient approach (Incropera and DeWitt; https://scipython.com/books/book2/chapter-8-scipy/problems/heat-dissipation-of-an-annular-fin-heatsink/); spreading resistance of a heat sink base plate, Lee, Song, Au and Moran (1995), https://www.electronics-cooling.com/1998/01/calculating-spreading-resistance-in-heat-sinks/ (its formulas could not be read and were not used); hybrid analytical models of the PCB, Zhang and Chen, PLOS ONE (2024), https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0310237.

![Block approaches in the Lumped and Analytic models](figures/fig_02_block_approaches.png)

*Figure 2: `figures/fig_02_block_approaches.png`.*

![Error of every case](figures/fig_03_block_error_per_case.png)

*Figure 3: `figures/fig_03_block_error_per_case.png`.*

The numbers of this table were re-run on the current program (`develop` at its latest commit; the cause was not traced, the errors against the FVM moved by up to 0.1 point, so the earlier 15.5 / 31.3, 8.8 / 18.7 and 2.0 / 4.8 are now 15.6 / 31.4, 8.8 / 18.8 and 1.9 / 4.7; the Analytic columns are unchanged). `docs/validation.md` section 17 still quotes the earlier values.

### 4.3 A finned block in every model

**D. Finned metal block** (60 × 40 mm two-layer board, 3 W part, aluminium block 40 × 30 mm on the bottom face, 5e-5 m²K/W interface, typed 10 W/m²K; rise of the hottest point in K):

| Block | Fin ratio at 10 W/m²K | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| plain plate 3 mm | 1.0 | 88.3 | 88.2 | 88.9 | 100.3 | 99.8 |
| fins 15 × 1.5 mm, pitch 8 mm | 4.7 | 61.2 | 61.2 | 61.7 | 72.1 | 69.4 |
| fins 15 × 1.5 mm, pitch 12 mm | 3.5 | 66.4 | 66.3 | 66.8 | 77.8 | 75.5 |
| fins 30 × 1.5 mm, pitch 8 mm | 8.4 | 53.2 | 53.2 | 53.6 | 62.4 | 59.3 |

The FVM, the FDM and the 3D solid agree within 1 % on a finned block (the same fin ratio in all three); the lumped and analytic models were 10 to 13 % high on a board with a block (they replaced it by an equivalent coefficient) and now they have the block as a ring layer and as a tile graph, 1 to 2 % off on average (section 17; section 15 for the fins).

### 4.4 The thick-plate check on the same 74 cases

The program warns when `q'' t / (2 k)` over the rise of the heater exceeds 5 % (a thick, poorly conducting plate under a source: the surface under the source is hotter than the node of the layered models by up to that amount). On these 74 cases (2 mm cells, FVM rise) the criterion with the flux that really enters the block, read from the solution, is **median 0.07 %, maximum 0.34 %**, no case above 5 % (`docs/validation.md` section 22; FVM 1 mm and FDM 2 mm give the same 0.07 / 0.34 %). The flux over the pad at a rise of 90 K, used in `research/effective-conductivity`, gives 0.04 / 0.42 %, and the power over the footprint 0.50 / 1.78 %. The flux that enters the block is 8 to 22 % of the footprint flux on these cases (1 to 3 % under a 2 or 3 mm part), because a block under the board is fed through the laminate and the copper, which spread the heat. These numbers come from the program's own section; this folder's scripts do not compute them.

## 5. Limits of this study

* The fin formula is checked against a 2D solution of a straight fin with a uniform coefficient, not against a measured heatsink or a manufacturer's θSA curve; the 3D solid uses the same fin ratio, so it does not test the fins independently.
* The channel effect between close fins (Elenbaas 1942; Bar-Cohen and Rohsenow 1984) is not modelled: a closely spaced array is optimistic. The program only warns below 4 mm of air gap in still air.
* Steady state only for the Lumped and Analytic block models; rectangular blocks and rectangular copper pads were tested, a block over scattered copper not.
* No measurement of a physical board.

## 6. Sources

Incropera and DeWitt (fin efficiency, straight fin with a corrected length); static condensation and Kron reduction of a network (references in section 4.2); Elenbaas (1942) and Bar-Cohen and Rohsenow (1984) for the channel effect, known from the searches and not read in full. See `docs/validation.md` sections 15 and 17 for the other addresses.

## What was read and what was not verified

* Not verified: no measured heatsink; the fin array channel effect; the Lee et al. formulas (not read).
* While reproducing the study two corrections were made: the script still called flags that no longer exist (`block_nodes`, `block_tiles`) and the case count was 74, not 62 (4 geometries x 6 thickness/metal pairs x 3 interfaces + 2 finned); the documents were corrected.
* The spreading-resistance literature of Lee, Song, Au and Moran (1995) could not be read and was not used.
* Not implemented: the channel effect between fins; a time simulation with a block in Lumped and Analytic.
