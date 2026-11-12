# Integration: recommendations per item

Evidence: `README.md` of this folder (sections in brackets). Nothing here edits the program; each accepted item is implemented on a `fix/` branch off `develop` by the executor after the reviewer,
with the frozen-number consequences below (a pending shift file per item, `tests/regression/make_pending.py`).

| # | Item | Recommendation | Size | Frozen numbers moved |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Lumped heats with a far via [1] | **Fix** (grouping by the smaller distance, lone via d_nn infinite) | S, about 10 lines in `viaconstriction.py`, 1 test file, theory 6.1 sentence | none (0 of 25 harness runs); no pending file |
| 2a | Lumped mirror asymmetry [2.1] | Optional fix (interpolated read of the other heaters at the centroid) | S, 1 line + helper in `lumped.py` | 9 of 51 Lumped records, at most 0.065 K (`example_board`, `profile_board`, `example_cut_to_T`) |
| 2b | FDM below the FVM across cut copper [2.2] | **Fix, with the maintainer's decision**: default `mean="harmonic"` in `fdm.Network` and `fdm.solve_steady` | XS code (2 defaults), M with the refreeze, documents and re-measured validation tables | 28 of 34 FDM records at 2 and 1 mm; large on bare-pad boards (`plate_pad` +36.8 / +20.7 K, `one_layer_pad` +7.5 / +4.3 K, `two_layer_partial` +1.6 / +1.1 K), at most 0.07 K on uniform and example boards |
| 3 | 3D solid, via on a grid line [3] | **Limit, not fix**: say it in the documents; optional symmetric split only if the maintainer wants symmetry | XS (text) / S (split) | split: 8 of 34 3D-solid records, -0.7 to -2.5 K |

## 1. Far via in the Lumped model (fix, small)

* **Change.** `viaconstriction.via_groups`: join `i` and `j` when `dist <= 2 min(d_i, d_j)` (both balls reach each other); in `ViaSet.__init__` set `d_nn` of a via whose group has one member to `inf` (the
  convention of `nearest_neighbour` for one via). Prototype and tests: `lib/grouping.py` (`min_inf`), `tests/test_small_defects.py`.
* **Measured impact.** The Lumped change when a far via is added: +1.263 to -0.000 K (16 vias under the part), mean error over 40 random boards 1.027 to 0.001 K, worst 4.78 to 0.006 K, none worse by
  more than 0.05 K; the harness records (Lumped, Analytic; 2, 1, 0.5 mm) do not move, so `v2.6.0.json` stays. The Analytic reads the same `ViaSet` for its tiles: it did not move on any board tried.
* **Risks.** Another consumer of `group` or `d_nn` (`_core_mask`, the zone model, `median_nn` of the Analytic) sees different groups for irregular via layouts (a stray via beside an array at 2 to 3
  pitches: the old rule joined it, the new one joins it only if its own distance and the array's reach each other: still joined when within 2 pitches of the array). Re-run `research/lumped-via-groups`
  and `lumped-zones-adoption` studies (their 36 and 62 boards) to confirm no regression before the merge: the executor should do it (not done here).
* **Not covered.** A via 1 pitch outside the cluster stays in the group and still reads +0.74 K against the FVM's -0.08 K (README 1.3); a separate item (the group's `d_nn` mean and `n_g` count the
  vias that are not under the footprint).
* **Documents.** `docs/theory.md` 6.1 (one sentence on the grouping), `docs/validation.md` (a line), `CHANGELOG`.

## 2a. Mirror symmetry of the Lumped (optional)

* **Change.** In `lumped.solve_steady` read `ri["dist"]` at the centroid by bilinear interpolation (`lib/centroid_patch.py`, `interp_at`) instead of the floor cell.
* **Impact.** Mirror difference 0.09 / 0.04 K to 0.000 K (1 / 0.5 mm); the example board moves +0.065 K away from the FVM (86.79 to 86.85 against 85.38 K): a symmetry fix, not an accuracy one. The same
  floor read exists in the transient cross terms (`lumped.py` line 1179, `cidx`): it would need the same change (not measured).
* **Recommendation.** Do it only if symmetry matters to the maintainer; low value, 9 records move.

## 2b. FDM harmonic mean (the decision)

* **Change.** `fdm.Network.__init__` and `fdm.solve_steady`: `mean="harmonic"` as the default (the option exists, nothing else to write); update `fdm.py` header and `docs/theory.md` (the FDM face
  conductance), `docs/validation.md` FDM rows, user-guide sentence about the FDM if any.
* **Impact (measured here, README 2.2).** FDM error against the FVM across cut copper halves (3 mm gap, 1 mm cell: -18.6 % to -9.6 %; 0.5 mm: -5.1 to -2.1 %); `plate_pad` -10.6 to -4.2 % at 1 mm (-6.0 to
  -2.7 % at 0.5 mm), `one_layer_pad` -10.3 to -4.0 %, `two_layer_partial` -1.4 to -0.6 %; uniform, hatched, via and finned boards unchanged. **It moves many frozen FDM records** (28 of 34): a pending
  file, `v2.6.x` refreeze, and the FDM numbers quoted in `docs/validation.md`, `docs/versions.md` and READMEs that import the FDM (`models-comparison`, `stackup` tables) must be re-run by the tester.
* **Risks.** The harmonic mean was not run on boards with imported copper (the face conductances there come from `copper.lateral`, not from `_mean`; expected unchanged), on a board with a block, on
  the FDM transient and the animation (same `Network`, not re-measured), nor on the node cover at an outline (outline boards move at most 0.4 K in the harness). A residual first-order error stays (-2 to
  -5 % at 1 mm): the real fix is the node-centred cut-cell treatment of `research/ROADMAP.md` A32.
* **Recommendation.** Adopt (it is the FVM's own mean, already in the code, and removes half the error), after the reviewer re-checks the above with the independent 3D solver (`tests/helpers/layered3d.py`)
  on the `plate_pad` and gap boards.

## 3. 3D solid with a via on a grid line (limit)

* **Finding.** The mirror asymmetry (0.5 to 1.6 K at 1 mm, 0.4 to 1.2 % of the rise) exists only for a via exactly on a line; the symmetric split removes it but creates a 2.4 K jump against the same via
  0.1 mm off the line, which the program does not have (the FVM jumps by 1.4 K for the same move: README 3.2). Neither choice is clearly nearer the truth.
* **Recommendation.** **Limit.** Add one sentence to `docs/theory.md` (3D solid, via footprint) and `docs/validation.md`: "a via exactly on a cell line is placed in the cell above and to the right; the
  mirror image of the board differs by up to 1.6 K (1 mm cell); move the via by a fraction of a cell". No code. If the maintainer wants symmetry, `lib/solid_gridline.py` is the change (S) with 8 pending
  3D-solid records (-0.7 to -2.5 K). A position-smooth footprint (cloud in cell) is the principled alternative and needs its own study.

## Order and checks

1 before 2b (they do not interact); 2b alone needs the refreeze. Each fix: its test from `tests/test_small_defects.py` moved into `tests/`, the docs gate, the frozen test with its pending file, and the
whole battery before a merge.
