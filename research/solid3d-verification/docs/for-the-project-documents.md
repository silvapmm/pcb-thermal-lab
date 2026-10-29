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

## Times and memory of the solves (`CHANGELOG.md`, `docs/versions.md`, `docs/models.md`, the comment of `pcbthermal/solid3d.py`, `docs/versions.md` "Planned" Next work #1 and #2)

The times quoted there are not reproduced. Why is not established: the comment of `solid3d.py` and the Decisions Log of `CLAUDE.md` say they were measured on a 4-layer board (16 slabs) on a 16 GB machine on which a calculation process had been paging, and with computed heat transfer coefficients the solve is repeated 3 to 6 times; which of the two applied to each point was not recorded, and neither was tested. Measured by `study_solve_cost.py` on a machine just restarted with nothing else running (macOS arm64, 10 cores, 16 GB, Python 3.13.5, SciPy 1.18.1; direct sparse solve with constant coefficients, each size in its own process):

| Model | Unknowns | Time (s) | Peak resident memory (GB) | In the documents |
| :-- | --: | --: | --: | :-- |
| 3D solid, plain two-layer board (6 slabs) | 158 000 | 2.0 | 0.75 | |
| 3D solid, plain two-layer board | 248 000 | 3.5 | 1.2 | |
| 3D solid, plain two-layer board | 393 000 | 7.5 | 2.65 | |
| 3D solid, plain two-layer board | 500 000 | 9.3 | 3.3 | |
| 3D solid, example board (16 slabs, like the board of the documents) | 158 000 | 7.2 | 2.15 | 49 s, 2.2 GB (160 000) |
| 3D solid, example board | 247 000 | 15.3 | 3.5 | 130 s, 4.4 GB (254 000) |
| 3D solid, example board | 392 000 | 32.8 | 7.4 | 276 s, 5 GB (5.3 GB in `solid3d.py`; 394 000) |
| 3D solid, example board | 512 000 | 57.7 | 9.9 | 320 s, 8 GB |
| layered FVM, plain board | 992 000 | 5.2 | 2.7 | 97 s, 4.4 GB (1 million) |
| layered FVM, plain board | 1 975 000 | 12.4 | 5.5 | 273 s, 8.4 GB (2 million) |

* Replace the times and memory in the four documents with these (or remove them), and say that they depend on the machine, on the board and on the computed-h loop: the example board with vias and a heatsink takes 3.6 to 6.2 times longer than the plain board of the same size, and the documents' times are 5.5 to 8.5 times the example board's (20 to 40 times the plain board's) while their memory is close to the example board's (lower at 394 000 and 512 000 unknowns).
* The limit `MAX_CELLS = 250 000` and the "slow above a million unknowns" note for the layered models were set from the old numbers. At the limit the example board takes 15 s and 3.5 GB. For time alone the limit could be higher (57.7 s at 512 000 unknowns on the example board, three to six times that with computed coefficients); for memory, the next measured points need 7.4 GB (392 000) and 9.9 GB resident (512 000) on a 16 GB machine, so on boards like the example it cannot rise much above about 400 000 unknowns (about half of the memory) without an estimate of the memory; on a plain board the same memory allows more than a million. A limit by estimated memory needs the number of slabs, because the cost per unknown is 6.6 KB on a plain board and 14 to 19 KB on the example board and grows with the size.
* The memory guard of `docs/versions.md` "Planned" Next work #2 can use the measured memory per unknown, which is not constant: 6.6 KB for the 3D solid on a plain board (3.3 GB at 500 000), 14.3 to 19.3 KB on the example board (3.5 GB at 247 000, 9.9 GB at 512 000), 2.8 KB for the layered FVM (5.5 GB at 1.98 million). A guard has to use the size of the case, not one number, and to leave room for the operating system and the application (the 512 000-unknown example board reached 9.9 GB resident, 62 % of the 16 GB).
* Not measured: whether the 512 000-unknown run paged (no `vm_stat` was taken after it; `/usr/bin/time -l` counted 906 major page faults for the whole study, and its "peak memory footprint" of 20 496 840 bytes is the parent process, 20.5 MB, not the 20.5 GB first written here); the computed-h loop; another machine.

## Decision of the maintainer on the memory limit

The limit is by estimated memory, not by number of unknowns (proposal above), and **the value must be adjustable in the settings** (Preferences, the `solver` section of `defaults.json`, so that a user with more or less memory can change it): the default is 50 % of the physical memory, read from the system, and the estimate per unknown (about 20 KB for the 3D solid with many slabs, 7 KB with few, 3 KB for the layered models) is a table in the same place, not a constant in the code. Implementation is a `fix/` branch off `develop` with the whole battery, after the maintainer takes it up; measure one more point on the example board above 512 000 unknowns before raising the default above about 400 000 unknowns on a 16 GB machine.
