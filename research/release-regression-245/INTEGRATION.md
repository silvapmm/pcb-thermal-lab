# Integration: the frozen numbers as a permanent regression test

Proposal; nothing here touches the program. It is implemented, after the maintainer decides, on a `feature/` or `fix/` branch off `develop` (CLAUDE.md, "Adoption").

## 1. What changes and what does not

* **New in the project (not in the program)**: `tests/test_frozen_numbers.py` and `tests/regression/` (the four library files `regress_boards.py`, `regress_harness.py`, `regress_classify.py`, `regress_frozen.py`, copied from `research/release-regression-245/lib/`) and `tests/regression/v2.4.5.json` (the frozen file). The research folder stays as the record. Nothing in `pcbthermal/` changes.
* **The test**: the same module as `research/release-regression-245/tests/test_frozen_numbers.py`, with the path of the frozen file and of the library changed. By default it runs the 2 mm cell only (measured by the review on a file frozen from the quick sets: 85 steady records and 58 times to 63 %, **144 tests in 27 s**; without the times to 63 % less) so that it can join the whole battery; the variables `PCBT_FROZEN_CELLS`, `PCBT_FROZEN_BOARDS`, `PCBT_FROZEN_MODELS`, `PCBT_FROZEN_TRANSIENTS` widen or narrow it, and the release procedure runs `PCBT_FROZEN_CELLS=2,1,0.5 PCBT_FROZEN_TRANSIENTS=1`.
* **Two classes of record**: `bit` (nothing in the release may change it: exact float equality) and `moved` (the release changed it on purpose: 1e-6 K on temperatures, 1e-7 relative on the field checksum and the heat split, exact unknown counts). The class is decided automatically from the v2.4.4 baseline when the file is made; a record that was not moved by 2.4.5 is a guard for every later version. The review recommends one tolerance for both classes (README 7.5): exact equality fails after a library update (8 of 44 bit records with NumPy 2.3.5 / SciPy 1.16.3, by 2.8e-11 K at most), and a number that 2.4.5 moved is no less a guard for 2.4.6.
* **What it catches**: any change of a temperature, a unknown count or a heat split of the five models on the 17 boards that is not announced by regenerating the file. It does not replace the physics tests (`tests/test_*.py`), the independent-solver tests (`tests/test_layered_vs_3d.py`) or the study scripts; it answers "did a number move".

## 2. Updating the file for a later version

A later version that **changes a model on purpose** (for example the zonal Lumped model, the memory guard that changes a limit, a new convection form as default) proceeds in this order, on the `fix/` or `feature/` branch:

1. Run the test; it fails on the records the change moves. Read the failures: each one must be a record the change is meant to move. A failure on a record that should not move is a regression: fix the code.
2. Make a result set of the previous release from the frozen file's tree: `study_baseline_release.py --tag v<previous>` (the tag of the previous release is a `git archive` away), and of the branch: `study_run_suite.py --label final`.
3. Write the items and rules of the change into a new `expected_shifts.json` section (the table is cumulative per release: copy it to `expected_shifts_<version>.json`, keep the boards, replace the items and rules), run `study_diff.py`, and explain every alarm before going on. When the diff is reviewed, `study_tighten_table.py` writes the measured limits (1.25 x each shift per board, model and cell, and its sign) so that a later commit of the same release cannot move a number further without an alarm.
4. `study_freeze_reference.py <previous> <final> --version <new>` writes `v<new>.json`; the old file stays in the repository as the record of the release it froze (the test reads the newest one).
5. The commit message and the `CHANGELOG.md` entry say which records moved and why, with the diff table in the research or the pull request text.

A version that only fixes bugs and moves nothing leaves the file as it is, and the test must pass without changes: that is its purpose.

## 3. Risks and limits

* **Exact equality across machines**: the frozen `bit` records are exact floats. Measured by the review: a second run and a run on one thread are bit-identical; NumPy 2.3.5 / SciPy 1.16.3 against 2.5.4 / 1.18.1 on the same machine moves 8 of 44 bit records by at most 2.8e-11 K (field 7e-13 relative). The file records the environment it was made on (`generated_from.environment`); `PCBT_FROZEN_BIT_TOL=1e-9` relaxes the bit records (it did not work on the heat balance before the review: corrected). Another CPU architecture was not tried.
* **Runtime in the battery**: the 2 mm default is meant to be a small part of the 8 minutes of the whole battery; this is an expectation, not a measurement. The 0.5 mm cells and the 3D solid are for the release procedure, not for every run.
* **Boards are inputs**: changing a board of the suite (a dimension, a power) invalidates the file; the builders are part of the frozen numbers, so a change of `regress_boards.py` needs a new freeze.
* **Coverage**: 17 boards and five models do not cover profiles in time (only the time to 63 %), computed convection (`h_mode = computed`), advanced stack-ups, the Power Calculator, the GUI. They are covered by the tests of the battery; if one of them becomes a risk, a board is added and the file regenerated.
* **The table is part of the record**: `expected_shifts.json` carries hypotheses (some bounds are *derived*); the first diff corrects them. A frozen file made while alarms are open carries `alarms_when_frozen` (the freeze refuses without `--allow-alarms`).
* **Independent references**: only four boards have one, and it is the solver the battery already uses. The frozen numbers hold the program to itself, not to the truth; the truth is the job of `tests/test_layered_vs_3d.py` and the research folders.

## 4. Decisions left to the maintainer (with the reviewer's recommendation, README 7.6)

1. Where the frozen test lives (`tests/` as proposed, or only in `research/` and run by the release procedure). Recommended: `tests/regression/`, in the battery; its fixture must call `model.reload_libraries()` after setting `PCBTHERMAL_CONFIG`, so that a test that changed the libraries cannot change the frozen numbers.
2. Exact equality or a tolerance for the `bit` records by default. Recommended: one tolerance for every record (temperatures 1e-8 K, field checksums 1e-10 relative, balance 1e-9 W, counts and status exact, times to 63 % 1e-6 relative); exact equality as an option on the machine that froze the file.
3. Whether the 2 mm default is in the whole battery or only in the release procedure. Recommended: in the battery (27 s with the times to 63 %); 2, 1 and 0.5 mm in the release procedure (about two minutes).
4. Whether the diff table of every release is kept (in `research/` or in the pull request) or only the frozen file. Recommended: keep the table of expected shifts of each release with its limits (`expected_shifts_<version>.json`) and a short summary of the classified diff in the research folder and the pull request; the full Markdown can be regenerated from two runs.
