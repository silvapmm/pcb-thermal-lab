# Review of `fix/imported-copper-outline-mask` (2.7.0)

Merged into `develop` as df80e7e8 (change 22064995) before review. Corrections on `fix/imported-copper-outline-mask-review` (from `develop`). Scripts: `scripts/study_outline_mask.py` (the program, any tree through `PCBT_TREE`) and `scripts/indep_two_sheets.py` (independent, imports nothing from `pcbthermal`).

## Verdict

**GO with the corrections of the review branch.** The code does what it says (the pixel sheet times its exact board share, the unmasked faces times the aperture where a cell centre is off the board), keeps the heat balance (1e-12), the symmetry and the sign of the matrix, moves no frozen record, and makes the heater rise of turned boards nearly independent of the angle. Its headline number (mean error halved) does not hold against an independent reference and is withdrawn in the documents.

## Findings, by severity

1. **Defect in the branch's tests** (fixed): the change deleted three unrelated regression tests of the drawn cut-cell treatment (`test_the_lumped_model_builds_its_network_without_the_series_term`, `test_a_constant_temperature_field_is_reproduced_to_round_off` for `h_side` 10 to 1e5, `test_a_dropped_sliver_keeps_the_heat_balance`). Restored; they pass.
2. **Wrong claim in the documents** (corrected: `docs/validation.md` 38.1 and 38.4, `CHANGELOG.md`): the before/after mean errors were measured against the same treatment at 0.25 mm. Against a reference that does not move with the treatment (per angle, the three treatments at 0.125 mm agree to 0.8 %; with the laminate rule off, the aligned board equals the independent solver, 67.584 against 67.58 K), at `h_side` 200 W/m2K, five turned squares, mean / spread: 1 mm before +0.34 / 6.06 %, after -2.20 / 1.86 %; 0.5 mm before +0.17 / 2.64 %, after -1.24 / 0.94 %; 2 mm +2.96 / 7.57 % against -2.51 / 5.74 %. The earlier mean was two errors cancelling (weak cut-cell links, hot; film on the node, cool: the aligned board reads -2.43 % at 1 mm in both trees). At 10 W/m2K all treatments agree within 0.4 %.
3. **Memory above the law** (fixed in `copper._pixel_board_cover`): `geometry.exact_coverage` on the pixel grid held about 40 B per pixel (642 MB on 16 M pixels); the faces of a 200 mm board at 1 mm peaked at 740 MB against 221 MB without an outline, above the 40 B per pixel of `memory.FACES_BYTES_PER_PIXEL`. Now in bands of a million pixels, float32: 248 MB; equal to one call to 6e-11; the heater rises of the study unchanged to the printed digit. Test added.
4. **Limit recorded**: the cooled-edge bias of the edge film on the node on imported boards (1 to 2.7 % cool at 1 mm, 200 W/m2K). The series film tried by the review: aligned +0.32 %, turned mean -1.56 % at 1 mm, spread 2.91 %; not adopted.
5. **Limit recorded**: a silent fallback to the cell cover if the outline crosses more than `OUTLINE_MAX_CROSSINGS` pixel lines (more than about 20 m of edges at the finest cell); unreachable for real boards.

## Checked and found right

* Real imported outlines (library, local): oswlight (round, 36 mm), rp2040, storm; two 3 mm heaters of 1 W; largest move -1.4 % (oswlight edge heater, 200 W/m2K, 1 mm); balance 1e-12.
* The 12 mm turned full-copper board of the tests at 0.5 mm: 117.84 K (the branch said 117.8 K); a time simulation ends at 117.81 K after 12 time constants.
* Matrix symmetric, no positive off-diagonal entry; the warnings of imported copper still fire for the FDM, Lumped, Analytic and 3D solid on an outline board; the removed warning text is gone from every model; hostile masks are untouched by the change (the masks are checked before this code; the pixel cover comes from the validated outline).
* Cost: the network build of an outline board takes 1.5 to 2 times as long (face problems twice): 2.2 to 3.8 s (100 mm, 0.5 mm), 21 to 31 s (200 mm, 1 mm).
* Frozen numbers: 317 passed at 2, 1 and 0.5 mm. Tests: `test_cut_cell_links.py`, `test_imported_copper.py`, `test_memory.py`, docs, licence header.

## Not verified

The FDM, Lumped and Analytic paths (unchanged by the code); a cell much finer than the pixel; a converged reference for the real boards (no independent solver of patterned copper on a round board); the executor's own case (its script was not kept).

## Open decisions for the maintainer

* Accept the cooled-edge bias (1 to 2.7 % cool at 1 mm, 200 W/m2K, imported copper on any outline), or open a study of the edge film for imported copper (the series film fixes the aligned board, not the turned ones).
