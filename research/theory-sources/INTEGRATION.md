# Integration: what enters the program and the documents from the theory sources

Nothing here changes the program. Every item is a proposal with its measured impact; the text for the documents is in `docs/for-the-project-documents.md`. The decisions are the maintainer's.

## 1. Documentation and citations only (no result changes)

| # | Proposal | Where | Evidence |
| :-- | :-- | :-- | :-- |
| 1 | Cite the printed source of the vertical-plate correlation: Lienhard (2024) equations 8.13a and 8.13b (pages 433 and 434) and Example 8.1; say that Churchill and Chu (1975) itself was not opened. | the docstring of `convection.h_natural_vertical`, `docs/theory.md` (heat transfer), `docs/validation.md` section 22 | README 3.1 |
| 2 | State the exponent of the Hollands (1984) equation as `Ra^(1/3)` inside the logarithm, and that the `ht` documentation's `Ra^(1/5)` is a misprint. | `docs/research.md` R3 and `docs/theory.md` if the equation is adopted | README 3.3 |
| 3 | Tie the effective-medium formulas to Milton (2002): equations 7.10 (Hashin-Shtrikman, d = 2 and 3, page 116), 3.9 to 3.11 (Keller and Dykhne, pages 48 to 50), 10.31 and 10.32 (Bruggeman, spheres, pages 195 and 196) and say that the 2D Bruggeman form is derived from 7.9 by the step of section 10.5. | `docs/theory.md` where `conduction.py` formulas are quoted (the Gerber folders' text) | README 3.5 |
| 4 | Add the validation rows: Muzychka and others case 1 (b) and case 2; Lemczyk Table 1 and Tables 2 and 3. | `docs/validation.md` | README 3.7 |
| 5 | Replace "from memory" by the page and equation for Lee (1998) equations 1 and 2 and for Yovanovich (2003) Table 3. | `docs/calculators.md`, `docs/validation.md` | README 3.11 |

## 2. Findings about the program, with measured impact (proposals; nothing was edited)

**2.1 Horizontal plates: the program's correlations against Raithby and Hollands.** The program's up-face coefficient (`0.54 Ra^(1/4)`, `0.15 Ra^(1/3)` above 1e7, `L = A/P`) is 7 to 26 % above Lienhard's 8.37a with 8.37b for boards of 100 mm and more (Ra 5e3 to 9e5); with radiation of emissivity 0.9 added the **total** coefficient is 3 to 11 % above the source's for 100 x 80 to 300 x 200 mm, so a board would be hotter by up to about that much in the h-limited part of its rise (for 40 x 30 mm the program is 7 % below at 5 K excess and 3.5 % above at 60 K). The down-face coefficient `0.27 Ra^(1/4)` is 30 to 40 % below Fujii and Imura's 8.38, outside its range (Ra below 1e6) and for a two-dimensional plate, so the program is the conservative one there. Proposal: either keep McAdams and state the spread against Raithby and Hollands as a documented limit, or adopt 8.37a/b for the up face (a small `fix/` change in `convection.h_natural_horizontal`, with the validation rows of `docs/validation.md` section 22 to be re-run). The effect on a result is the change of the convective share of `h_top`; on the example board it would need a run, which was not made here (the board is not a research input of this folder).

**2.2 Mixed convection: `p = 3` against `p = 2` for a horizontal board.** Jaffer and Jaffer (Table 4) find `p = 2` for a level flow over an upward-facing plate and `sqrt(3) to 3` for a vertical plate. For a hot 100 mm board (60 C in 20 C air) the program's convective coefficient is 7 to 11 % below the `p = 2` value at 0.2 to 2 m/s (README 3.4). The program is the more conservative. Proposal: record it; changing the exponent needs Churchill (1977) or a second source for the horizontal case, so it is a **research question**, not a change.

**2.3 The thick-plate effect on a heat-sink base (case 2 of Muzychka and others).** On a 10 mm plate of k 150 under 10 x 10 mm sources the one-layer models are 2.9 to 5.5 K low at the centroids (4 to 7 % of the rise), 67 to 89 % of the bound `q'' t / (2 k)` (3.3 to 8.3 K); the 3D solid is 2.0 to 4.6 K low. The thick-plate warning of the program (`checks.check_thick_plates`, bound above 5 % of the heater rise) would apply: the bound is 4 to 10 % of the 72 to 79 K rise. This confirms the earlier finding (`research/effective-conductivity` 4.6) on a case that was not run there; no change.

**2.4 The grid convergence of the references.** The independent 3D solver is converged in the plane to a thousandth of a kelvin on cell edges and to 0.06 % in the through-thickness sub-slab count at 16 slabs (case 2: 102.419, 102.525, 102.875 K for 16, 8 and 4 slabs, extrapolated 102.373 K against the paper's 102.33 K). The statement of `research/models-comparison` and `research/effective-conductivity` that 2.5 mm cells overstate a 25 mm source by 0.3 to 0.4 K should be re-read with the sub-slab count in mind (a reference with 6 sub-slabs reads 0.1 to 0.4 K high on a 10 mm plate); the program's models are not affected.

## 3. What does not change and why

* `docs/theory.md` equations are not edited: every equation of the program that was checked is the printed one (vertical plate, Hollands exponent, Hashin-Shtrikman, Bruggeman).
* The Culham and Yovanovich plateau (Biot above 60) is **not** a program issue: the program does not homogenise a stack, and the plateau remains unexplained (README 3.6).
* The planned topics 12 (Foster), 15 (Gerber import) and 16 (multigrid) keep their plans; 3.8 and 3.9 give the acceptance checks a future implementation must pass (AN11261 Cauer ladder: sum 0.4000 K/W, Zth(4 ms) 0.26 K/W, Foster equivalence to 1e-12; the three Gerber examples; an h-independent V-cycle factor below 0.15).

## 4. Risks

The percentages of 2.1 and 2.2 compare the program with correlations of the open literature that this folder read in a textbook and a preprint, not with a measured board; neither the program nor the references are compared with a physical board anywhere in the project. A change of the horizontal-plate correlation would move every result of boards in still air by up to the amounts above and needs the whole validation battery.
