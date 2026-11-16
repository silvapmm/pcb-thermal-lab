# Review of `fix/fem-interface-pad-film`

Reviewer's record of the correction of the blocking defect found by the final opinion of 2.8.0 (`releases/2.8.0/final-opinion/README.md` section 1): the FEM put the convection film of a metal block's walls also on the side walls of its interface pad, a fictitious layer whose height is the contact resistance times `femmesh.K_PAD` = 1 W/mK. Commits reviewed: 85886841 (code and two tests) and c62a456e (documents) on `development` b4ee3955. Every number below was printed on this machine by the scripts named, at a 2 mm cell unless said, on the branch tree with the correction of section 3.

**Verdict: GO** for the merge into `development`, with the correction of section 3 (committed with this file) and the decisions of section 6.

## 1. The diagnosis: which slab carries a film on its exposed sides

Read: `femmesh.build` (films, lines 'Films'), `solid3d.Solid3D` (edge and block films), `blocks.block_layers` (FVM and FDM), `blocks.exposed_h` and `wall_h`.

| Slab (FEM `kind`) | Exposed side faces | 3D solid | FVM / FDM | FEM before | FEM now |
| :-- | :-- | :-- | :-- | :-- | :-- |
| board copper `cu` and laminate `gap` | the outline walls | `h_side` on every board slab | `h_side` on the edge length of every node layer | `h_side` on every board slab | unchanged |
| open core of a hollow via | the hole wall | no hole (rod) | no hole | no element; the core quads stay in the set `all`, so no boundary edge and no film (adiabatic wall) | unchanged |
| via barrel and filled core | none (inside the board) | - | - | board quads, film only where they meet the outline | unchanged |
| block pad `pad` | the footprint perimeter | no film (`blk_ids` only) | no pad node (the contact is in `g_link`) | `wall_h` over the pad height (**defect**) | no film |
| block metal `blk` | the footprint perimeter | `h_face + h_extra` times slab height times edge length | `wall_h` times block thickness times side length | `wall_h` | unchanged |
| block exposed face | the outer plane | `h_face` x fin ratio + `h_extra`, through half the outer slab | `exposed_h` through half the block | `exposed_h` per quad | unchanged |
| board face under a block | covered | none | scaled by `1 - share` | none | unchanged |

Fins are not a slab of any model: a finned block is a fin ratio on the exposed face (`blocks.fin_ratio`) in all three, and the walls have no fin ratio in all three. So `kind == "blk"` is the right rule for the walls. The shift of the frozen board `finned_block` (+0.29 to +0.30 K on the block and the part, FEM records at 1 and 2 mm) is the pad wall film of its 5e-4 m2K/W pad (0.5 mm), not a fin effect.

## 2. A second defect of the same pad: it spread heat in its plane

The pad was isotropic, 1 W/mK, over a height of `rc` x 1 W/mK: 0.5 mm at 5e-4, 5 mm at 5e-3, 50 mm at 5e-2 m2K/W. Its lateral conductance per square (`k dz` = 0.05 W/K at 5e-2) is larger than that of the two copper layers of the board (2 x 35 um x 390 W/mK = 0.027 W/K). Over a part on the top face (part directly under the pad) the FEM spread the heat in the pad and read cold (board 40 x 30 mm, two layers, 3 W part 6 x 6 mm, 5 mm block 16 x 12 mm on the top face, h = 10 W/m2K):

| rc (m2K/W) | FEM before | FEM now | 3D solid | FVM | FEM/FVM before | now |
| --: | --: | --: | --: | --: | --: | --: |
| 5e-4 | 141.616 | 141.759 | 142.311 | 142.280 | -0.47 % | -0.37 % |
| 5e-3 | 150.800 | 153.485 | 154.138 | 154.636 | -2.48 % | -0.74 % |
| 5e-2 | 151.765 | 168.256 | 169.883 | 169.586 | -10.5 % | -0.78 % |

The same board without the block: FEM 169.776, 3D 171.595, FVM 171.082 (-0.76 % against the FVM). The test of the cause: making the pad thin in both the FEM and the 3D solid (`K_PAD` = 1e-2 and 1e-3 in a copy of the run, the resistance unchanged) brought the FEM to 168.29 at 5e-2 and the FEM/3D gap to -1.06 %, the plain-board gap; the bottom-face block (the board spreads the heat before the pad) moved by 0.3 K only. Correction (section 3): the pad conducts across only. The 3D solid has the same artefact in a milder form (its pad cell centre is at mid height, so it spreads at a lower temperature): with a thin pad it reads 155.063 instead of 154.138 at 5e-3 (+0.6 %), 170.083 instead of 169.883 at 5e-2. It is left as a question (section 6).

## 3. Correction made by the review

* `pcbthermal/femmesh.py`: new constant `K_PAD_INPLANE` = 1e-3 W/mK, the in-plane conductivity of the pad elements (`K_PAD` stays across, so the pad height and its resistance `rc` are unchanged). Not zero because `femcore.Model` requires a positive conductivity; the lateral conductance per square is then `rc` x 1e-3 W/K.
* `tests/test_fem_model.py`: third test `test_the_interface_pad_of_a_block_does_not_spread_heat_sideways` (the top-block board at 5e-3 and 5e-2 within 1.5 % of the FVM, balance 1e-9, the conductivities of the pad elements). It fails with an isotropic pad (`K_PAD_INPLANE` set back to 1 in a copy of the run: fails at 5e-3). The comment of the second test said the plain-board read-out bias was 1.5 %; it is 1.1 % on that board (section 4) and is corrected.
* Documents: `docs/theory.md` 4a (through the thickness; the film convention), `CHANGELOG.md`, `docs/decisions-log.md`, `docs/versions.md`.
* The conjugate-gradient path with pyamg and the anisotropic pad: 120 x 90 mm, four layers, top block at 5e-2, 1 mm cell, 308 600 unknowns: residual 1.7e-10, balance -1.5e-11, 13 s, 2.06 GB; FEM 61.694 against FVM 62.319 (-1.0 %).

## 4. Re-measurement on three boards with a block (contact 5e-4, 5e-3, 5e-2)

Rise of the hottest cell (column read-out), K, with the correction:

| Board | rc | FEM | 3D solid | FVM | FEM/3D | FVM/3D | FEM balance |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| A: 2 layers, 5 W, bottom block 3 mm, h_extra 20 | 5e-4 | 202.814 | 205.769 | 204.788 | -1.44 % | -0.48 % | 1.2e-11 |
| | 5e-3 | 214.446 | 217.404 | 216.508 | -1.36 % | -0.41 % | 1.2e-11 |
| | 5e-2 | 268.870 | 271.874 | 271.033 | -1.11 % | -0.31 % | 1.4e-11 |
| A without the block | - | 282.961 | 285.992 | 285.136 | -1.06 % | -0.30 % | -1.6e-11 |
| B: 4 layers, 2 W, edges 10, bottom block 1 mm | 5e-4 | 99.572 | 100.640 | 100.522 | -1.06 % | -0.12 % | -5.5e-12 |
| | 5e-3 | 100.240 | 101.309 | 101.191 | -1.06 % | -0.12 % | -4.9e-12 |
| | 5e-2 | 104.642 | 105.721 | 105.595 | -1.02 % | -0.12 % | -1.9e-11 |
| B without the block | - | 101.706 | 102.777 | 102.688 | -1.04 % | -0.09 % | -2.6e-11 |
| C: 2 layers, 3 W, top finned block 5 mm (fins 8 / 1 / 3 mm) | 5e-4 | 104.561 | 105.097 | 105.079 | -0.51 % | -0.02 % | 8.5e-12 |
| | 5e-3 | 123.845 | 124.541 | 124.989 | -0.56 % | +0.36 % | 1.2e-11 |
| | 5e-2 | 161.961 | 163.579 | 163.288 | -0.99 % | -0.18 % | 1.8e-11 |
| C without the block | - | 169.776 | 171.595 | 171.082 | -1.06 % | -0.30 % | - |

Before the review's correction board C read 121.448 at 5e-3 (-2.5 %) and 145.865 at 5e-2 (-10.8 %); boards A and B moved by less than 0.8 K. The residual gap of board A (1.4 % against 1.1 % without the block) is the column read-out of the cell: it falls with the cell together with the plain-board gap (1 mm: -0.63 % and -0.47 %; 0.5 mm: -0.14 % and -0.12 %). On board C at 1 mm the FEM is within 0.4 % of the 3D solid and 0.25 % of the FVM for every contact resistance.

**The one-dimensional column** (block over the whole 20 x 20 mm board, insulated edges, the closed form with the wall film of the metal only): rc 5e-4 / 5e-3 / 5e-2 and block 1 and 3 mm: FEM minus closed form between -0.0010 and +0.0031 K; 3D solid and FVM within 0.005 K. With the film on the pad walls (tree b4ee3955) the first case read 225.47 against 230.82 K.

**Energy balance**: every FEM solve above between 2e-13 and 5.6e-11 (the test bound is 1e-9).

## 5. Frozen numbers and the new tests on the tree before the fix

* `PCBT_FROZEN_CELLS=2,1,0.5 pytest -q tests/regression`: on the branch as delivered, 2 failed, 411 passed (181 s): only `finned_block|fem|1` and `|2`, block maximum 65.097 -> 65.398 K and part maximum 129.918 -> 130.208 K (+0.29 to +0.30 K). With the review's correction the same two records and nothing else: block maximum 65.400 and 65.393 K (+0.002 K more), 2 failed, 411 passed. No pending file is written by this branch (section 6).
* The two tests of 85886841, run on a scratch worktree of b4ee3955: both fail (column 225.47 against 230.82 +- 0.02 K; board A 199.29 against 205.77 K +- 2 %).
* `tests/test_fem_*.py`, `test_docs`, `test_license_header`, `test_version`, `test_model_lists`: 968 passed (42 s).

## 6. Open decisions for the maintainer

1. **The frozen records `finned_block|fem|1` and `|2`**: the frozen file `tests/regression/data/v2.8.0.json` belongs to the unreleased 2.8.0; either refreeze those two records in it (the release has not been tagged) or write a pending file `fem-interface-pad` with `make_pending.py`. Until then `tests/regression` is red on this branch by design.
2. **The pad of the 3D solid**: it also conducts in its plane at 1 W/mK over the height `rc` x 1 W/mK; on the top-block board it reads 0.6 % of the rise below a thin pad at 5e-3 and 0.1 % at 5e-2 (within the read-out spread of the comparison models). Giving it the same in-plane 1e-3 W/mK would move 3D frozen numbers of boards with a top block; recommendation: a `fix/` branch after 2.8.0, not now.

## 7. What was not verified

* Two blocks touching on the same face: each gets a wall film on the shared edge in the FEM and in the FVM (both count the edge of each block's own polygon); not measured.
* The FEM transient is not touched by this branch (the pad conductivities enter its stiffness the same way); not re-run.
* No whole battery (only the light tests and the frozen numbers listed).
