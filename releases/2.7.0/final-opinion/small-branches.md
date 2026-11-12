# Review of three small branches of 2.7.0

Branches reviewed one after the other, each merged with `develop` (9883b18c) first: (A) `fix/lumped-via-groups-lone-via` (2c8d0274), (B) `fix/robustness-and-balance-tests` (2552b0f0), (C) `feature/hole-categories` (3a500378). The corrections of the review are commits on each branch.

## A. `fix/lumped-via-groups-lone-via`

**Verdict: GO.** The rule (two vias joined at twice the SMALLER nearest-neighbour distance, a via left alone with `d_nn = inf`) removes the defect it targets and every number of the branch reproduces; the frozen numbers are unchanged (317 passed at 2, 1 and 0.5 mm on the branch merged with `develop`). It is not a uniform improvement, and the documents now say so.

Findings:

1. **Unexplained result, now measured** (`docs/validation.md` 41.5): on 24 new random irregular boards (`scripts/study_via_groups_review.py`, FVM at 0.25 mm as reference) the Lumped via-effect error falls from 36.7 % to 27.9 % on average (14 boards better, 7 worse), the hottest-rise error from 2.02 % to 1.74 %, but **6 boards read cooler than before** (the unsafe direction), the largest -1.6 points of the rise (an array with satellites, 2 layers, 1.9 K).
2. **Stale claim** (corrected): "the zone decision is the same" holds only on the 62 study boards; on the random boards it changes on 2 of 24 (two vias under a part, the second now alone: zoned before, one node after), both towards the FVM.
3. **Stale claim** (corrected): the Lumped via warnings read the same groups, so the "too cool" warning changes on 3 of 24 random boards (dropped once, added twice, each time consistent with the error). The 21 of 28 counts of validation 18.1 were not re-run.
4. **Analytic with `d_nn = inf`**: a satellite of a tight pair is now spread bilinearly and leaves the median spacing: tile 0.41 to 0.40, 0.49 to 0.45, 0.46 to 0.44, 0.50 to 0.45 mm on the four affected boards, hottest rise within 0.03 K, no non-finite value (inf enters only through `min` and `mean` of a lone group).
5. **Document defect** (fixed): `docs/validation.md` 40.2 pointed to a section 40.4 that did not exist, and `develop` had meanwhile taken the number 40 (drawn-layer edge film); the section is renumbered 41 (theory 5.1, versions, CHANGELOG follow) and 41.4 states the frozen run.

Not verified: the 93-board warning study of `research/lumped-zones-adoption` with the new groups; boards with an outline or imported copper and irregular vias.

Open for the maintainer: none beyond accepting that the fix is better on average and not on every irregular layout.
