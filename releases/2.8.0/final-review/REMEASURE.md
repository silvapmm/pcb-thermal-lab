# Re-measure of the Lumped numbers on the final tree (final review of 2.8.0)

Branch `docs/final-remeasure` from `development` 7a3ca02e. The program of this tree equals `da16d80f` in every model (the commits since change texts only: `git diff da16d80f..7a3ca02e -- pcbthermal` touches warning strings, the help and the calculator texts), so it holds every 2.8.0 model item: the Lumped part read-out, the drawn copper read as imported copper, the images of the sides in the Lumped first link (section 53), the exact block cover and the film through the half copper layer (section 55).

Scope (from `PART_1B.md` F1 and F6, `PART_2B.md` 2, `PART_2C.md` T1 and T5): the Lumped numbers of `docs/validation.md` 18.1, 18.2, 31, 35, 42, 48 and 50, the imported-copper warning of the Lumped and Analytic (`copper.REDUCED_MODEL_WARNING`, validation 27.7), the zoned-Lumped warning text and the README model table.

Progress notes are written here as the runs finish (a cut-off loses nothing).

## Progress

* `study_final_remeasure.py ring` (75 s, peak 6.24 GB, the 3D check at 8 sub-slabs): done; numbers in section 2 (validation 31).
* `readout` (8 s, 0.83 GB), `farvia` (1 s, 0.2 GB): done; numbers in section 2 (validation 48, 42).
* `subcell` (94 s, 1.69 GB): done; numbers in section 2 (validation 35.3).
* `zones` (51 s, 0.96 GB): done; the 62 via boards against the FVM at 0.25 mm (section 2, validation 18.2).
* `study_via_groups_review.py models` / `fvm` (24 random via boards of validation 42.5; 0.1 GB and 0.94 GB): done (section 2, validation 42.5).
* `research/lumped-zone-placement/scripts/study_independent_shift.py --dx 0.25` (13 s): done (section 2, validation 50).
* `imported rp2040` (27 parts, 46 s, 0.52 GB): done (section 3).
* `imported oswlight` (all 51 heat sources, 163 s, 0.42 GB): done (section 3).
* `whole025`, `whole1` (`study_whole_board_reduced_models.py`, RP2040 U1, U3), `imported co60` (4 parts, 131 s, 2.72 GB), `unrefined` (54 s, 1.69 GB), `study_via_checks.py fillgain shen` (82 s): done.
* Every run was alone on the machine under the heavy-job lock; the largest peak was 6.24 GB (`ring`, the independent 3D solver with eight sub-slabs and the FVM at 0.25 mm), slightly above the 6 GB asked; every other run stayed under 3 GB.

## 1. Commands (from the root of the worktree, `QT_QPA_PLATFORM=offscreen`, `PCBT_REAL_BOARDS` from `pcb-library/scripts/link_env.sh`)

* `releases/2.8.0/final-review/scripts/study_final_remeasure.py ring | readout | farvia | subcell | unrefined | zones | imported rp2040 | imported oswlight | imported co60 RGB1,U1,C1,R1` (new, this review)
* `releases/2.7.0/final-opinion/scripts/study_via_groups_review.py models <json>` and `... fvm <json>` (PYTHONPATH the worktree)
* `research/lumped-zone-placement/scripts/study_independent_shift.py --dx 0.25`
* `research/gerber-real-boards/scripts/study_whole_board_reduced_models.py 0.25 <rp2040> U1,U3` and `... 1 <rp2040> U3`
* `releases/2.8.0/audit/scripts/study_via_checks.py fillgain shen`

## 2. Lumped numbers of `docs/validation.md` (item, old number and its tree, new number on 7a3ca02e, reference, status)

### 2.1 Validation 18.1 and 18.2 (vias)

| item | old (tree) | new | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| 18.1 copper-fill gain, Lumped 0.5 / 1 / 0.8 mm | −4.54 / −4.71 / −4.35 K (2.7.1, 5fc91430) | −4.67 / −4.72 / −4.46 K | model against model (FVM −4.25 / −4.20 / −4.07, unchanged) | re-measured, table replaced |
| 18.1 the other rows (FVM, FDM, 3D solid, Analytic) | 2.7.1 | unchanged at the printed digit | – | re-measured |
| 18.1 the 29 + 17 boards (via effect 8 % / 20 %) | 2.4.5 (fix/via-constriction) | – | program FVM 0.25 mm | **not re-measured**: the review scripts that built the boards are not in the repository; replaced as evidence by the 62 boards and the 24 random boards below |
| 18.1 Shen case like for like, Lumped / Analytic | +4.1 / +1.2 % (5fc91430) | +4.3 / +1.4 % | unit-cell solver 1.4611 K/W | re-measured |
| 18.2 zones, 36 family boards: via effect, mean / max | 3.8 / 9.1 % (2.4.5 to 2.5.0, against the 1/16 mm layered reference) | 3.8 / 9.5 % (36 within 10 %) | **FVM 0.25 mm** (not the 1/16 mm reference) | re-measured, reference changed |
| 18.2 zones, 26 held-out: via effect | 4.6 / 20.6 % | 4.9 / 21.4 % (23 within 10 %) | FVM 0.25 mm | re-measured |
| 18.2 family: hottest temperature | 2.6 / 7.2 % (0 too cool) | 2.86 / 7.56 %, range −0.89..+7.56 % (0 more than 2 % cool) | FVM 0.25 mm | re-measured |
| 18.2 held-out: hottest temperature | 1.6 / 7.6 % (1 too cool) | 1.73 / 8.08 %, range −1.93..+8.08 % (0 more than 2 % cool) | FVM 0.25 mm | re-measured |
| 18.2 3D check, profiles, the example board arrays | 2.5.0 | – | – | not re-measured |

Note: 30 of the 36 family boards and all 26 held-out boards are zoned by the program; the six one-node family boards read the via effect +3.6 to +6.5 % and the hottest +0.4 to +3.4 %.

### 2.2 Validation 31 (first ring)

| item | old (tree) | new | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| 31.1 30 x 20, 1 / 3 mm | +0.4 / +1.2 % (2.6.0) | +1.3 / +1.6 % | FVM 0.5 mm | re-measured, column added |
| 31.1 60 x 40 | +1.6 / +1.8 % | +3.3 / +2.3 % | FVM 0.5 mm | idem |
| 31.1 100 x 80 | +1.0 / −2.4 % | +3.1 / +2.1 % | FVM 0.5 mm | idem |
| 31.1 200 x 150 | +2.5 / −2.4 % | +4.6 / +2.3 % | FVM 0.5 mm | idem |
| 31 1 mm part, 100 x 80, against `layered3d.py` | Lumped 44.93 K against 44.81 K, +0.3 % | 45.87 K, +2.4 % (3D 44.81 K with eight sub-slabs, 44.86 K with two; FVM 44.55 K, −0.6 %) | independent 3D | re-measured; the earlier text said two sub-slabs for the 44.81 K, which is the eight-sub-slab value |
| 31.4 reconstructed boards (block, corner, half off the edge, across cell edges, strip) | −2.2, −5.9, −1.1, +2.1, −2.8 % (2.6.0) | +4.5, +2.4, +3.6, +1.9, +3.7 % (and −1.7 % for a 1 mm part 1 mm from a side) | FVM 0.5 mm | re-measured on boards rebuilt from the text (block contact resistance assumed 5 K cm2/W; the L outline not rebuilt) |
| 31.6 3 x 1 mm on 60 x 40 / 100 x 80 / 200 x 150 | +0.7..+6.3 / +10.1 / +9.3 % (up to +12.3 %) | +2.2 / +4.9 / +4.1 % | FVM 0.5 mm (0.25 mm on 100 x 80) | re-measured |
| 31.6 6 x 2 mm, 0.5 / 1 mm Lumped cell | −1.7 / +9.6 % (100 x 80), +12.0 % at 1 mm (200 x 150) | +0.9 / +3.7 % (100 x 80), +1.1 / +5.8 % (200 x 150) | FVM 0.5 mm | re-measured |
| 31.6 10 x 0.5 mm tab | −5.4 % | −1.9 % | FVM 0.5 mm | re-measured |
| 31.6 1 mm part at the 1 mm Lumped cell | −15 to −17 % | +2.4 % (100 x 80), +4.6 % (200 x 150) | FVM 0.25 / 0.5 mm | re-measured |
| 31.1 source sweep, 31.2 imported uniform sheets, 31.3 times, the cap sensitivity, the sub-cell part across a corner | 2.6.0 | – | – | **not re-measured** |

### 2.3 Validation 35.3 (small part, finer raster)

| item | old (tree) | new | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| refined raster, 26 cases, 0.2 to 2 mm, 0.5 and 1 mm requests | −6.7 to +3.7 % (`develop` 2.5.2); 0.2 to 0.3 mm parts 3.5 to 6.7 % cool | −0.1 to +3.7 % (28 cases incl. 1.5 mm at 0.5 mm) | FVM 0.0625 mm | re-measured |
| unrefined raster (the text of `checks.check_lumped_small_part`), sides 0.1 to 0.5 mm | −19 to +6 % | −12.7 to +5.9 % at 0.5 mm, −18.2 to −3.2 % at 1 mm | FVM 0.0625 mm | re-measured; the warning now says −18 to +6 % |
| 35.1 and 35.2 (near edge) | – | superseded by section 53 (measured on the final model) | – | not re-run here |

### 2.4 Validation 42 (via groups)

| item | old (tree) | new | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| 42.1 far via, n = 0..16, Lumped after | −0.001 K (2.7.0) | −0.001 / −0.000 K | FVM | unchanged |
| 42.3 a via one pitch beyond the array | +1.211 K | +1.228 K (two and three pitches −0.040, −0.013 K) | FVM −0.083 K | re-measured |
| 42.3 the 3 x 3 array on 40 mm, four layers | 32.06 K against 31.41 K | – | – | not re-measured (board not written down in full) |
| 42.5 24 random boards, Lumped via effect, mean abs. | 27.9 % (median 23.4 %) | 32.6 % (median 22.5 %) | FVM 0.25 mm | re-measured |
| 42.5 hottest rise mean abs., range | 1.74 %, −6.72..+5.53 % | 1.88 %, −7.56..+4.78 % (5 of 24 more than 2 % cool) | FVM 0.25 mm | re-measured |

### 2.5 Validation 48 (part read-out)

| board | old (read-out branch) | new | status |
| :-- | :-- | :-- | :-- |
| 12 mm pad and plate | −1.0 % | +1.2 % | re-measured |
| plain plane, 6 mm part | −1.1 % | +1.0 % | re-measured |
| two parts | −1.3 / +2.5 % | +1.6 / +4.9 % | re-measured |
| 6 mm part on two full planes | −0.6 % | +1.5 % | re-measured |
| two 2 W parts 2 mm apart | −3.4 / −0.6 % | −0.7 / +0.5 % | re-measured |
| L-shaped outline | −4.1 % | −0.8 % | re-measured (the outline of the test) |
| four full planes | −0.2 % | +1.9 % | re-measured |
| top path | −1.3 % | −0.7 % | re-measured |
| the edge, 12 x 2 mm, via, 4 x 4, four parts in a row, bare-laminate rows of 48.3 | – | – | not rebuilt (boards not written down in full) |

Reference: the FVM part rows at 0.5 mm (the same quantity, `heater_rows`).

### 2.6 Validation 50 (zone position)

| item | old (review of the folder) | new | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| zones as shipped, peak 3 x 3 / 5 x 5 | +0.78 / −0.75 % | −0.07 / −1.14 % | independent 3D at 0.0625 mm (from the 0.25 mm run, ratio of table 10.1) | re-measured |
| zones as shipped, mean | +0.62 / −0.57 % | −0.30 / −1.00 % | idem | re-measured |
| zone raster converged (0.125 mm), peak / mean | −1.52 / −2.35 %; −1.93 / −2.00 % (0.125 mm column) | −1.21 / −2.35 %; −1.59 / −2.00 % | idem | re-measured |
| one node, peak | +2.51 / +3.12 % | +1.65 / +2.72 % | idem | re-measured |
| placement range (eight diagonal shifts) | 1.79 / 1.04 points | 1.66 / 0.98 points (8 x 8: 0.48) | – | re-measured; the 66-case sweep (1 to 3 points) not re-run |

The shift (0.4 to 0.9 point cooler for every rule) was not traced to one item; the folder's review ran before the images of the sides were merged.

## 3. The imported-copper warning (`copper.REDUCED_MODEL_WARNING`, validation 27.7)

| item | old (tree) | new (7a3ca02e) | reference | status |
| :-- | :-- | :-- | :-- | :-- |
| 42 parts, Lumped / Analytic | 25 to 82 % / 17 to 77 % (2.5.x; six parts re-run on 5fc91430) | 82 parts (RP2040 27, oswlight 51, CO60 4): 23 to 76 % / 19 to 77 % | FVM 0.5 mm (not converged for an 0402) | re-measured on a larger set: the oswlight subset of 10 and the fifth CO60 part are not named in the folder, so every oswlight heat source was run and the four named CO60 parts |
| smallest parts | 39 to 81 % (0402 class) | 33 to 76 % / 30 to 77 % for the 57 parts with a side below 1.5 mm (0402 and 0603) | FVM 0.5 mm | re-measured |
| RP2040 whole board, 0.5 mm | Lumped −31 to −74 %, Analytic −22 to −75 % | −31.9 to −73.0 %, −26.6 to −75.5 % | FVM 0.5 mm | re-measured |
| U1 0.5 / 0.25 mm | −41.6 / −42.4 % and −33.6 / −34.6 % | −39.3 / −39.8 % and −34.1 / −34.7 % | FVM | re-measured |
| U3 1 / 0.5 / 0.25 mm | −27.2 / −31.2 / −26.8 % and −15.5 / −21.6 / −16.6 % | −26.2 / −31.9 / −27.0 % and −20.6 / −26.6 / −21.2 % | FVM | re-measured; the Analytic of U3 moved 5 points cooler (not traced) |
| CO60 per part | C1 −30 % uniform etc. | C1 −73.9 / −75.7, R1 −76.3 / −77.1, RGB1 −48.8 / −50.3, U1 −51.9 / −52.7 % | FVM 0.5 mm | re-measured (2.72 GB) |

## 4. Edited texts

* `pcbthermal/copper.py` `REDUCED_MODEL_WARNING`: '42 parts ... 25 to 82 % and 17 to 77 % ... (39 to 81 % for passives of 0402 size)' -> '82 parts ... 23 to 76 % and 19 to 77 % ... (33 to 76 % and 30 to 77 % for passives with a side below 1.5 mm, 0402 and 0603 size)'. Tests `tests/test_reduced_warning_text.py`, `tests/test_imported_copper.py` follow; the user guide (two places), `docs/models.md` and `docs/theory.md` 1.7 limits follow.
* `pcbthermal/checks.py` zoned-Lumped text: '1.6 to 2.6 % ... (up to 7.6 %) ... against a fine-grid layered solver' -> '1.7 to 2.9 % ... (up to 8.1 %, on the hot side but for a few parts within 2 %) ... against the finite-volume model at 0.25 mm'; the resolved 3D cluster (−2.4 / +1.0 %) keeps 'measured before the mirror images of the sides'. The user guide follows.
* `pcbthermal/checks.py` small-part text (three places) and the `lumped.small_part_cell` docstring: '−19 to +6 %' -> '−18 to +6 %' (0.5 or 1 mm raster); the user guide and `docs/theory.md` 5 follow.
* `docs/validation.md`: the head note, 18.1, 18.2, 27.7, 31.1 (column added), 31 3D check, 31.4, 31.6, 35.3, 42.3, 42.5, 48, 50; earlier values kept with their tree.
* `docs/theory.md`: 1.7 limits, 5 (first ring, small-part raster and its figure caption, zone position); `docs/models.md` 2.3 and 19.1.
* `README.md`: the Lumped column of 'Which model should I use?' -> '0.1 to 4.5 % (−4.5 % on a 20 mm one-sided pad, within 2.2 % on the other three boards)' (validation 3 as re-run by part 2b on da16d80f).
* No threshold, rule or formula was changed; the frozen numbers do not move (section 5).

## 5. What could not be re-measured

* Validation 18.1, the 29 + 17 via boards: no committed script builds them.
* Validation 18.2 against the independent 1/16 mm layered reference and the 3D check with barrels drawn (hours of reference solves; replaced here by the FVM at 0.25 mm, which is about 0.5 % under the converged 3D on these boards, `research/lumped-zone-placement` 10.2).
* Validation 31.1 source sweep, 31.2 (imported boards on the uniform sheet), 31.3 (times), the cap sensitivity, the sub-cell part across a corner; 31.4 L-shaped board.
* Validation 42.3, the 3 x 3 array board; 48.3, the rows whose boards are not written down in full.
* Validation 50, the 66-case sweep of the placement noise.
* The finite-element references of `research/independent-fem-extensions` (the scratch environment is not installed): the zoned cluster −2.4 / +1.0 % and the Lumped via effect next to a cooled wall (+11 to +31 %) stay of the earlier tree.
* The full `validation_study.py` (8.3 GB) was not run: section 2 of `validation.md` was already re-run by part 2b on da16d80f, which is this program.
* The imported-copper reference stays the FVM at 0.5 mm, not converged for 0402 parts (E13 open).

## 6. Tests

* `PCBT_FROZEN_CELLS=2 pytest -q tests/regression`: 153 passed (no record moves: text only).
* `tests/test_docs.py`, `test_license_header.py`, `test_version.py`, `test_help.py`, `test_warning_texts_plain.py`, `test_warning_context.py`, `test_tooltips.py`, `test_reduced_warning_text.py`, `test_imported_copper.py`, `test_lumped_near_edge.py`, `test_lumped_zones.py`, `test_no_fabricator_names.py`: 934 passed, 4 skipped.

## 7. Left for the maintainer

* `docs/versions.md` 'After 2.6.0' item 10 (re-measure the reduced-model warning) and the CHANGELOG were not edited (outside the scope of this branch); the item is done by section 3.
* The Lumped is now on the hot side on almost every simple board here (+1 to +5 %), the safe side; on the 24 irregular via boards of 42.5 it is a little worse than after the fix (via effect 32.6 % against 27.9 %, five boards more than 2 % cool, the worst −7.6 %, warned).
