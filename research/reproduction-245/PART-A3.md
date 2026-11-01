#  Reproduction pass of 2.4.5, part A3: the long studies of lumped-via-groups and lumped-analytic-vias

Tree under test: tip of `research/reproduction-245` (detached), program of 2.4.5. All runs with `nice -n 15`, one job at a time, `QT_QPA_PLATFORM=offscreen`, `.venv/bin/python`. Reference files (fine grid, 1/16 mm) were built from scratch in `out/refcache` (git-ignored). Tolerance 0.5 % (no other tolerance in the folders). Nothing in `pcbthermal/`, `tests/`, the project documents or the README numbers was changed.

## What was run

| study | command | result | time |
| :-- | :-- | :-- | --: |
| lumped-via-groups `study_zone_sensitivity.py` | no arguments | finished | 19 min |
| `study_family.py` | `--procs 2 --ref-procs 1` | finished, wrote `out/family.json` | 28 min |
| `study_review.py` | `--procs 2` | finished | 1 min |
| `study_holdout.py` | `--procs 2 --ref-procs 1` | finished | 23 min |
| lumped-analytic-vias `study_arrays.py` | `--procs 2` | finished (it was killed at 25 min in part A) | 14 min |
| extra, outside the repository (scratchpad): FVM column of the arrays on the tree of `5e93182~1` and on the tree under test; real 2.4.5 Lumped on the 36 boards | `fvm_arrays.py`, `now.py` | finished | a few minutes |

## Comparison with the README numbers

| folder | README section | README | now | 2.4.5 item | verdict |
| :-- | :-- | :-- | :-- | :-- | :-- |
| lumped-via-groups | 6 (layouts, 12 rows x 6 variants; knobs of the zone model, 14 rows x 2; raster 0.5 / 0.75 / 1.0 mm) | as printed | identical, every cell | none (the library freezes the program as of `f2d5c03`; the references are the fine-grid solver of the folder) | OK (about 110 cells) |
| lumped-via-groups | 4.2 (family: 36 boards x 12 variants, E_ref, best factor, summary mean / max / counts) | `L_prog` 20.9 / 72.2, `L_nn` 13.6 / 62.5, `L_zone_r` 4.4 / 20.1, `L_zone` 3.6 / 9.1, `L_zone_k` 7.6 / 32.0 | identical (all 12 summary rows, all 36 E_ref) | none (frozen) | OK (about 450 cells) |
| lumped-via-groups | 12.1 (null vias, absolute maximum with vias, second reference FVM_fix, 36 + 36 + 4 rows) | null-via effect +0.0 to +4.2 K (`L_zone_r`), up to 44 %; absolute error `L_prog` 6.8 / 22.1 (30 of 36 cooler), `L_zone` 2.8 / 7.3 (5); FVM_fix within -0.1 to -0.3 % | identical | none | OK (about 300 cells) |
| lumped-via-groups | 12.4 (decimation of the potential integrals: closed-form ratios 1.254 / 1.166 / 3.024 strided against 0.993 / 0.984 / 0.929 block; program `_footprint_potentials` link ratio 1.000 ... 0.892 for the 30 mm square, 0.960 / 0.948 for the 20 mm square / disc) | as printed | identical (this part calls the real program: `lumped._footprint_potentials`) | none (the decimation of the program at 900 cells is still there in 2.4.5) | OK (24 cells) |
| lumped-via-groups | 12.2 (26 held-out boards; mean / max / within 10 %: `L_prog` 28.9 / 176.6 (7), `L_nn` 22.6 / 152.9 (11), `L_grp0` 16.0 / 41.4 (9), `L_zone_r` 6.7 / 21.0 (20), `L_zone` 4.5 / 20.2 (23); warning rules 4 + 6 + 3 + 59 and 7 + 3 + 0 + 62) | as printed | identical | none (frozen) | OK (about 350 cells) |
| lumped-via-groups | 12.3 (36 boards at the 1.0 mm raster: `L_prog` 20.1 / 73.8 (15), `L_nn` 13.2 / 64.2 (22), `L_grp0` 18.3 / 37.2 (7), `L_zone_r` 9.1 / 20.8 (24), `L_zone` 8.0 / 20.8 (27) and the 36 rows) | as printed | identical | none (frozen) | OK (about 190 cells) |
| lumped-analytic-vias | 4.3 (lone via, row of five: summary E and gain, `L_prog`, `L_ring`/`L_grp0`, `A_prog`, `A_fin`) | 73.4 / 287.8 / 230.5 / 540.8; 15.1 / 31.4; 83.6 / 236.2; 2.3 / 4.0; row 72.1 / 100.6, 34.6 / 50.2, 8.0 / 10.9, 36.3 / 56.8, 0.7 / 1.4 | identical | none (frozen) | OK (about 200 cells, with the 64 per-case rows) |
| lumped-analytic-vias | 4.4 (48 array cases + 6 pad cases at a 0.1 mm reference: `L_prog`, `L_ring`, `L_grp0`, `L_grp`, `A_prog`, `A_on`, `A_fin`, `FVM_fix`, E and gain, mean / max) | 26.8 / 69.7 ..., 11.0 / 24.1, 9.7 / 33.9, 0.3 / 1.1, pad 8.1 / 17.4 ... | identical, all columns except `FVM` | none | OK (about 700 cells) |
| lumped-analytic-vias | 4.4, row "FVM, program" (array, 48 cases) | E mean / max 5.3 / 10.2, gain mean / max 10.2 / 23.1 | 6.8 / 10.1 and 9.9 / 17.4 | fix of the point via (`5e93182`): the same FVM column on a `git archive` of `5e93182~1` gives 5.3 / 10.2 / 10.2 / 23.1 (the README) and on the tree under test 6.8 / 10.1 / 9.9 / 17.4 (the table now) | EXPLAINED (24 array boards x 2 fills; the same item as the 7 x 7 array of part A) |

Counts: 10 table groups checked (about 2 400 cells); unchanged 9; explained 1 (the FVM column of the arrays); UNEXPLAINED 0; not run 0.

## What changed in the program and what did not

`lib/` of lumped-via-groups and the `L_*` and `A_*` columns of lumped-analytic-vias freeze the program as of `f2d5c03`, and zones are a proposal, so they reproduce by construction; the only column that calls the real program in these studies is `FVM` (the arrays table) and the decimation of part 4 of `study_review.py` (unchanged). The `FVM` column moved only in the mean of E (5.3 to 6.8 %) and in the maximum of the gain (23.1 to 17.4 %): the point via of 2.4.5 is the reason (the program's FVM now gives the copper-fill 7 x 7 array 21.05 K where it gave 19.23 K); `FVM_fix` (0.6 / 1.2) is the proposal and unchanged, so the 2.4.5 program is in between: it is 5.7 points closer in the maximum of the gain and 1.5 points farther in the mean of E than before; the README sentence "FVM, program 5.3 %" is the 2.4.4 number.

## For the queued zonal Lumped model (`research/lumped-zones-adoption`)

The scripts do not give the 2.4.5 Lumped on the family: `L_prog` of the family table is the program frozen at `f2d5c03` (no point via, no constriction, no micro well). I measured it with a scratch script (`now.py`, outside the repository: `refs.lumped_E` with no patch, so the real program, against the cached fine-grid E_ref of `out/family.json`, 36 boards, error of E in percent):

| variant | raster | mean | max | within 10 % | model cooler (E too large) |
| :-- | --: | --: | --: | --: | --: |
| `L_prog` frozen (README, `f2d5c03`) | 0.5 mm | 20.9 | 72.2 | 13 of 36 | 33 of 36 |
| **2.4.5 Lumped (micro well + macro cap 0.75)** | 0.5 mm | **10.8** | **32.0** | **20 of 36** | 21 of 36 |
| **2.4.5 Lumped** | 1.0 mm | 10.9 | 33.4 | 19 of 36 | 20 of 36 |
| `L_nn` (micro well alone, README) | 0.5 mm | 13.6 | 62.5 | 20 of 36 | |
| `L_grp0` (README) | 0.5 mm | 18.0 | 38.7 | 9 of 36 | 4 |
| `L_zone_r` (README) | 0.5 mm | 4.4 | 20.1 | 35 of 36 | |
| `L_zone` (README, after the review) | 0.5 mm | 3.6 | 9.1 | 36 of 36 | 17 of 36 |
| `L_zone` (README) | 1.0 mm | 8.0 | 20.8 | 27 of 36 | |

Reading: 2.4.5 halves the error of the program on this family (20.9 to 10.8 % mean, 72 to 32 % maximum) and is now about as good as the micro well alone in the mean and much better in the maximum, but it is still three times the zone model's mean at 0.5 mm (3.6 %) and the maximum is on the boards with a small share of the footprint covered by the vias (14 mm source, 5 x 5 at 0.8 mm copper +28.1 %, 5 x 5 at 1.2 mm copper +32.0 %, 7 x 7 +30.9 %); the unsafe side (model cooler than the reference with vias, positive error) is 21 boards of 36. Its raster dependence is small (10.8 to 10.9 %). The numbers of the zone model in the README were measured against the frozen program, not against 2.4.5, so the "gain of the zones" over the program is 10.8 to 3.6 % in the mean (not 20.9 to 3.6 %) and 32 to 9 % in the maximum. I did not re-run `L_zone` against the 2.4.5 network (its library copies the old network); that comparison belongs to the adoption branch. The row-level numbers are in the scratchpad file `now.log`, not committed.

## Not verified

- The zone library was not re-run on the 2.4.5 network (see above).
- No physical measurement; all references are the layered fine-grid solver of the folder.
