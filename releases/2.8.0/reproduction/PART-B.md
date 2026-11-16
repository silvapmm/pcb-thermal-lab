# Reproduction pass 2.8.0, part B (in progress)

Tree: development 77ed4822, detached worktree. Machine at start: load 2.5, swap used 1.1 GB of 2 GB, free+inactive about 9 GB. One job at a time, nice 10.

## 1. Research tests (research/<folder>/tests)

| folder | result |
| :-- | :-- |
| analytic-edge-spatial | 19 passed in 3.67s (unchanged) |
| fin-channel | 18 passed in 6.61s (unchanged) |
| gerber-cad-profiles | 36 passed, 1 skipped in 0.37s (unchanged) |
| gerber-real-boards | 50 passed, 7 skipped in 7.27s (unchanged) |
| imported-via-rim | 2 passed in 0.43s (unchanged) |
| independent-fem-edge | 11 passed, 1 skipped in 3.50s (unchanged) |
| laminate-nodes | 20 passed in 3.65s (unchanged) |
| lumped-zone-placement | 4 passed in 0.73s (unchanged) |
| memory-guard | 59 passed in 2.24s (unchanged) |
| reduced-models-imported-passives | 9 passed in 2.32s (unchanged) |
| strong-edge-laminate | 6 passed in 1.63s (unchanged) |
| via-edge-image | 7 passed in 1.94s (unchanged) |
| via-well-sheet-order | 2 passed in 0.46s (unchanged) |
| young-omega-tiles | 23 passed, 3 skipped in 0.67s (unchanged) |
| zone-union | 9 passed in 1.26s (unchanged) |
ALLDONE
| power-calculator, solid3d-verification | no tests directory |

Studies (section 2) are running; the table is filled when they end.
