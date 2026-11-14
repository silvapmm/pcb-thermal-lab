# Metal block in the Lumped and Analytic models: re-measure of "within about 5 % of the FVM"

Status: plan, scripts and the cheap (1 mm cell) runs done; the 0.5 and 0.25 mm runs, the independent 3D reference and the review are NOT done.

## 1. Question

The warning of `pcbthermal/api.py` (line 1053), the hint of `gui/panels.py`, `docs/models.md` (section on blocks), `pcbthermal/help/index.html` and
`docs/validation.md` section 17 say that the Lumped and Analytic models represent a metal block "within about 5 % of the FVM in 74 test cases". Those 74 cases
(`research/block-and-fins/scripts/block_equivalent_study.py`) have ONE source on the top face over ONE pad. Does the claim hold when the block is joined to the board
through several pads, with parts of different power on them, and where does it stop holding?

![The block joined to the board through several pads, with the heat paths](figures/fig_01_block_several_pads.png)

*Figure 1 (`fig_01_block_several_pads.png`): schematic cross-section; heat enters the plate only through the bottom copper pads (and the interface sheet), is shared inside the plate and leaves by its free face.*

## 2. Design

`scripts/study_block_pads.py`: synthetic board of ours, 100 x 80 mm, two layers, full top copper, 1.5 mm aluminium plate (204 W/mK) on the bottom face, a bottom copper pad
and a 6 mm part on the top face for each pad, 5 W in total (3 : 1 : 1 : 1 when unequal, so that sharing between pads is tested), default convection. Reference: the FVM at the same cell.
Error = (model - FVM) / FVM rise, percent. Sweeps: pad count 1, 2, 4; pad side 8, 12, 25 mm; interface 0.1 to 20 K cm2/W; block 40x30 to 100x80 mm; h_extra 0 to 200 W/m2K.
CONTROL rows run the same board WITHOUT the block, so that an error of the models that is not about the block can be told apart.

## 3. Results at a 1 mm cell (`--set all`, 1 mm; numbers as printed)

Hottest point of the board (L = Lumped, A = Analytic), worst part, and the difference of the hottest-to-coolest part spread (sharing between pads):

| Case | FVM rise K | L hot | A hot | L worst part | A worst part | L spread | A spread |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| control, 1 pad, no block | 144.0 | -0.8 | -2.7 | -9.0 | -2.7 | 0 | 0 |
| control, 2 pads, no block | 113.7 | -2.5 | -2.8 | -10.0 | -2.8 | -10.6 | -2.1 |
| control, 4 pads, no block | 83.6 | -0.5 | -3.0 | -6.7 | -3.0 | -9.7 | -2.4 |
| 1 pad 12 mm, block | 115.2 | -0.7 | -0.9 | -10.5 | -0.9 | 0 | 0 |
| 2 pads 12 mm, block | 92.4 | -4.4 | -0.9 | -13.5 | -0.9 | -8.9 | -0.4 |
| 4 pads 12 mm, block | 69.4 | -2.2 | -0.9 | -10.1 | -0.9 | -7.1 | -0.4 |
| 2 pads 25 mm, block | 91.6 | -4.5 | -1.1 | -13.7 | -1.1 | -9.0 | -0.3 |
| 2 pads, block 40x30 | 101.7 | -6.8 | -0.4 | -14.9 | -1.4 | -8.8 | +1.1 |
| 2 pads, block 60x45 | 96.0 | -5.7 | -1.5 | -14.4 | -1.5 | -8.4 | -0.5 |
| 2 pads, block 100x80 | 90.3 | -3.1 | -0.6 | -12.5 | -0.6 | -9.2 | -0.4 |
| 2 pads, h_extra 200 | 72.4 | -4.0 | -0.8 | -15.6 | -0.8 | -11.5 | -0.5 |

The full table (interface sweep included) is printed by the script; the maximum absolute errors over all 28 cases are: Lumped hottest point 6.8 %, Analytic 3.0 %,
Lumped worst part 15.6 %, Analytic 3.0 %, Lumped spread 11.5 %, Analytic 2.4 %.

![Error of the Lumped and Analytic against the FVM, every case](figures/fig_02_block_errors.png)

*Figure 2 (`fig_02_block_errors.png`, from `out/cell1.csv`): the grey band is the claim to be tested.*

## 4. What the numbers say (1 mm cell, to be repeated at 0.5 mm)

1. **Analytic**: within 5 % on the hottest point and on every part in all 28 cases (0.4 to 3.0 %); the control without a block is already -2.7 to -3.0 %, so the block adds little.
2. **Lumped, hottest point of the board**: -0.4 to -6.8 %; it goes outside 5 % when the block is small against the board (40x30 and 60x45 mm: -6.8 and -5.7 %) and with two pads (-4.4 to -4.5 %, near the limit). With one or four pads it is -0.4 to -2.3 %.
3. **Lumped, the temperature of a part**: -6 to -16 %, NOT within 5 %. The control without a block is -6.7 to -10.0 %, so most of this is the known small-part limit of the Lumped (a 6 mm part at a 1 mm cell), but the block adds 1.5 to 5 points. The claim "within about 5 %" was about the hottest point; for a part the Lumped must not be called 5 %.
4. **Heat sharing between pads**: the Lumped spread between the hot and the cool part is 7 to 11.5 points of the rise too small (-10.6 and -9.7 also without the block): it spreads heat between the parts more than the FVM. The Analytic is within 2.4 points.
5. Pad area, interface resistance (0.1 to 20 K cm2/W) and the face h on the block move the errors by under 2 points; the dominant factors are the block size against the board and the pad count for the Lumped.

## 5. Not done, not verified

* 0.5 and 0.25 mm cells (the claim of 5 % is at a 1 mm cell in the old study, so the 1 mm table is the like-for-like one; the finer reference may change the sign and size).
* The independent 3D reference (`research/independent-fem-edge`) and the 3D solid: the FVM is the only reference here, so a common error of the layered models is invisible.
* The block temperature and the heat into the block per pad: the Lumped and Analytic results do not report them (the columns are nan), so the sharing is judged by the part temperatures.
* One metal and thickness (1.5 mm Al); vias; a block off the pads' axis; cases with fins. The earlier 74 cases are not re-run.
* Not reviewed by the reviewer agent.

## 6. What was read and what was not verified

No literature was needed (the question is about the program against itself). The old study README of `research/block-and-fins` and `docs/validation.md` 17 were read for the claim. Reproduced: the script reruns on the program as it is
(tree `development`), 1 mm cell only. Nothing from outside the repository.
