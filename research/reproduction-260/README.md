# Reproduction pass of 2.6.0: the research tests on the combined tree

This branch (`research/reproduction-260`) starts from `feature/integration-260`, not from `develop` (an exception to the branch rule: the 2.6.0 program and the research
folders to be re-run live only there). It edits research code, tests and documents only; `git diff feature/integration-260 --stat -- pcbthermal tests examples ico docs README.md
CHANGELOG.md CLAUDE.md` is empty.

## 1. Method

`pytest -q research/<folder>/tests --timeout=900 --timeout-method=thread -p no:cacheprovider`, one folder per call, one call at a time, offscreen, with the library
environment of `pcb-library/scripts/link_env.sh` (load average 3.3 to 4.3, peak memory under 1 GB). 45 folders have a `tests/` directory. Scripts (`study_*.py`,
`make_figures.py`) were not re-run, except where a test imports them; see section 4.

## 2. Totals

| | folders |
| :-- | --: |
| checked (folders with tests) | 45 |
| green before any repair | 28 |
| red before: stale copy of program code | 8 |
| red before: number moved by an item of 2.6.0 (explained, test restated) | 8 |
| red before: needing PCBT_REAL_BOARDS (skipped) | 0 (the variable was set; one test of memory-guard raised without it, now skips) |
| green after the repairs | 45 (one strict xfail, section 3) |
| unexplained shifts | 1 (Lumped, section 3) |
| flagged for the maintainer (explained, but a result to look at) | 1 (via barrel against the resolved Shen cell, section 3) |
| not run | the studies and figure scripts (section 4) |

(Some folders belong to two causes; each row of section 5 gives the cause of each failing test.)

## 3. For the maintainer

* **Unexplained shift (strict xfail kept visible).** `research/lumped-ring-uniform-deficit/tests/test_lumped_log.py::test_defaults_are_the_program`: the Lumped model patched
  from the v2.5.1 text plus the first-ring cap differs from the live 2.6.0 Lumped by 1.1e-4 K (60 x 40 mm, 2 layers), 1.5e-5 K (100 x 80 mm, 4 layers) and 1.2e-2 K (30 x 20 mm,
  1 layer) on boards with no outline, no vias and no part under two cells. The cap, the near-edge refinement and the barrel do not act on these boards; the cause was not isolated
  to an item of the version. Possible defect or a rounding-level change of the exact board cover; to be isolated by bisecting the integration merges.
* **Explained, but the program moves away from an independent reference.** The 2.6.0 via barrel (`viawell.barrel_length`, half the copper thickness added to the gap) moves the FVM
  at 0.1 mm on the 12 x 12 via array of `research/lumped-zones-adoption` from 1.4728 K (reference of the resolved axisymmetric cell 1.4611 K, +0.8 %) to 1.5777 K (+8.0 %). In the other
  published case (`research/published-cases-followup`, Shen unit cell) the same item moves the program from -7.46 % to -0.30 % of its reference. The two cases pull in
  opposite directions; the barrel fraction rests on `research/via-contact-geometry` only.
* Several research libraries copy program code. They now either read the program (`viawell.barrel_length`) or a frozen copy: `lib/analytic_v251.py` (v2.5.1 `analytic.py`,
  in `lumped-analytic-vias` and `analytic-2-6`), `git show v2.5.1:` for `solid3d.py` (rotated-square-3d) and `lumped.py` (lumped-ring-uniform-deficit).

## 4. Not run

The study scripts, the figure scripts and the tests that skip (gerber real boards, 7 + 5 + 3 + 1 skipped, as before) were not re-run. Edited and **not executed**:
`research/laminate-2-6/scripts/study_solid_slices.py` (the face term is no longer added when the solid already carries `face_mean`),
`research/analytic-2-6/scripts/study_transient_both.py` (new variant `current`; `program` is the v2.5.1 calibration). The figure of `research/rotated-square-3d`
that the audit listed (fig 37) was not regenerated. The README numbers of the research folders were not re-compared one by one: only where a test holds them.

## 5. Per folder (command: `pytest -q research/<folder>/tests`; before / after)

| folder | before | after | cause | fix |
| :-- | :-- | :-- | :-- | :-- |
| analytic-2-6 | 3 failed, 6 passed | 9 passed | (a) `lib/calib_variants.py` read `analytic._calibrated_dynamics`, removed; (b) the per-layer edge and the local modal transient are now the program, so the prototypes equal it | frozen v2.5.1 copy for the old calibration; the tests assert that the program now agrees with the independent finite differences and is within 3 % of the FVM |
| analytic-edge-spatial | 1 failed | 19 passed | (b) Analytic via barrel (0.15 K on the example board) and the per-layer edge loop (1.1e-4 K) | copy follows `d_barrel`; test switches the loop off with `EDGE_MISMATCH_MIN` |
| cut-cell-links | 3 failed | 30 passed | (b) laminate edge band (+2.4 K on the 30 mm edge board, film floor binds on full copper), exact cover and cut-cell film (sliver jump above 3 K -> 0.285 K) | statements restated with the numbers |
| face-down-convection | 1 failed | 5 passed | (b) lower-face law 0.475 Ra^(1/5) | `current_down` added, `program_down` stays the 2.5.x baseline |
| horizontal-plate-h | 1 failed | 15 passed | (b) same | same |
| laminate-2-6 | 7 failed | 7 passed | (a) `laminate.plan_gaps` takes `edge` | replacement accepts it |
| laminate-edge-band | 2 failed | 7 passed | (a)+(b) same signature; the band is in the program, baseline 100.387 K against the study 100.328 K | band switched off for the baseline |
| laminate-nodes | 1 failed | 20 passed | (b) rim uncoupling removes the barrel into a bare plane, no odd cycle | test reproduces it with full rim contact and asserts the 2.6.0 behaviour |
| lumped-analytic-vias | 6 failed | 13 passed | (a) text anchors of `analytic.solve_steady`; (b) barrel +0.13 % on the Lumped unit cell (360.2915 -> 360.7554 K) | frozen v2.5.1 analytic; barrel fraction 0 reproduces the f2d5c03 number to the last digit |
| lumped-ring-uniform-deficit | 1 error | 5 passed, 1 xfailed | (a) anchors of the first-ring cap, now in the program; (d) residual shift | patches read the tag v2.5.1; strict xfail |
| lumped-zones-adoption | 1 failed | 20 passed | (b) barrel, see section 3 | both numbers asserted |
| memory-guard | 1 failed | 59 passed | (b) edge band: 452 -> 1568 unknowns (ratio 3.47; 200 -> 800 without); (c) a family needs PCBT_REAL_BOARDS | ratio stated both ways; skip without the variable |
| published-cases-followup | 1 failed | 19 passed | (b) barrel, -7.46 % -> -0.30 % | expected value restated |
| rotated-square-3d | 1 error (collection), then 9 failed behind it | 34 passed | (a) the SOR patch anchor and the 3D-solid text anchors; (b) cut-cell links and film, edge band, solid slabs adopted (2.6.0 solid 61.107 K against 61.619 K, -0.83 %) | `plain_program()` = fvm.Network with `cut_cells=False` and no band; solid variants from the tag; SOR redirect on `_lateral_links` |
| theory-sources | 1 failed | 32 passed | (b) lower-face law: README numbers -1.1, +0.6, +1.0, +0.7 % reproduce exactly with the 2.5.x law; +0.35, +1.04, +1.09, +0.68 % with 2.6.0 | both asserted |
| via-edge-image | 2 failed | 7 passed | (a) copy of `viawell.build` with k A / d | copy follows `barrel_length` and the rim shares |
| via-real-board | 2 failed | 26 passed | (a) same | same; the bit-for-bit prototype comparison sets the barrel fraction to 0 |
| (the other 28 folders) | passed | passed | | |

The 28 unchanged folders: analytic-partial-copper, bare-spot-under-source, bochkov-robin-check, bom-role-and-close-hook, component-heatsink, convection-laws,
effective-conductivity, fin-channel, fin-channel-sources, gap-subdivision, gerber-cad-profiles, gerber-import, gerber-models, gerber-nets, gerber-real-boards,
lumped-near-edge, lumped-via-groups, paper-case-studies, plate-h-level, point-via-convergence, reduced-models-imported-passives, release-regression-245,
sor-with-via-couplings, theory, via-contact-geometry, via-partial-copper, young-omega-tiles, zone-union.

`tests/test_docs.py` and `tests/test_license_header.py` on this tree: 667 passed.

## 6. What was read and what was not verified

Test results are the printed pytest lines of two sweeps of all 45 folders (before and after the repairs). The causes were established by switching the single item off in memory
(barrel fraction 0, `laminate.edge_band` returning no cell, `cut_cells=False`, the 2.5.x lower-face constants, the tag v2.5.1 text) and getting the earlier number back; where that
reproduced the frozen number to the last digit it is said so. No claim about the physics of an item is made here.
