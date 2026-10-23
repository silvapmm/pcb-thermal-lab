# The stack-up: advanced mode, typical templates and fabricators' tables

Status: **implemented** in the program (see `IMPLEMENTED.md`). Investigated on 2026-10-21 and 2026-10-22; moved to this folder on 2026-10-23. Studies: `stackup_outline_study.py` (sections 4.1 and 4.2) and `stackup_vendor_check.py` (section 4.3); figures: `make_figures.py`.

## 1. The questions

1. Does an advanced stack-up (copper per layer, material and thickness per gap) work in all five models, and does it add a model error?
2. How sensitive is the temperature to each stack-up number?
3. Are the program's typical stack-up templates (`pcbthermal/data/stackups.json`) close to what fabricators publish?

## 2. Findings in short

* The advanced stack-up with equal gaps reproduces the simple one (0.1 K apart), and an exact series circuit of layer nodes to 1e-6 K in the FVM and FDM.
* The stack-up matters (70 to 102 K of rise on the same board between heavy and half-ounce copper, 71 K with a ceramic core) and the models follow it in the same direction; the spread between models is the same as on a plain board.
* **The one parameter that matters is the finished outer copper**: a 15 % thinner finish raises the rise by 5.7 %; dielectric conductivity and thickness move it by about 1 %.
* The program's 4-layer template is the JLCPCB table to the last digit; the other fabricators' dielectric splits move the maximum temperature by 0.1 to 1.7 °C.

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `stackup_outline_study.py` | Tables of the advanced stack-up in five models, the outline (see `../outline/`), the sensitivity to the stack-up numbers, the finned block. |
| `stackup_vendor_check.py` | The example board with the program's templates and with the published tables of seven fabricators entered layer by layer. |
| `make_figures.py` | Draws the three figures (runs both studies and reads the tables they print). |
| `figures/` | `fig_01` to `fig_03`. |
| `IMPLEMENTED.md`, `LOG.md` | Where it lives in the program; what was read and how. |

## 4. How to run, and the results

```sh
.venv/bin/python research/stackup/stackup_outline_study.py   # about 10 seconds
.venv/bin/python research/stackup/stackup_vendor_check.py    # about 2 seconds
.venv/bin/python research/stackup/make_figures.py
```

### 4.1 Exact checks and the advanced stack-up in five models

`python research/stackup/stackup_outline_study.py` prints the two tables; `tests/test_stackup.py`, `tests/test_outline.py`, `tests/test_inverse.py` and `tests/test_compute.py` hold the checks.
Board of the study: 60 × 40 mm, 4 layers with full copper, nine vias under a 6 × 6 mm heater of 3 W, typed 12 W/m²K on both faces, FVM at 1 mm.



**Exact checks.**
* A uniform board (heater and copper over the whole board, insulated edges) is one-dimensional: a chain of layer nodes joined by `k/d` of every gap. The FVM and the FDM reproduce the exact series circuit of a stack with three different gaps (0.12 mm at 0.4 W/mK, 0.9 mm at 2 W/mK, 0.25 mm at 0.3 W/mK) to 1e-6 K on every layer.
* The advanced stack-up with equal gaps against the simple one: 0.1 K apart (80.8 against 80.7 K rise); the small difference is how the laminate of the layer nodes is shared (copper plus half of each gap against thickness/N).
* An outline that is the whole rectangle gives the same result as no outline (1e-9 K), and an outline that cuts the board to a smaller rectangle gives the same result as the smaller board (0.05 K) in the FVM, the FDM and the 3D solid.
* The energy balance closes to 1e-9 on every outline in all three models, and a part drawn off the board still delivers its whole power.

**A. Advanced stack-up.** Rise of the hottest point in K (FVM) and the other models as a difference from it:

| Stack | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: |
| simple, equal FR-4 gaps | 80.7 | -4.1 % | -1.5 % | -2.1 % | +7.7 % |
| advanced, the same gaps | 80.8 | -4.1 % | -1.7 % | -2.2 % | +7.7 % |
| thin prepreg 0.1 mm top and bottom, 0.7 mm core | 76.9 | -3.6 % | -1.5 % | -2.4 % | +4.8 % |
| prepreg 0.1 mm, metal-core dielectric 1 mm (2 W/mK) | 75.1 | -3.4 % | -1.5 % | -2.5 % | +4.5 % |
| polyimide flex 0.1 mm gaps (0.15 W/mK) | 77.4 | -5.3 % | -2.1 % | -5.6 % | +2.5 % |
| alumina core 0.6 mm (24 W/mK) | 71.2 | -3.6 % | -2.1 % | -4.3 % | +3.6 % |
| copper 70 / 35 / 35 / 70 µm | 69.8 | -2.2 % | -0.6 % | -0.0 % | +6.4 % |
| copper 17.5 µm on every layer | 102.5 | -6.0 % | -2.6 % | -4.4 % | +7.8 % |

* The stack-up matters: the same board goes from 102.5 K (half-ounce copper) to 69.8 K (heavy outer copper) and from 80.7 to 71.2 K with a ceramic core; the models follow it in the same direction (every row of `test_stackup.py` checks the trend in all five models).
* The spread between models is the same as on the plain board (FDM about 4 % low because a via is sampled at the nearest node, the 3D solid within 2.6 %, the Lumped within 6 %, the Analytic 2.5 to 8 % high): the advanced stack-up does not add a model error.

![Several stack-ups in the five models](figures/fig_02_stackups_in_five_models.png)

*Figure 2: `figures/fig_02_stackups_in_five_models.png`.*

### 4.2 Sensitivity to the stack-up numbers

**C. Sensitivity to the stack-up numbers** (`python research/stackup/stackup_outline_study.py`; the typical 4-layer stack-up of `stackups.json`, base rise 84.5 K):

| Change | Rise [K] | Change in the rise |
| :-- | --: | --: |
| dielectric k through -30 % (0.21 W/mK) | 85.4 | +1.0 % |
| dielectric k through +30 % (0.39 W/mK) | 83.8 | -0.8 % |
| all dielectric thicknesses -10 % (fabricator tolerance) | 84.2 | -0.4 % |
| all dielectric thicknesses +10 % | 84.8 | +0.4 % |
| prepreg 0.25 and core 0.35 W/mK | 84.6 | +0.1 % |
| finished copper 15 % thinner (etch and plating spread) | 89.3 | +5.7 % |
| finished copper 15 % thicker | 80.8 | -4.4 % |

Without the vias under the part (base rise 93.4 K) the same ±30 % in the dielectric conductivity gives +3.3 / -2.3 %. The prepreg and the core matter little; the copper and the vias matter more.

![Sensitivity of the rise to the stack-up numbers](figures/fig_03_sensitivity_to_stackup_numbers.png)

*Figure 3: `figures/fig_03_sensitivity_to_stackup_numbers.png`.*

### 4.3 The typical stack-ups against fabricators' tables

`python research/stackup/stackup_vendor_check.py` solves the example board (FVM, 2 mm) with the program's template of each layer count and with the published tables of seven fabricators entered layer by layer.

**What was found online.** Complete layer tables: JLCPCB (4 layers with 7628, 3313, 1080 and 2116 prepreg; 6 layers JLC06161H-3313), PCBWay (76 four-layer tables, 1 oz or 1.5 oz inner copper; an older blog table for 6 and 8 layers), OSH Park (4 layers, FR408HR), Bittele 7pcb (2 to 10 layers, 0.062 in, 1 oz), PCBGOGO (4, 6, 8 layers, 0.4 to 2.4 mm), AdvancedPCB (one 4-layer sample; the 6, 8 and 10-layer drawings are images). NextPCB gives only the prepreg thicknesses in text (2116 0.125 mm, 1080 0.077 mm, 7628 0.2 mm, central prepreg of the 6-layer 0.103 mm; the cores are in drawings). Eurocircuits does not publish tables as text: its builds are chosen in the configurator (about 940 predefined builds); the catalogue is cores of 100, 200, 360 and 710 µm with 12, 18, 35 or 70 µm foil and prepregs PR1080 70 µm, PR2116 120 µm, PR7628 180 µm; pooled boards are 1.55 mm (6 layers and more) and 1.00 mm (4 layers). Sierra Circuits (Proto Express) gives a nominal 1.57 mm, minimum core and dielectric 4 mil, and makes the final stack-up per order. For Eurocircuits, Sierra and NextPCB no complete layer table could be read, so they are checked only against the catalogue values (every prepreg and core of the templates is inside the catalogues: 76 to 210 µm prepreg, 330 to 1065 µm core).

| Stack-up | Total (mm) | Tmax (°C) |
| :-- | --: | --: |
| 4 layers, program template (= JLC04161H-7628: 35 / 15.2 / 15.2 / 35 µm, prepreg 210.4, core 1065) | 1.586 | 101.00 |
| 4 layers, AdvancedPCB sample (1 oz, 2 × 2116 per side, core 39 mil) | 1.613 | 101.62 |
| 4 layers, Bittele (1 oz, 2 × 2116 of 0.0091 in, core 0.037 in) | 1.544 | 99.97 |
| 4 layers, PCBGOGO (18 → 35 µm outer, prepreg 0.11, core 1.2) | 1.560 | 100.60 |
| 4 layers, PCBWay (1 oz inner, prepreg 190, core 1030) | 1.550 | 100.59 |
| 4 layers, OSH Park (43.2 µm outer, 17.5 µm inner, prepreg 199.9, core 990.6) | 1.512 | 93.64 |
| 6 layers, program template | 1.600 | 122.20 |
| 6 layers, JLC06161H-3313 as published (99.4 / 550 / 108.8 / 550 / 99.4 µm) | 1.538 | 122.31 |
| 6 layers, Bittele (0.0081 / 0.013 / 0.0091 / 0.013 / 0.0081 in) | 1.517 | 121.33 |
| 6 layers, PCBGOGO (prepreg 0.11, cores 0.6) | 1.740 | 121.73 |
| 6 layers, PCBWay blog table (110 / 530 / 110 / 530 / 110 µm) | 1.600 | 121.97 |
| 8 layers, program template | 1.600 | 120.40 |
| 8 layers, Bittele (1080 × 2, 0.009, 7628, 0.0051, 7628, 0.009, 1080 × 2) | 1.542 | 121.13 |
| 8 layers, PCBGOGO (prepreg 0.18, cores 0.2) | 1.600 | 121.77 |
| 8 layers, PCBWay blog table (175 / 130 alternating) | 1.370 | 122.18 |

* The 4-layer template is the JLCPCB table to the last digit. The other fabricators' dielectric splits (prepreg 190 to 250 µm, core 940 to 1200 µm; 6 layers cores 330 to 600 µm; 8 layers cores 130 to 229 µm) move the maximum temperature by 0.1 to 1.7 °C (0.2 to 1.5 % of the rise): a 4-layer board stays within 1.0 °C of the template, 6 layers within 0.9 °C, 8 layers within 1.4 °C. The exact prepreg and core split hardly matters on a board whose heat goes down the vias and spreads in the outer copper.
* **The one parameter that matters is the finished outer copper.** OSH Park's 1 oz outer copper is 43.2 µm (clad + plated), against the 35 µm of the templates: with its own dielectrics but 35 µm outer copper the board is at 100.55 °C, with 43.2 µm at 93.65 °C (−6.9 K, 9 % of the rise), and the JLCPCB dielectrics with 43.2 µm give 94.08 °C. A fabricator's "1 oz" finished outer copper is 35 to 43 µm (plating on 18 µm foil; PCBGOGO, PCBWay and JLCPCB quote 35 µm, OSH Park 43.2 µm), so the 35 µm default is the conservative end of the range; type the real value in the Stack-up tab when it is known.
* The old PCBWay blog table for 8 layers sums to 1.37 mm, not the 1.6 mm it is titled with, so it is not consistent (PCBWay calls it the old version); the PCBGOGO 6-layer table sums to 1.74 mm against its 1.6 mm title, probably because the cores listed include copper. Both are shown as published.
* The middle prepreg of the 6-layer template (200 µm) is thicker than the 109 to 110 µm of JLCPCB and PCBWay (the template keeps 1.6 mm by thickening it) and than the 231 µm of Bittele's two-sheet 2116; the effect on the temperature is 0.1 K, so the templates were left unchanged.
* Not covered: constructions with blind or buried vias, sequential lamination, heavy copper, metal-core and ceramic boards (they are in the dielectric presets, with no fabricator table checked).

![Program templates against published stack-ups](figures/fig_01_vendor_stackups.png)

*Figure 1: `figures/fig_01_vendor_stackups.png`.*

## 5. Limits of this study

* One board (the example board with 9 vias under a part), FVM at 1 to 2 mm; the temperatures are for that board.
* The fabricator tables are as published on their pages on 2026-10-22 (read from search snippets and pages, see `LOG.md`); two of them do not add up to their stated thickness and are shown as published.
* No blind or buried vias, sequential lamination, heavy copper or metal-core boards were checked against a fabricator table.
* No measurement of a physical board.

## 6. Sources

Fabricator pages read on 2026-10-22: JLCPCB (4 and 6 layers), PCBWay (76 four-layer tables and an older blog table), OSH Park (FR408HR), Bittele 7pcb, PCBGOGO, AdvancedPCB (one 4-layer sample); NextPCB gives only prepreg thicknesses in text. The pages are named in `docs/validation.md` section 14; their addresses were not recorded in this repository, so this list is as read, not a citation list.
