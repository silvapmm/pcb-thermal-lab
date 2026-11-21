# Interface pad of the 3D solid conducts across only (`fix/solid3d-pad-inplane`, item e16 of `releases/2.9.0/PLAN.md`)

**The defect.** The pad slab of a metal block in the 3D solid (`solid3d.py`, `block_slabs`) had `k` = `K_PAD` = 1 W/mK in every direction and a height of `R''` times 1 W/mK (0.5 mm at 5e-4, 5 mm at 5e-3, 50 mm at 5e-2 m2K/W). A contact resistance conducts across only, but this slab also spread heat sideways in its plane, in cells whose centre is at mid height. The FEM had the same artefact and got `K_PAD_INPLANE` = 1e-3 W/mK in `fix/fem-interface-pad-film` (`releases/2.8.0/fem-model/REVIEW_FEM_PAD_FILM.md` 2, 6.2), which measured 0.6 % in the 3D solid at 5e-3 on a copy and left the fix for after 2.8.0.

**The fix.** One constant, `solid3d.K_PAD_INPLANE` = 1e-3 W/mK (the FEM's value), used for the lateral conductivity of the pad slab (`np.maximum(cov, 0) * K_PAD_INPLANE`); the conductivity across (`K_PAD`) and the height (`R''` times `K_PAD`) are unchanged, so the resistance per area is still exactly `R''`. Not zero: the lateral links of a cell divide by the sum of the two conductivities. The slab already existed: the slab and unknown counts, and so the memory law, are unchanged (`tests/test_solid3d_pad_inplane.py::test_the_unknown_count_of_the_memory_law_is_unchanged`).

**Trees and references.** Before: `development` at `820ed1ef`. After: this branch (the commit that holds this file). Reference: `tests/helpers/stack3d.py`, an independent anisotropic 3D finite-volume solver written for this item (imports nothing from the program; the pad has `kx` = 0 exactly, `kz` = 1 W/mK, height `R''`; the metal in 4 times more slabs than the program; the board slabs, uniform on these boards, read once from the program's own slab list, so the comparison is about the solver and the pad, not about the laminate model). It is certified against `tests/helpers/layered3d.py` on the Cu / FR-4 / Cu coupon (0.01 %) and against the program on the bottom-block board, where the pad cannot spread (3D solid -0.003 to -0.013 % of the reference at 2 and 1 mm). The FVM (no pad slab: the contact is a link) and FEM columns are for context. Script: `scripts/study_pad_inplane.py` (`run --tree <checkout> --out <file>` on each tree, then `compare`). Cases: two-layer 40 x 30 mm board, full copper, 3 W on a 8 x 8 mm part at (16, 10, 24, 18) mm, h 10 W/m2K on both faces, insulated edges; a 5 mm aluminium block (204 W/mK) on the top face over the part (16 x 14 mm), the same block over the whole board, a 3 mm block on the bottom face; R'' = 5e-4, 5e-3, 5e-2. Rises over the ambient in K. Energy balance of every solve, both trees: residual under 6e-12, reference balance within 6e-11 W.

## 1. Before and after, 2 mm cell

Columns: reference (independent), 3D solid before and after, each against the reference, the shift, FVM and FEM (column maximum under the part, same cell).

| cell | case | rc | read-out | independent | solid before | solid after | before - ref (%) | after - ref (%) | after - before (K) | FVM | FEM |
| --: | :-- | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| 2 | top_block | 0.0005 | col_max | 135.1029 | 135.0340 | 135.0982 | -0.051 | -0.004 | +0.0642 | 135.029 | 134.296 |
| 2 | top_block | 0.0005 | layer_mean_top | 112.4899 | 112.4840 | 112.4822 | -0.005 | -0.007 | -0.0017 |  |  |
| 2 | top_block | 0.0005 | layer_mean_bottom | 107.0312 | 107.0256 | 107.0239 | -0.005 | -0.007 | -0.0017 |  |  |
| 2 | top_block | 0.0005 | block_max | 123.3929 | 123.3304 | 123.3481 | -0.051 | -0.036 | +0.0177 |  |  |
| 2 | top_block | 0.005 | col_max | 146.2354 | 145.4723 | 146.2264 | -0.522 | -0.006 | +0.7540 | 145.939 | 144.809 |
| 2 | top_block | 0.005 | layer_mean_top | 114.6253 | 114.6340 | 114.6177 | +0.008 | -0.007 | -0.0163 |  |  |
| 2 | top_block | 0.005 | layer_mean_bottom | 109.0630 | 109.0713 | 109.0557 | +0.008 | -0.007 | -0.0155 |  |  |
| 2 | top_block | 0.005 | block_max | 115.4571 | 115.2754 | 115.4388 | -0.157 | -0.016 | +0.1635 |  |  |
| 2 | top_block | 0.05 | col_max | 161.8829 | 161.6816 | 161.8576 | -0.124 | -0.016 | +0.1760 | 161.523 | 160.208 |
| 2 | top_block | 0.05 | layer_mean_top | 127.0425 | 127.0346 | 127.0344 | -0.006 | -0.006 | -0.0002 |  |  |
| 2 | top_block | 0.05 | layer_mean_bottom | 120.8776 | 120.8701 | 120.8699 | -0.006 | -0.006 | -0.0002 |  |  |
| 2 | top_block | 0.05 | block_max | 65.8574 | 65.8249 | 65.8458 | -0.049 | -0.018 | +0.0209 |  |  |
| 2 | top_whole | 0.0005 | col_max | 112.3675 | 112.3165 | 112.3647 | -0.045 | -0.003 | +0.0481 | 112.364 | 111.869 |
| 2 | top_whole | 0.0005 | layer_mean_top | 99.1555 | 99.1497 | 99.1497 | -0.006 | -0.006 | +0.0001 |  |  |
| 2 | top_whole | 0.0005 | layer_mean_bottom | 94.3439 | 94.3383 | 94.3384 | -0.006 | -0.006 | +0.0001 |  |  |
| 2 | top_whole | 0.0005 | block_max | 98.9458 | 98.8921 | 98.8960 | -0.054 | -0.050 | +0.0039 |  |  |
| 2 | top_whole | 0.005 | col_max | 132.5457 | 131.3848 | 132.5385 | -0.876 | -0.005 | +1.1537 | 132.275 | 131.175 |
| 2 | top_whole | 0.005 | layer_mean_top | 103.3909 | 103.3840 | 103.3853 | -0.007 | -0.005 | +0.0013 |  |  |
| 2 | top_whole | 0.005 | layer_mean_bottom | 98.3737 | 98.3672 | 98.3684 | -0.007 | -0.005 | +0.0013 |  |  |
| 2 | top_whole | 0.005 | block_max | 95.9846 | 95.9278 | 95.9665 | -0.059 | -0.019 | +0.0387 |  |  |
| 2 | top_whole | 0.05 | col_max | 170.9199 | 170.1856 | 170.8918 | -0.430 | -0.016 | +0.7062 | 170.562 | 169.244 |
| 2 | top_whole | 0.05 | layer_mean_top | 136.2389 | 136.2342 | 136.2349 | -0.003 | -0.003 | +0.0007 |  |  |
| 2 | top_whole | 0.05 | layer_mean_bottom | 129.6278 | 129.6233 | 129.6240 | -0.003 | -0.003 | +0.0007 |  |  |
| 2 | top_whole | 0.05 | block_max | 76.0920 | 76.0657 | 76.0828 | -0.035 | -0.012 | +0.0172 |  |  |
| 2 | bottom_block | 0.0005 | col_max | 154.3379 | 154.3318 | 154.3329 | -0.004 | -0.003 | +0.0011 | 153.934 | 152.702 |
| 2 | bottom_block | 0.0005 | layer_mean_top | 119.7860 | 119.7810 | 119.7809 | -0.004 | -0.004 | -0.0001 |  |  |
| 2 | bottom_block | 0.0005 | layer_mean_bottom | 113.1449 | 113.1397 | 113.1396 | -0.005 | -0.005 | -0.0002 |  |  |
| 2 | bottom_block | 0.0005 | block_max | 115.2039 | 115.1885 | 115.1912 | -0.013 | -0.011 | +0.0027 |  |  |
| 2 | bottom_block | 0.005 | col_max | 155.8713 | 155.8523 | 155.8662 | -0.012 | -0.003 | +0.0139 | 155.491 | 154.226 |
| 2 | bottom_block | 0.005 | layer_mean_top | 121.0868 | 121.0830 | 121.0817 | -0.003 | -0.004 | -0.0013 |  |  |
| 2 | bottom_block | 0.005 | layer_mean_bottom | 114.5121 | 114.5081 | 114.5067 | -0.003 | -0.005 | -0.0014 |  |  |
| 2 | bottom_block | 0.005 | block_max | 108.2162 | 108.1821 | 108.2066 | -0.032 | -0.009 | +0.0245 |  |  |
| 2 | bottom_block | 0.05 | col_max | 163.8036 | 163.7936 | 163.7980 | -0.006 | -0.003 | +0.0045 | 163.440 | 162.137 |
| 2 | bottom_block | 0.05 | layer_mean_top | 128.7053 | 128.7001 | 128.7001 | -0.004 | -0.004 | +0.0000 |  |  |
| 2 | bottom_block | 0.05 | layer_mean_bottom | 122.5192 | 122.5136 | 122.5137 | -0.005 | -0.004 | +0.0000 |  |  |
| 2 | bottom_block | 0.05 | block_max | 66.6713 | 66.6605 | 66.6642 | -0.016 | -0.011 | +0.0037 |  |  |

## 2. Before and after, 1 mm cell (column maximum and block maximum)

| cell | case | rc | read-out | independent | solid before | solid after | before - ref (%) | after - ref (%) | after - before (K) | FVM | FEM |
| --: | :-- | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| 1 | top_block | 0.0005 | col_max | 135.1842 | 135.0878 | 135.1571 | -0.071 | -0.020 | +0.0693 | 135.113 | 134.985 |
| 1 | top_block | 0.0005 | block_max | 123.1412 | 123.0514 | 123.0727 | -0.073 | -0.056 | +0.0213 |  |  |
| 1 | top_block | 0.005 | col_max | 146.4708 | 145.6620 | 146.4392 | -0.552 | -0.022 | +0.7772 | 146.169 | 146.110 |
| 1 | top_block | 0.005 | block_max | 115.2812 | 115.0695 | 115.2404 | -0.184 | -0.035 | +0.1709 |  |  |
| 1 | top_block | 0.05 | col_max | 162.0926 | 161.8705 | 162.0426 | -0.137 | -0.031 | +0.1722 | 161.727 | 161.648 |
| 1 | top_block | 0.05 | block_max | 65.7476 | 65.6970 | 65.7182 | -0.077 | -0.045 | +0.0212 |  |  |
| 1 | top_whole | 0.0005 | col_max | 112.6026 | 112.5328 | 112.5824 | -0.062 | -0.018 | +0.0496 | 112.598 | 112.485 |
| 1 | top_whole | 0.0005 | block_max | 98.9479 | 98.8759 | 98.8799 | -0.073 | -0.069 | +0.0040 |  |  |
| 1 | top_whole | 0.005 | col_max | 132.8077 | 131.6224 | 132.7837 | -0.893 | -0.018 | +1.1613 | 132.532 | 132.462 |
| 1 | top_whole | 0.005 | block_max | 95.9843 | 95.9099 | 95.9488 | -0.078 | -0.037 | +0.0389 |  |  |
| 1 | top_whole | 0.05 | col_max | 171.1330 | 170.3947 | 171.0927 | -0.431 | -0.024 | +0.6980 | 170.770 | 170.684 |
| 1 | top_whole | 0.05 | block_max | 76.0926 | 76.0504 | 76.0676 | -0.055 | -0.033 | +0.0172 |  |  |
| 1 | bottom_block | 0.0005 | col_max | 154.5614 | 154.5399 | 154.5412 | -0.014 | -0.013 | +0.0013 | 154.152 | 154.148 |
| 1 | bottom_block | 0.0005 | block_max | 115.1264 | 115.0944 | 115.0978 | -0.028 | -0.025 | +0.0034 |  |  |
| 1 | bottom_block | 0.005 | col_max | 156.0852 | 156.0513 | 156.0649 | -0.022 | -0.013 | +0.0136 | 155.699 | 155.669 |
| 1 | bottom_block | 0.005 | block_max | 108.1528 | 108.1014 | 108.1272 | -0.047 | -0.024 | +0.0258 |  |  |
| 1 | bottom_block | 0.05 | col_max | 164.0112 | 163.9859 | 163.9900 | -0.015 | -0.013 | +0.0041 | 163.642 | 163.589 |
| 1 | bottom_block | 0.05 | block_max | 66.6237 | 66.5992 | 66.6031 | -0.037 | -0.031 | +0.0038 |  |  |

## 3. What moved and why

* **Top block, part directly under the pad** (cases `top_block`, `top_whole`): the column under the part rises by 0.06 to 1.16 K. The bias before was -0.05 / -0.52 / -0.12 % (block over the part, 5e-4 / 5e-3 / 5e-2) and -0.05 / -0.88 / -0.43 % (whole board) at 2 mm (-0.07 / -0.55 / -0.14 and -0.06 / -0.89 / -0.43 % at 1 mm); after it is -0.003 to -0.031 % everywhere (1 and 2 mm). It is largest at 5e-3: the pad is 5 mm tall and spreads the heat sideways at a lateral conductance per square of `k dz` = 5e-3 W/K, a fifth of the two copper layers (0.027 W/K); at 5e-4 the pad is too short to spread, at 5e-2 it is so resistive that most heat leaves through the board and the bottom face, so the sideways path matters less. This is the 0.6 % that the FEM review quoted (it was 0.52 % here on the block over the part).
* **Bottom block** (`bottom_block`): the heat reaches the pad already spread by the board, so the shift is 0.001 to 0.014 K (the FEM review measured 0.3 K in the FEM for a bottom block of a different board).
* **Block maximum**: +0.004 to +0.17 K; the block is cooler than the part and its read-out follows the heat that crosses the pad. The remaining -0.02 to -0.05 % of the block maximum does not change with the fix (`top_whole` 5e-4: -0.054 % before, -0.050 % after): it is the through-thickness discretisation of the block (5 slabs against 20 in the reference) and the mean-over-slab read-out, not the pad.
* **The part column** keeps a residual of -0.003 to -0.03 % against the reference after the fix. At 5e-4 and 5e-3 it is the plain-board bias of the 3D solid at these cells (the bottom-block rows, where the pad plays no role, read -0.003 to -0.013 %). *Correction of the review*: at 5e-2 most of it is the 1e-3 W/mK floor itself, not the board: the same solve with 1e-9 W/mK in the plane reads 0.017 K (block over the part) and 0.024 K (whole board) higher, i.e. -0.002 to -0.005 % of the reference instead of -0.016 % (section 6).
* **Layer means** move by 0.02 K at most (they are dominated by the board's far field and the film, which the pad does not change).
* **The FVM and FEM columns** are context: the FVM has no pad slab, the FEM reads lower at 2 mm (-0.4 to -1.0 % of the reference, the plain-board column bias of the FEM at 2 mm of `REVIEW_FEM_PAD_FILM.md` 4) and agrees with the FVM at 1 mm; neither is the reference of this fix.

## 4. Frozen numbers

Of the 20 boards of the harness only `finned_block` (3 mm bottom block, 5e-4 m2K/W) has a block; its 3D-solid records move by 0.002 K at most (part maximum 130.5015 -> 130.5035 degC at 1 mm; layer means -0.0005 K): a bottom block with a short pad, as in section 1. The three records `finned_block|solid3d|{2, 1, 0.5}` are in the pending file `tests/regression/data/pending/solid3d-pad-inplane.json` (written by `make_pending.py solid3d-pad-inplane --board finned_block --model solid3d --no-times`; the 3D solid has no time record). `PCBT_FROZEN_CELLS=2,1,0.5 pytest -q tests/regression -k solid3d`: 54 passed with the pending file (it failed on the first record without it). **No frozen board has a block on the top face, where the defect is largest**: the shift of the frozen numbers is therefore two to three orders smaller than the shift of the model; a board with a top block would hold the fix in the frozen set. **Decision of the review**: a top-block board (`top_block_pad`, the `top_block` case of this study at 5e-3) is added to the harness at the 2.9.0 refreeze, in one addition with the thick-copper board of item e33 (two boards, not one: a block switches off the laminate rule and the face term of the whole board, `laminate.uses_rule`, which the thick-copper board must hold); until then the fix is held by the tests of section 5.

## 5. Tests (`tests/test_solid3d_pad_inplane.py`, 8)

Fail before the fix, pass after: a pad over a uniform plate against the independent solver within 0.1 % (block over the part and over the whole board, three resistances; before -0.12 to -0.88 %), the conductivities of the pad slab. Guards that pass on both trees: the independent solver against `layered3d.py`, the closed-form one-dimensional column with a block over the whole board (insulated edges, the wall film of the metal only) within 0.02 K and the energy balance to 1e-8, the unknown count of the memory law. Added in review: the pad constants (`K_PAD`, `K_PAD_INPLANE`) equal the FEM's, and the 1e-3 W/mK floor reads the part less than 0.05 K below a pad with no lateral conduction (worst case of the sweep, 0.024 K).

## 6. Review: independent checks

The reviewer re-ran the study on both trees (`development` 820ed1ef exported, and this branch): the 54 rows of sections 1 and 2 are reproduced to the last digit. Then three checks that do not share the reference's inputs:

* **A reference that does not read the program's slabs.** The same `stack3d.py` with the board built from the input data alone (35 um copper of 385 W/mK, a 1.53 mm gap of 0.9 W/mK in the plane and 0.3 across, cut into 16 slabs instead of the program's 8; the block in 30 slabs). Column under the part, before -> after, % of this reference: block over the part 5e-3: -0.520 -> -0.004 (2 mm), -0.550 -> -0.020 (1 mm); whole board 5e-3: -0.874 -> -0.004, -0.891 -> -0.016; block over the part 5e-2: -0.122 -> -0.014, -0.135 -> -0.029; bottom block 5e-3: -0.010 -> -0.001. The two references agree within 0.003 K, so the conclusion does not rest on the slab list shared with the program.
* **The FEM** (its own mesh, its own pad with 1e-3 W/mK in the plane), rise under the part at 5e-3, degC above the ambient. It reads 0.3 % low at 1 mm on every case (its plain-board bias), so the comparison is on the difference top block minus bottom block (the bottom block is where the pad cannot spread):

| cell | case | FEM | reference | 3D solid before | 3D solid after |
| --: | :-- | --: | --: | --: | --: |
| 1 | block over the part | 146.110 | 146.468 | 145.662 | 146.439 |
| 1 | whole board | 132.462 | 132.805 | 131.622 | 132.784 |
| 1 | bottom block | 155.669 | 156.082 | 156.051 | 156.065 |
| 1 | over the part minus bottom | -9.559 | -9.614 | -10.389 | -9.626 |
| 1 | whole board minus bottom | -23.207 | -23.277 | -24.429 | -23.281 |
| 0.5 | block over the part | 146.427 | 146.520 | 145.621 | 146.405 |
| 0.5 | whole board | 132.780 | 132.869 | 131.617 | 132.781 |
| 0.5 | bottom block | 156.020 | 156.125 | 156.035 | 156.049 |
| 0.5 | over the part minus bottom | -9.593 | -9.605 | -10.414 | -9.644 |
| 0.5 | whole board minus bottom | -23.240 | -23.256 | -24.418 | -23.268 |

  The FEM, which shares neither the solver nor the slabs, agrees with the reference and the corrected 3D solid within 0.06 K on the differences and is 0.8 to 1.2 K away from the 3D solid before the fix. At 0.5 mm the corrected 3D solid reads the part 0.08 % (block over the part) and 0.05 % (bottom block) below the 16-slab reference: the plain-board bias grows a little with plan refinement on the program's 8 gap slabs, the same on both faces, so it is not the pad.
* **The floor.** The pad with 1e-9 W/mK in its plane (`K_FLOOR`, no lateral conduction) instead of 1e-3: the part reads 0.0016 to 0.0019 K higher at 5e-3, 0.017 to 0.024 K higher at 5e-2, 0.0004 K or less with a bottom block. The value is the FEM's; the 3D solid itself would solve with 0 too (its `add` floors every conductivity and the pad cells keep their link across; the direct solve is the only path). Kept at 1e-3 so that the two models stay equal (a test holds them equal).
* **Frozen numbers**: `PCBT_FROZEN_CELLS=2 pytest tests/regression -k solid3d` gives 20 passed with the pending file; without it only `finned_block|solid3d|2` fails (part maximum 130.2493 -> 130.2513 degC). Of the 20 boards only `finned_block` has a metal block (checked on the built boards; the example boards have plain heatsinks only).

## 7. What was not verified

* The surface read-out of the 3D solid does not exist yet (item e22): only the column, the layer means and the block read-outs were compared.
* Blocks with fins and `h_extra` over the part, two touching blocks, blocks on boards with an outline or with imported copper: not measured (the pad physics is the same; the reference solver was built for uniform boards).
* Time: the 3D solid is steady only.
* `docs/validation.md` was not re-run; the whole battery was not run (light tests only, as asked).
