# Corrections for the project documents (from the review)

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

## Times and memory of the solves (`CHANGELOG.md`, `docs/versions.md`, `docs/models.md`, the comment of `pcbthermal/solid3d.py`, `docs/roadmap.md` Next work #1 and #2)

The times quoted there were measured while the machine was swapping and are not reproduced. Measured by `study_solve_cost.py` on a machine just restarted with nothing else running (macOS arm64, 10 cores, 16 GB, Python 3.13.5, SciPy 1.18.1; direct sparse solve, each size in its own process):

| Model | Unknowns | Time (s) | Peak memory (GB) | In the documents |
| :-- | --: | --: | --: | :-- |
| 3D solid, plain two-layer board | 158 000 | 2.0 | 0.75 | 49 s, 2.2 GB |
| 3D solid, plain two-layer board | 248 000 | 3.5 | 1.2 | 130 s, 4.4 GB (254 000) |
| 3D solid, plain two-layer board | 393 000 | 7.5 | 2.65 | 276 s, 5 GB |
| 3D solid, plain two-layer board | 500 000 | 9.3 | 3.3 | 320 s, 8 GB (512 000) |
| 3D solid, example board (16 slabs) | 158 000 / 247 000 | 7.2 / 15.3 | 2.15 / 3.5 | |
| layered FVM, plain board | 992 000 | 5.2 | 2.7 | 97 s, 4.4 GB |
| layered FVM, plain board | 1 975 000 | 12.4 | 5.5 | 273 s, 8.4 GB |

* Replace the times and memory in the four documents with these (or remove them), and say that they depend on the machine and on the board (the example board with vias and a heatsink takes about 4 times longer than the plain board of the same size).
* The limit `MAX_CELLS = 250 000` and the "slow above a million unknowns" note for the layered models were set from the old numbers: reconsider them with the table (the example board at 500 000 unknowns was not measured, so the new limit needs one more run on it).
* The memory guard of `docs/roadmap.md` Next work #2 can use the measured memory per unknown: about 6.6 KB for the 3D solid on a plain board (3.3 GB at 500 000), 14 KB on the example board (3.5 GB at 247 000), 2.8 KB for the layered FVM (5.5 GB at 1.98 million).
