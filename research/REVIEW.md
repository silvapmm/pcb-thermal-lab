# Review register of the investigations

What the independent `reviewer` agent has checked in each folder, so that a later session continues where the last one stopped; the chapter `N. Review` of each folder's README holds the status, the independent checks, the limits (what was not verified) and the defects of the program found; this file only registers them. Status `reviewed` means the findings are fixed and the numbers of the documents are the ones the scripts print now. Program version is the last commit of `develop` that touched `pcbthermal/` when the studies were last run. Update a row in the commit of the review it records; what is left to finish is `ROADMAP.md` section 1.

| Folder | Status | Program version | Open points (details in the README of the folder) |
| :-- | :-- | :-- | :-- |
| `solid3d-verification/` | reviewed | `6eb9adf` | none; the cost caption and documents corrected after the long runs |
| `models-comparison/` | reviewed | `0ea5f07` | none |
| `effective-conductivity/` | reviewed | `6eb9adf` | F1: the Culham and Yovanovich shortfall above Biot 60 is not closed |
| `outline/` | reviewed | `0ea5f07` | edge loss on grid lines: corrected in the program |
| `stackup/` | reviewed | `0ea5f07` | none |
| `block-and-fins/` | reviewed | `a9c1cd1` | fin ratio on the sides: corrected in the program; a block beyond the outline pinned to the ambient: corrected in the program (`fix/block-beyond-outline`) |
| `component-heatsink/` | reviewed | `1674d52` | top-path loop: corrected in the program |
| `power-calculator/` | reviewed | `6eb9adf` | none; the band does not hold the true power for a drawing error (D4) |
| `via-fill/` | reviewed | `6eb9adf` | open: the point via does not converge with the cell (A5); the 3D solid clips a via larger than its cell; the tooltip says "finished hole" while the model uses the drill; Lumped and Analytic overstate vias (A6) |
| `point-via-convergence/` | reviewed | `3d672f1` (develop at 2.4.4) | the treatment converges (0.4 to 0.7 % against the layered reference); `0.78 r_v` is a single constant, -2.1 to +3.9 % from an axisymmetric 3D barrel on 2 to 6 planes; on adoption: footprints restricted to cells on the board, SOR refused or given the via couplings (today 19 to 22 K low with a warning), Lumped `gz_via`, fill-in with thousands of vias to measure; decisions in `INTEGRATION.md` |
| `bare-spot-under-source/` | reviewed | `1b7250a` (develop at 2.4.4) | every table reproduced (outputs identical) except the real-board table, which was stale (printed before the face term; re-run: n = 4 gives -7.3 / -4.1 %, not -8.6 / -5.1 %); the reference is 0.3 to 2.2 % high, not 0.3 to 1 % (graded-grid extrapolation, `scripts/study_review.py`); the 3D solid's 1.3 to 2 % low is its maximum taken at the centre of the top copper slab, not a missing laminate; the hatched overshoot is the face term on a partial cell, not the mean thickness; open for P1: the face term on partial cells and the same face in the 3D solid; decisions in `INTEGRATION.md` |
| `theory/` | reviewed | `3e90a7f` | open: `Heater.top_resistance()` uses `theta`, `analysis.part_split` uses `junction_theta()` |
| `gerber-import/` | reviewed | `a6f822b` | none in the program (no model involved) |
| `gerber-models/` | reviewed | `a6f822b` | open: zones combined by the maximum per cell (-8.2 % FVM, -19.1 % FDM on abutting strips); two laminate nodes 5.5 to 13.6 % cool on patterned copper (A11); the laminate of a one-layer board in the 3D solid is corrected |
| `gerber-nets/` | reviewed | not applicable (no electrical code in `pcbthermal/`) | none in the program; limits: return current in the ground net, resistivity, plated outer copper |
| `lumped-analytic-vias/` | not yet reviewed | develop at 2.4.4 | the investigation is complete and waits for the reviewer: the claims are in the README summary; the references are the fine-grid layered solver and the 3D solver of `point-via-convergence`; no published via-array constriction case was reproduced; the calibrated constants and the Gerber boards are open |
| `plate-h-level/` | reviewed | `5979a4f` | none in the program; all numbers reproduced (2D plate re-run at Ra 1e4 to 1e7), the similarity coefficient checked by a second solver; corrected in the folder: the 3 to 4 % uncertainty read from the 2D energy balance (the finer grid moves Nu by 0.01 to 0.11 %), the explanation of the -0.1 % of `fin-channel` (7 % offset to the laminar form, measured: -1.8 % offset, +1.7 % channel), inverted percentages (0.59 is 4 to 13 % high, the all-range form 6 to 11 %), the 0.68 is a fitted constant (the 2D plate gives 0.35 to 0.54), Figures 1 and 2; open: decisions in `INTEGRATION.md` 6 (names and default of the two options, `auto`, the warning at low `Ra`) |
| `fin-channel/` | reviewed | `11b3bc4` | none in the program; all numbers reproduced, the channel solver checked by a second solver (0.3 %); corrected in the folder: the baseline of README 5 and 6 (a 7 % offset between the composite's plate limit and the Churchill and Chu plate had been read as "no channel effect at 6.5 mm" and the `phi` form as conservative; the channel effect is +1.9 % of the rise there), the 3D-solid pitch counted `h_extra` twice (regression test), the `beta` and block-temperature notes, Figure 10; open: decisions in `INTEGRATION.md` 6 (rule at `Ra_b < 90`, the `phi` option, C3a, radiation, the plate level) |
| `fin-channel-sources/` | reviewed | `5066576` | none in the program; corrected in the folder: the program's coefficient of the horizontal arrays now uses the program's fin ratio (`W/p` fins; 1.85 -> 1.81 at 5.55 mm, 1.09 -> 1.02 at 14.35 mm, `phi` 1.10 -> 1.06), four missing plot points, the Elenbaas limit 0.5996, Tari's Table 2 sets, and the arrays are fins up (not the fins-down block of the examples); Table I confirmed by a third solver; the Bar-Cohen, Iyengar and Kraus array is within about 1.5 % with tabulated air; open: the 2.66 / 1.25 reading, the originals (C3b), fins down |
| `zone-union/` | reviewed | `98bae17` | open (decisions in `INTEGRATION.md` 3 and 4): adopt the per-point union (prototype `fix/zone-union`, 681 passed); limit found, not about zones: the layered models lose 12 to 14 points of the peak on a part over bare laminate (README 8.3); the real-board reference is 5 to 14 % low at 0.25 mm |

Program defects found by a review are never corrected from a research branch: they are items of `docs/versions.md` ("Planned") or are marked "corrected in the program" above.

## Decisions left to the maintainer

Row 4 of `ROADMAP.md` section 1; the recommendation to start from is after each.

* gerber-nets: the ground return current (not yet; list it as a limit); the copper resistivity (1.72e-8 ohm m with 0.393 %/K, editable); whether the rho(T) loop reuses `api._solve_with_tc` (reuse, evaluated on the hottest track cell, iterated to convergence).
* gerber-models: the default mapping of an import (flow-based faces for patterned copper, the fill as the fast fallback); a `fix/` branch for the union of zones per sample point; refine the laminate nodes (investigate first, A11); the 42-window studies on the program's network.
* via-fill: the point via (A5), the label of the via diameter (drill), Lumped and Analytic overstating vias (A6), the 3D clip of a large via.
* block-and-fins and fin-channel: the 4 mm threshold of the fin warning (C3): replace it by a rule on the channel Rayleigh number and whether to add the correction (`fin-channel/INTEGRATION.md`).
* gerber-import: the reader accepting LM/LR/LS and aperture blocks (E10).
* the other folders: the items in each folder's `INTEGRATION.md` and in `docs/versions.md` ("Planned").
