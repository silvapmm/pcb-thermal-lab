# Design of the FEM comparison campaign (validation 56 and 57)

Tree at the start: `development` 7886ac42 (2.8.0 plus the FEM transient, the copper slabs of the 3D solid, the pad defect of the 3D solid and the new default stepping of the FVM and FDM transient, Crank-Nicolson with the Rannacher start). Branch `release/2.9.0-fem-campaign`. Nothing in this note is a result.

## 1. Where the definition comes from (nothing here is invented)

`docs/validation.md` (line 14) says only that sections 56 and 57 are reserved for the campaign of `releases/2.8.0/fem-model/COMPARE_PLAN.md`. That file is the definition: rows C1 to C8 (steady, section 56.1 to 56.8) and T1 to T3 (transient, 57.1 to 57.3), with 'tolerances to confirm'. `releases/2.9.0/PLAN.md` adds: row c (the campaign runs after the two 3D-solid number-moving changes, so it measures the tree that ships), e30 (validation 57 must state on its first line whether a published transient case was reproduced; the text is `research/transient-published-case/INTEGRATION.md` item 1, used verbatim), the correction of `docs/theory.md` 4b and of the test docstring (done in the first commit of this branch), and 'new corrections found by the campaign are proposals in `INTEGRATION.md`, never made here'. The campaign is against independent solvers and published cases, not measurements.

## 2. What each validation compares

**Validation 56, the steady FEM against the other models and the independent references.** Quantity: the rise above the ambient of the hottest column temperature (`t_max - ambient`), the part means and the heat balance; differences always in K and as a share of the rise, signed (model minus reference). Models: FVM, FDM, Lumped, Analytic, 3D solid, FEM (keys `fvm fdm lumped analytic solid3d fem`). Reference per row: the independent finite elements and the exact or published values named below; the program's own FEM and FVM are compared with each other too, but never as the only reference.

| row | question | boards, cells | reference | data |
| :-- | :-- | :-- | :-- | :-- |
| 56.1 (C1) | Do the six models agree on every board of the frozen suite? | the 20 boards of `tests/regression/regress_boards.py` at 2, 1 and 0.5 mm (those above the model's cap skipped and listed) | FEM and, where one exists, the independent layered 3D solver of the four reference boards (`REFERENCE_SPECS`) | `study_compare_c1.py` (the harness code of `tests/regression/regress_harness.py`, steady only) |
| 56.2 (C2) | The surface and part-point read-outs | the same records (the surface map and the part `t_max_surface`, `t_mean_surface`) | FEM and 3D solid against the FVM and FDM estimate | the same run, `study_compare_c1.py report` |
| 56.3 (C3) | Case 2 of Muzychka, Culham and Yovanovich (2003) | the published plate (50 x 50 x 10 mm, four sources) and its cross | the independent 3D solver of `research/muzychka-case2-analytic/lib/case2.py` (column mean) and the paper's printed values (surface) | `study_compare_c3.py` |
| 56.4 (C4) | Published cases already in `docs/validation.md` | the cases that all six can represent, taken from `tests/test_published_cases.py` | the published numbers | `study_compare_c4.py` (decided after reading the test file, stage 3) |
| 56.5 (C5) | Thick plates and blocks | `finned_block`, the thick plate of `checks.check_thick_plates` | the independent finite elements (`research/independent-fem-edge`) and the heat balance | no separate script: covered by 56.3, 56.4 and `finned_block` of 56.1 (56.5; the thick-plate bound and the Lee plate were not run in the FEM) |
| 56.6 (C6) | Thin copper boards | the plain boards of C1 (a subset of the same records) | no difference beyond 1 % expected | `report` of C1 |
| 56.7 (C7) | Vias | `plate_vias`, `plate_lone_via`, the example board; the research cases of `independent-fem-extensions` | the via effect (rise without minus rise with) of the independent finite elements | `study_compare_c7.py` |
| 56.8 (C8) | Edge film | a strong edge film on a rectangle and the drawn boards (200 to 2000 W/m2K) | the finite elements of section 46 of the validation | `study_compare_c4.py edge` (as run) |

**Validation 57, the FEM transient.** Models: FVM, FDM, Analytic, Lumped, FEM (the 3D solid has no transient). The stepping of the FVM and FDM is the 2.9.0 default (Crank-Nicolson, Rannacher start, first stage in quarters), so a difference to the FEM is no longer the first-order time error of 2.8.0.

| row | question | cases | reference | data |
| :-- | :-- | :-- | :-- | :-- |
| 57.0 | The published case (first line of the section, the reviewer's text verbatim) | NAFEMS T3 (36.60 degC at x = 0.08 m, t = 32 s) | the exact series 36.6031 degC, the method of lines, the published MOOSE mesh results (`research/transient-published-case/lib/exact1d.py`) | `study_compare_t0.py` |
| 57.1 (T1) | Step response, time to 63 % and plateau | `plate_uniform`, `plate_vias`, `finned_block`, `reference_board`, `example_board` (where the FEM mesh allows), `part_top_path` | the FEM and `reference_in_time` (the same network without its time-step error), the exact Robin plate series for the plate | `study_compare_t1.py` |
| 57.2 (T2) | Profiles | one square wave per board class, slow (about 1/10 of the time to 63 %) and fast (20 Hz), peak, swing, last-window curve | the converged FEM (the profile with halved steps) | `study_compare_t2.py` |
| 57.3 (T3) | First seconds | a small source on a bare plate | the semi-infinite closed form (Lienhard, eqn 5.56) and the FEM with the finest mesh that fits | `study_compare_t3.py` |
| 57.4 | Cost and memory | steady cost of every model per record (seconds, unknowns); the FEM transient law of `releases/2.9.0/fem-transient/MEASURED.md` quoted, not re-measured | the measured table | `report` |

Every number a table prints names its read-out (column peak, column mean, node, part mean, surface) and the tree (the commit printed by the scripts); no number is quoted that a script did not print.

## 3. Choices that the campaign makes and states

* **Cells**: 2, 1 and 0.5 mm as the frozen suite; the headline of every difference is the 1 mm cell, the 0.5 mm cell shows the trend. The FEM is run at the same cell as the others (one element per cell), so differences contain discretisation error of both; where a converged reference exists (the independent FEM, an exact series) the table also shows the model against it.
* **Caps**: FVM and FDM above 400 000 unknowns, the 3D solid above 150 000 and the FEM above 130 000 are skipped and listed (the caps of the frozen harness), no run is forced past the guard.
* **Tolerances** are the acceptance criteria of `COMPARE_PLAN.md` (about 1 % on boards without vias, edge or outline effects); a difference above them is classified (known limit with the section that states it, warned, or unexplained) and **never fixed here**: an unexplained one becomes a proposal in `INTEGRATION.md`.
* **Independent references**: the independent finite elements of `research/independent-fem-edge` and `research/independent-fem-extensions` (scikit-fem, `.venv-research`) are the references of C5, C7 and C8. Their raw outputs (`out/`) are not in the repository; where this campaign does not re-run them the table quotes the committed number with its document and says 'quoted, not re-run'.

## 4. Runtime and memory (estimates before any run, to be replaced by the measured ones)

| job | estimate | basis |
| :-- | :-- | :-- |
| C1 harness, 20 boards x 6 models x 3 cells | 30 to 60 min, peak 3 to 8 GB (the 3D solid at 0.5 mm on the example board is the peak, capped at 150 000 unknowns) | the 2.8.0 reference run of the harness; one fresh process, run alone |
| C3 to C8 | minutes each, under 2 GB | the models on one board at a few cells |
| T0 | seconds | 1D bar |
| T1, T2, T3 | 10 to 40 min together; the FEM direct step response of the example board at 2 mm is 82 s (`MEASURED.md`) | `MEASURED.md` tables |

Rules: one heavy job at a time; before each, `uptime`, `sysctl vm.swapusage`, `vm_stat`; pause if the load exceeds 8 or the free plus inactive memory is below 6 GB plus the peak (swap total is 2 GB here); long runs are background scripts with a log and `--resume`.

## 5. Stages (commit and plain push after each)

0. This note, the two corrections (theory 4b and the test docstring with the source keys).
1. C1, C2, C6: the harness run (resumable), the report tables, validation 56.1, 56.2, 56.6.
2. 57.0 to 57.3: the T3 case and the board-level transient comparison.
3. C3 to C5, C7, C8.
4. The documents: `docs/validation.md` 56 and 57, `docs/versions.md`, `CHANGELOG.md`, `docs/decisions-log.md`; `INTEGRATION.md` with the proposals the campaign found.

## 6. Open questions for the reviewer

1. The definition rests on `COMPARE_PLAN.md` (a plan with tolerances 'to be confirmed'); the first tables will say whether the tolerances are the right ones.
2. The independent finite-element raw outputs are not in the repository: rows C5, C7 and C8 either re-run `.venv-research` jobs (heavy, one at a time) or quote the committed numbers; which rows deserve the re-run?
3. No published board-level transient case exists in the library (the ITherm 2023 paper was not obtained): 57.1 to 57.3 rest on independent solvers and closed forms, and the first line of 57 says so.
4. The memory column of 56 and 57 is quoted from `MEASURED.md` and the 2.8.0 law, not re-measured per record (a fresh process per run is the only honest peak).
