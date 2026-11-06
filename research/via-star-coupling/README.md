# via-star-coupling

Measurements of the star coupling of the via that `feature/via-star-coupling` put into `pcbthermal/viawell.py` (variant (c) of `research/via-partial-copper`, README 5 and 9.4). The program is the implementation; this folder holds the before-and-after studies, which run on any program tree (`--tree`), so the "before" is a checkout of the commit before the change. The numbers and their reading are in `docs/validation.md` 31 and `docs/theory.md` 2.2 and 2.6.

## 1. Question

Does a barrel node per layer reached from every footprint cell (an M-matrix by construction) remove the cold spot and the positive off-diagonal entries of K, keep what the mean-potential via got right (convergence with the cell, the copper-fill gain, the edge image, memory), and what does it do to the cases where the copper changes inside the footprint?

### 1.1 Picture

![The star coupling of a via](figures/fig_01_star_coupling.png)

*Figure 1 (`figures/fig_01_star_coupling.png`, `scripts/make_diagrams.py`): plan of the footprint at the end of a copper edge (weights illustrative) and the section with the barrel nodes and the star of conductances.*

## 2. Studies

| script | what it answers | needs |
| :-- | :-- | :-- |
| `scripts/study_star_before_after.py --tree <tree> --out out/<name>.json`, then `--compare` | the documented board, the 10 mm cases against the tabulated 3D values, the dense array, the 3 x 3 copper-fill gain, the example board, direct/CG/SOR, the cost | nothing |
| `scripts/study_array_reference.py --tree <tree>` | the dense 10 x 10 array on a 16 mm board against the 3D solid at 0.2 and 0.1 mm | 3D solid, about 1 GB |
| `scripts/study_real_windows.py --tree <tree>` | the CO60 windows with their plated holes | `PCBT_REAL_BOARDS` |
| `research/memory-guard/scripts/study_via_law.py` (run on both trees) | the peak memory of the direct solve | nothing, one child process per case |

## 3. Results (summary; the tables are in `docs/validation.md` 31)

* Positive off-diagonal entries of K: 0 everywhere (example board 16 / 64 at 1 mm and 144 / 432 at 0.5 mm before; 10 x 10 array 96 to 3104 before). The cold spot of the board of `docs/theory.md` 2.2 (-7.94 K at 0.5 mm, -14.43 K at 0.25 mm) is gone; its via effect is 13.68 / 13.06 / 12.63 / 12.54 K at 1 to 0.125 mm (6.41 to 8.28 K before).
* Against the 3D solid at 1/20 mm on 10 mm boards (FVM, 0.25 to 1 mm): copper edge through the via -31..-47 % to +6..+32 %; track -45..-68 % to -11..-34 %; island and edge past the via unchanged; **a via on bare laminate just outside a copper edge worse** (2 to 9 times high at 0.5 mm and coarser).
* The dense array of 100 vias is within 1 % of the 3D solid (50.31 / 50.39 K) before and after; the 3 x 3 copper-fill gain within 0.06 K of the resolved -4.51 K.
* Frozen records: 21 of 30 move, at most 0.73 K (`tests/regression/data/pending/via-star-coupling.json`); windows of the CO60 board -0.4 to -4.4 K.
* Cost: memory and non-zeros of K equal to the tree before; network build of 8500 vias 3.1 s against 2.8 s.

## 4. Defects found in the first version of the implementation (fixed, with tests)

* The root finder of the star conductance assumed a positive target and gave the cap for cells smaller than the target radius: +1.2 % and +5.2 % at the finest cells of the periodic unit cell (`test_a_lone_via_in_a_periodic_cell_converges_with_the_cell`, `test_the_calibration_keeps_the_resistance_of_a_lone_via`).
* The edge image as a number (`edge_term`) in the star's target gave +4.5 % at a corner and +1.8 % near an edge at fine cells; as a matrix over the footprint cells (`edge_kernel`) the sweep of `docs/validation.md` 28 keeps its errors.

## 5. What was read and what was not verified

Read and used: `research/via-partial-copper` (README, INTEGRATION.md, `lib/viavariants.py`, tests), `docs/theory.md` 2.2 and 2.6, `pcbthermal/viawell.py`, `fvm.py`, `fdm.py`, `checks.py`. Reproduced: the cold spot and the via effects of that README (the documented board, to the digit), the research star's numbers (the same to the printed digit before the edge image). Not re-run: the 3D references of the 10 mm boards (taken from `research/via-partial-copper` README 3 and 9.2). Not verified: a physical board; a resolved 3D reference of the 30 mm board; the imported windows beyond CO60; the FDM next to a board edge; the reflex-corner wobble at 0.5 mm (+4 to +5 %) is measured, not explained beyond the grid at the corner. The review and the registers (`research/REVIEW.md`, `research/README.md`) are the reviewer's.
