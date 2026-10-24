# The stack-up: advanced mode, typical templates and fabricators' tables

Status: **implemented** in the program (see the program's `docs/versions.md` and `docs/validation.md`). Studies: `stackup_outline_study.py` (sections 4.1 and 4.2), `stackup_vendor_check.py` (section 4.3) and `study_dielectric_sensitivity.py` (section 4.4); figures: `make_figures.py`. Reviewed on 2026-10-24 on the corrected program (section 7).

## 1. The questions

1. Does an advanced stack-up (copper per layer, material and thickness per gap) work in all five models, and does it add a model error?
2. How sensitive is the temperature to each stack-up number?
3. Are the program's typical stack-up templates (`pcbthermal/data/stackups.json`) close to what fabricators publish?

### 1.1 Diagrams and illustrations

![The stack-up as schematics](figures/fig_04_stackup_schematic.png)

*Figure 4 (`figures/fig_04_stackup_schematic.png`): The stack-up as schematics: 1, the simple mode (equal gaps, the thickness shared by the layers); 2, the advanced mode (copper per layer, material and thickness per gap; each node is the copper plus half of each adjacent gap); 3, the vertical chain as a series of half gaps and what it was found to matter.*

![Figure 5](figures/fig_05_stackup_to_scale.png)

*Figure 5 (`figures/fig_05_stackup_to_scale.png`): the program's 4-layer stack-up in true proportions (35 / 15.2 / 15.2 / 35 um copper, 7628 prepreg 210.4 um, core 1065 um) and what each number is worth for the temperature.*

## 2. Findings in short

* The advanced stack-up with equal gaps reproduces the simple one (0.1 K apart), and an exact series circuit of layer nodes to 1e-6 K in the FVM and FDM.
* The stack-up matters (70 to 102 K of rise on the same board between heavy and half-ounce copper, 71 K with a ceramic core) and the models follow it in the same direction; the spread between models is the same as on a plain board.
* **On a board with copper on both faces, the parameter that matters is the finished copper**: a 15 % thinner finish raises the rise by 5.7 %; the dielectric conductivity (±30 %) and thickness (±10 %) move it by about 1 % with vias under the part and by 2 to 3 % without. **This does not hold for a one-layer board with a pad**: there the heat crosses the laminate and ±30 % of dielectric conductivity moves the rise by +8.7 / -6.1 % (section 4.4; the independent 3D solver agrees within 0.2 points on every case).
* The program's 4-layer template is JLC04161H-7628 as recorded from the JLCPCB pages in 2026-10-22 (only the core 1065 µm and the 15.2 µm inner copper were confirmed again in this review, section 7); the other fabricators' dielectric splits move the maximum temperature by 0.1 to 1.5 °C. With inner planes the 0.5 oz (15.2 µm) inner copper of the templates makes the board 5 to 8 K hotter than the 1 oz inner copper of most published tables.

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `scripts/stackup_outline_study.py` | Tables of the advanced stack-up in five models, the outline (see `../outline/`), the sensitivity to the stack-up numbers, the finned block. |
| `scripts/stackup_vendor_check.py` | The example board with the program's templates and with the published tables of seven fabricators entered layer by layer. |
| `scripts/study_dielectric_sensitivity.py` | The sensitivity of section 4.2 repeated on one-layer, two-layer and four-layer boards, against the independent 3D solver `../effective-conductivity/lib/layered3d.py`. |
| `scripts/make_figures.py` | Draws the three figures (runs both studies and reads the tables they print). |
| `scripts/make_diagrams.py` | Draws the schematic diagram and the illustration (figures 4 and 5; no data, no program; uses `research/diagram_kit.py`). |
| `figures/` | `fig_01` to `fig_05`; figures 4 and 5 are the diagram and the illustration (`make_diagrams.py`). |

## 4. How to run, and the results

```sh
.venv/bin/python research/stackup/scripts/stackup_outline_study.py        # about 2 minutes
.venv/bin/python research/stackup/scripts/stackup_vendor_check.py         # about 15 seconds
.venv/bin/python research/stackup/scripts/study_dielectric_sensitivity.py  # about 2 minutes
.venv/bin/python research/stackup/scripts/make_figures.py                  # about 2 minutes
.venv/bin/python research/stackup/scripts/make_diagrams.py
```

### 4.1 Exact checks and the advanced stack-up in five models

`python research/stackup/scripts/stackup_outline_study.py` prints the two tables; `tests/test_stackup.py`, `tests/test_outline.py`, `tests/test_inverse.py` and `tests/test_compute.py` hold the checks.
Board of the study: 60 × 40 mm, 4 layers with full copper, nine vias under a 6 × 6 mm heater of 3 W, typed 12 W/m²K on both faces, FVM at 1 mm.



**Exact checks.**
* A uniform board (heater and copper over the whole board, insulated edges) is one-dimensional: a chain of layer nodes joined by `k/d` of every gap. The FVM and the FDM reproduce the exact series circuit of a stack with three different gaps (0.12 mm at 0.4 W/mK, 0.9 mm at 2 W/mK, 0.25 mm at 0.3 W/mK) to 1e-6 K on every layer.
* The advanced stack-up with equal gaps against the simple one: 0.1 K apart (80.8 against 80.7 K rise); the small difference is how the laminate of the layer nodes is shared (copper plus half of each gap against thickness/N).
* An outline that is the whole rectangle gives the same result as no outline (1e-9 K), and an outline that cuts the board to a smaller rectangle gives the same result as the smaller board (0.05 K) in the FVM, the FDM and the 3D solid.
* The energy balance closes to 1e-9 on every outline in all three models, and a part drawn off the board still delivers its whole power.

**A. Advanced stack-up.** Rise of the hottest point in K (FVM) and the other models as a difference from it:

| Stack | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: |
| simple, equal FR-4 gaps | 80.7 | -4.1 % | -1.5 % | -3.2 % | +7.7 % |
| advanced, the same gaps | 80.8 | -4.1 % | -1.7 % | -3.3 % | +7.7 % |
| thin prepreg 0.1 mm top and bottom, 0.7 mm core | 76.9 | -3.6 % | -1.5 % | -3.5 % | +4.8 % |
| prepreg 0.1 mm, metal-core dielectric 1 mm (2 W/mK) | 75.1 | -3.4 % | -1.5 % | -3.6 % | +4.5 % |
| polyimide flex 0.1 mm gaps (0.15 W/mK) | 77.4 | -5.3 % | -2.1 % | -6.6 % | +2.5 % |
| alumina core 0.6 mm (24 W/mK) | 71.2 | -3.6 % | -2.1 % | -5.2 % | +3.6 % |
| copper 70 / 35 / 35 / 70 µm | 69.8 | -2.2 % | -0.6 % | -0.9 % | +6.4 % |
| copper 17.5 µm on every layer | 102.5 | -6.0 % | -2.6 % | -5.9 % | +7.8 % |

* The stack-up matters: the same board goes from 102.5 K (half-ounce copper) to 69.8 K (heavy outer copper) and from 80.7 to 71.2 K with a ceramic core; the models follow it in the same direction (every row of `test_stackup.py` checks the trend in all five models).
* The spread between models is the same as on the plain board (FDM about 4 % low because a via is sampled at the nearest node, the 3D solid within 2.6 %, the Lumped 0.9 to 6.6 % low, the Analytic 2.5 to 8 % high; the Lumped column was 1 point less low before the minimum ring width of the corrected program): the advanced stack-up does not add a model error.

![Several stack-ups in the five models](figures/fig_02_stackups_in_five_models.png)

*Figure 2: `figures/fig_02_stackups_in_five_models.png`.*

### 4.2 Sensitivity to the stack-up numbers

**C. Sensitivity to the stack-up numbers** (`python research/stackup/scripts/stackup_outline_study.py`; the typical 4-layer stack-up of `stackups.json`, base rise 84.5 K):

| Change | Rise [K] | Change in the rise |
| :-- | --: | --: |
| dielectric k through -30 % (0.21 W/mK) | 85.4 | +1.0 % |
| dielectric k through +30 % (0.39 W/mK) | 83.8 | -0.8 % |
| all dielectric thicknesses -10 % (fabricator tolerance) | 84.2 | -0.4 % |
| all dielectric thicknesses +10 % | 84.8 | +0.4 % |
| prepreg 0.25 and core 0.35 W/mK | 84.6 | +0.1 % |
| finished copper 15 % thinner (etch and plating spread) | 89.3 | +5.7 % |
| finished copper 15 % thicker | 80.8 | -4.4 % |

Without the vias under the part (base rise 93.4 K; printed by the same script since this review) the same ±30 % in the dielectric conductivity gives +3.3 / -2.3 %. On this board the prepreg and the core matter little; the copper and the vias matter more. Section 4.4 shows where that stops being true.

![Sensitivity of the rise to the stack-up numbers](figures/fig_03_sensitivity_to_stackup_numbers.png)

*Figure 3: `figures/fig_03_sensitivity_to_stackup_numbers.png`.*

### 4.3 The typical stack-ups against fabricators' tables

`python research/stackup/scripts/stackup_vendor_check.py` solves the example board (FVM, 2 mm) with the program's template of each layer count and with the published tables of seven fabricators entered layer by layer.

**What was found online.** Complete layer tables: JLCPCB (4 layers with 7628, 3313, 1080 and 2116 prepreg; 6 layers JLC06161H-3313), PCBWay (76 four-layer tables, 1 oz or 1.5 oz inner copper; an older blog table for 6 and 8 layers), OSH Park (4 layers, FR408HR), Bittele 7pcb (2 to 10 layers, 0.062 in, 1 oz), PCBGOGO (4, 6, 8 layers, 0.4 to 2.4 mm), AdvancedPCB (one 4-layer sample; the 6, 8 and 10-layer drawings are images). NextPCB gives only the prepreg thicknesses in text (2116 0.125 mm, 1080 0.077 mm, 7628 0.2 mm, central prepreg of the 6-layer 0.103 mm; the cores are in drawings). Eurocircuits does not publish tables as text: its builds are chosen in the configurator (about 940 predefined builds); the catalogue is cores of 100, 200, 360 and 710 µm with 12, 18, 35 or 70 µm foil and prepregs PR1080 70 µm, PR2116 120 µm, PR7628 180 µm; pooled boards are 1.55 mm (6 layers and more) and 1.00 mm (4 layers). Sierra Circuits (Proto Express) gives a nominal 1.57 mm, minimum core and dielectric 4 mil, and makes the final stack-up per order. For Eurocircuits, Sierra and NextPCB no complete layer table could be read, so they are checked only against the catalogue values (every prepreg and core of the templates is inside the catalogues: 76 to 210 µm prepreg, 330 to 1065 µm core).

The board is the example board reshaped to each layer count: its top copper on layer 1, its bottom plane on the last layer, its heaters, vias and bottom heatsink; the two inner planes of the example are dropped in the first column (so that only the dielectric split and the outer copper differ) and put on every inner layer in the second (so that the inner copper of each table counts).
Until this review the 6 and 8-layer boards had **no bottom copper** (the script kept only zones on layer indices 0 and n - 1, and the bottom plane of the example is index 3): their rows were about 21 K hotter (122.2 °C for the 6-layer template) and the comparison was of a different board. The 4-layer rows did not change.

| Stack-up | Total (mm) | Tmax, outer copper only (°C) | Tmax, a plane on every inner layer (°C) |
| :-- | --: | --: | --: |
| 4 layers, program template (= JLC04161H-7628: 35 / 15.2 / 15.2 / 35 µm, prepreg 210.4, core 1065) | 1.586 | 101.00 | 90.40 |
| 4 layers, AdvancedPCB sample (1 oz, 2 × 2116 per side, core 39 mil) | 1.613 | 101.62 | 84.12 |
| 4 layers, Bittele (1 oz, 2 × 2116 of 0.0091 in, core 0.037 in) | 1.544 | 99.97 | 82.98 |
| 4 layers, PCBGOGO (18 → 35 µm outer, prepreg 0.11, core 1.2) | 1.560 | 100.60 | 82.04 |
| 4 layers, PCBWay (1 oz inner, prepreg 190, core 1030) | 1.550 | 100.59 | 82.98 |
| 4 layers, OSH Park (43.2 µm outer, 17.5 µm inner, prepreg 199.9, core 990.6) | 1.512 | 93.64 | 84.83 |
| 6 layers, program template | 1.600 | 100.95 | 84.80 |
| 6 layers, JLC06161H-3313 as published (99.4 / 550 / 108.8 / 550 / 99.4 µm) | 1.538 | 100.66 | 84.43 |
| 6 layers, Bittele (0.0081 / 0.013 / 0.0091 / 0.013 / 0.0081 in) | 1.517 | 99.44 | 77.41 |
| 6 layers, PCBGOGO (prepreg 0.11, cores 0.6) | 1.740 | 101.12 | 77.52 |
| 6 layers, PCBWay blog table (110 / 530 / 110 / 530 / 110 µm) | 1.600 | 100.46 | 76.97 |
| 8 layers, program template | 1.600 | 99.24 | 79.72 |
| 8 layers, Bittele (1080 × 2, 0.009, 7628, 0.0051, 7628, 0.009, 1080 × 2) | 1.542 | 99.12 | 73.89 |
| 8 layers, PCBGOGO (prepreg 0.18, cores 0.2) | 1.600 | 100.03 | 74.70 |
| 8 layers, PCBWay blog table (175 / 130 alternating) | 1.370 | 98.82 | 73.55 |

* The 4-layer template is the JLCPCB table JLC04161H-7628 as it was read on 2026-10-22 (the addresses are in the program's `docs/validation.md`, section 14). In this review only part of it could be confirmed again: a search snippet of the JLCPCB help page gives the 1.065 mm core and 0.2 mm of 7628 prepreg with 0.0175 mm inner copper (an older version of the page, it seems), and an independent collection of JLCPCB's impedance templates (gsuberland/jlcpcb_autogenerated_stackups on GitHub, which disclaims any guarantee) gives 0.0152 mm for the inner copper of 4 to 8 layers; the 210.4 µm prepreg was not seen again. **Published versus constructed**: the 4-layer entry is the only one copied from a fabricator's table; the 2-layer entry (one 1.53 mm core) and the 6, 8, 10 and 12-layer entries are constructed so that the layers add up to the nominal thickness (the file `stackups.json` says so), and the 1-layer entry is the simple mode. Only the 4, 6 and 8-layer templates are compared with tables here.
* With the outer copper only, the other fabricators' dielectric splits (prepreg 190 to 250 µm, core 940 to 1200 µm; 6 layers cores 330 to 600 µm; 8 layers cores 130 to 229 µm) move the maximum temperature by 0.1 to 1.5 °C (0.2 to 2.0 % of the rise): a 4-layer board stays within 1.0 °C of the template, 6 layers within 1.5 °C, 8 layers within 0.8 °C. The exact prepreg and core split hardly matters on a board whose heat goes down the vias and spreads in the outer copper.
* **With inner planes the inner copper matters.** The templates use 0.5 oz (15.2 µm) inner copper, most tables 1 oz (34 to 36 µm): with a full plane on every inner layer the published boards are 6.3 to 8.4 °C cooler than the 4-layer template, 7.3 to 7.8 °C than the 6-layer and 5.0 to 6.2 °C than the 8-layer one, while the JLCPCB 6-layer table, which has the same 15.2 µm inner copper, is within 0.4 °C. The 0.5 oz inner copper is the conservative end; type the real value when it is known.
* **The finished outer copper matters too.** OSH Park's 1 oz outer copper is 43.2 µm (clad + plated), against the 35 µm of the templates: with its own dielectrics but 35 µm outer copper the board is at 100.55 °C, with 43.2 µm at 93.64 °C (−6.9 K, 9 % of the rise), and the JLCPCB dielectrics with 43.2 µm give 94.08 °C (both printed by the script since this review). A fabricator's "1 oz" finished outer copper is 35 to 43 µm (plating on 18 µm foil; PCBGOGO, PCBWay and JLCPCB quote 35 µm, OSH Park 43.2 µm), so the 35 µm default is the conservative end of the range.
* The old PCBWay blog table for 8 layers sums to 1.37 mm, not the 1.6 mm it is titled with, so it is not consistent (PCBWay calls it the old version); the PCBGOGO 6-layer table sums to 1.74 mm against its 1.6 mm title, probably because the cores listed include copper. Both are shown as published.
* The middle prepreg of the 6-layer template (200 µm) is thicker than the 109 to 110 µm of JLCPCB and PCBWay (the template keeps 1.6 mm by thickening it) and than the 231 µm of Bittele's two-sheet 2116; the whole JLCPCB 6-layer table, which has the same copper, is 0.3 to 0.4 °C cooler than the template (0.1 K before this review, on the board without bottom copper), so the templates were left unchanged.
* Not covered: constructions with blind or buried vias, sequential lamination, heavy copper, metal-core and ceramic boards (they are in the dielectric presets, with no fabricator table checked).

![Program templates against published stack-ups](figures/fig_01_vendor_stackups.png)

*Figure 1: `figures/fig_01_vendor_stackups.png`.*

### 4.4 Where the dielectric matters: other boards and an independent solver

`.venv/bin/python research/stackup/scripts/study_dielectric_sensitivity.py` repeats the changes of section 4.2 on boards where the heat has to cross the dielectric, with the FVM of the program and with the independent 3D finite-volume solver `../effective-conductivity/lib/layered3d.py` (real slabs, none of the program's code). The same physics on both sides: 60 × 40 mm, a 6 × 6 mm source of 3 W in the middle, 12 W/m²K on both faces (also under the source), insulated edges, FR-4 taken isotropic at 0.3 W/mK (the independent solver is isotropic per slab), 1 mm cells. Change in the rise, program / independent:

| Board | Base rise [K] | k -30 % | k +30 % | thickness -10 % | thickness +10 % | copper -15 % | copper +15 % |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 layer, full copper, 1.6 mm | 115.7 / 115.7 | +1.1 / +1.1 | -0.8 / -0.8 | -0.0 / -0.0 | +0.0 / +0.0 | +8.6 / +8.6 | -6.5 / -6.5 |
| 1 layer, 20 mm pad, 1.6 mm | 216.1 / 222.7 | +8.7 / +8.9 | -6.1 / -6.3 | +1.6 / +1.4 | -1.4 / -1.3 | +3.3 / +3.2 | -2.5 / -2.5 |
| 2 layers, full copper, no vias | 105.7 / 105.9 | +2.8 / +2.7 | -2.0 / -2.0 | -0.7 / -0.7 | +0.6 / +0.6 | +7.3 / +7.3 | -5.5 / -5.6 |
| 4 layers (template), full copper, no vias | 96.1 / 96.2 | +3.2 / +3.2 | -2.3 / -2.3 | -0.9 / -0.9 | +0.8 / +0.8 | +6.3 / +6.3 | -4.8 / -4.8 |
| 4 layers (template), full copper, 9 vias | 87.2 | +1.1 | -0.9 | -0.7 | +0.7 | +5.6 | -4.3 |

* The program and the independent solver agree on every sensitivity within 0.2 points, and on the base rise within 0.2 % except the one-layer pad (3.0 % low, the bare-pad error of the laminate nodes recorded in the program's `docs/theory.md`, section 1.4).
* "The dielectric conductivity and thickness move the temperature by about 1 %, the copper by 5 %" holds on the board it was measured on (4 layers, full copper, vias: +1.1 / -0.9 % and +5.6 / -4.3 % here, against +1.0 / -0.8 % and +5.7 / -4.4 % on the anisotropic board of section 4.2). Without vias the dielectric conductivity is worth 2 to 3 %; **on a one-layer board with a pad it is the first parameter** (+8.7 / -6.1 % for ±30 %), and the laminate thickness is worth 1.4 to 1.6 %. On a one-layer board with full copper the laminate barely matters (the copper spreads the heat over the whole board, which then loses it through the top film) but the copper is worth 6.5 to 8.6 %.
* The "copper weight" of the earlier statement is a ±15 % spread of the finished copper, not a change of weight: half-ounce against two-ounce outer copper moves the rise by 30 % (section 4.1).
* Limits: one source size, one coefficient (12 W/m²K), insulated edges, FR-4 isotropic in this table (the program's default is 0.9 W/mK in the plane); the board with vias has no independent value (the independent solver has no vias; the 3D solid column of section 4.1 is the check there).

## 5. Limits of this study

* Sections 4.1 to 4.3 use one board each (the study board with 9 vias under a part, the example board reshaped), FVM at 1 to 2 mm; the temperatures are for those boards. Section 4.4 adds one-layer, two-layer and four-layer boards without vias, with one source size and one coefficient.
* The documents of the program describe the simple stack-up only: `docs/theory.md` section 1.2 gives `slab = t_pcb / L` and one gap `d`, not the advanced mode (copper plus half of each adjacent gap, `k/d` per gap, the thickness-weighted in-plane laminate of `Board.slab_thicknesses` and `Board.layer_laminate`); text for it is in `docs/for-the-project-documents.md`.
* The fabricator tables are as published on their pages (read from search snippets and pages, see the last section); two of them do not add up to their stated thickness and are shown as published.
* No blind or buried vias, sequential lamination, heavy copper or metal-core boards were checked against a fabricator table.
* No measurement of a physical board.

## 7. Review (2026-10-24, reviewer agent, program at `0ea5f07`)

Every study of the folder was re-run on the corrected program (`stackup_outline_study.py`, `stackup_vendor_check.py`, the new `study_dielectric_sensitivity.py`, `make_figures.py`, `make_diagrams.py`); `tests/test_stackup.py` and `tests/test_templates.py` pass (17 tests).

* **Defect in a study, fixed**: `stackup_vendor_check.py` dropped the bottom plane of every board with more than four layers (it kept zones on layer indices 0 and n - 1; the bottom plane of the example is index 3). The 6 and 8-layer rows of section 4.3 and of the program's `docs/validation.md` section 14 described boards with no bottom copper, about 21 K hotter than with it (6-layer template 122.20 -> 100.95 °C). The bottom plane now goes to the last layer; the 4-layer rows are unchanged. The ranges quoted from those rows changed (0.1 to 1.7 °C -> 0.1 to 1.5 °C; 0.2 to 1.5 % -> 0.2 to 2.0 % of the rise; 6 layers within 0.9 -> 1.5 °C; 8 layers within 1.4 -> 0.8 °C; the JLCPCB 6-layer table 0.1 K -> 0.3 K from the template). The old "8 layers within 1.4 °C" also left out the PCBWay row (1.78 °C away).
* **Stale numbers, fixed**: the Lumped column of table A (section 4.1) was from before the minimum ring width of the corrected program; it is 0.9 to 1.1 points lower on every row (for example -2.1 -> -3.2 % on the plain board). FVM, FDM, 3D solid and Analytic columns and tables B and C reproduce to the digit.
* **Numbers no script printed, now printed**: the board without vias of section 4.2 (93.4 K, +3.3 / -2.3 %: reproduced) and the three OSH Park variants of section 4.3 (100.55 and 94.08 reproduced; 93.65 is the 93.64 of the table).
* **Claim with a narrower scope than stated**: "the dielectric conductivity and thickness move the temperature by about 1 %, the copper weight by 5 %" is true on the 4-layer board with vias it was measured on, and checked against an independent solver here; it is 2 to 3 % without vias and 6 to 9 % on a one-layer board with a pad, and the "5 %" is a ±15 % spread of the finished copper, not a copper weight (section 4.4).
* **Template provenance**: only the 4-layer template comes from a fabricator's table; the others are constructed (as `stackups.json` says). The `sources` list of `stackups.json` says the published tables differ "by under 0.5 %"; the tables of section 4.3 give up to 2.0 % with outer copper only and up to 13 % with inner planes (8.4 K of a 65 K rise, the inner copper weight): the sentence belongs to the program and is left for the maintainer (`docs/for-the-project-documents.md`).
* **Checked and right**: the exact 1D series-circuit checks (in `tests/test_stackup.py`), the advanced-equals-simple check (0.1 K), the outline table B, the sensitivity table C; the advanced-mode code (`Board.slab_thicknesses`, `gap_properties`, `layer_laminate`) against its docstrings.
* **Stale run times, fixed**: the outline study takes about 2 minutes (not 10 seconds), the vendor check about 15 seconds.
* **Figures**: `fig_01` redrawn with the corrected rows (its title range 0.1 to 1.5 °C), `fig_02` with the new Lumped column; `fig_04` and `fig_05` texts corrected (the scope of the 1 % claim, 0.2 to 2.0 %).

## 6. Sources

Fabricator pages read: JLCPCB (4 and 6 layers), PCBWay (76 four-layer tables and an older blog table), OSH Park (FR408HR), Bittele 7pcb, PCBGOGO, AdvancedPCB (one 4-layer sample); NextPCB gives only prepreg thicknesses in text. The pages are named in `docs/validation.md` section 14; their addresses were not recorded in this repository, so this list is as read, not a citation list.

## What was read and what was not verified

* Read in full or from search snippets: the fabricator layer tables were taken from the pages found; two tables (PCBWay's old 8-layer blog table, PCBGOGO's 6-layer table) do not add up to their stated thickness and are shown as published. The addresses were not saved.
* Not verified: no measurement of a physical board.
* Not implemented: blind and buried vias, sequential lamination, heavy-copper and metal-core fabricator tables.
