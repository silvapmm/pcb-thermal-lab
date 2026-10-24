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
| `solid3d-verification/` | re-run | `0ea5f07` | yes (the one-layer part, checked against `lib/layered3d.py`) | Reviewed once by the main session before the reviewer agent existed; needs the reviewer. |
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

## Open points found while merging `develop` into this branch

* `docs/roadmap.md` on this branch holds a section "Open points of the research branch" that `develop` does not have; the rule says the project documents stay identical to `develop` on a research branch. Decision for the maintainer: move that text to `research/*/docs/roadmap-entry.md` or accept it as part of the adoption.
* The figure numbers of `models-comparison/` and `solid3d-verification/` collided between the two sides of the merge; the diagrams of this branch were renumbered (8 to 10 and 8) because `docs/` links the figures of `develop`.
