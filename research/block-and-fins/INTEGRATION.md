# Integration: where the metal block and its fins live, and a defect found in the review (corrected)

The work of this folder is in the program since 2.3.0 (the block in the FVM, FDM and 3D solid, the fins) and 2.4.0 (the block in the Lumped and Analytic steady states).

## Where it lives and how it is tested

| What | Code | Tests |
| :-- | :-- | :-- |
| Fin ratio (plate fins, efficiency `tanh(m Hc)/(m Hc)`) | `pcbthermal/blocks.py` (`fin_ratio`, `exposed_h`), repeated in `solid3d.py` | `tests/test_fin_model.py` (imports `scripts/fin_validation.py`), `tests/test_heatsink_part.py` |
| Block layer of the FVM and FDM | `blocks.extra_layers`, used by `fvm.py`, `fdm.py` | `tests/test_blocks.py`, `tests/test_heatsink_part.py` |
| Block in the Lumped (ring layer) and Analytic (Schur complement on the tile graph) | `lumped.py`, `analytic.py` (both call `blocks.extra_layers`) | `tests/test_block_models.py` |
| Fin air-gap warning (below 4 mm in still air) | `checks.py` | `tests/test_heatsink_part.py` |
| Side walls of a finned block without the fin ratio (`blocks.wall_h`, the correction below) | `blocks.wall_h`, `extra_layers` (`h_wall`), `solid3d.py` | `tests/test_block_side_loss.py` |
| Thick-plate warning with the flux into the block | `checks.check_thick_plates`, `checks._block_flux_under` | `tests/test_thick_plate.py` |

## A defect of the program found in the review: the fin ratio on the sides of the block (corrected in the program)

**Status: corrected** on `fix/finned-block-sides` (`blocks.wall_h` gives the side walls `h_face + h_extra`, `extra_layers` carries it as `h_wall`, `solid3d.py` does the same; `docs/versions.md`, `docs/validation.md` section 3 and the Decisions Log of `CLAUDE.md`, "Side walls of a finned block"). The finned blocks of the table below became 65.0 / 70.0 / 56.6 K in the FVM. The description and the option that follow are kept as the record.

**What.** `blocks.extra_layers` gives every block cell the conductance to the ambient `h_tot (A c + t L_edge)` with `h_tot = h_face × fin_ratio + h_extra`; `solid3d.py` does the same (`vk[s] += h_tot * dz * edge`). The first term is right: the fins stand on the exposed base face, and the ratio is per unit of base area. The second term gives the **sides** of the base plate the fin ratio too, though the sides carry no fins; they should see `h_face + h_extra`. `docs/theory.md` section 7 writes the exposed term as `(h_face + h_extra)(Δx Δy c + t L_edge)` (no fin ratio at all) and the Lumped bullet of the same section as `h_exp (A c + t L_edge)`: neither describes the code as a fin model should be.

**How much** (`scripts/study_finned_block_all_models.py`, FVM, the 60 × 40 mm board of `tests/test_heatsink_part.py`, 3 W, aluminium block 40 × 30 × 3 mm):

| Block | program (K) | sides at `h_face + h_extra` (K) | the program is low by |
| :-- | --: | --: | --: |
| plain plate | 88.3 | 88.3 | 0 |
| fins 15 × 1.5 mm, pitch 8 mm | 61.2 | 65.0 | 6.2 % |
| fins 15 × 1.5 mm, pitch 12 mm | 66.4 | 70.0 | 5.5 % |
| fins 30 × 1.5 mm, pitch 8 mm | 53.2 | 56.6 | 6.4 % |

The error grows with the ratio of the side area `t × perimeter` to the base area (thick plates, small blocks) and with the fin ratio. It is optimistic (too cool), in the same direction as the channel effect that the program also ignores.

**Correction (applied afterwards on `fix/finned-block-sides`, as written here).** In `blocks.extra_layers`, keep `h_tot` for the base and use `h_side = h_face + s.h_extra` for the sides: `g_amb = h_tot * area * c + (h_face + s.h_extra) * s.thickness * side`; the same in `solid3d.py` (`vk[s] += (h_face + f["he"]) * slabs[s]["dz"] * edge`). The Lumped and Analytic models take `g_amb` from `blocks.extra_layers` and follow. Whether `h_extra` (a typed extra coefficient of the exposed face) should apply to the sides is a choice: it does now, and the correction keeps that. A regression test: the finned block of `tests/test_heatsink_part.py` with the side area made large (a thick, small block) against a hand sum of the conductances of one cell, or the second table of the study (+5.5 to +6.4 % after the change). Numbers that move: `docs/validation.md` section 12 D and `docs/models.md` section 15 (finned rows), the finned cases of `block_equivalent_study.py`.

**Decision of the maintainer**: the correction was applied (a `fix/` branch with the reviewer).

## Open (limits of the model, in `docs/versions.md` "Planned")

* The channel effect between close fins (Elenbaas; Bar-Cohen and Rohsenow): the warning at 4 mm of air gap leaves a 6.5 mm gap, near the optimum spacing of a short array, with a channel coefficient that a remembered correlation puts 10 to 30 % below the typed one (`README.md` 4.1). A channel correlation for still air, or a lower warning threshold, is the maintainer's choice.
* A time simulation with a block in the Lumped and Analytic models.
