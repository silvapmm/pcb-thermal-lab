# Review of three small branches of 2.7.0

Branches reviewed one after the other, each merged with `develop` (9883b18c) first: (A) `fix/lumped-via-groups-lone-via` (2c8d0274), (B) `fix/robustness-and-balance-tests` (2552b0f0), (C) `feature/hole-categories` (3a500378). The corrections of the review are commits on each branch.

## A. `fix/lumped-via-groups-lone-via`

**Verdict: GO.** The rule (two vias joined at twice the SMALLER nearest-neighbour distance, a via left alone with `d_nn = inf`) removes the defect it targets and every number of the branch reproduces; the frozen numbers are unchanged (317 passed at 2, 1 and 0.5 mm on the branch merged with `develop`). It is not a uniform improvement, and the documents now say so.

Findings:

1. **Unexplained result, now measured** (`docs/validation.md` 42.5): on 24 new random irregular boards (`scripts/study_via_groups_review.py`, FVM at 0.25 mm as reference) the Lumped via-effect error falls from 36.7 % to 27.9 % on average (14 boards better, 7 worse), the hottest-rise error from 2.02 % to 1.74 %, but **6 boards read cooler than before** (the unsafe direction), the largest -1.6 points of the rise (an array with satellites, 2 layers, 1.9 K).
2. **Stale claim** (corrected): "the zone decision is the same" holds only on the 62 study boards; on the random boards it changes on 2 of 24 (two vias under a part, the second now alone: zoned before, one node after), both towards the FVM.
3. **Stale claim** (corrected): the Lumped via warnings read the same groups, so the "too cool" warning changes on 3 of 24 random boards (dropped once, added twice, each time consistent with the error). The 21 of 28 counts of validation 18.1 were not re-run.
4. **Analytic with `d_nn = inf`**: a satellite of a tight pair is now spread bilinearly and leaves the median spacing: tile 0.41 to 0.40, 0.49 to 0.45, 0.46 to 0.44, 0.50 to 0.45 mm on the four affected boards, hottest rise within 0.03 K, no non-finite value (inf enters only through `min` and `mean` of a lone group).
5. **Document defect** (fixed): `docs/validation.md` 40.2 pointed to a section 40.4 that did not exist, and `develop` had meanwhile taken the number 40 (drawn-layer edge film); the section is renumbered 41, then 42 at the merge (the FDM harmonic section took 41; theory 5.1, versions, CHANGELOG follow) and 41.4 states the frozen run.

Not verified: the 93-board warning study of `research/lumped-zones-adoption` with the new groups; boards with an outline or imported copper and irregular vias.

Open for the maintainer: none beyond accepting that the fix is better on average and not on every irregular layout.

## B. `fix/robustness-and-balance-tests`

**Verdict: GO with the review's corrections** (two commits on the branch, after a merge of `develop`).

Findings:

1. **Defect in the program** (fixed, `jobs.failure_message`): the window message was the text of the exception, so an `OSError` naming a file of the user showed the home folder (the claim 'no path' held only for the name of the log). The home folder is now written `~`; test with a `FileNotFoundError` in the home folder.
2. **Defect in the program** (fixed, `jobs._attach_log_file`): the log grew without bound, and when the configuration folder changed in one process (the tests do it) the old handler stayed and kept writing to the old file. It is now a `RotatingFileHandler` (1 MB, one older copy) and a handler of another folder is closed and replaced; test.
3. **Defect in a test** (fixed): `test_transient_energy_balance` claimed that 'a wrong capacity breaks the sum'. It does not: with implicit Euler the sum `C x + lost = q t` holds for ANY positive C (C x 2 and random factors close it to 1e-12, checked); it tests that K conserves heat and that the loss vector is its row sum. Added: the program's stepper (`fvm.transient_from_network`, same steps) gives the same field as the march (2.9e-11 K), and a new test holds the total heat capacity of the FVM and FDM networks to the closed form `rho c V` of copper and laminate, full copper and half copper with the laminate ladder (1e-12).
4. **Stale document** (fixed): `docs/models.md` 2.6 pointed to `docs/research.md` R2, which the empty template no longer has; it points to `research/component-heatsink/NOTES.md` now (the old text is kept there in full).
5. Checked and right: `power_out["blocks"]` is read only generically (`Result.summary`, `balance_error`, JSON of the run), so its absence breaks no report, CSV, plot or GUI summary; the Lumped, Analytic and 3D solid already keyed it on a block. `WELL_LOG_FLOOR`: the reduced barrel is continuous to 1e-6 relative from a log of 1e-3 down to the infinite well (`kron_barrel` rows 0.268291526 against 0.268292683), bit-identical above 1e-6; the frozen numbers at 2 mm pass. A `ValueError` stays plain. An unwritable folder leaves the message. The 29 tests run in 5 s and gave the same result twice.

Limits: two program instances share one log file (the rotation of a `RotatingFileHandler` is not safe across processes; the calculation process is one per window, jobs run one at a time, so a lost line is the worst case).

## C. `feature/hole-categories`

**Verdict: GO with the review's corrections** (one commit after a merge of `develop`).

Findings:

1. **Defect in the program** (fixed, `model._checked_holes`): the holes of a project file were not checked at the loading boundary; now the editor draws them, a hole with a string, a missing key or a list made the canvas fail when the project opened (ValueError, KeyError, AttributeError from `_add_holes`), and a NaN hole opened but could not be saved (older: the field existed unchecked). Every hole is now checked on loading (finite position and diameter up to 1 km, a string kind, both ends of a slot) and refused with `imports[i]: ... holes[j]`; a hole without a kind is read as a via (what every version wrote). Test.
2. **Defect in the program** (fixed, `ImportSession._other_holes`, `canvas.hole_at`): a plated slot was stored as 'nonplated' and its tooltip said 'Non-plated slot'; a plated slot is now a component hole ('Plated slot ...'). No test with a plated slot file (the synthetic board has none).
3. **Coordinator's item, partly confirmed** (fixed, `MainWindow._select_all`): with View - Holes: vias off, Select all put the hidden vias in the element list and the inspector (an inspector edit would change vias the user cannot see); Delete did NOT remove them (the invisible scene items are not selected, measured: 9 vias before and after). Select all now leaves the vias out while they are hidden; test.
4. Checked and right: tag v2.6.0 (detached worktree) opens a format-2 file with the three kinds, runs it (FVM 89.117, Lumped 84.406 degC, the same on the branch), saves it with the holes byte-for-byte equal, and the branch reopens it. Package `.pcbtz` round trip keeps the holes; undo and redo keep the hole items; the theme switch recolours them; 100 000 holes: build 0.08 s, paint 0.22 s, hover 0.14 ms, about 170 MB of peak resident memory; the re-import tests `kind == "via"` positively; the stress scenario passes.
5. **Limit to record**: a re-import made by 2.6.0 of a file written by 2.7.0 reads a non-plated hole as an imported via position (its rule is `kind != "component"`), so a hand-drawn via placed exactly on a non-plated hole would be dropped by that old re-import.
6. **Not from this branch (reported)**: the type-ahead search of the element tree never receives letters or digits: every tool key (S, Z, H, C, V, O, P), G, T, D, M, L and the layer keys 0 to 9 are window shortcuts and take the key first (measured: H, V, Z leave the current item on 'Zones', L and 1, 2 change the layer, D opens the Display panel), and the four group titles all start with a shortcut letter. `QTreeWidget.keyboardSearch('H')` itself works. The layer digits added 0 to 9 to a search that was already dead for letters; a fix would give the tree the keys while it has the focus (a decision for the maintainer: then L, D, M and the digits do not act from the tree).

Not verified: the CO60 board of the local library (the 100 000-hole synthetic case stands in for it), a real re-import with moved holes, the real macOS display.

## Open for the maintainer

* A: accept that the lone-via fix is better on average and not on every irregular layout (6 of 24 random boards cooler, at most 1.6 points of the rise).
* C: whether the element tree should get its type-ahead search back (keys to the tree while it has the focus).
