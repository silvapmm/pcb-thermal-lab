# Review: the FDM face between two nodes by the harmonic mean of the sheets

Branch: `fix/fdm-harmonic-face-mean` (a723963e, from `develop` fd1c863a; `develop` b5a902ae merged in by the reviewer). Reviewer's verdict: **GO**, with the document corrections below (code unchanged).

## Verdict in short

* The code does what `docs/theory.md` 3 says: the physical sheets (divided by the outline cover) are joined by the harmonic mean and multiplied by the mean cover; the laminate nodes of the rule keep the arithmetic mean where both exist; imported layers with the faces or lambda mapping keep their own face conductances; the metal-block layers take the harmonic mean of their cover-scaled sheets, as the FVM does.
* The claims reproduce: the branch's tests (`test_fdm_harmonic_face.py`, the three re-baselined files) 51 passed; the frozen numbers at 2, 1 and 0.5 mm 317 passed with the pending file; without it exactly its 42 steady records and 11 of its 14 times fail (the times of `plate_vias`, `reference_board` and `round_outline` move by 2e-7 to 9e-7 relative, under the 1e-6 tolerance: harmless entries). `part_across_outline`: arithmetic +0.53 / +0.37 / +0.09 %, cover-weighted harmonic +0.54 / +0.37 / +0.09 %, plain harmonic +0.85 / +0.56 / +0.11 % of the rise at 2 / 1 / 0.5 mm against the FVM at 0.25 mm, which confirms why the cover is divided out.
* No case got worse and none overshoots the reference in what the reviewer added (FDM 1 mm against the FVM 0.25 mm, arithmetic to harmonic): outlines with a top pad T -4.47 to -1.89, L -5.43 to -2.35, round -4.30 to -1.85, turned square -3.05 to -1.21 %, the same with full copper identical; a 3 mm block over a copper edge, its edge 0 / 0.3 / 0.5 mm off the grid, -5.5 / -5.6 / -5.7 to -2.9 / -3.0 / -3.0 %; a pad over hatched copper (fill 0.5 / 0.25) -0.25 / -1.23 to -0.11 / -0.66 %; imported copper faces -0.34 % and lambda +0.53 % unchanged, fill -1.54 to -0.63 %.

## Findings

| # | Kind | Finding | Evidence | Action |
| :-- | :-- | :-- | :-- | :-- |
| 1 | stale document | The FDM columns of `docs/validation.md` 1, 2, 2.1, 3, 3.1 and 12 A/B, `docs/models.md` 3 (example 85.13 against 85.23 °C, '3.5 % below the FVM' at a copper edge) were those of the arithmetic mean. | `study_fdm_harmonic_review.py`, the study builders re-run for the FDM only: heater straddling the copper edge -3.4 to -1.9 %; heater-sized pad of 3.1 against the finite elements -12.9 to -5.2 %, bare laminate with a heatsink -14.6 to -5.9 %; FEM 20 mm pad -2.4 to -1.1 % | Refreshed (old values kept in the text). |
| 2 | wrong document | `CHANGELOG.md` said the via and finned boards and the time to 63 % of the example board were unchanged; the frozen records of `plate_vias`, `plate_lone_via`, `finned_block` move (at most 1.2e-3 K) and the example's time to 63 % +0.2 %. `validation.md` 41 said imported copper with the fill mapping moves 'within 0.01 point': it moves like drawn copper where the copper has an edge. | frozen run without the pending file; `imported` part | Corrected. |
| 3 | stale document (pre-existing) | A row of the scenario table of `validation.md` 2 (two heaters 60 mm apart) sat inside the grid table of 2.1, with a doubled separator in both tables. | `develop` text | Moved back. |
| 4 | limit to record | The residual -2 to -7 % on a bare pad is the first-order error of a node-centred scheme with the copper edge between nodes; the FDM stays below the FVM. | branch table, validation 41 | Kept as stated. |
| 5 | text to re-measure (code, not changed here) | Warnings in `checks.py` that quote FDM numbers measured with the arithmetic mean: a part on bare laminate 'the FDM 2 to 20 %' (`check_model_limits`), a small part over a thick laminate '-6 to -14 % over a copper pad' (FVM and FDM together), the partial-copper via '15 to 85 % low' (FVM and FDM). The new FDM sits closer to the FVM, so the ranges are on the wide side, not wrong in sign. | `checks.py` lines 798, 1073, 1493 | Left for a re-measure (open decision). |
| 6 | research records | READMEs that quote FDM numbers of the arithmetic mean, to refresh in the reproduction pass of 2.7.0: `gerber-models`, `models-comparison`, `gap-subdivision`, `solid3d-verification`, `rotated-square-3d`, `outline`, `zone-union`, `via-fill`, `stackup`, `effective-conductivity`, `block-and-fins`, `bare-spot-under-source`, `via-real-board`, `via-edge-image`, `via-contact-geometry`, `laminate-nodes`, `via-partial-copper`, `strong-edge-laminate`, `point-via-convergence`, `small-model-defects`. | grep of FDM percentages | Listed only. |

## Other checks (all pass)

Matrix symmetric (0 to 2e-18), no positive off-diagonal except the 64 via couplings of the example, row sums equal the ambient conductances to 2e-17, balance below 1.1e-12 and no node below the ambient, on T, L, round and turned outlines with a pad and on the example. Power profiles through `api.simulate` at 1 mm: example profile board peak 135.13 to 135.17 °C (FVM 135.31), a 20 s square wave on a pad 364.10 to 363.97 °C (FVM 366.57; the hottest part is the one on bare laminate), the same regimes; the times to 63 % of every heater move by at most 0.4 %. Cost: the same number of matrix entries (1 077 251 on the example at 0.5 mm), solve time within 5 %, so the memory guard is unchanged. Tests after the reviewer's changes: `test_docs.py`, `test_version.py`, `test_fdm.py`, `test_fdm_harmonic_face.py` 722 passed.

## Reproduce

`.venv/bin/python releases/2.7.0/final-opinion/scripts/study_fdm_harmonic_review.py <part>` with `outline`, `harness`, `block`, `hatch`, `imported`, `profile`, `invariants` (each under a minute, under 2.5 GB). The frozen check: `PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression`, then the same with the pending file moved away.

## Not verified

The independent 3D solver numbers of the branch table (plate_pad, one_layer_pad, the gap and strips) were not re-run by the reviewer beyond the gap rows held by `test_fdm_harmonic_face.py` and the one-layer pad of `test_layered_vs_3d.py` (both pass); the outline, block, hatch and imported checks are against the converged FVM, not an independent solver; the one-layer pad table of `validation.md` 20 (FDM 76.49) was not re-run (marked); the whole battery was not run (the maintainer's).
