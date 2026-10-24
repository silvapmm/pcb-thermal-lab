# Corrections for the project documents (from the review of 2026-10-24)

The project documents are not edited on a research branch. These are the changes the review of this folder found necessary in `docs/validation.md`; apply them on a `docs/` or `fix/` branch off `develop`. Every number below is printed by a script of this folder (README section 7).

## `docs/validation.md`, section 3 (metal block table)

* Add the program's 3D solid as a column, and name the script that prints the table (`research/solid3d-verification/scripts/study_block_against_fem.py`; no script printed it before):

  | Case | 3D FEM [°C] | FVM | FDM | 3D solid (FV) |
  | :-- | --: | --: | --: | --: |
  | no block (bottom pad only) | 134.2 | 133.2 (−0.9 %) | 132.6 (−1.5 %) | 134.3 (+0.1 %) |
  | Al 3 mm, gap pad 5 K cm²/W | 115.5 | 115.0 (−0.5 %) | 114.9 (−0.6 %) | 115.4 (−0.0 %) |
  | same, finned (extra h 60 W/m²K) | 99.7 | 99.0 (−1.0 %) | 99.0 (−1.0 %) | 99.6 (−0.2 %) |
  | same, worse interface (20 K cm²/W) | 118.8 | 118.4 (−0.4 %) | 118.3 (−0.5 %) | 118.8 (−0.0 %) |
  | Al 1 mm | 117.3 | 116.8 (−0.5 %) | 116.8 (−0.6 %) | 117.2 (−0.0 %) |
  | Cu 3 mm | 115.3 | 114.8 (−0.5 %) | 114.8 (−0.6 %) | 115.3 (−0.0 %) |
  | Al 3 mm 40 × 40 over a 50 × 50 mm pad | 120.4 | 119.4 (−1.0 %) | 119.0 (−1.4 %) | 120.4 (−0.0 %) |
  | Al 3 mm 30 × 30 exactly over the pad | 129.3 | 128.1 (−1.1 %) | 127.4 (−1.8 %) | 129.5 (+0.2 %) |

  (The FDM "Al 1 mm" is 116.8, not 116.7.) State the board: full top copper, 10 × 10 mm heater at the centre, aluminium 204 W/mK.

## `docs/validation.md`, section 3.1

* "the 3D FV solid is within 2 % there" (pads of 20 mm and more) is wrong: it is +3.6 % on the 20 mm pad and within 2 % from 30 mm. Replace with "the 3D FV solid is within 2 % from 30 mm (+3.6 % at 20 mm)".
* "1 mm cells here, 0.5 mm in the FEM script's column header" is unclear: the 3D solid runs at 0.5 mm in the four-board table of section 3 (`validation_study.py --fem`) and at 1 mm in the tables of 3.1 (`copper_dissipation.py`).
* The convergence paragraph is reproduced by `research/solid3d-verification/scripts/study_small_pad_convergence.py`; add the independent solver's numbers from README 4.2.1 of the folder.
* "The remaining 0.4 to 2 % of the FVM comes from ... (no lateral spreading inside the gap)": the FVM does carry the laminate's in-plane conduction (at the copper node temperatures), and the attribution was not measured. Suggested: "is attributed to representing each copper layer by one node and the dielectric between two layers as a one-dimensional vertical resistance (not measured separately)".
* The last row of the copper-against-heatsink table: its "heat over the area" is over the heater's own 10 mm pad, not over the 40 mm heatsink area.

## `docs/validation.md`, section 16

* Add the closed forms: the Bessel series reproduces Table 3 to its four digits (0.9401, 0.8010, 0.6649, 0.5337), and the double cosine series of the square tube that the 3D solid solves gives 0.8027 (ε = 0.2) and 0.6676 (ε = 0.3); the 3D solid is +0.6 % and +0.3 % from the square tube. The square tube accounts for 0.2 to 0.4 points of the 0.7 to 0.8 %, the mesh for the rest (the sentence "the one-dimensional resistances subtracted from a large total account for ..." was not measured; drop it).

## `docs/validation.md`, section 20

* "The 3D solid is now 3 % above the layered models with full copper and 13 % with a 20 mm pad" was true between the two corrections; after section 21 the FVM is −0.1 % (full copper) and −3.5 % (20 mm pad) of the 3D solid's rise (FDM −0.1 / −9.5 %, Lumped +1.2 / −10.7 %, Analytic −0.9 / −11.0 %; `study_one_layer_board.py` part 1). Replace "now" with "before the laminate nodes of section 21".
