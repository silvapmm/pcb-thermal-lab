# The part and its heatsinks: what is still open

What is already in the program (releases 2.3.0 and 2.4.0: the junction-to-pad resistance with its limit, the package families, the top path, the interface as one sheet, the heater types and typical heatsinks) is described in the program's `docs/versions.md`, `docs/models.md` and `docs/theory.md`; this file keeps only what is still open.

## Open (in `docs/roadmap.md`)

* **Junction node (JESD15-3 two-resistor)**: only worth it with a heatsink on top (this folder: without one the node is 1.3 to 3.4 K below the worst-case offset; with a 12 K/W heatsink the top takes 41 to 51 % of the heat and the rise of the junction roughly halves, README 4.10).
* **Heatsink scenarios**: θSA scaled with the temperature rise from a reference rise, an "other speed (estimated)" factor, the flow linked to the board air speed, heatsinks with a fan, a heatsink from its geometry with the channel effect, comparison with catalogue curves. `heatsink_convection_study.py` is the first look at the scaling and the forced factors.
* **Foster chain / heat capacity of the junction and the heatsink** for transient work with a part.
* **Top path in the time simulation** (steady state only today).
* **A heatsink larger than its contact** and a plate layer on top of a package (`NOTES.md` R3 and R8).

## A defect of the program found in the review: the top-path loop on small pads (corrected in the program)

**Status: corrected** on `fix/top-path-convergence` (`api._top_path_split` solves the root `g(P_b) = 0` of each part instead of iterating; see `docs/versions.md` and the Decisions Log of `CLAUDE.md`, "The top-path split is a root, not a loop"). The text below is the description of the defect and the design that was proposed, kept as the record; the program follows it (Illinois regula falsi for one part, Broyden for several, the power temperature coefficient as an outer fixed-point loop, the message "the top-path split did not converge"). `scripts/study_top_path_convergence.py` on the corrected program prints a program junction equal to the exact root on all eight rows (README 4.11).

**What happens.** `api._solve_with_tc` finds the split of the power of a part with a top path by plain fixed-point iteration, `P_b <- P − p_top(T_max(P_b))`, with `p_top` from `analysis.part_split`. Linearised, the map has the slope `−R_b/(R_top + θ)` (`R_b` the board's resistance under the part). Above 1 the iterates oscillate and grow; the loop stops after 80 iterations on the last iterate. On the four chips with an 8 mm pad (ratio 1.3 to 2.4) the reported junction is 17 to 58 K below the operating point (MOSFET 33.2 against 90.9 °C), on the unsafe side, and the warning says the board is "close to thermal runaway", which is not the cause (there is no power coefficient). Between 0.9 and 1 (the LDO on the 25 mm pad) the loop does not settle in 80 iterations either, but its last iterate is within 0.1 K. Evidence: `scripts/study_top_path_convergence.py`, README 4.11.

**Proposed correction** (a `fix/` branch off `develop`, then the reviewer):

* For the top path, solve the scalar equation of each part `g(P_b) = P_b − P + p_top(P_b) = 0`, which is monotone in `P_b` on `[0, P]`: with fixed face coefficients the board is affine in `P_b`, so a secant from two solves gives the root (the power calculator already uses this, `inverse.py`); with computed coefficients a safeguarded secant (or Brent on `[0, P]`) takes 3 to 6 solves. Several parts with top paths: a damped iteration with the relaxation `ω = 1/(1 + R_b,i/(R_top,i + θ_i))` per part, `R_b,i` measured from the first two solves, or Newton with the diagonal Jacobian `1 + R_b,i/(R_top,i + θ_i)` (coupling between parts is weak).
* Keep the plain loop for the power temperature coefficient alone, where its slope `α P₀ R` is the physical runaway condition; when both are present, wrap the power coefficient around the top-path solve.
* Change the message when the loop does not settle without a power coefficient: "the top-path split did not converge", not "thermal runaway".
* Regression test: the board of `component_study.part_board` with an 8 mm pad, MOSFET 2 W, θ 4.5, θJC(top) 30, 0.5 K cm²/W, θSA 12: `Tj` 90.9 °C (FVM 0.5 mm, computed h) within 0.1 K, and `P_top + P_board = P`, `Tj − T_amb = R_top P_top` as in the current test.

**What does not change**: the worst-case convention, `part_split` itself (its algebra is right) and every converged result (the 25 mm rows of `docs/validation.md` 9 are within 0.1 K of the exact root).

**Risk**: the time cost (2 to 6 solves instead of 20 to 36 on the 25 mm pads, so it is faster); a part whose top heat would be clipped at 0 or P (`part_split` limits it) makes `g` flat at one end, which Brent handles.
