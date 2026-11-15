# Release gate of 2.8.0: checklist (prepared, nothing run)

Source of the order: `CLAUDE.md` section 12 'A release' and section 6 'Branches and Versions'; the earlier record of the same steps is `releases/2.7.0/` (reproduction, battery, final-opinion, doc-review) and `releases/2.7.1/final-opinion/`. This file was made on `release/2.8.0-gate` from `development` at `6c225276`; the plan of the whole version is `releases/2.8.0/plan-resume/PLAN.md` (its G-0 to G-9). Companion files: `REFREEZE_PLAN.md` (step 7a in detail), `DOC_REVIEW_CHECKLIST.md` (step 6b in detail).

**Nothing below was run.** The state read is the tip of `development` (`pcbthermal.__version__` 2.7.1) and the worktrees of the open GUI branches.

## 0. Rules that hold at every step

* **Load**: before every heavy job and at every report, measure and write the numbers in the report: `uptime`; `sysctl vm.swapusage`; `vm_stat` (free + inactive pages, 16 KB each); `ps -axo rss,pid,command | sort -nr | head -5`. Heavy jobs (a battery, a long study, a big solve, a harness run; each declares its expected peak) run in parallel **up to 3** only while load < 5 (10 cores), swap used < 2.5 GB and grown < 1.5 GB since the job started, and free + inactive > 6 GB plus the new job's peak; otherwise in series. **One whole `pytest` battery at a time** on the 16 GB machine. Above load 8 or swap 2.5 GB, pause or stop a job. Reading and writing work may always run in parallel. Reviewers: at most 2 at once.
* **Real-board environment**: the whole battery and the research tests that use `pcb-library` run with `eval "$(pcb-library/scripts/link_env.sh)"` **in the same shell**, and the skip count is read (about 11 to 12; about 76 means the boards were not seen and the run does not count for the real-board tests). Proof before the run: `echo "$PCBT_REAL_BOARDS" "$PCBT_GERBER_DATA" "$PCBT_GERBER_SAMPLES"` prints three existing folders.
* **Interpreter**: `.venv/bin/python` of the checkout the job runs in (a worktree has no `.venv` of its own: use the absolute path of the main checkout's, `/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python`). Outputs in the scratchpad or git-ignored folders; no generated file is added to git.
* **Nobody merges on a red or unfinished battery.** A battery is read to its last line; the report says it was run and what it returned.
* **The word of the maintainer** is needed for step 7b onwards (bump already decided in 7a is a prepare step, merge, tag, push and GitHub release are not). No agent message is that approval.

## 1. Summary table

| # | Step | Who | Heavy | Produces |
| --: | :-- | :-- | :-- | :-- |
| 1 | Every `fix/` and `feature/` branch merged (each through executor, reviewer, maintainer with its whole battery) and the research and `docs/` branches decided | maintainer, reviewer, executor | yes (a battery per merge) | `development` with everything of 2.8.0; this file's table 1 filled |
| 2 | Theory and documents reviewed against the code | reviewer (maintainer for the documents) | no | `releases/2.8.0/final-review/` addendum, verdict written |
| 3 | Reproduction pass of the research folders that import the program | tester x up to 4 | yes (series by tester) | branch `release/2.8.0-reproduction`, `releases/2.8.0/reproduction/README.md` |
| 4 | Reviewer's final opinion (go / no-go) | reviewer | no | `releases/2.8.0/final-opinion/README.md` |
| 5 | Whole battery on the final tree, real boards proven loaded, plus the four gates | tester | yes, alone | `releases/2.8.0/battery/README.md` |
| 6b | Documentation review | maintainer + reviewer for numbers | no (screenshots: one GUI job) | `releases/2.8.0/doc-review/README.md` |
| 7 | Bump, CHANGELOG, refreeze, merge to `main`, tag, push, GitHub release | maintainer (executor for the refreeze runs) | the refreeze runs | `v2.8.0`, release page |
| 8 | Housekeeping | main session / maintainer | no | worktrees and `worktree-agent-*` branches removed |

## 2. Step 1: all branches merged

Rule: a work branch is created from `development`, merged with `git merge --no-ff`, never deleted. A branch's whole battery (about 45 to 50 minutes) is run before its merge, never merged on a partial run. Branches that share `panels.py`, `theme.py`, `tips.py`, `help/index.html`, `test_gui_stress.py`, `test_help.py`, `CHANGELOG.md`, `docs/versions.md` are merged one after another (`GUI_FIX_PLAN.md` 1).

Check at the start, from `development`: `git branch --no-merged development` and `git worktree list`. State at the time of writing (read, not changed):

| Branch | What | State | Action before the gate |
| :-- | :-- | :-- | :-- |
| `feature/gui-panel-polish` (A) | Simulation panel grouped by model, one name per model, the `units.py` rule, theme tokens | 2 commits ahead of `development`; **the worktree `.claude/worktrees/gui-panel` holds 79 modified files not committed** (read as `git diff --stat` there: 602 insertions, 361 deletions) | executor commits and finishes; reviewer; maintainer: whole battery; merge first |
| `feature/gui-results-warnings` (B) | warning rows with the severity dot, Summary table from one column definition (`ΔT K`, balance in percent, the surface column), Components tables, units in K, regenerated screenshots | 6 commits ahead; merges after A (it reuses A's name table and `units.py`; `gui/dots.py` is dropped at the merge if A has its own painter) | reviewer; battery; merge second; it changes `report.txt` (step 3) |
| `fix/gui-review-rest` (C) | the rest of the general GUI review, ends with the units and typography scan test and the one set of screenshots | **does not exist yet**; planned by `GUI_FIX_PLAN.md` (branch `docs/gui-general-review`), to start only after A and B are in `development` | create from `development` after A and B; reviewer implements; battery; merge third |
| `research/fem-amg-thin-layers` | AMG for the thin layers: closed with its review (last commit 'Review the AMG thin-layer investigation and close it') | 4 commits ahead, 22 files, folder `research/fem-amg-thin-layers/` imports the program | check `git diff origin/development --stat -- pcbthermal tests examples ico` is empty on it, research tests only (`research/fem-amg-thin-layers/tests`), merge `--no-ff`; the registers (`research/REVIEW.md`, `README.md`, `ROADMAP.md`) are in its review commit: check |
| `research/readout-conventions`, `research/through-thickness-readout` | read-out conventions, surface study | already merged | none |
| `docs/gui-general-review`, `docs/model-labels-review`, `docs/readout-selector`, `docs/simulation-panel-review`, `docs/units-delta-t`, `docs/warning-select-review` | review notes and prototype pictures kept as records under `releases/2.8.0/fem-model/` (documents and `figures-*` only; `docs/readout-selector` is 60 commits behind and 1 file) | unmerged; no program or test file | decide per branch: merge `--no-ff` (the record, recommended for the ones the GUI plan cites: `units-delta-t` for the unit rule, `gui-general-review` for the plan, `simulation-panel-review`, `warning-select-review`, `model-labels-review`) or leave deliberately; `docs/readout-selector` answered a question that `surface-always-both` closed: merge it as the record or leave it and say so |
| `feature/via-star-coupling` | no-go in the 2.6.0 review; also on `origin` | unmerged on purpose | leave; open question 6 of `PLAN.md` (record merge or not) |
| `tmp/article-1319202`, `tmp/merge-280d`, `tmp/paper-notes-policy`, `tmp/settings-layout-proto`, `tmp/warning-select-proto` | throwaway branches | exist, with worktrees | not release work; question 5 of `PLAN.md` (keep, fold or delete each; `tmp/merge-280d` and `tmp/article-1319202` hold commits that are on no other branch) |

**Not implemented although the maintainer's order puts them in 2.8.0** (`docs/versions.md` 'Planned, the maintainer's order', `CLAUDE.md` section 15; none has a branch): the **FEM transient** (branch 8 `feature/fem-transient`, design on `docs/fem-transient-design`), the **comparison campaign** of every model against the FEM and the 3D solid (`releases/2.8.0/fem-model/COMPARE_PLAN.md`, `docs/validation.md` sections 56 and 57 reserved: the file ends at 55), and the copper slabs in the 3D solid (`feature/solid3d-copper-slabs` is not a branch; `feature/solid3d-slabs-by-thickness` is). Decision 1 below.

Also required in this step: `git ls-files .venv .venv-research` is empty; `git status` clean in the integration checkout; a `feature/` item makes the version a minor number (2.8.0, as planned); each new feature has its stress scenarios in `tests/test_gui_stress.py`.

Expected result: `git branch --no-merged development` lists only what table 1 says is left on purpose; the tip of `development` is the candidate.

## 3. Step 2: theory and documents reviewed

Reviewer. Command: read `docs/theory.md` against the code and write the verdict.

* **4a Finite elements** (`docs/theory.md` 4a, line about 608 of the file): against `pcbthermal/femcore.py` (hexahedra, Robin and flux faces, direct up to 30 000 unknowns, CG with optional pyamg, the CG tolerance 1e-10), `pcbthermal/femmesh.py` (the mesh builder and its refusals, the memory law) and `pcbthermal/fem.py` (the column, surface and point read-outs, the heat by path, the blocks). Re-run the checks that its numbers cite: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_fem_port.py tests/test_fem_mesh.py tests/test_fem_model.py tests/test_fem_memory.py`.
* **1.2c surface** (the formula `T_top - T_m = t (2 q_top - q_bot) / (6 k)`, label 1.2c): against `pcbthermal/thickness.py` and the FVM and FDM read-outs; picture `docs/images/fig_50_surface_readout.png`.
* Everything the face-film (1.2), drawn-copper (1.7, 2.7), Lumped first-link (5) and block (blocks) corrections touch. `releases/2.8.0/final-review/` (PART_1A to PART_2C and `REMEASURE.md`) already read the whole theory once; this pass reads only what changed since.
* Number kept check for any rewrite: `releases/2.8.0/simplify/scripts/check_doc_moves.py` (its `--numbers-kept` option).
* **Documentation simplification plan status** (`releases/2.8.0/simplify/DOCS_PLAN.md`): only its branch 1 part was started (`docs/validation-history.md` exists, the bodies of validation 6, 20, 21 moved byte for byte). Its branches 1 to 6 (`docs/simplify-validation`, `-theory`, `-models`, `-guide`, `-versions`, `-changelog-index`) are NOT done; its start condition (FEM branches 4 to 8, surface estimate merged) is **not** met while branch 8 is open. Decision 2 below: do it before the release (six branches in series, each with its whole battery by the plan) or after 2.8.0 (recommended by size, the plan does not change a number).
* Document tests: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_docs.py tests/test_license_header.py tests/test_version.py tests/test_help.py tests/test_third_party_text.py tests/test_no_fabricator_names.py research/theory/tests`.
* Output: an addendum in `releases/2.8.0/final-review/` with the verdict. Expected: no section that states an equation the code does not implement; any number that moved is in `docs/validation.md` with its tree and reference.

## 4. Step 3: reproduction pass

Tester agents, **up to 4**, **one branch for the whole pass** `release/2.8.0-reproduction` owned by the first tester (part A); the others work in detached worktrees (`git worktree add --detach <path> release/2.8.0-reproduction`), one job at a time, commit a part report (`PART-B.md`, `PART-C.md`, `PART-D.md`) and hand the hash to the first tester, who cherry-picks them and writes `releases/2.8.0/reproduction/README.md` with the totals. Testers pause when the load stays above 6 or memory is tight; one is withdrawn if the machine becomes slow. Start only on the FINAL tree of step 1 (after the GUI branches), the reproduction runs the studies on the tag `v2.7.1` and on the tree and diffs the outputs, as `releases/2.7.0/reproduction/README.md` did (timeout 300 s, 1500 s for the long ones; raw outputs in `raw/` as `<tree>__<folder>__<script>.txt`).

**Which folders**: those whose `scripts/` or `lib/` mention `pcbthermal`, counted by `grep -l pcbthermal research/*/scripts/*.py research/*/lib/*.py | cut -d/ -f2 | sort -u | wc -l`: **69 of the 70 folders of `development`** import the program (only `bochkov-robin-check` does not); with `research/fem-amg-thin-layers` merged (its `lib/cases.py` imports it) the count is **70 of 71**. The split below is by the number of scripts and test files, with the folders that were slow or needed the real boards in 2.7.0 weighted up; the time of each folder was not measured now (balance the parts by the first tester if one is late).

| Part | Tester | Folders |
| :-- | :-- | :-- |
| A (owner) | 1 | `analytic-partial-copper`, `bare-spot-under-source`, `block-and-fins`, `block-warning-remeasure`, `bom-role-and-close-hook`, `drawn-copper-faces`, `gerber-models`, `imported-copper-edge-film`, `lumped-dense-via-group`, `lumped-edge-link`, `lumped-via-groups`, `outline`, `point-via-convergence`, `small-model-defects`, `sor-with-via-couplings`, `stackup`, `via-contact-geometry` |
| B | 2 | `analytic-edge-spatial`, `fin-channel`, `gerber-cad-profiles`, `gerber-real-boards`, `imported-via-rim`, `independent-fem-edge`, `laminate-nodes`, `lumped-zone-placement`, `memory-guard`, `power-calculator`, `reduced-models-imported-passives`, `solid3d-verification`, `strong-edge-laminate`, `via-edge-image`, `via-well-sheet-order`, `young-omega-tiles`, `zone-union` |
| C | 3 | `analytic-edge-and-transient`, `component-heatsink`, `convection-laws`, `cut-cell-links`, `face-down-convection`, `gerber-import`, `gerber-nets`, `horizontal-plate-h`, `independent-fem-extensions`, `laminate-edge-band`, `lumped-zones-adoption`, `plate-h-level`, `published-cases-followup`, `readout-conventions`, `theory-sources`, `through-thickness-readout`, `via-fill`, `via-real-board` |
| D | 4 | `effective-conductivity`, `fast-wave-oscillation`, `fdm-inset-edge`, `fem-amg-thin-layers`, `fin-channel-sources`, `gap-subdivision`, `laminate-slabs-and-local-rule`, `lumped-analytic-vias`, `lumped-near-edge`, `lumped-ring-uniform-deficit`, `market-fem-comparison`, `models-comparison`, `muzychka-case2-analytic`, `paper-case-studies`, `rotated-square-3d`, `theory`, `transient-reference-boards`, `via-partial-copper` |

Each tester, for each folder: (1) the folder's tests, `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/<folder>/tests` (research tests only, never the whole battery); (2) the scripts that print the numbers its README quotes, on `v2.7.1` (`git worktree add --detach <scratch>/wt-v271 v2.7.1`) and on the tree, one at a time; (3) diff of the outputs; (4) every shift linked to an item of the version. Known from 2.7.0: `gap-subdivision/study_validation_impact` takes about 731 s per tree (timeout), `via-real-board/study_validation_rows` and the Gerber folders need the real boards (`link_env.sh` proven), `solid3d-verification/study_small_pad_convergence` needs scikit-fem (not installed), `gerber-models` studies need the real Gerber windows, `independent-fem-*` need the scratch FEM environment (not in the repository: state "not re-run"). The folders marked 'stale README' in the 2.7.0 report were listed there; check whether the audit corrected them (`PLAN.md`).

**Items of the version that explain shifts** (the table of `REFREEZE_PLAN.md` 2): M1 face film half copper (every FVM, FDM, Lumped, Analytic number, by a few 1e-5 K typically, up to 0.04 K), M2 drawn copper faces (FVM and FDM of boards with a cut drawn layer, and any study with zone edges inside cells), M3 Lumped part readout and first link (part rows up to about 10 % of the rise, Lumped board maximum -0.5 to +3.1 %), M4 block exact cover (Analytic finned block +0.09 K), plus the audit's text corrections and the surface read-out (new numbers, not shifts). Not linked to one of these = unexplained = a defect until proven otherwise.

**The report format changed in this cycle** (branch B, `feature/gui-results-warnings`, `api.py`: `SUMMARY_COLUMNS`, `summary_grid`, `balance_text`; and the unit rule `ΔT K`): the Summary table of `to_text`, `report.txt` and `to_markdown` (and so the stdout of `python -m pcbthermal run`) has new column titles (`Tmax °C (column)`, a `Tmax °C (surface)` column when a model has a surface read-out, `Tmean °C (all layers)`, `ΔT K`, `Rθ K/W`, `Balance` as a percentage with a floor (`0.00 %`, `+0.31 %`), `Error vs FVM (of ΔT)`), the text report says `Rθ` for `Rth`, `K` for `degC`/`°C` differences (`Oscillation [K]`, `Margin K`), and the header of the Markdown table moves. `summary.json` keeps its keys (the raw balance value stays; `t_max_surface_c` is a new key of the rows). Expected shifts of the reproduction: **text only**, never a temperature.

Readers of the old format (searched with `grep -rnE 'dT C|Error vs|ΔT \[|Balance|to_text|report\.txt|to_markdown|Osc\. |Oscillation \[|Tmean \[|Time \[s\]' pcbthermal tests research releases examples tools --include='*.py'` on `development`, and the same on the three worktrees):

| Reader | What it reads | Action |
| :-- | :-- | :-- |
| `tests/test_numfmt.py` (`test_balance_column_of_the_summary_...`) | the Markdown row of `fvm`, cell index 7 of the split (the balance, in the old order) | **already rewritten on branch B** (reads the `Balance` header, expects a percentage); until B is merged the test on `development` is the old one |
| `tests/test_report_disclaimer.py`, `test_model_io.py`, `test_convection.py` (`report.txt`), `test_gui_stress.py` (`report.txt` exists), `test_gui_boxes.py` (`to_text().count("WARNING:")`), `test_stackimpedance.py` ("average + ripple" in `report()` and `to_markdown()`), `test_thickness.py`, `test_blocks.py`, `test_component.py`, `test_profiles.py`, `test_tooltips`-style words | substrings of the report text, not the table | run on the final tree; B's test list (`test_summary_table.py`, `test_gui*.py`, `test_help.py`, `test_numfmt.py`, ...) is what it changed |
| `research/*/scripts` | **none reads `report.txt`, `to_text()`, `to_markdown()` or the CLI stdout** (`sim.table()` rows are read by several studies; their keys are unchanged, `t_max_surface_c` is added); `research/models-comparison/scripts/solver_equivalence.py:50` and `research/via-real-board/scripts/study_validation_rows.py:64` (and `bare-spot-under-source`, `laminate-nodes/make_figures.py`) write and parse their OWN Markdown tables | no shift expected; a mismatch there is a study defect |
| `examples/csv_profiles/run_example.py:34` | prints `sim.report()` | its printed text changes, nothing parses it |
| Documents that quote the old table: README (the usage example), `pcbthermal/help/index.html` (results chapter), `docs/models.md` (the CLI output example), `research/lumped-zone-placement/README.md` (4 lines), `research/fdm-inset-edge/README.md`, `research/theory/topics/31-program-architecture-and-api.md`, `releases/2.8.0/fem-model/*.md`, `releases/2.7.0/gui-redesign/NOTES.md` | quoted output, prose | the documentation review (6b) refreshes the first three; the research READMEs are records of their run and stay as they are (state it) |

Report format of the pass (`releases/2.8.0/reproduction/README.md`, tester A): per part the table `folder | script or test | v2.7.1 | tree | shift | item | class`, and the totals line **checked / unchanged / explained / unexplained / not run** with the reason of every 'not run'; the raw outputs in `raw/`; the stale READMEs listed (a documentation finding, not a defect). Expected: unexplained = 0.

## 5. Step 4: the reviewer's final opinion

Reviewer, after steps 1 to 3 (and after the fixes they bring). Input: `git diff v2.7.1..development --stat`, the reviews of every branch (`releases/2.8.0/reviews/`, `audit/FINAL.md`, `final-review/`), the reproduction report, `REFREEZE_PLAN.md`. Writes `releases/2.8.0/final-opinion/README.md` (format of `releases/2.7.1/final-opinion/README.md`: verdict, what entered with category and 'moves a number', interactions between items (face film x Lumped first link x drawn copper on the same records; surface read-out x FEM x FVM/FDM; GUI branches x report text), re-runs, the open decisions, the proposed CHANGELOG text and the list of the release commit). It must answer: is every `pcbthermal/` change released with its documents, tooltips and tests; do the six pending files cover exactly the records that moved; does the project file format change (it should not: `project.py`, `fileschema.py`, `model.py`: `git diff v2.7.1..development -- pcbthermal/project.py pcbthermal/fileschema.py pcbthermal/model.py`). A written **go or no-go**. Expected: GO, with the gate items of its section 6 listed.

## 6. Step 5: the whole battery on the final tree

Tester, alone on the machine (no other heavy job), on the tree after step 1 and the reviewer's fixes, **before** the bump (the refreeze is done after it and re-runs `tests/regression`):

```sh
cd <tree> && eval "$(pcb-library/scripts/link_env.sh)" && echo "$PCBT_REAL_BOARDS"
QT_QPA_PLATFORM=offscreen /Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python -m pytest -q -rs tests --timeout=900 --timeout-method=thread
```

Then the gates, each its own command: `PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression` (with the six pending files present); `PCBT_COMPAT_V245=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_format_compat_245.py` (expected 5 passed); `PCBT_PUBLISHED_FULL=1 .venv/bin/python -m pytest -q tests/test_published_cases.py tests/test_calculator_validation.py`; `PCBT_SCAN_KEY_VALUES=1 .venv/bin/python -m pytest -q tests/test_no_secrets.py` (expected 4 passed). The research tests of the folders touched since the last pass (`research/<folder>/tests`) are part of step 3, not of this battery.

Expected: the last line is `N passed, ~11-12 skipped, 2 xfailed, 1 warning in about 45 to 50 min`, no failure. For reference only: the last recorded whole battery (merge of the surface read-out) gave `3830 passed, 12 skipped, 2 xfailed, 1 warning in 47 min 29 s` (`CLAUDE.md` section 14); the GUI branches add tests, so N is higher and is not predicted here. Known flakes under load: `tests/test_gui_stress.py::test_live_checks_stress_many_vias_and_option_changes` and the live-check timing test (both pass alone: re-run alone and record). A failure is classified: real defect, explained moved number, or load timeout; a failure is never waved through. Output: `releases/2.8.0/battery/README.md` (command, last line, load and swap, skip list from `-rs`, flakes). The battery is run once more on the refrozen tree (step 7a, the 2.7.0 precedent: `3445 passed` on the refreeze branch).

## 7. Step 6b: documentation review

Maintainer, with the reviewer for the numbers; the list is `DOC_REVIEW_CHECKLIST.md`. It writes `releases/2.8.0/doc-review/README.md` (the table `# | Document | Checked | Changed | Stale on purpose`, as in 2.7.0). The screenshots are regenerated once on the final tree (one GUI job, `examples/make_screenshots.py` in its three modes) and **each changed picture is looked at**. Expected: every row filled; nothing stale that is not named.

## 8. Step 7: release (in this order)

**7a. Prepare, on `release/2.8.0-refreeze` from `development`** (this is a prepare step; it changes no history of `main`):

1. Bump `pcbthermal/__init__.py` `__version__ = "2.8.0"` (the only definition; `tests/test_version.py` checks that `CHANGELOG.md` has `## [2.8.0]` and `README.md` mentions `2.8.0`).
2. `CHANGELOG.md`: the `[Unreleased]` entries become `## [2.8.0] - <date of the release>`, with a new empty `[Unreleased]` above; the text proposed by the final opinion. `README.md`: version badge, tests badge (the count of step 5), the versions list, the feature bullets. `docs/versions.md`: 'Unreleased (2.8.0, in progress)' becomes the 2.8.0 chapter, 'How 2.8.0 was tested' with the battery line, 'Planned' moved; `CLAUDE.md` section 14 'Current state of the battery' and section 15 'Where to continue' (and the test counts it quotes); `docs/decisions-log.md` prepended.
3. The refreeze (`REFREEZE_PLAN.md` 4, steps 0 to 8): result is `tests/regression/data/v2.8.0.json`, the six pending files deleted in the same commit, `releases/regression-harness/reference/v2.8.0.json` and `expected_shifts_2.8.0.json`. **The harness runs only after the bump** (it refuses a run of another version).
4. The whole battery on the refrozen tree (step 5 command) and the four gates; the line goes into `docs/versions.md`. English commits ending with the two attribution lines of the session.

**7b. Only with the maintainer's word** (nothing below starts without it; an agent's request is not that word):

```sh
git checkout main && git merge --no-ff development -m "Release 2.8.0"     # or the refreeze branch merged into development first, then development into main
git tag -a v2.8.0 -m "PCB Thermal Lab 2.8.0: confidence release (measured, bounded and warned errors); the finite-element comparison model; the surface read-out"
git push origin main && git push origin v2.8.0
sed -n '/^## \[2.8.0\]/,/^## \[2.7.1\]/p' CHANGELOG.md | sed '$d' > <scratchpad>/notes-2.8.0.md      # the CHANGELOG section, read before it is used
gh release create v2.8.0 --title "v2.8.0" --notes-file <scratchpad>/notes-2.8.0.md --verify-tag
gh release list      # v2.8.0 carries the Latest mark; check before calling the release closed
```

Before the merge: `git ls-files .venv .venv-research` empty; `git diff origin/development --stat -- pcbthermal tests examples ico` shows only what step 1 merged; no generated output staged. The merge commit and the tag message are in English. **Work branches are not deleted** (they stay as the record). The GitHub release is mandatory (CLAUDE.md section 6).

## 9. Step 8: housekeeping

Remove the finished agent worktrees (`git worktree list`; `git worktree remove <path>` without `--force`; a worktree with untracked files is looked at first), check `git rev-list --count development..<branch>` is 0 and delete the `worktree-agent-*` branches (`git branch -D`; if a commit exists only on one, report and do not delete). Only those branches are deleted. Open the next version's studies (`docs/versions.md` 'Planned', `research/ROADMAP.md`); the 2.9.0 folder `releases/2.9.0/` already exists.

## 10. Decisions left to the maintainer

1. **What is in 2.8.0**: the FEM transient (branch 8) and the comparison campaign (validation 56 and 57) are in the maintainer's order for 2.8.0 and are not implemented; ship 2.8.0 without them (the FEM steady comparison model plus the surface read-out; transient and campaign to 2.9.0), or finish them first (a feature branch, a campaign of tester jobs, a second reviewer pass; it also restarts the refreeze only if a steady number moves, which it should not).
2. The six `docs/simplify-*` branches before or after the release (section 3).
3. The six unmerged `docs/*` record branches, `feature/via-star-coupling` and the `tmp/*` branches: merge, keep or delete (section 2).
4. Release date and the words of the tag message; whether the GUI real-screen checklist (`releases/2.8.0/fem-model/GUI_TEST_CHECKLIST.md`, about one hour with his hands) is done before the word (the GUI is tested offscreen only).
5. JESD51 registration and the papers still to download (`PLAN.md` section 5): they do not block the gate.

## 11. What was not verified

Nothing of this file was executed; the list of branches and the counts (69 folders, the split, the 79 uncommitted files) were read from git and from the worktrees at the time of writing and will have changed; the time of the reproduction folders and of the battery after the GUI branches are not known; the report format is read from the diff of branch B and from the open work in the `gui-panel` worktree, not from a run.
