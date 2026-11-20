# FEM thin copper: a part on an outer layer enters through its face (items e20 and e21)

Branch `fix/fem-thin-copper-source`, from `development` db6244b1 (the tree "before"); the tree "after" is this branch. Every number below was printed by a command listed in section 6.

## 1. The defect, reproduced

`research/surface-readout-models/scripts/study_fem_thin_source.py` on the tree before (cells 2, 1, 0.5 mm; term = surface minus column under the part; 35 um copper, 20 x 20 mm board, insulated top and sides):

| board | q t / 2k | FVM | FEM before | FEM after |
| :-- | --: | --: | --: | --: |
| 4 W part over the whole face (one-dimensional, exact 1.00) | 0.455 mK | 0.455 mK (1.00) | 0.227 mK (0.50) at every cell | 0.455 mK (1.00) at every cell |
| 1 W part of 4 x 4 mm, cell 2 / 1 / 0.5 mm (physical range 0.67 to 1.00) | 2.841 mK | 1.970 / 1.971 / 1.971 mK (0.69) | 0.135 / 0.153 / 0.156 mK (0.05) | 1.369 / 1.558 / 1.576 mK (0.48 / 0.55 / 0.55) |

Cause (`femmesh.build`): a layer of one slab (copper up to 105 um) took the power of a part as a volumetric source in the slab, and one linear element through the copper carries half of such a load at its bottom node. Above 105 um (several slabs) the part was already a face flux.

## 2. The fix

`pcbthermal/femmesh.py`, `build`: the part of a heater on the top or the bottom copper layer is a prescribed flux `q''_e = P s_e / W` over the faces of the outer slab, whatever the thickness (the condition `len(slabs) > 1` is removed; it now needs only one slab). An interior layer has no face to load and keeps the volumetric source. `heater_loads` / `load_vector` (the transient) already read `heater_flux`, so the unit load of the transient is the same face load, the capacity (`sum(M)`) is not touched (no element, material or mass changes), and `fem.solve_transient` ends on the steady column (test). Comments and docstrings of `femmesh.py` and `fem.py` say "outer layer" instead of "thick outer layer".

## 3. Plates against the independent solver (cell 1 mm)

`scripts/study_fem_thin_copper.py --tree <tree>`: 50 x 50 mm two-layer board, top copper of 18 to 105 um, 1 mm laminate of 0.3 W/mK, 35 um bottom copper, 10 W/m2K below, insulated top; a 1 W square part. Reference `tests/helpers/layered3d.py` (8 sub-slabs through the copper, 4 through the laminate, 1 mm in the plane); the FVM is the program's. The tree "before" is `development`, run with `--tree`.

| top copper (um) | part (mm) | q t / 2k (mK) | independent term (mK) | FVM term (mK) | FEM term before (mK) | FEM term after (mK) | FEM column shift (mK) |
|--:|--:|--:|--:|--:|--:|--:|--:|
| 18 | 2 | 5.844 | 4.046 (0.69) | 3.994 (0.68) | 0.160 (0.03) | 2.678 (0.46) | +0.160 |
| 18 | 4 | 1.461 | 1.053 (0.72) | 1.040 (0.71) | 0.105 (0.07) | 0.828 (0.57) | +0.105 |
| 18 | 8 | 0.365 | 0.284 (0.78) | 0.281 (0.77) | 0.058 (0.16) | 0.240 (0.66) | +0.058 |
| 35 | 2 | 11.364 | 7.767 (0.68) | 7.687 (0.68) | 0.180 (0.02) | 5.073 (0.45) | +0.180 |
| 35 | 4 | 2.841 | 1.992 (0.70) | 1.972 (0.69) | 0.123 (0.04) | 1.529 (0.54) | +0.123 |
| 35 | 8 | 0.710 | 0.525 (0.74) | 0.521 (0.73) | 0.073 (0.10) | 0.428 (0.60) | +0.073 |
| 70 | 2 | 22.727 | 15.406 (0.68) | 15.276 (0.67) | 0.199 (0.01) | 9.974 (0.44) | +0.199 |
| 70 | 4 | 5.682 | 3.913 (0.69) | 3.878 (0.68) | 0.142 (0.03) | 2.954 (0.52) | +0.142 |
| 70 | 8 | 1.420 | 1.014 (0.71) | 1.005 (0.71) | 0.090 (0.06) | 0.800 (0.56) | +0.090 |
| 105 | 2 | 34.091 | 23.027 (0.68) | 22.860 (0.67) | 0.213 (0.01) | 14.846 (0.44) | +0.213 |
| 105 | 4 | 8.523 | 5.831 (0.68) | 5.781 (0.68) | 0.155 (0.02) | 4.375 (0.51) | +0.155 |
| 105 | 8 | 2.131 | 1.499 (0.70) | 1.487 (0.70) | 0.102 (0.05) | 1.168 (0.55) | +0.102 |

The FEM energy balance is below 1e-10 in every case, before and after. The FEM column under the part is 0.05 to 5.2 K below the independent column (the largest on the 2 mm part at this 1 mm cell), before and after alike: the fix changes it by the last column only (0.06 to 0.21 mK).

**Review: the 5.2 K is the resolution of the 1 mm finite-volume reference, not an FEM defect.** Thin copper under a small part has a steep, nearly logarithmic in-plane profile (the sheet conductance of 18 um of copper is 0.007 W/K), and a cell-centred finite-volume cell of 1 mm reads it high. The independent solver on the 18 um, 2 mm case, its column averaged over the same 1 mm cells (scratch probe of the review, not committed; 4 sub-slabs through the copper): 115.72 degC at a 1 mm cell, 112.30 at 0.5 mm, 111.39 at 0.25 mm (converging toward about 111.1); the FEM at a 1 mm cell reads 110.52, so it is about 0.6 to 0.9 K below the converged area mean, not 5.2 K; the FVM at 1 mm reads 115.47, like the finite-volume reference at the same cell. The term of the reference at those cells is 4.13, 4.12, 4.12 mK.

**Review: what the remaining 0.2 of the term is.** The same three cases with more elements through the copper (a scratch probe of the review that replaced `femmesh.copper_slab_count` by at least 2 or 4; not a program change), cell 1 mm, term in mK: 18 um / 2 mm: 2.678 (1 element), 3.267 (2), 3.414 (4), reference 4.046; 35 um / 4 mm: 1.529, 1.850, 1.930, reference 1.992; 105 um / 2 mm: 14.846, 18.461, 19.366, reference 23.027. The column moves by less than 0.1 mK. So most of the residual is the one element through the copper, as stated; the rest on the 2 mm parts is the plan resolution (the 18 um / 2 mm term is 3.076 mK with one element at a 0.5 mm cell).

The FEM term now reads 0.44 to 0.66 of `q t / (2 k)` against 0.68 to 0.78 for the independent solver: the sideways spreading inside the copper (heat that leaves the face sideways rather than down) cannot be represented by one linear element through the copper, which reads `q_down t / (2 k)` with `q_down` the local flux that goes down. This stays after the fix; it is a mesh matter (two or more elements in thin copper would remove it, at a cost on every FEM number and on the memory law), a proposal and not done here.

## 4. Why the harness boards move, and by how much

Frozen FEM steady records (`v2.8.0.json`, 38 records, cells 2, 1 and 0.5 mm) against the tree after (`tests/regression/data/pending/fem-thin-copper-source.json`; part rows, column `t_max` and the term `t_max_surface - t_max`):

| board | model | cell (mm) | part | column t_max before (degC) | after (degC) | shift (mK) |
|:--|:--|--:|:--|--:|--:|--:|
| drawn_ell | fem | 0.5 | U | 118.8488 | 120.3247 | +1475.86 |
| drawn_ell | fem | 1 | U | 108.0215 | 109.0556 | +1034.17 |
| drawn_ell | fem | 2 | U | 89.3190 | 89.4254 | +106.37 |
| drawn_inset_square | fem | 0.5 | U | 84.3204 | 84.3205 | +0.12 |
| drawn_inset_square | fem | 1 | U | 83.3718 | 83.3719 | +0.11 |
| drawn_inset_square | fem | 2 | U | 80.9581 | 80.9581 | +0.09 |
| drawn_stripes_pad | fem | 0.5 | U | 100.6713 | 100.6715 | +0.17 |
| drawn_stripes_pad | fem | 1 | U | 99.4543 | 99.4544 | +0.16 |
| drawn_stripes_pad | fem | 2 | U | 96.4137 | 96.4139 | +0.15 |
| example_board | fem | 2 | U1 | 83.6383 | 83.6388 | +0.53 |
| example_board | fem | 2 | U2 | 71.8098 | 71.8100 | +0.20 |
| example_cut_to_T | fem | 2 | U1 | 92.7132 | 92.7138 | +0.53 |
| example_cut_to_T | fem | 2 | U2 | 80.9844 | 80.9846 | +0.20 |
| finned_block | fem | 1 | U | 130.2106 | 130.2108 | +0.27 |
| finned_block | fem | 2 | U | 129.0986 | 129.0989 | +0.26 |
| hatched_copper | fem | 1 | U | 111.9100 | 111.9103 | +0.31 |
| hatched_copper | fem | 2 | U | 110.9335 | 110.9338 | +0.31 |
| one_layer_full | fem | 1 | U | 55.2783 | 55.2783 | +0.01 |
| one_layer_full | fem | 2 | U | 54.6795 | 54.6795 | +0.01 |
| one_layer_pad | fem | 1 | U | 91.8830 | 91.8830 | +0.02 |
| one_layer_pad | fem | 2 | U | 90.3031 | 90.3031 | +0.02 |
| part_across_outline | fem | 0.5 | U | 229.9406 | 229.9409 | +0.34 |
| part_across_outline | fem | 1 | U | 229.4907 | 229.4911 | +0.34 |
| part_across_outline | fem | 2 | U | 227.2744 | 227.2747 | +0.34 |
| part_top_path | fem | 1 | Q1 | 73.8199 | 73.8200 | +0.04 |
| part_top_path | fem | 2 | Q1 | 73.6430 | 73.6431 | +0.04 |
| plate_lone_via | fem | 1 | U | 149.8549 | 149.8553 | +0.40 |
| plate_lone_via | fem | 2 | U | 148.9156 | 148.9160 | +0.36 |
| plate_pad | fem | 1 | U | 345.0866 | 345.0868 | +0.24 |
| plate_pad | fem | 2 | U | 339.0603 | 339.0605 | +0.23 |
| plate_uniform | fem | 1 | U | 159.0061 | 159.0063 | +0.25 |
| plate_uniform | fem | 2 | U | 156.4071 | 156.4074 | +0.24 |
| plate_vias | fem | 1 | U | 134.6718 | 134.6726 | +0.77 |
| plate_vias | fem | 2 | U | 133.6248 | 133.6256 | +0.77 |
| profile_board | fem | 2 | U1 | 83.6383 | 83.6388 | +0.53 |
| profile_board | fem | 2 | U2 | 71.8098 | 71.8100 | +0.20 |
| reference_board | fem | 2 | Heater 1 | 89.8991 | 89.8992 | +0.09 |
| t_outline | fem | 1 | U | 186.7929 | 186.7930 | +0.14 |
| t_outline | fem | 2 | U | 186.0827 | 186.0828 | +0.14 |
| two_layer_partial | fem | 1 | U | 162.8268 | 162.8270 | +0.21 |
| two_layer_partial | fem | 2 | U | 161.2795 | 161.2797 | +0.20 |

Explanation of the shifts. (1) The column rises by 0.01 to 0.8 mK on the boards whose part sits on copper (the face load sits at the top of the slab, and the column is the slab mean), and the term grows by roughly its own size (0.1 to 2.5 mK). (2) `drawn_ell`: its 4 mm part straddles the corner where the top copper is absent (1.2 x 1.2 mm of the 4 x 4 mm footprint); there the slab under the part is a 35 um laminate slab (k 0.3 W/mK through) and the face flux now crosses it entirely: the term of the hottest cell goes from 1.48 to 3.30 K at 0.5 mm and the column of that cell by +0.106, +1.034, +1.476 K at 2, 1, 0.5 mm (at 2 mm the corner is averaged into cells that are partly copper, hence the small move). The independent check is now a committed script (`scripts/study_drawn_ell_corner.py`, run by the review on the tree before, `development` db6244b1, and on this branch). Part A is the board of `drawn_ell` with no edge film (the sides of `layered3d` are insulated) and a laminate of 0.3 W/mK in every direction; the reference has 8 sub-slabs through the top copper, 6 through the laminate, the copper patterned per cell and the film under the part (hottest column and hottest surface under the part, degC; term in K):

| cell (mm) | reference column | term | FVM column | term | FEM before: column | term | FEM after: column | term |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0.4 | 260.246 | 3.441 | 244.240 | 0.000 | 243.084 | 1.564 | 244.675 | 3.338 |
| 0.2 | 255.824 | 3.447 | 242.444 | 0.000 | 245.673 | 1.588 | 247.288 | 3.408 |

The FEM term now matches the reference within 3 % (it was half of it), and the FEM column moves toward the reference by 1.6 K (gap 17.2 -> 15.6 K at 0.4 mm, 10.2 -> 8.5 K at 0.2 mm). The column of the hottest cell of a corner is not converged in any model at these cells: the reference falls with the cell (260.2 -> 255.8) and the FEM rises (244.7 -> 247.3), so the converged value lies between them; it is not a quantity to read to the kelvin. The FVM's surface read-out over absent copper equals its column (term 0.000 K, the estimate of `thickness.py` uses the copper of the layer); the reference says 3.4 K: a limit of the FVM's surface estimate over bare laminate, recorded here and not part of this fix.

Part B, the frozen board as it is (edge film 200 W/m2K, default materials), hottest column under the part (degC) and FEM term (K):

| cell (mm) | FVM | 3D solid | FEM before | term | FEM after | term |
|--:|--:|--:|--:|--:|--:|--:|
| 2 | 96.432 | 91.074 | 89.319 | 0.105 | 89.425 | 0.232 |
| 1 | 127.681 | 142.477 | 108.022 | 1.029 | 109.056 | 2.280 |
| 0.5 | 116.327 | 129.457 | 118.849 | 1.481 | 120.325 | 3.296 |

On this board the column under the part depends strongly on the cell in every model (the FVM 96 -> 128 -> 116, the 3D solid 91 -> 142 -> 129: the copper edge at 10.8 mm cuts cells of 2 and 1 mm differently); only the FEM rises monotonically, and its move by the fix (+0.1, +1.0, +1.5 K) is small against the spread of the models. The record is a stress case for cut cells, not a converged number. (3) `plate_lone_via` and `plate_vias` have the largest terms among the copper boards (1.1 to 1.5 mK before, 2.9 to 3.3 mK after at the finer cells); the reason (a via under the part changes the local flux through the copper) was not investigated.

Times to 63 % of the FEM step response (the 16 `fem|` entries of `fem-transient`, moved in the same pass: one record in one file, so `fem-transient.json` was regenerated with `make_pending.py --new-times fem` on the tree after and carries them; the note in its `why` says so):

| board | part | before (s) | after (s) | relative |
|:--|:--|--:|--:|--:|
| drawn_ell | U | 23.1679 | 23.0969 | -3.1e-03 |
| drawn_inset_square | U | 27.2757 | 27.2756 | -3.9e-06 |
| drawn_stripes_pad | U | 22.9438 | 22.9437 | -5.1e-06 |
| finned_block | U | 14.6423 | 14.6421 | -1.6e-05 |
| hatched_copper | U | 18.4839 | 18.4837 | -1.3e-05 |
| one_layer_full | U | 22.0568 | 22.0567 | -4.0e-06 |
| one_layer_pad | U | 59.3086 | 59.3085 | -1.2e-06 |
| part_across_outline | U | 34.2702 | 34.2700 | -5.6e-06 |
| part_top_path | Q1 | 15.9805 | 15.9804 | -7.2e-06 |
| plate_lone_via | U | 21.6672 | 21.6670 | -1.3e-05 |
| plate_pad | U | 60.3013 | 60.3012 | -1.7e-06 |
| plate_uniform | U | 20.4597 | 20.4595 | -8.8e-06 |
| plate_vias | U | 32.9480 | 32.9473 | -2.3e-05 |
| reference_board | Heater 1 | 18.7130 | 18.7130 | -4.9e-06 |
| t_outline | U | 48.2072 | 48.2071 | -2.0e-06 |
| two_layer_partial | U | 24.9409 | 24.9408 | -5.1e-06 |

The biggest shift is `drawn_ell` (the laminate slab under the corner, as above); the rest are 1e-6 to 2e-5 of the value.

## 5. Proof

* `tests/test_fem_thin_copper_source.py`: six tests of the executor (the review added two, section 8), three of them fail on the tree before (the mesh holds a face flux; the one-dimensional board reads `q t / 2k` to 1e-6 relative at 5 and 2 mm; the 4 mm part within 0.6 to 1.05 of the independent term and above 8 times the old volumetric term) and pass after; the column against the numbers of the tree before to 1e-3 K (1076.001026 and 299.588221 degC at cell 2 mm; after: 1076.001253 and 299.588338); the energy balance below 1e-9; `F @ powers` equals the steady load; the FEM power step ends on the steady column within 1e-3 of the rise.
* Tests that changed because the load moved: `test_a_one_dimensional_column_is_exact_and_the_film_is_the_plain_h` (the closed form now has the part at the top face: `q_up = q B / (1/h_top + B)` with `B = 1/h_bottom + d/k_z + 2 t / k`, met to the same 1e-6), the surface lines of two tests of `tests/test_fem_model.py` (`+0.001 K`, `-0.001 K` instead of `+0.000 K`), and the two mesh tests that summed `q * V` (now `_power_loaded`, the unit loads times the powers).
* `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_fem_model.py tests/test_fem_mesh.py tests/test_fem_port.py tests/test_fem_transient_load.py tests/test_fem_transient_port.py tests/test_fem_transient_closed_forms.py tests/test_fem_profile_adapter.py tests/test_fem_thin_copper_source.py` green; `tests/test_published_cases.py`, `tests/test_solid3d_pad_inplane.py`, `tests/test_solid3d_copper_slabs.py`, `tests/test_models_part_table.py`, `tests/test_fem_memory.py`, `tests/test_fem_transient_memory.py`: 78 passed, 1 skipped.
* Frozen: `PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression -k "fem or pending"`: 58 passed (38 steady FEM records, 16 FEM times, the pending-file tests).

## 6. Commands

* `.venv/bin/python research/surface-readout-models/scripts/study_fem_thin_source.py` (section 1).
* `.venv/bin/python releases/2.9.0/fem-thin-copper/scripts/study_fem_thin_copper.py --tree <tree> [--json file]` (section 3; "before" with `--tree` the root of a checkout of `development` db6244b1).
* `.venv/bin/python releases/2.9.0/fem-thin-copper/scripts/study_drawn_ell_corner.py --tree <tree> [--json file]` (section 4, `drawn_ell`; about 30 s).
* `.venv/bin/python tests/regression/make_pending.py fem-thin-copper-source --board <the 19> --model fem --no-times ...` and `... fem-transient --board <the 16> --new-times fem ...`.

## 7. The documents

`docs/theory.md` 4a: the sentence "through 35 um the volumetric source and the face flux differ by micro-kelvin" is corrected (item e21): true for the column of a part over copper (0.06 to 0.2 mK on the plates), not for the surface minus column term, which read 0.50 of `q t / 2k` (one-dimensional) and 0.02 to 0.16 under a small part before the fix; what holds after: the face flux, `q'' = P s / W`, the exact one-dimensional term, 0.44 to 0.66 under a small part (limit of one element through the copper). `docs/theory.md` 4a "Sources and films" and "Range and limits", `docs/models.md` (the FEM read-outs and limits), `CHANGELOG.md` (Unreleased, Fixed), `docs/versions.md`, `docs/decisions-log.md`. `docs/USER_MANUAL.md` and `pcbthermal/help/index.html` were searched for FEM surface numbers and thin-copper behaviour (`FEM`, `surface`, `thin`, `volumetric`, `105`, `micro-kelvin`): they quote none (only "resolved" for the FEM surface), so they are unchanged. The research folders (`research/surface-readout-models`, among them its `INTEGRATION.md` section 9) are not edited: this fix is the adoption of its proposal D (a face flux for every part on an outer copper layer, with a pending file); the research folder stays as the record.

## 8. Review

Done by the reviewer on this branch (the numbers of sections 1, 3 and 4 re-run and reproduced to the printed digits: the twelve plates, the 38 frozen records and 16 times through `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression -k "fem or pending"`, 58 passed; `tests/test_fem_*.py`, 151 passed):

* The load is right in sign, place and size: the closed form of the one-dimensional board is met to 1e-6 for a part on the top face (`tests/test_fem_model.py`) and, added by the review, for a part on the BOTTOM face (`test_a_bottom_layer_part_enters_through_the_bottom_face`: the bottom film, the top film and the term `q_up t / (2 k)` of both faces, mirrored); a part on an interior layer keeps the volumetric source (`test_an_interior_layer_part_keeps_the_volumetric_source`). A one-layer board has its copper on top, so the face is the top face (`femmesh._slabs`). A part under a top block loads the copper face that the pad also touches, as the thick-copper path of 2.8.0 did and as the FVM puts the source in the copper node.
* The three test changes of the executor are legitimate: the closed form was re-derived for the face load (same 1e-6 tolerance), the surface lines now pin the new rounded values (+0.001 K, -0.001 K) instead of +0.000 K, and the two mesh tests sum the unit loads instead of `q V` (a face flux has no `q`); none is looser than before.
* `fem-transient.json`: only the 16 `t63` values (class `new`, records that no frozen file holds) and the `why` changed; regenerating them in that file is the rule of one record in one file (`CLAUDE.md` 6), so it is legitimate.
* The 5.2 K column gap and the residual 0.2 of the term are explained in section 3; `drawn_ell` in section 4 with a committed script.
* Wording: the FEM surface was called *resolved, not an estimate* everywhere; through copper of one element (up to 105 um) its difference to the column is about a third low under a part a few millimetres wide. The help, the tooltip of the surface column, the user manual and `docs/theory.md` now say so.
* Decision of the review: ship this fix in 2.9.0 with the residual stated; two or more elements through thin copper is a proposal for later (it would move every FEM term and unknown count and the memory law, for a difference of 0.04 to 8 mK per watt on the plates; the comparison campaign measures it).

## 9. What was not verified

* Only the tests listed in section 5 and the review's runs were run, not the whole battery. The GUI tests of the FEM, `test_gui_stress.py` and `test_help.py`/`test_user_manual.py` are the maintainer's battery (the review ran `test_help.py`, `test_tooltips.py`, `test_user_manual.py` and `test_docs.py` after its wording changes).
* The independent reference for `drawn_ell` at 0.1 mm (640 000 unknowns) was started and stopped for the load of the machine; the corner column is therefore bracketed (section 4), not converged.
* The convergence probes of section 3 (reference at 0.5 and 0.25 mm, two and four elements through the copper) are scratch probes of the review, not committed scripts.
