# The FEM comparison campaign (validation 56 and 57)

Branch `release/2.9.0-fem-campaign`, from `development` 7886ac42; the program is untouched (`git diff development --stat -- pcbthermal` is empty). Definition, boards, models, cells, read-outs, runtime and the open questions: `DESIGN.md`. The sections written from these results: `docs/validation.md` 56 and 57. Proposals: `INTEGRATION.md`. The raw outputs are in `out/` (git-ignored); the tables the scripts printed are in `tables/` (committed, they are what the sections quote).

## Results (numbered)

1. **Steady, 20 boards x six models x 2, 1, 0.5 mm** (`scripts/study_compare_c1.py`, `tables/c1_steady_all_models.md`): on the 14 boards without a drawn feature or a bare pad window the FVM, FDM and 3D solid read the FEM peak within 1.4, 2.4 and 2.2 % at 1 mm and within 0.46, 0.51 and 0.77 % at 0.5 mm; the heat balances close to 1e-6 or better. The pad boards and the three drawn boards are classified in 56.1.1 and 56.1.2.
2. **Against the independent layered solver** (four boards): the 3D solid equals it; the FEM and the solver have limits within 0.15 % of each other on `plate_pad` (325.27 and 325.76 K).
3. **Case 2 of Muzychka and the other published plates** (`study_compare_c3.py`, `study_compare_c4.py published`): the FEM surface read-out equals the printed centroids within 0.21 K (case 2) and 0.0 to 0.5 % of the rise (cases 1a, 1b, 3).
4. **Via effect** (`study_compare_c7.py`): the FEM is the closest to the independent value at 0.25 mm and 1000 W/m2K in all three geometries; the FVM and FDM rows reproduce the independent study's errors to the digit.
5. **Strong edge** (`study_compare_c4.py edge`): the FEM at 0.25 mm is -0.4 and -1.1 % of the independent limits at 200 and 1000 W/m2K.
6. **Transient** (`study_compare_t0.py` to `t3.py`): NAFEMS T3 reproduced (exact 36.603116, FEM 36.6106 / 36.6050 / 36.6036 at 100 / 200 / 400 elements, MOOSE's mesh results to 1e-5 K); the stepping error of the three cell models is 0.67 to 0.83 % on the time to 63 %; the layered models are 12.5 to 13.3 points of the plateau below the FEM at 0.3 s; slow profiles agree within 1.1 K (FEM, FVM, FDM); a 20 Hz wave is the stated limit and the default FEM mesh reads 22 % below the independent solver.

## What was run, what was not

Run: everything above, on one machine (macOS arm64, 16 GB), one job at a time (load below 3, swap unchanged at 0.6 GB). Not run: the independent finite elements (their numbers are quoted), the Lee plate and the thick-plate bound in the FEM, the Lumped and Analytic via effect, the FEM on `round_outline` (refused by the program), 0.5 mm on the four large boards (above the caps), a cell finer than 0.25 mm, any comparison with a measurement. `tests` were not run beyond `test_docs`, `test_license_header`, `test_fem_transient_closed_forms` (light).

## What was read and what was not verified

Read in full: `COMPARE_PLAN.md`, `research/transient-published-case` INTEGRATION.md, `releases/2.9.0/fem-transient/MEASURED.md`, `tests/test_published_cases.py` (the cases), `tests/regression/regress_harness.py`, `research/independent-fem-extensions` README 8.1 (the quoted E values), `research/drawn-ell-fvm-fdm` README (head). Read in part: `docs/theory.md` 4b, `docs/validation.md` 55 and 46. Not opened: the NAFEMS publication (status N, the case is read in four open documents), the ITherm 2023 paper (no board-level published transient case exists in the library). Not verified: the quoted independent values were not re-run; the explanations marked 'not explained' in 56.2 and 57.3 are open.
