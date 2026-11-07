# Integration: what the thesis changes in the cut-cell film of the program

Status: a proposal; nothing of the program is changed (see `README.md` for the numbers).

## 1. Verdict

The thesis (Bochkov and Gibou 2019, section 1.4.2, eqs. 1.10 to 1.14) **confirms** the adopted scheme: the film of `aperture+film` is the thesis' symmetric Robin term, term for term (`mu alpha L/(mu - alpha d)`), with the aperture link of eq. 1.7. Nothing in the symmetric scheme is more accurate than the proposal for sliver cells or corners (measured: README 2.1), so **no change of method is recommended**. The thesis adds three things that the implementation should respect.

## 2. Message for the executor of `fix/cut-cell-aperture-film`

1. **Keep the two-point aperture links and the closest-point film as they are**; do not add the thesis' kink treatment (1.15 to 1.19) or the non-symmetric scheme (1.8, 1.20): on the triangle with three kinks the solution error is the same within the scatter over the grid placements (1.2e-4 against 1.2e-4 at 257 points) and the non-symmetric forms break the symmetric LU.
2. **The data side must carry the same factor as the conductance.** In the program the ambient term is `g_amb T_amb`; changing `g_amb` by `g_new - g0` does that. Do NOT use the thesis' right-hand side `int g + g d alpha L/(mu - alpha d)` with a floored denominator: with the floor the pair is inconsistent (stiff errors 4 to 450 against 1e-2). A test: a constant temperature field with every face film active must be reproduced to round-off at `h_side` from 10 to 1e5 (`tests/test_robin2d.py::test_constant_solution_is_exact_every_scheme` is the model).
3. **Keep the floor 0.25.** The thesis has none and says only that the condition `mu - alpha d > 0` holds for fine grids; for a centre outside the board with a stiff edge the unfloored formula gives a negative diagonal (errors up to 12 on the test, 12 to 101 cells with a negative denominator) and the floored one stays at 1e-2; the value of the floor is not critical (0.25, 0.5 and a smooth `1/(1 + alpha d)` replacement agree within 0 to 60 %), so keep 0.25 and the test that no film factor goes below it. The thesis does not give a better small-cell recipe.
4. **A sliver that carries a cut face must stay a node.** A cell whose cover rounds to zero but whose face aperture is positive must not be treated as "off the board" (pinned to ambient): in the independent solver this single rule produced an O(1) error spike (3.5e-3 against 1e-4) on a disc placement. Check in the vectorised aperture that `a > 0` implies positive cover on both sides, or keep the cell as a node (its volume may be zero).
5. **Cite** Papac, Gibou and Ratsch (2010) and Bochkov and Gibou (2019, eqs. 1.7, 1.13 and 1.14, condition 1.21) with Barrett and others in the docstring and in `docs/theory.md`; correct the entry `[BochkovGibou2019]` of the bibliography (status R for the pages listed in the README; the sign of the printed 1.14 is a misprint, the 1.13 form is the one that is correct).

## 3. Not done and not claimed

* Re-entrant corners (the small T) with the thesis' kink treatment; the 3D solid and the FDM (the same film applies in the 3D solid on the side faces); imported copper.
* Papac et al. (2010) and Arias et al. (2018): the first is the origin of the symmetric scheme and worth obtaining (it may state the stability of the symmetric scheme for `alpha < 0`); the second is a six-page note on the second-order-gradient variant and is not needed.
