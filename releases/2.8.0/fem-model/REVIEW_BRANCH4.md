# Review of FEM branch 4 (`feature/fem-model`)

Reviewer's record of the model branch: `pcbthermal/fem.py`, the key `fem` of `api.simulate`, `SolverOptions.fem_gap_elements` / `fem_refine`, the project keys `comparison_models` / `comparison_only`, `--model fem` / `compare`, `checks.check_fem`, the pending frozen records `fem-records.json` and the documents (commits c38400b8, aa947a09, 20c1f981 on `development` dfde802b). Every number below was printed on this machine by `releases/2.8.0/fem-model/scripts/study_review_branch4.py` (parts `flux`, `case2`, `converge`, `plain`, `hollow`, `hollow_research`) and the tests named, on the branch tree with the corrections of section 4 (none of them moves a number of section 3 except where said).

**Verdict: GO** for the merge into `development`, with the corrections of section 4 (committed with this file) and the open points of section 6 for the window branch.

## 1. Code against the theory (docs/theory.md 4a, DESIGN.md)

| Claim | Verdict | Evidence |
| :-- | :-- | :-- |
| Column = volume mean of the field over the copper slabs of a layer, per run cell, elements shared by plan overlap | holds | `fem._gauss_weights` (2x2x2 Gauss, `|det J|`), `_cell_shares` / `_to_cells` (the shares of a quad add up to 1); the 1D column test and the plain boards below |
| Surface = exact area mean on the outer face; point = hottest node | holds, **one defect corrected** | on a one-layer board the bottom 'surface' was the bottom of the laminate, not the copper face that `thickness.py` names (section 4.1) |
| Plain `h` at the boundary, no half cell; 1D column exact | holds | `tests/test_fem_model.py` 1D column to 1e-6 of the rise; `femmesh` faces carry `board.h_*`, `exposed_h`, `wall_h` |
| Energy balance an identity of the assembly | holds | printed 2e-15 to 6e-11 on every run of section 3 |
| Metal blocks | holds | `block_T`, extras; `w_to_air` = `w_to_block` is the same integral by construction (documented as an identity, not two measurements) |
| Computed h, top path, power coefficient wrap the FEM | holds | top path of the test board: FEM 0.741 W to the heatsink, FVM 0.743 W; computed h within 5 % of the FVM's (test) |
| Memory verdict before any 3D array; `FemUnavailable` a skipped model | holds | `memory.check(..., fem_params)` first in `solve_steady`; tests without pyamg |
| A solver failure leaves the other models running | **defect corrected** | a conjugate-gradient `RuntimeError` escaped `api._simulate` (only `ValueError` and `FemUnavailable` were caught) and stopped every model of the run (section 4.2) |
| Cancel | holds | `cancel` between assembly chunks (API test); the application cancels by stopping the job process (`jobs.py`), so `_run_model` needs no callback |
| Frozen numbers | holds | 346 passed at 2, 1 and 0.5 mm (317 old records untouched, 29 `fem` added; 204 s); after the corrections the 29 `fem` records pass again (62 s) |
| Project file | holds | `PCBT_COMPAT_V271=1` and `PCBT_COMPAT_V245=1`: 22 passed; a file with the FEM ticked opens in v2.7.1 with `models` `["fvm", "fdm"]`, the FEM-alone file opens there as the FVM; hostile values (11 cases) are a `ProjectFormatError` naming `solver`; a re-save in v2.7.1 drops the keys (documented) |

## 2. The decision: a part on thick outer copper as a face flux

**Recommendation: keep the face flux (the executor's choice) for a part on an outer layer thicker than 105 um; keep the volumetric source on inner layers and thin outer layers.**

* **Physics.** A part dissipates in its die and package; its heat reaches the board through the pads on the face it sits on, so on a plate the heat enters through that face. A volumetric source spreads the same power through the plate thickness, which is right only for heat generated in the copper itself (Joule heating of a busbar); the program has no such source type (a heater is a part), so the face flux is the right reading of what a heater is. An inner layer has no face a part sits on: volumetric is the only meaning there.
* **The other models.** The FVM and FDM put the power at the layer node (one value through the thickness: the two conventions are the same number there); the surface read-out of `thickness.py` takes the power as entering through the outer face (`src_top` in `q_top` on layer 1, `src_bot` on the last layer); the independent 3D solver (`research/solid3d-verification/lib/layered3d.py`) and case 2 of Muzychka, Culham and Yovanovich are a flux on the top face. The FEM face flux is the same convention as all three.
* **Measured** (`scripts/study_review_branch4.py flux` and `case2`; the volumetric variant is a copy of `femmesh.build` with the face-flux branch switched off):

| Board | FEM face flux: surface / column | FEM volumetric: surface / column | independent 3D (face flux): surface / column |
| :-- | :-- | :-- | :-- |
| 40 x 30 mm, 2 layers, 6 mm part 1 W, 35 um | 55.0827 / 55.0826 K | 55.0827 / 55.0826 | 55.3789 / 55.3779 (1 mm cells) |
| same, 100 um (one slab: the volumetric source is used) | 47.4359 / 47.4358 | 47.4359 / 47.4358 | 47.5490 / 47.5465 |
| same, 110 um (two slabs: the switch) | 47.0155 / 47.0131 | 47.0131 / 47.0131 | 47.1168 / 47.1141 |
| same, 400 um | 43.4937 / 43.4847 | 43.4847 / 43.4847 | 43.5231 / 43.5135 |
| case 2, surface of the 1 mm cell centred on each centroid (FR-4 film) | 97.467 / 103.851 / 101.327 / 99.992 degC | 95.436 / 99.231 / 97.571 / 97.095 | paper 97.40 / 103.82 / 101.28 / 99.94 (the film adds about 0.09 K) |

* **Continuity at the 105 um switch**: the switch itself moves the surface by 2.4 mK at 110 um (0.01 % of the rise) and the column by nothing; the 3D reference puts the surface 2.7 mK above its column there, the face flux 2.4 mK, the volumetric source 0. No jump that a user can see; the step from 100 to 110 um is the thickness, 0.42 K, the same in every column.
* **Where the volumetric source fails**: on a plate (case 2) the volumetric source makes the surface equal to the column (2.0 to 4.6 K below the paper, 2.0 to 4.7 K below the face flux); the face flux fails only for heat made inside the copper, which the program does not model.
* DESIGN.md (sources) is updated to say so.

## 3. Independent checks (numbers printed in this review)

**Case 2 (Muzychka, Culham and Yovanovich 2003).** The test of the branch read 97.40 / 103.82 / 101.28 / 99.94 degC, the paper to the printed digit, but **that agreement is two offsets that cancel**: (a) a one-layer `Problem` must carry a laminate (here 1 um of FR-4, k 0.3), which adds about 0.09 K (its resistance times the mean flux 28 kW/m2); (b) the test averaged a 2 x 2 cell window chosen with `round()`, which rounds 12.5 down and 37.5 up (to even), so the window is 0.5 mm off the centroid and about 0.07 K below it (the classic `round()` alignment defect). The 1 mm cell centred on the centroid reads 97.467 / 103.851 / 101.327 / 99.992 (column 95.436 / 99.231 / 97.571 / 97.095); the test now reads that cell and states the film. The node at the centroid, converged: 97.474 / 103.870 / 101.341 / 100.003 (cell 1, refinement 2), within 0.01 K from cell 2 to 0.5 and refinement 1 to 4 (828 000 unknowns at most). With the film made as conductive as the plate: **97.381 / 103.777 / 101.248 / 99.909** (cell 1) and 97.380 / 103.774 / 101.246 / 99.908 (cell 0.5, refinement 4): **0.02 to 0.05 K below the paper**. The centred column 95.436 / 99.231 / 97.571 / 97.095 against the independent 3D column means 95.35 / 99.15 / 97.49 / 97.01 (0.08 to 0.09 K above, the same film). The earlier statement 'to the printed digit' in the CHANGELOG, README, models, theory and decisions log was wrong as an explanation and is replaced; a node test is added.

**Plain boards against the FVM, the FDM and the 3D solid** (4 layers, 1 W 6 mm part, h 10, 2 mm cell; rise of the hottest cell, K): 60 x 40 mm FEM 34.129, FVM 34.270, 3D 34.299, FDM 34.270; 40 x 30 mm FEM 54.284, FVM 54.762, 3D 54.792, FDM 54.047. The hottest node is 35.312 and 55.080 K; at a 1 mm cell the column reads 34.988 and 54.758 (a smaller cell mean of the same field).

**What the 0.4 to 0.9 % is** (40 x 30 mm, 2 layers, 35 um, isotropic laminate 0.3 W/mK, insulated edge, heater surface mean, a quantity that does not depend on the cell): the FEM converges from below, 55.003 / 55.083 / 55.104 / 55.108 K (fine element 1 / 0.5 / 0.25 / 0.25 mm), the independent finite volumes from above, 55.379 / 55.183 / 55.134 K (1 / 0.5 / 0.25 mm, order 2); both meet at about 55.12 K. At the default mesh the FEM is 0.06 % low and the finite volumes at 1 mm 0.5 % high: the gap between the FEM and the FVM is mostly the finite volumes. Six or twelve elements across the gap give the same number to 0.1 mK.

**Hollow via against the research FEM** (the 10 x 10 mm four-layer strong-edge board: 0.5 W on 3 x 2 mm at (1..4, 4..6) mm, h 10 / 200 / 200 on the edge, FR-4 0.3; one open via of 0.3 mm drill and 25 um plating at (7, 5) mm; the program meshes it as a patch, 0 rods): effect of the via on the hottest node 1.422 / 1.428 / 1.436 K (program FEM at cell 1 / 0.5 / 0.25 mm) against 1.431 / 1.434 K (research tool `independent-fem-extensions`, fine size 0.2 / 0.1 mm); on the heater surface mean 1.475 / 1.481 / 1.482 against 1.476 / 1.481 K. Absolute: hottest node without the via 36.896 K (0.25 mm) against 36.932 (research 0.1 mm), heater mean 35.448 against 35.489 (0.1 % apart).

**Reproducibility.** Conjugate gradients against the direct solve on four meshes (12 558 to 80 500 unknowns): 6e-10 to 1.8e-9 K, the largest difference over every cell. Peak resident memory of the process 0.39 to 0.81 GB on 12 000 to 80 000 unknowns. Time: 1 to 2 s at 22 000 to 84 000 unknowns, 4 s at 147 000, 8 s at 315 000 (case 2, with pyamg); the README's '5 s at 92 000 unknowns' had no script behind it and is replaced.

## 4. Corrections made in this review

1. **One-layer bottom surface** (`fem.py`): the bottom face of a one-layer board is now the face of its copper on the laminate (the meaning of `thickness.py`); the bottom of the laminate stays `extras["bottom_face_mean"]` (the computed-h loop, unchanged value). Before, an ordinary 40 x 30 mm one-layer 35 um board with 1 W printed 'Hottest surface (bottom): 73.3 degC ... -6.8 K' in its report, the laminate drop under the name of a copper surface. Test `test_a_one_layer_board_reads_the_copper_face_not_the_laminate_bottom`. No frozen record moves (the records hold no surface).
2. **A solve that does not converge** (`fem.py`, `femcore.py`): the case-2 plate with a conductive film at 828 000 unknowns stopped with 'the conjugate-gradient solution has a relative residual of 1.12e-08' as a raw `RuntimeError` that `api._simulate` does not catch, so the FVM of the same run was lost too. Now `femcore` restarts the conjugate gradients once from the solution when the true residual is above the bound (that case then solves: 97.380 / 103.774 / 101.246 / 99.908), and `fem.solve_steady` turns a remaining `RuntimeError` into a `ValueError` with the reason, so the API leaves the FEM out with a warning beside other models. Test `test_a_solve_that_does_not_converge_leaves_the_fem_out_and_the_other_models_answer`. No number moves (the restart runs only where the old code raised).
3. **Documents**: case 2 'to the printed digit' replaced by the converged node and the cancellation (CHANGELOG, README, `docs/models.md`, `docs/theory.md` 4a, `docs/decisions-log.md`, test comments); the 0.4 to 0.9 % explained by the convergence measurement; the review's checks added to theory 4a 'Where it is checked'; the README time replaced by measured times; the user guide no longer says the surface of a metal block is resolved (a block reports its mean through the thickness, as in the other models); 'a part is a source in the copper' completed with the face flux (theory, models); DESIGN.md sources updated (section 2).
4. **Figure 52**: the right edge of the 'solve' box was cut by the axes; redrawn (`make_diagrams.py 52`) and looked at.
5. Tests: `test_case_2_of_muzychka_the_resolved_surface_meets_the_paper` now reads the 1 mm cell centred on the centroid (was a 2 x 2 window 0.5 mm off by `round()`), and `test_case_2_the_converged_node_at_the_centroid_meets_the_paper_with_a_conductive_film` is new (both with pyamg).

## 5. Tests run

`tests/test_fem_*.py`, `test_api.py`, `test_project_file_fuzz.py`, `test_project_format2.py`, `test_format_compat_245.py`, `test_format_compat_271.py`, `test_memory.py`, `test_docs.py`, `test_license_header.py`, `test_version.py`, `test_help.py`, `test_tooltips.py`, `test_thickness.py`, `test_no_secrets.py`: 1069 passed, 6 skipped (the gates); the two compatibility gates on: 22 passed; frozen numbers at 2, 1 and 0.5 mm: 346 passed (before the corrections), the 29 `fem` records again after them: passed. There is no `test_cli*.py` file; the command line is tested inside `test_fem_model.py` and `test_api.py`. The whole battery was not run (not asked; it is the maintainer's step before the merge).

## 6. Not verified, and left for the window branch

* Not verified: the FEM on imported copper (Gerber boards, the real-board environment not loaded here); the memory law against the peaks printed above (only the verdict tests ran); a part over bare laminate on thick copper (the face flux then enters a laminate face; not measured); the power coefficient loop with the FEM beyond the test.
* For the window branch (5): the tooltip of DESIGN.md section 6 says 'within about 0.2 % of the FVM and the 3D solid ... reads the surface of thick copper and blocks': use the measured numbers (0.4 to 0.9 % below at the same cell, mostly the finite volumes' error; no block surface); the Layer entry 'Surface (bottom)' of a one-layer board now shows the copper face; `arrays["T_point"]` is not shown anywhere yet; the branch `docs/surface-readout-help` (not merged) says the FEM 'will resolve' the surface: on its merge it must say 'resolves' (true on this branch).
* For the maintainer: whether the frozen records should one day hold the surface read-out of the FEM (they hold the column only, so a change of the surface is not caught by the frozen numbers; the tests above hold it).
