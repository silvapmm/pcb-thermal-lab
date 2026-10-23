# Log: metal block and fins

| Date | What |
| :-- | :-- |
| 2026-10-16 | Metal block added to FVM and FDM; the Lumped and Analytic models first used an equivalent coefficient and warned. |
| 2026-10-22 | The maintainer asked to reactivate the block in Lumped and Analytic and to validate the fins. `block_equivalent_study.py` compared three approaches; the coefficient approaches (9 to 31 % off) were dropped for the ring layer and the Schur tile graph. `fin_validation.py` compared the fin formula with a 2D fin. Literature on spreading resistance (Lee, Song, Au and Moran 1995) could not be read and was not used. |
| 2026-10-23 | Folder created: scripts moved from `examples/`; figures added. **Two corrections found while reproducing the study:** (1) the script still called `lumped.solve_steady(..., block_nodes=True)` and `analytic.solve_steady(..., block_tiles=True)`, flags that no longer exist because the block is handled by default; the script was fixed to call the plain functions, and it reproduces the documented means and maxima (15.5/31.3, 17.3/31.5, 8.8/18.7, 11.0/19.7, 2.0/4.8, 1.1/4.3). (2) The documents said 62 cases; the case list has 74 (4 geometries × 6 thickness/metal pairs × 3 interfaces + 2 finned), so the documents (and the program's tooltip and user guide) were corrected to 74. |

Not verified: no measured heatsink; the fin array channel effect; the Lee et al. formulas (not read).
