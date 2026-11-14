# Review of `fix/lumped-part-readout`

**Verdict: GO** for the merge into `development`, after the corrections below (committed on the branch), and with the whole battery left to the tester.

## What the branch does

With the Lumped as the only model, every part read-out (`analysis.heater_stats`: the Results rows, `Tj`, the margin, the power limit, the Components table, the Power Calculator, the top-path split and the convection calibration to a part temperature) read the painted footprint, which is the ring-0 node without the peak term of `docs/theory.md` eq. 5.5. `lumped.solve_steady` now stores the own peak of every powered part in `arrays["heater_peak"]` and `heater_stats` reads the larger of it and the painted field.

## Checks

1. **Same quantity as the board maximum.** `heater_peak[k]` is computed inside the loop that gives `SteadyResult.t_max`, with the same three terms (own node of the source layer, `peak_extra`, the other networks read at the centroid). For a zoned footprint `peak_extra` is `_ZonePeak.extra`, relative to node A and already the largest of the A field, the core mean plus the micro peak and the bump, so nodes C and A, the `cap` macro and the micro peak enter exactly as in `t_max`. Measured: `heater_peak` equals the research re-derivation (`study_block_pads.lumped_part_peaks`) to 1e-14 K; on fifteen boards (one part, several parts, a zoned via group, vias, a block, four layers, an outline) the hottest part row equals the Lumped `t_max` to 0. Parts with no power keep NaN and read the field. The index of each part is found by identity in the same problem object (`drop_off_board_vias` keeps the order).
2. **Frame on an outline board.** The value is a temperature per part, with no position, so the stretch of the equivalent rectangle in `api._run_model` does not concern it; the heaters keep their order in the copy. Test added.
3. **No double count.** The Lumped has no face terms (`laminate.face_terms` are an FVM and FDM array), `t_junction` and `part_split` add `P theta` to the part reading once, as they did to the field reading. Where the painted field is hotter than the own peak (two parts 2 mm apart: the neighbour's profile near its own edge) the field is kept, so the row never falls below the map. The only over-estimate seen: a part beside a hotter one reads 2.5 to 3 % of its rise hot against the FVM and the independent 3D solver (the neighbour is read at the centroid and added to the part's own hottest point), on the safe side.
4. **Top-path split.** The board stays affine in the board power at fixed coefficients and the peak is linear in it, so `g(P_b)` stays monotone with the same bracket `[0, P]`. One part and three coupled parts (two clipped) converge with no warning; the heat to the top moves toward the FVM (1.865 to 1.899 W against 1.941 W on `part_top_path`; 2.062 to 2.112 against 2.135 W, 2.039 to 2.091 against 2.150 W on the review's boards). On `part_top_path` the Lumped board maximum moves from +0.3 to -1.2 K of the FVM (a cancellation that the old reading hid); on the review's board from +1.26 to -0.39 K. Test added.
5. **Time path.** `lumped._own_point` already read the peak in the profile and step-response curves, so steady rows and time curves now share one definition.

## Independent re-run

`docs/validation.md` 48.3 holds the table: fifteen boards against the FVM at 0.5 mm (single parts before -9 to -15 %, now -0.2 to -5.8 %; parts at or across the edge and a 2 mm part on bare laminate keep the known Lumped limits, reduced by about 5 to 8 points) and four boards against `tests/helpers/layered3d.py` (FVM within 0.5 %; Lumped from -10.3 / -8.3 / -3.9 / -6.8 % to -0.6 / -1.0 / -0.3 / -1.3 % on the hottest parts).

## Frozen numbers

`PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression`: 317 passed with the pending file; without it exactly the 51 records of `lumped-part-readout.json` fail (every Lumped record of the 17 boards at three cells) and nothing else. Moved metrics: part `t_max` and `t_junction` (up to 13.4 K); on `part_top_path` also the board maximum, means and the heat to the top. No record is in two pending files (it is the only one).

## Corrections made by the review

* `tests/regression/data/pending/lumped-part-readout.json`: the evidence pointed to `docs/validation.md` 17.4, which does not exist; now 48.
* `tests/test_lumped_part_readout.py`: the first assertion was a tautology (`row == max(row, peak)`); it now compares with the reading without the array. Three tests added: a neighbour hotter than the peak keeps the field, an outline board, the top-path split.
* `CHANGELOG.md`, `docs/theory.md` 5: '9 to 12 %' was narrower than measured; now 'about 10 %' (9 to 15 % on the review's boards, 2 to 4 % beside a hotter part), and theory states that the time path already used the peak.
* `docs/validation.md` 48.2: the `part_top_path` numbers are degrees Celsius with the FVM beside them and the cancellation said; the convection calibration added to what moves; the research folders that move listed; 48.3 added.
* `research/block-warning-remeasure`: its test failed on the branch because the first-pass 'field' column of `study_block_pads.py` read `heater_stats`, which now returns the peak; the script holds the array aside for that column (the first-pass CSV stays reproducible) and the README says so.

## Research folders that move (A45)

Lumped `t_max` or `t_junction` read through `heater_stats`: `component-heatsink` (`top_path_study.py`), `lumped-near-edge` (`study_seri_lee.py`), `published-cases-followup` (`study_near_edge.py`), `paper-case-studies` (`study_vertical_plate.py` with the Lumped). Their tests pass (3, 7, 31, 19), as do those of `lumped-zones-adoption` (20) and `block-warning-remeasure` (2, after the fix). The studies themselves were not re-run: the reproduction pass of the release does it.

## Warning texts

The block warning ('Lumped on the cool side, about 5 % with one pad, up to about 7 % with several pads or a block much smaller than the board; Analytic about 5 %') matches `research/block-warning-remeasure` (Lumped one pad -0.8 to -1.2 %, several pads -2.9 to -7.0 %; Analytic -1.3 to +0.1 %) and the 74 one-pad cases (Lumped at most 4.7 %, Analytic 4.3 %); it is not over-precise.

## Not verified

The whole battery (left to the tester); the four research studies above; imported copper (the code path does not depend on it, not run); a metal block with vias.

## For the maintainer

No decision is needed to merge. To note: the Lumped part on a board with a top path now reads its board maximum slightly cooler than the FVM on the frozen board (the old reading had hidden it), and a part across an outline in the equivalent-rectangle path stays about 28 % cool (a limit of that path, `docs/versions.md` 'Planned' if wanted).
