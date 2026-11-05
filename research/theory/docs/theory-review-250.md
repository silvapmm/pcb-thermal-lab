# Review of `docs/theory.md` for the 2.5.0 release gate (step 3)

Reviewed against the code of `develop` at `e97b62f`; corrections on the branch `docs/theory-review-250` (documents only, nothing in `pcbthermal/`).

## Verdict

**GO for the theory**, after the corrections below (all made on this branch). The equations, constants and limits of every model section were read against the code; the one statement that said the opposite of the code (the zone decision of the Lumped model) and the stale or historical passages were corrected. What is left are the open items at the end, none of which describes the program wrongly.

## How it was checked

* Every section read against its module: `geometry.py` (sampling counts), `laminate.py` (rule, margin, options, `uses_rule`), `viawell.py` (`TARGET_RATIO`, `KAPPA`, `POINT_SINK_RADIUS`, the walls of the edge image), `fvm.py` (`lu_factor` tolerances, CG and SOR tolerances, the omega cap, the step stages), `memory.py` (`CONTINUOUS`, `VIA_GAIN`, `VIA_CELLS_REF`, factors, ceiling, the imported-copper terms), `solid3d.py`, `lumped.py` and `viaconstriction.py` (ring edges, potential blocks, `CORE_R`, `MAX_CORE`, `FINE_MM`, `ZONE_CELL_MM`, groups, wells, tiles), `analytic.py` (`beta`, `h_eff`, `h_tot`, tiles, modes, warnings), `blocks.py`, `convection.py`, `api.py` (Picard loop, power loop, top-path split), `analysis.py` (ring), `profiles.py`, `gerber/raster.py`, `gerber/parser.py`, `copper.py`, `gerber/parts.py`, `checks.py`.
* Re-run (light, under 1 GB): `tests/test_maximum_principle.py` (example and dense 0.5 mm, and the copper-edge cold spot at 0.5 and 0.25 mm): 16 / 64 positive entries, 0.0183 of the diagonal, 832 / 864 with 0.74 / 1.31, cold spots −7.941 and −14.429 K, all as written in theory 2.2. `research/models-comparison/scripts/solver_equivalence.py`: the SOR agrees with the direct solver to 6.3e-9 K (676 sweeps on the example board), as in `validation.md` 5. `tests/test_docs.py` and `research/theory/tests`: 561 passed.
* Pictures: every image link of the theory resolves; the sections without a picture were found and given one (below).
* Sources: the statuses of the OCR reviewer's image pass were applied where the pages support them (section 12 of the theory and the new last section of `research/theory/BIBLIOGRAPHY.md`).

## Defects found and corrected

| # | Kind | Where | What was wrong | Correction |
| :-- | :-- | :-- | :-- | :-- |
| 1 | wrong statement | 5.2, the decision | "one node when the core covers more than 92 % on the Lumped grid **and** on the 0.1 mm grid"; the code (`lumped.py`, `n_core <= MAX_CORE * n_foot and (zone_ok or fine share <= MAX_CORE)`) keeps one node when **either** count passes 92 % | rewritten as the code does it |
| 2 | wrong statement | figure 21 caption | "the sum of the coverages equals the area of the triangle, so the power is exact": the sampled sum is the area only to the sampling error; the power is exact by the normalisation (1.5) | caption corrected |
| 3 | missing | 2.7 | the imported-copper terms of the guard (`copper_run_bytes`, `check_import`) were not described; `t_eff` is clipped at 1 in the code | paragraph added; (2.8) gives `max(1, ...)` |
| 4 | missing | 1.7 | the import pixel `min(m w_min / 4, cell / 10)` and the coarse-raster warning (8 pixels per cell) were not stated | added; the sources line no longer reads "[R] none read" for a source known from memory |
| 5 | wrong number | 11 | solvers "agree to 2·10⁻⁸ K" (validation 5 and the re-run: 7·10⁻⁹); the 3D row "±4 % on a heater-sized pad" is in no document (validation 3 and 3.1: +1.6 % on a 20 mm pad, +8 % on the heater-sized pad, bracketed; GCI 1.14 %); the FVM row omitted the 1.2 % of 3.1 | rows rewritten from validation 3, 3.1, 5, 16 |
| 6 | inconsistent | 8, sources line | air properties "k ±0.5 %, ν −0.4 to −0.9 %" against "at most 2.2 %, ν −0.2 to −0.9 %, k −1.4 to +0.5 %" in the same section | both ranges stated with their temperature range |
| 7 | history in the theory | 1.6, 1.8, 2.2, 2.3, 2.7, 4 | the 55 bytes per pixel of the research importer, the quadratic patterns of the prototype, the retired 'largest' shape and the first exposed-pad rule, the withdrawn 'exaggerates' statement and the unreproduced run, "not the 200 MB the old comment said", the history of the via gain, "the old fixed limit of 250 000 is gone" | removed, with a pointer where the record is (`versions.md`, `validation.md` 25, 29.3, 30.1); each was checked to be there first |
| 8 | symbol clash | 0, 1.4, 1.8, 4, 6 | section 0 claims one meaning per letter, but `S` was also the side of a part (1.4) and the frame score (1.8), `β` the 3D footprint share (4) and the modal coordinates (6) besides the edge parameter | renamed `w_p`, `M(d)`, `χ`, `ζ`; section 0 now says which standard letters are local (gravity, the expansion coefficient, Stefan-Boltzmann, the residual of 9.1, which figure 42 draws) |
| 9 | missing picture | 1.3.3, 7.4 | no picture | `images/outline_equivalent_rectangle.png` (research/outline fig. 4) and `images/fin_channel_boundary_layers.png` (research/fin-channel fig. 1) |
| 10 | incomplete | 1.3.1, 10 | sampling of a heatsink on the Analytic tiles (8) and of the Lumped footprint (4); the profile run's stopping options, step limit, default implicit Euler and the typed start | added |
| 11 | source status | 2.3, 2.7, 12 | [LiSuperLU2005] was "N, not cited" while its section 3.2.2 is the setting of `fvm.lu_factor` and was verified on the page image; [ShenWang2019Vias] "R pages 1 to 17" did not say that most of it rests on the text layer; [Muzychka2006EdgeCooling] S while equations 1 to 20 were read by image | cited in 2.3; statuses of eleven sources updated with the pages read |
| 12 | stale document | `validation.md` 27.5 | "the memory law of the FVM itself ignores the vias ... a separate fix" (the via term is in the code) | corrected |

## Open items (not changed; for the maintainer)

1. **Numbers of the theory that `validation.md` does not hold**, against the rule of the theory's first paragraph: the via term (0.82 to 1.09, 1.27, 4.75 times, the CO60 peaks; only in `research/memory-guard` README 14.12), the small-part table of 1.4 (`research/paper-case-studies` 16.3), the Analytic edge limit −8.6 to +5.8 % and the 57 % edge share (`research/analytic-edge-spatial` 8), the 0.0183 of 2.2 (printed by `tests/test_maximum_principle.py` only), Lienhard's examples 4.233 and 21.39 W/m²K and the TI barrel 261 °C/W (`research/theory-sources`). Folding them into `validation.md` (26 and new rows) is a documents task; not done here.
2. The equivalent-rectangle figure quotes the study's numbers at the time it was drawn (0.4 to 2.9 %, up to 18 %), which differ slightly from `validation.md` 13 (0.4 to 2.1 %, 6 to 11 % and 1.4 to 15 %); the caption says so. Regenerating the figure belongs to `research/outline`.
3. `validation.md` 5 says the SOR needs 676 sweeps on the example board at 1 mm, `validation.md` 25 (row "Relaxation factor") gives the 2244 of the old factor; the Decisions Log of `CLAUDE.md` quotes 810. Not re-run at 1 mm here; the 676 is that of `solver_equivalence.py`, whose cell may differ.

## What was not verified

Re-run only the two light checks above (the machine was running four reproduction testers). Not re-run: the memory measurements, the small-part laminate table, the Analytic edge numbers, the exposed-pad tables, the Gerber memory constants (measured on one machine and noted in the code), the CAD-profile counts, the convection comparisons. The source statuses were raised on the OCR reviewer's image record (`papers/notes/BIBLIOGRAPHY_PROPOSED.md`, local and untracked); section 3.2.2 of the SuperLU overview was read in its transcription here and agrees with the statement made in theory 2.3.
