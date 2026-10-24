# Review register of the investigations

What the independent `reviewer` agent has checked in each research folder, so that a later session continues where the last one stopped. Update a row in the same commit as the review it records.

**Why it is needed.** The program's models changed after the review of the earlier work (`pcbthermal` at commit `0ea5f07`: laminate nodes of one-layer boards, minimum width of the Lumped rings, board time constant with an outline, laminate slabs of the 3D solid). Every study that runs the program has to be re-run on the corrected version, and every claim re-checked against an independent reference (see `CLAUDE.md`, "Agents and workflow").

**Status values.**

* `not reviewed`: no review by the reviewer agent yet.
* `in review`: started; the findings are in the "Notes" column and the folder.
* `reviewed`: the reviewer's findings are fixed and the numbers of the documents are the ones the scripts print now.
* `re-run`: the scripts were run on the corrected program (listed in "Program version"), with no independent review of the claims.

**Program version** is the commit of `develop` the studies were last run on.

| Folder | Status | Program version | Re-run on the corrected models | Notes |
| :-- | :-- | :-- | :-- | :-- |
| `solid3d-verification/` | reviewed | `0ea5f07` | yes (every study re-run on 2026-10-24: Yovanovich and GCI, FEM four boards, copper sweep, metal block, one-layer parts 1 and 2, axisymmetric) | Reviewer agent, 2026-10-24 (README section 7). Table 3 confirmed by the exact Bessel series; square-tube series added (it explains 0.2 to 0.4 of the 0.7 to 0.8 %). Fixed: three wrong numbers (one-layer pad 7 % -> 3.5 %; FVM within 2.2 % -> 2.5 % on 20 mm pads; 3D FV within 2 % -> 3.6 % at 20 mm), the stale accuracy line of fig_04, the metal-block table and the small-pad convergence now printed by scripts (`study_block_against_fem.py`, `study_small_pad_convergence.py`, which adds the independent solver), the FEM block interface read through `interface_resistance()`. Same stale numbers in `docs/validation.md` sections 3, 3.1 and 20: text in `solid3d-verification/docs/for-the-project-documents.md`. |
| `models-comparison/` | reviewed | `0ea5f07` | yes (every study re-run on 2026-10-24: 19 scenarios, grid, `--fem`, solvers, nine boards with `--compare`, Lumped rings, time and coefficients) | Reviewer agent, 2026-10-24 (README section 7). The 19-scenario and grid tables of `docs/validation.md` are current; the README's Lumped column was stale in six rows (up to 0.07 K). Fixed: stale step-animation rows (0.2 to 0.4 °C) and an incomplete solver table; sections 4.6 and 4.7 now printed by `scripts/study_time_and_coefficients.py` (no script printed them); `validation_study.py --fem` repaired (import error since the move out of `examples/`); four statements the tables contradict (FDM "±0.5 °C jumps", FDM "within 1 %", Analytic "exact" on uniform boards, the sign of the Analytic explanation in 4.8); the off-grid heater case marked not reproduced; the 3D-solid reference of 4.8 checked against the independent solver (`scripts/study_complex_boards_independent.py`: within 1.4 % at 1 mm, 0.2 % at 0.5 mm). Text for `docs/validation.md` sections 1, 2, 2.1, 5 to 8 and 21 in `models-comparison/docs/for-the-project-documents.md`. Broken link left for the theory folder: `theory/topics/01-layered-idealisation.md` and `theory/README.md` still name `fig_04_the_five_models_schematic.png` (now `fig_08`). |
| `effective-conductivity/` | reviewed | `0ea5f07` | yes (every study re-run on 2026-10-24: Culham, Lee, program vs coupon, Muzychka with `--mesh-check`, natural convection, Biot definitions, corrections impact, channels, one-layer board; figures and tests) | Reviewer agent, 2026-10-24 (README section 8). Published values checked: Muzychka and others (2003) text read in full (pypdf), Seri Lee (1998) re-read; Culham and Yovanovich not re-opened. Unchanged: Culham tables (every digit), Lee, natural convection, plate check, Biot, channels. Fixed: the one-layer table of 4.11 described the program before the laminate nodes (FVM -1.9 / -10 % -> -0.0 / -2.5 %) and its candidate column counted the laminate twice on the corrected program (replaced by the FVM before, switched off in memory; `INTEGRATION.md` 5 marked superseded); Lumped of 4.5 (+1.0 -> +0.0 % at 35 mm); "case 1 between the paper's two solutions" true only for the centroids; three numbers no script printed (cross area mean, Biot mesh check, Culham mesh) now printed; the "film on the node" explanation tested directly (film in series with t/2k closes the gap to 0.0 to 0.1 K); the 1.62 mm thickness of the text explains half of the Culham shortfall (7.81 -> 8.03 against 8.28); figures 14 and 16 unlinked, 8/9 order, stale run time and figure count. `lib/layered3d.py` and the copy in `solid3d-verification/lib/` differ only by two docstring lines. Nothing in `docs/` is stale from this folder. |
| `outline/` | not reviewed | | no | Time constant with an outline changed in the program. |
| `stackup/` | not reviewed | | no | One-layer boards changed in the program. |
| `block-and-fins/` | not reviewed | | no | |
| `component-heatsink/` | not reviewed | | no | |
| `power-calculator/` | not reviewed | | no | Uses the board model run backwards: depends on every correction. |
| `via-fill/` | not reviewed | | no | |
| `theory/` | not reviewed | | not applicable | Text and pictures; check against `docs/theory.md` after the corrections. |
| `gerber-import/` | not reviewed | | not applicable | Independent reader; no model involved. |
| `gerber-models/` | not reviewed | | no | Five models on real boards: depends on every correction. Section 4.39 proposes two corrections to the program. |
| `gerber-nets/` | not reviewed | | not applicable | Design and prototype. |

## Notes

* The open points that used to sit in `docs/roadmap.md` of this branch are in `gerber-models/docs/roadmap-entry-open-points.md`.
* The figure numbers of `models-comparison/` and `solid3d-verification/` collided between the two sides of a merge with `develop`; the diagrams of this branch were renumbered (8 to 10 and 8) because `docs/` links the figures of `develop`.
