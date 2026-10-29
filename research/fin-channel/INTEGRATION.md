# Integration: the channel effect between close fins

What would enter the program, the measured impact of each proposal, what does not change and the risks. The program is not touched from this branch; every number below was measured on a copy in memory (`lib/program_patch.py`) and is in `README.md` (section numbers in brackets). Decisions are the maintainer's (section 6).

## 1. What the study found, for the decision

* The channel effect alone (the coefficient the program is given times the channel fraction `phi` of the composite) raises the rise of the hottest point of the example block (40 mm channels, 3 W) by +1.9 % at the 6.5 mm gap, +4.7 % at 5.5 mm, +11.8 % at 4.5 mm, +27 % at 3.5 mm, +55 % at 2.5 mm [5]; with 100 and 200 mm channels at 6.5 mm, +5.5 and +11.3 %; with the block 8.6 K above the air, +9.4 % [5].
* The full Bar-Cohen and Rohsenow coefficient against an isolated Churchill and Chu plate gives lower numbers (-0.1, +2.4, +8.8, +22.5, +48 % at the same gaps) because the composite's wide-gap limit is 7 % above that plate: at 6.5 mm the two cancel. **Correction of the review**: the first version of this file read that as "the program's model is right from 5.5 mm up"; it is right to within 2 % of the rise at 6.5 mm and 5 % at 5.5 mm for these 40 mm channels, and the absolute level of the plate coefficient is a separate question [5, "How to read"].
* The warning of today (still air, gap below 4 mm) misses 367 of the 667 cases (of a 1080-case grid) whose channel effect costs 10 % or more of the finned-face conductance (312 of 612 with the loss measured against the Churchill and Chu plate), because the gap at which the loss starts is 4.4 to 11.7 mm depending on the channel length and the temperature [6].
* The effect is known only for **vertical channels** (a vertical board, or fins horizontal on a vertical base). For a horizontal board, with the block over or under it, no source was read, and the program's examples are of that kind [7]. At gaps near 3 mm the closed channel model is itself far too pessimistic (the measured arrays are open in front) [7].

## 2. Proposal A: replace the 4 mm warning by a rule on the channel Rayleigh number (warning only)

**What.** A post-run check next to `checks.check_thick_plates` (it needs the temperature of the block): for every finned block,

* `theta` = mean excess of the block over the ambient air (from the result, `arrays["block_T"]` weighted by `block_cov`);
* `b` = `fin_pitch - fin_thickness`; `L` = the length of the channels: the longer side of the bounding box of the block (the program has no fin direction; the longer side is the conservative choice);
* `Ra_b = g beta theta b^4 Pr / (nu^2 L)` with the air properties at `ambient + theta/2` (`convection.air_properties`, `rayleigh`-like) and `beta = 1/T_film`;
* warn when `Ra_b < 90` (the channel keeps less than 90 % of the isolated-plate coefficient: `phi(90) = 0.90`), with the text of `docs/theory-text.md` below, including `phi`, the estimated loss of the finned face and the sentence that the block may be in another orientation;
* for the pre-run check (no temperature known) keep a gap threshold, but a larger one, as a hint only (for example 6 mm in still air), or drop it when the post-run check exists.

**Measured impact** [6]: on the 1080-case grid (gaps 1.5 to 20 mm, heights 5, 15, 30 mm, channels 20 to 200 mm, 10 to 80 K above the air), with the loss measured as the channel effect alone (against the composite's own plate limit), the rule `Ra_b < 90` misses 1 case and gives no extra warning, `Ra_b < 50` misses 79, the rule of today misses 367 (no extra warning). With the loss measured against the Churchill and Chu plate (the first version of the study), `Ra_b < 90` misses none with 54 extra warnings, `Ra_b < 50` misses 24 with none, the rule of today misses 312. The channel loss is `1 - phi(Ra_b)`, 10 / 25 / 50 % at `Ra_b` = 90 / 40.5 / 16.5. 90 is proposed (it is `phi = 0.9`); 50 only if the maintainer prefers a warning at about 18 % loss.

**What does not change**: no result. Boards without finned blocks: nothing. The input check `checks.py` list and the tests that count warnings: the 4 mm message changes text; `tests/test_checks.py` (if it checks the old text) and `docs/versions.md` are updated by the maintainer's branch.

**Test cases for the adoption** (from this study, FVM and 1 mm cells where a run is needed):

| case | expected |
| :-- | :-- |
| gap 5.5 mm, `L` 40 mm, 40 K (`Ra_b` about 62) | warns; `phi` 0.85 (rise +4.7 % with the `phi` form; the full coefficient against the Churchill and Chu plate: loss 8 %, rise +2.4 %) |
| gap 6.5 mm, `L` 40 mm, 40 K (`Ra_b` about 137) | no warning |
| gap 6.5 mm, `L` 100 mm, 20 K (`Ra_b` about 32) | warns; loss of the finned face 31 % (channel effect; 24 % against the Churchill and Chu plate) |
| gap 3.5 mm, `L` 40 mm, 3 W (`Ra_b` about 12) | warns; rise +27.1 % with the `phi` form (+22.5 % with the full coefficient) |
| gap 20 mm, any | no warning |
| `phi(54.38)` = 0.816, `phi(121.5)` = 0.933, `phi(90.07)` = 0.900 | the function |

## 3. Proposal B: the correction (a model change; optional)

**What.** `h_fin = phi(Ra_b) h_face` on the faces of the fins and on the free base between them, `phi = [1 + (14.16 / Ra_b^(3/4))^2]^(-1/2)`, then the program's own fin formula: `h_exp = h_fin fin_ratio(h_fin) + h_extra`. `phi` is the fraction of the isolated-plate limit that the Bar-Cohen and Rohsenow composite keeps (`channel.phi`), a function of `Ra_b` alone, so it keeps whatever the user typed or the program computed where the channel is open (`phi` tends to 1) and never gives more cooling than the program gives today. The prototype is `lib/program_patch.py: phi_effect`, `solve_phi`; the full channel coefficient (`exposed_h_channel`, Nu from equation 21 and the fin efficiency with it) is the reference it is measured against.

**Where it enters.** `blocks.exposed_h(s, h_face)` is the single function through which the FVM, FDM, Lumped and Analytic reach the coefficient (`blocks.extra_layers`); the 3D solid has its own copy of the fin ratio (`solid3d.py`, the lines that compute `ratio`/`h_tot`), which would have to call the same function so that the two stay equal. The coefficient depends on the temperature of the block, so the steady solve is repeated until the block temperature changes by less than 0.05 K (3 to 7 solves of the study; the same Picard structure as `api._solve_computed_h`, for which `h_mode` "computed" already repeats the solve). Time simulation: the coefficients are fixed at the steady state, as for the computed `h`. New inputs: the length of the channels (a fin direction on the block, or the longer side of the block as a default) and the condition that the board is vertical (`Board.orientation`); with a horizontal board no correction is applied and only the warning of Proposal A is given.

**Measured impact** [5, 6], rise of the hottest point against the program (60 x 40 mm board, 3 W, fins 15 x 1.5 mm, 40 mm channels, FVM 1 mm):

| gap (mm) | full channel coefficient | `phi` form |
| --: | --: | --: |
| 1.5 | +90.6 % | +96.9 % |
| 2.5 | +48.3 % | +55.2 % |
| 3.5 | +22.5 % (3D solid +22.7 %) | +27.1 % |
| 4.5 | +8.8 % | +11.8 % |
| 5.5 | +2.4 % | +4.7 % |
| 6.5 | -0.1 % | +1.9 % |
| 8.5 | -1.5 % | +0.4 % |
| 14.5 | -1.7 % | +0.0 % |

The `phi` form is 1.6 to 2.3 points hotter than the full channel from 5.5 mm up and 3 to 7 points hotter below. **Correction of the review**: this is not a safety margin; it is the 7 % by which the composite's plate limit exceeds the Churchill and Chu plate used as the program's coefficient. The `phi` column is the channel effect applied to the coefficient the program has; the full column also changes the plate level. Boards without a finned block, plain plates and gaps of 10 mm and more: unchanged to 0.1 point. With a typed coefficient of 6 to 12 W/m²K at a 6.5 mm gap the `phi` form gives +1.7 to +2.3 % [6].

**Risks and limits**

* **Narrow gaps.** Below `Ra_b` of about 14 (about 3 mm in the cases of the study) real arrays are open in front and carry 2 to 6 times more heat than the closed channel (README 7); the full channel model and the `phi` form are pessimistic there, the program's uniform coefficient is optimistic by a factor of 3 or more. A correction at those gaps should be given as a bound (hotter than the program, cooler than the closed channel) or not applied.
* **Orientation and the channel length** are inputs the program does not have; a wrong length changes `Ra_b` as `1/L`.
* **Radiation** between the fins (blocked by the facing fin) is not modelled: with the program's computed `h` (radiation included) the `phi` form scales the whole coefficient, which is a plausible but unvalidated treatment of the radiation share.
* **No measured block** like the program's (a block on a board) and no measured array whose absolute level agrees with the model were found (README 7): the correction is validated for shape and optimum spacing, not for absolute heat.
* The correlation is for the isothermal symmetric channel; fin walls have a temperature falling from the base (the mean wall excess `eta theta_b` is used).
* Cost: three to seven times the steady solve of a finned block; the 3D solid does it at its own cost.

## 4. Documents that would change on adoption

`docs/theory.md` section 7 (the fin model: the channel fraction and its limits), `docs/models.md` (the new warning and the option), `docs/validation.md` (the numbers of README 5 and 6), `docs/versions.md` (chapter "Planned": item for the post-run warning as a `fix/` item, the correction as a `feature/` item after this investigation), the user guide (`pcbthermal/help/index.html`, the fins and the warning), the tooltip of "fin pitch" in `pcbthermal/gui/tips.py` (it says "chokes ... under 4 to 6 mm"), `tests/test_help.py` and `tests/test_tooltips.py` for the new words, `CHANGELOG.md`. The texts are in `docs/`.

## 5. What is not proposed

No change to the 3D solid's other physics, to the plain plate or to the pin fins; no time-dependent channel effect; no correction for the horizontal-board orientations (no source read); no use of the absolute level of the plot data.

## 6. Decisions for the maintainer

1. Replace the 4 mm warning by the post-run rule on `Ra_b` (threshold 90 or 50)? A `fix/` branch; reversible; no result changes.
2. Add the correction as an option? If yes: as the `phi` form (keeps the user's coefficient and applies the channel loss to it) or the full channel coefficient (which also replaces the plate level by the composite's, 6 to 13 % higher than the Churchill and Chu laminar plate); vertical boards only or also as a bound for the horizontal ones; and the new input (a fin direction or channel length on the block).
3. Whether the study of the open-front arrays and the horizontal orientations (ROADMAP C3a) comes before the correction.
4. Whether radiation in the channel is to be treated (a view factor between the fins) before the correction.
5. (From the review) Which plate level the program's computed coefficient should have on a vertical face is a separate question that this study only touched: the composite's `0.59 Ra^(1/4)`, the Churchill and Chu laminar form and laminar boundary-layer theory (`0.515 Ra^(1/4)`) differ by up to 13 %, as much as the channel effect at a 6.5 mm gap; it is not proposed here.
