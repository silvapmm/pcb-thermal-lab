# Text for the project documents (review)

The review of `research/block-and-fins/` (README section 7) found numbers and statements in the project documents that the re-run does not support. `docs/` and `pcbthermal/` are not edited on a research branch; this is the replacement text, to be applied on `develop` by the maintainer. Numbers from `develop` `a9c1cd1`, and checked against the documents of that commit. If the fin-ratio-on-the-sides correction of `INTEGRATION.md` is adopted, the finned rows below move again (by +5.4 to +6.4 % in the FVM) and have to be re-run with `study_finned_block_all_models.py`.

## 1. `docs/validation.md`, section 12 D (finned metal block)

Replace the table and the paragraph under it with (`research/block-and-fins/scripts/study_finned_block_all_models.py`, 1 mm cells):

| Block | Fin ratio at 10 W/m²K | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| plain plate 3 mm | 1.0 | 88.3 | 88.2 | 88.9 | 89.8 | 91.5 |
| fins 15 × 1.5 mm, pitch 8 mm | 4.7 | 61.2 | 61.2 | 61.7 | 62.7 | 62.1 |
| fins 15 × 1.5 mm, pitch 12 mm | 3.5 | 66.4 | 66.3 | 66.8 | 67.8 | 67.5 |
| fins 30 × 1.5 mm, pitch 8 mm | 8.3 | 53.2 | 53.2 | 53.6 | 54.6 | 53.7 |

The FVM, the FDM and the 3D solid agree within 1 % on a finned block (the same fin ratio in all three, so this does not test the fins). The Lumped and Analytic models, which have had the block as a ring layer and as a tile graph since 2026-10-22, are +1.6 to +2.7 % and +1.0 to +3.6 % at 1 mm cells (Lumped within 0.1 % at 0.5 mm); the earlier columns of this table (Lumped 100.3 to 62.4, Analytic 99.8 to 59.3 K, 10 to 13 % high) were from the time they replaced the block by an equivalent coefficient. The sides of the base plate get the fin ratio as well (`research/block-and-fins/INTEGRATION.md`): with the sides at the face coefficient the finned rises are 5.4 to 6.4 % higher.

## 2. `docs/validation.md`, section 15 (fins against a 2D fin)

* Carbon-steel row (1 × 30 mm, 100 W/m²K): difference **+0.02 %** (was +0.01 %).
* After "are within 0.08 %" add: "on the 12 × 240 grid of the script; on 24 × 480 the largest is 0.09 % and the difference tends to about 0.1 % (stainless, 100 W/m²K, 1.5 × 15 mm)".
* In "What is not validated" (1), add: "A remembered form of the Bar-Cohen and Rohsenow correlation (Incropera and DeWitt, not re-opened) puts the channel coefficient of a 30 to 40 mm array at a 30 to 50 K rise at 7 to 9 W/m²K for a 6.5 mm gap, which does not warn, and 3.5 to 6 W/m²K at 4 mm (`research/block-and-fins/README.md` 4.1)."

## 3. `docs/validation.md`, section 17 (the block in the Lumped and Analytic models)

* Table: already the re-run values on `develop` (15.6 / 31.4, 8.8 / 18.8, 1.9 / 4.7). Add under it: "The earlier 15.5 / 31.3, 8.8 / 18.7 and 2.0 / 4.8 of the Lumped columns were moved by the merge of thin Lumped rings (`lumped.RING_MIN_WIDTH = 1`, 2026-10-24); with the constant at 0 the study reprints them exactly."
* Replace "(+13 % for 1 mm, +19 % for 6 mm of aluminium on the 30 × 30 pad)" with "(30 × 30 pad, 5 K·cm²/W, Lumped / Analytic with the earlier coefficient: +15.9 / +17.4 % for 1 mm of aluminium, +20.6 / +22.2 % for 6 mm)", and add: "The FVM itself with the block's lateral conduction removed is as hot as the equivalent (within 0.1 to 1.8 points, `research/block-and-fins/scripts/study_why_coefficients_fail.py`), so the error is the equivalent's, not the reduced models'."
* Replace "The finned blocks are at −1.5 % (Lumped) and −0.1 % (Analytic). Typical cases: ... Lumped −2.2 %, Analytic −1.1 %." with "The finned blocks are at −1.5 and −1.4 % (Lumped) and −0.2 and −0.0 % (Analytic). Typical case: 30 × 30 pad in a 60 × 60 block, 3 mm of aluminium, 5 K·cm²/W: FVM rise 90.0 K, Lumped −2.2 %, Analytic −1.1 %. The largest errors (−4.7 % and −4.3 %) are on the block equal to its 40 × 40 pad with 1 K·cm²/W; from 1 to 0.5 mm cells the errors move by at most 0.3 points."
* Sources: the Seri Lee (1998) entry is already right in this section; `research/block-and-fins/README.md` had called it "Lee, Song, Au and Moran (1995)" (corrected there).

## 4. `docs/models.md`, section 15 (the metal block as a computed heatsink)

* Fins: "30 mm tall fins: 8.4" → **8.3** (8.35).
* Last bullet: replace "the FVM, FDM and 3D solid agree within 1 %, lumped and analytic about 10 to 13 % high" with "the FVM, FDM and 3D solid agree within 1 %, the Lumped and Analytic +1 to +4 % at 1 mm cells (`validation.md` section 12 D)".
* Limits: add "The sides of the base plate get the fin ratio too, which makes a finned block 5 to 6 % too cool on a 40 × 30 × 3 mm plate (`research/block-and-fins/INTEGRATION.md`)", unless the correction is applied.

## 5. `docs/theory.md`, section 7 (metal blocks)

The equation block says `exposed surface and sides G = (h_face + h_extra)(Δx Δy c + t L_edge)`: the code (`blocks.extra_layers`, `solid3d.py`) uses `h_exp = h_face · fin_ratio + h_extra` on both terms, and the fin ratio is described nowhere in `theory.md`. Replace that line with

    exposed surface             G = h_exp Δx Δy c,        h_exp = h_face · R_fin + h_extra
    sides                       G = h_exp t L_edge        (the code; the correction of research/block-and-fins/INTEGRATION.md uses h_face + h_extra)

and add after the block:

**Fins** (plate fins perpendicular to the base, `blocks.fin_ratio`): per unit of base area `R_fin = (1 − t_f/p) + 2 H_c η/p`, `H_c = H + t_f/2` (convecting tip as an adiabatic tip at the corrected height), `η = tanh(m H_c)/(m H_c)`, `m = √(2 h_face/(k t_f))`; `R_fin = 1` without fins. It is evaluated at the face coefficient, so the channel effect between close fins (slower air, Elenbaas; Bar-Cohen and Rohsenow) is not in it; `checks.py` warns below a 4 mm air gap in still air. Checked against a 2D conduction solution of one fin within about 0.1 % (`validation.md` section 15).
