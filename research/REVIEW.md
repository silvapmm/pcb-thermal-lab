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
| `models-comparison/` | re-run | `0ea5f07` | yes (nine boards, Lumped rings, laminate nodes) | Same. The 19-scenario tables of sections 1 to 4.7 are the older ones: to confirm. |
| `effective-conductivity/` | re-run | `0ea5f07` | partly (`program_vs_coupon`, `corrections_impact`, one-layer check) | Closed investigation, corrected once "after a review" by the main session; needs the reviewer. |
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
