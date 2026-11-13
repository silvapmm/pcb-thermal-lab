# Final opinion of the reviewer on 2.7.0

Tree: `develop` fd49b969 (version still 2.6.0 in the code; previous release the tag `v2.6.0`). Branch of this opinion: `release/2.7.0-final-opinion`. The per-branch reviews of the version are the other files of this folder (`cut-overlay.md`, `drawn-edge-film.md`, `edge-film.md`, `fdm-copper-edge-faces.md`, `fdm-harmonic.md`, `imported-via-rim-mask.md`, `outline-mask.md`, `simple-stackup.md`, `small-branches.md`); this file is the release gate step 5 (`CLAUDE.md`, 'Agents and workflow'): the code as a whole diff against `v2.6.0` and how the items interact, the program, the documents and the investigations.

## Verdict

**GO for the code and the physics. NO-GO for the release commit until the three gate items of section 6 are closed** (two investigations whose numbers the program quotes are not in the repository, and the refreeze). None of them changes a number of the program.

No defect of the program was found by this pass. Every frozen record that moves is explained by one of four items, and the steady shifts of the example board are exactly the documented ones (checked against the tag, section 2). The documents had one structural defect (four 2.7.0 items written into the released 2.6.0 chapter of `docs/versions.md`, eight 2.7.0 items missing from it), fixed here.

## 1. The diff against v2.6.0 and the interactions

`git diff --stat v2.6.0..fd49b969 -- pcbthermal`: 59 files, +2318 / -703 (464 files in the whole tree). Physics files: `fvm.py` (centroid edge film for every layer), `fdm.py` (harmonic face, then the cell-fill copper face), `model.py` (`Board.slab_thicknesses`, the checked holes of the import record), `viawell.py` (`RimMasks`, `WELL_LOG_FLOOR`), `viaconstriction.py` (lone-via grouping), `copper.py` (outline per pixel, span warning, copper numbering), `geometry.py` (`cover_centroids`), `checks.py` (warning texts and the thin-laminate trigger), `laminate.py`, `solid3d.py`, `analytic.py` (the slab rule through `slab_thicknesses`, comments). The rest is the GUI redesign (boxes, warnings accordion, layer keys, shortcuts dialog, elided labels), plots (cut overlay, markers), `jobs.py` (error log).

Interactions examined (each item was reviewed alone; the question here is what two items do together):

| pair | what can interact | finding |
| :-- | :-- | :-- |
| physical slabs x node capacity x profile decisions | the outer copper node of a simple 4-layer board holds 0.278 mm of laminate instead of 0.4 mm | Steady +0.06 to +0.09 K (documented). **The step response is faster: time to 63 % of U1 -1.6 to -2.4 %, of the small part U2 -10.6 to -17.0 %** (example and profile boards, FVM / FDM / Lumped / Analytic, from the pending files against `v2.6.0.json`); validation 43.3 said only 'times move'. The node swing of the fast heater of `test_profiles.py` 0.393 to 0.543 K; the regime and the closed-form floor (2.013 K) unchanged, because the floor dominates. Numbers added to `CHANGELOG.md` and `docs/validation.md` 43.3. No independent transient reference (limit). |
| physical slabs x the advanced stack-up of 2.6.0 | the new simple rule claims to be the old advanced rule with equal gaps | **Checked against the tag** (`git archive v2.6.0`, example board, 2 mm): v2.6.0 with the board typed as an advanced stack-up of equal gaps gives FVM 85.29380457046574 °C, step response U1 10.52217 s / U2 2.30990 s (FVM), 8.84308 / 2.42619 s (Lumped); the tree with the simple stack-up gives the same digits. The shift is exactly the slab rule, nothing else. |
| physical slabs x FDM harmonic face x FDM cell-fill face | three items on the same FDM records | The FDM records of `example_board`, `profile_board`, `example_cut_to_T` carry all three; they live in one pending file (`fdm-copper-edge-faces.json`), no record in two files (checked: 0 duplicates). Additive: simple +0.07..0.085, harmonic about +0.04, face -0.010..+0.008 K, total +0.107..+0.136 K against v2.6.0. |
| centroid edge film x laminate edge band | the band's laminate nodes take the centroid distance too | Reviewed in `drawn-edge-film.md`. Side effect measured on the tree by the tester: the closed-form time constant of a disc board moves from within 0.3 % to +0.70 % (1 mm) / +0.34 % (0.5 mm), and the sliver jump of `research/cut-cell-links` 0.591 K (bound 0.5 -> 0.6). Both are the documented first-order hot error of the centroid film (falls with the cell); the tests were restated with reasons (4e8dfc22). Accepted. |
| centroid edge film x imported copper outline mask x simple stack-up | imported boards on an outline with three or more layers | No harness board; the three items act on different factors (pixel share of the sheet, film distance, slab thickness) and the simple stack-up review states that imported boards move like drawn ones. Not measured on a real 4-layer imported board with an outline (limit). |
| FDM cell-fill face x imported copper | the face rule must not touch imported layers | Bit-identical with the switch off, held by `test_imported_copper_layers_keep_their_own_faces`. |
| via rim mask x lone-via grouping x Lumped zones | the rim mask acts on the FVM/FDM wells, the grouping on the Lumped constriction | Disjoint paths. The Lumped and Analytic still warn on imported copper; the grouping moves no harness record (317 frozen passed). |
| memory guard law x new nodes | do the items add unknowns? | None adds unknowns: the slabs change thicknesses, the faces change conductances, the centroid strips are bounded (54 MB on a 200 mm board at 0.25 mm), the rim masks are the cached arrays. The law needs no refit. |
| project files | v2.6.0 files open in 2.7.0; 2.7.0 files (new hole kinds) open in 2.6.0 | A v2.6.0 hole has `x_mm`, `y_mm`, `d_mm`, `kind` (via or component), all accepted by `model._checked_holes` (unknown keys kept, missing kind = via). The reverse was checked by the hole-categories review on the tag; the compat test (`PCBT_COMPAT_V245=1`) passed 5 on the candidate. Stated limit: a re-import made by 2.6.0 reads a non-plated hole as a via position. A v2.6.0 project of a simple 4-layer board gives the documented +0.09 K. |
| warnings that quote numbers x the items | texts measured before a later item | The edge-laminate texts quote the finite-element check (validation 46) since `fix/edge-warning-fem-numbers`; the FDM-specific ranges were restated for the harmonic face (validation 41.2) but not again for the cell-fill face (the face moves the FDM towards the references, so the quoted low ranges are upper bounds; `fdm-copper-edge-faces.md` 6). The first clause of `check_edge_laminate` still quotes 3.2 mm two-layer boards (-2.4 / -5.5 / -16 %) against the cell-centred reference of `research/laminate-edge-band`, which the finite elements showed to read hot at a 0.25 mm cell: those figures are probably pessimistic by a similar factor; not re-measured (non-blocking). `_edge_laminate_uncut` says 'against an independent 3D solver at the same cell' and in the next sentence 'the reference is an independent finite-element solution': the first phrase is stale wording (non-blocking). |

## 2. The 17 harness boards before and after

Computed from the four pending files against `tests/regression/data/v2.6.0.json` (`fo_shifts.py` in the session scratchpad; the tester's frozen run on the tip passed 317 at 2, 1 and 0.5 mm with the pending files, and exactly these records fail without them). The 3D solid moves on no board. **What `expected_shifts_2.7.0.json` must contain** (baseline v2.6.0, target 2.7.0; `make_expected_shifts.py` is written for 2.6.0 and needs its ID map and baseline changed):

| id | item, branch | records that move (model, boards, cells 2/1/0.5) | direction and size of `t_max` | times to 63 % |
| :-- | :-- | :-- | :-- | :-- |
| L1 | simple stack-up physical slabs, `fix/simple-stackup-physical-layers` (validation 43) | FVM, Lumped, Analytic of `example_board`, `profile_board`, `example_cut_to_T` (27 records); the FDM records of the same boards jointly with L3, L4 | up: FVM +0.087..+0.091 K, Lumped +0.075..+0.081, Analytic +0.063..+0.077; `t_mean` down 0.002..0.004 K | down: U1 -1.6..-2.4 %, U2 -10.6..-17.0 % (FVM, Lumped, Analytic of example and profile; FVM of example_cut_to_T); the Analytic of example_cut_to_T within tolerance |
| L2 | centroid edge film for drawn layers, `fix/drawn-layers-edge-film-centroid` (validation 40) | FVM of `part_across_outline`, `round_outline` (6 records), FVM of `example_cut_to_T` jointly with L1 | up: +0.0024..+0.0091 K | up: +0.01 / +0.03 % |
| L3 | FDM harmonic face, `fix/fdm-harmonic-face-mean` (validation 41) | FDM of `finned_block`, `part_across_outline`, `plate_lone_via`, `plate_vias`, `reference_board`, `round_outline`, `t_outline` (21 records, 0 to +0.0026 K); jointly with L4 on `plate_pad`, `one_layer_pad`, `part_top_path`, `two_layer_partial`; jointly with L1, L4 on the three example boards | up (0 to +0.0026 K alone) | within 1e-6 relative on its own boards |
| L4 | FDM cell-fill copper face, `fix/fdm-copper-edge-faces` (validation 47) | FDM of `example_board`, `profile_board`, `example_cut_to_T` (with L1, L3: +0.107..+0.136 K), `plate_pad` (with L3: +45.01 / +27.26 / +15.30 K), `one_layer_pad` (+8.49 / +5.38 / +3.08 K), `part_top_path` (+1.35 / +0.98 / +0.59 K, `t_mean` -0.73 / -0.53 / -0.32 K), `two_layer_partial` (+1.71 / +1.52 / +0.87 K) | up on `t_max`; `t_min` and `t_mean` of the pad boards slightly down | FDM: example/profile U1 -1.94 %, U2 -14.5 % (with L1); example_cut_to_T U1 -1.53 %, U2 -9.15 %; one_layer_pad +4.49 %; plate_pad +4.09 %; part_top_path -10.41 %; two_layer_partial +1.61 % (all against v2.6.0, L3 included) |

Items that move no frozen record (no harness board has imported copper, an imported outline, a lone via beside an array that changes the group, or hole kinds): the imported via rim mask, the imported edge film from the centroid, the imported outline per pixel, the lone-via grouping, every text, display and tool item. The table must mark them 'no record'. The `evidence` fields of the pending files point to the old validation numbers (fdm-copper-edge-faces 46 -> 47, fdm-harmonic-face-mean 40 -> 41, simple-stackup-physical-layers 42 -> 43): use the right ones in the table.

## 3. The documents

Fixed on this branch:

* `docs/versions.md`: four 2.7.0 items (thin-laminate warning, FDM cell-fill face, FDM harmonic face, underlay default and shortcuts window) and two more (window growth, view fitted after a re-import) were written into the released **2.6.0** chapter; moved to '2.7.0 (unreleased)'. Eight 2.7.0 items had no entry there (simple stack-up, imported outline per pixel, hole kinds, markers and cut overlay, boxes and keys, robustness tests, edge-warning texts, import size / Add files, the developer tools): one line each added, pointing to the reviews and the CHANGELOG.
* `CHANGELOG.md` [2.7.0], simple stack-up: the step-response shift and the check against the tag added; the pending-file count explained (36 records moved, 9 FDM of them held by `fdm-copper-edge-faces.json`).
* `docs/validation.md` 43.3 and 43.6: the time shifts with numbers, the tag check, the stale 'live only in this file' (those FDM records moved again with section 47) and the stale 'Open: the edge warning is silent' (closed by section 44).

Checked and consistent: the CHANGELOG numbers of sections 41, 42, 43, 44, 45, 46, 47 against `docs/validation.md` (the FEM corrections of 44 and 28 are in both and in the user guide's validation table and in `checks.py`); `tests/test_docs.py` and `tests/test_version.py` 735 passed after the edits.

Left for the release commit (not mine to change now): `pcbthermal.__version__`, the CHANGELOG date, the README badge (`version-2.6.0`, `3217 collected`) and versions list, the summary at the top of `docs/versions.md`, the test-count line and 'Where to continue (2.6.1)' of `CLAUDE.md` (stale: there is no 2.6.1), `gui/warning_box.py` missing from the structure of `CLAUDE.md`, `docs/version-comparison.md` (not regenerated for 2.6.0 either: it needs result sets for every tag).

## 4. The investigations

`research/REVIEW.md` has a reviewer verdict for every folder added or changed in 2.7.0 (`strong-edge-laminate`, `small-model-defects`, `imported-via-rim`, `via-well-sheet-order`, `imported-copper-edge-film`, the renamed `analytic-edge-and-transient` and `laminate-slabs-and-local-rule`). Two are missing:

* **`research/fdm-inset-edge` is not merged into `develop` and has no review row**, but `CHANGELOG.md`, `docs/validation.md` 47.2, `docs/versions.md` and the pending file name it as the evidence of `fix/fdm-copper-edge-faces` (which is merged and reviewed), and 47.2 cites its script `study_independent_3d.py`. The tester found the folder absent. Gate item.
* **The finite-element reference (`tmp/fem`, git-ignored; `research/independent-fem-edge` paused, unmerged)** is the evidence of `docs/validation.md` 46, of the corrected numbers in 28, 43, 44, of the user guide's validation table and of the texts of `checks.check_edge_laminate` and `_edge_laminate_uncut`. Validation 46 says honestly that the program is 'not part of the repository', but then no script in the repository reproduces numbers the program prints in its warnings. Its own review (`tmp/fem/REVIEW.md`) exists. Gate item: bring it in as a research folder (our code, MIT; it needs only numpy and scipy, scikit-fem and pyamg are optional) with its REVIEW row, or have the maintainer accept a reference kept outside the repository.

## 5. The finite-element comparison against the documents

Read: `tmp/fem/REPORT.md` and `REVIEW.md`. Its section 4 and 6.3 proposals are all applied: validation 28 (the reference hot, via +0.5 % with eight sub-gaps), 43.2 (FEM column), 44 ('reconciled', the FEM column), 46, the two warnings and the user guide. Nothing in `docs/validation.md` contradicts it. Its remaining findings are recorded limits: the FDM at a copper edge (partly cured by section 47), the FDM box edge against an outline edge of the same square (A40, open), the FDM via effect 4 to 16 % low (validation 46). Not covered by the FEM and still quoted against a cell-centred reference: the 3.2 mm two-layer figures of `check_edge_laminate` (section 1).

## 6. What remains before the release commit

Gate items (NO-GO until done):

1. Merge `research/fdm-inset-edge` after a reviewer verdict (its review row in `research/REVIEW.md`), or remove the references to it.
2. The finite-element reference into the repository as a research folder with its review row, or the maintainer's explicit acceptance that validation 46 and the warnings rest on a program outside the repository.
3. The refreeze after the version bump: the four pending files folded into `tests/regression/data/v2.7.0.json` and deleted in that commit, `expected_shifts_2.7.0.json` with the items of section 2 (`study_diff.py --strict`, 0 alarms), the frozen numbers at 2, 1 and 0.5 mm; then the whole battery on the final tree read to its last line.

Release chores: version bump, CHANGELOG date, README (badge, test count, versions list), `docs/versions.md` summary, `CLAUDE.md` (test count, 'Where to continue', structure), the GitHub release.

Non-blocking, for the maintainer:

* The first clause of `check_edge_laminate` (3.2 mm boards, -2.4 / -5.5 / -16 %) is against a cell-centred reference the FEM found hot; re-measure or say so. Wording of `_edge_laminate_uncut` ('3D solver at the same cell' -> 'finite-element solution').
* The open decisions of the per-branch reviews: accept the hot first-order error of the centroid film where drawn copper reaches the outline (+1 to +2 % at 1 mm); the FDM box-edge against outline-edge difference (A40); accept that the lone-via fix is better on average, not on every irregular layout; the cut-overlay default of the command line; a reach from the pad size for the rim mask; the type-ahead of the element tree.
* No transient of the simple-stack-up change was compared with an independent solver (the U2 time to 63 % moves 16 %).

## 7. Battery and what was not verified

Not run by this reviewer (the tester's): the whole battery and the reproduction pass. The tester's candidate report (`releases/2.7.0/battery/README.md` in the tester's worktree, candidate 06cb04d6) found 11 failures, all stale expectations of the simple stack-up and the centroid film, restated in 4e8dfc22; on the tip `tests/regression` at three cells 317 passed, the compat test 5, the secret scan 4, and two research tests (cut-cell-links, strong-edge-laminate) restated in the same commit. The final battery on fd49b969 was running when this opinion was written; its result decides with the gate items above.

Not verified: a real imported board of four layers with an outline (three 2.7.0 items at once); any transient against an independent solver; the GUI on a real display (all GUI tests offscreen).
