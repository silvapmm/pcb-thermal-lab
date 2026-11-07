# Integration: via contact geometry and barrel length

Status: **a proposal, reviewed** (README 7; the recommendations of section 3 are the reviewer's, after the independent checks). Nothing in `pcbthermal/`, `tests/`, `examples/` or `ico/` was changed; the variants are copies in memory (`lib/barrel.py`, `lib/contact.py`). The numbers are those of `README.md` (sections in brackets).

## 1. What would change (all in `pcbthermal/viawell.py`, FVM and FDM)

1. **Barrel length (A22).** In `build`, the barrel conductance of every gap becomes `k_cu A / (d_k + 0.5 t_bar,k)`, with `t_bar,k` the mean of the thicknesses of the two copper layers around the gap (`lib/barrel.py` does it by scaling `gv` before `kron_barrel`). One constant, `0.5`, measured (README 2.2).
2. **Weights by sheet conductance for a footprint that is not uniform (A20).** The per-layer weights `w^l_a` proportional to the geometric weight times the sheet conductance of the cell in that layer; the footprint enlarged until the weighted effective radius reaches `e^(-1/4) r_via`; a footprint with uniform sheet conductance and full copper rim is built by the program's own code (bit-identical). This is variant (a) of `via-partial-copper`.
3. **Contact (A20).** The share `f` of the rim of the drill (48 samples, the copper of a layer as the union of its zones) that touches copper multiplies the well; `f = 0` leaves the layer uncoupled. Needs the zones of the problem inside `build` (it already receives the problem); imported masks need a sample of the mask instead (not done).
4. Tests: a via outside a copper edge never heats the board and reads no cooler than the program's value (`research/via-contact-geometry/tests`), the cold-spot board of `tests/test_maximum_principle.py` keeps no cold spot, the unit-cell sweep as a test of the barrel rule on three stacks (a small version of `study_barrel_length.py`).
5. Documents (when adopted): `docs/theory.md` 2.6 (the barrel length, the weights, the contact; the text is in `docs/for-the-project-documents.md`), `docs/validation.md` (a section with the tables 2.2, 3.3 and 3.4), `docs/versions.md`.

## 2. Measured impact

| change | frozen records that move | size | other |
| :-- | --: | :-- | :-- |
| barrel rule `a` = 0.5 | 30 of 30 FVM/FDM and 30 of 30 Lumped/Analytic steady maxima of the five via boards (2, 1, 0.5 mm), 36 of 36 times to 63 % | FVM/FDM +0.028 to +0.149 K, Lumped +0.016 to +0.159 K, Analytic +0.037 to +0.158 K (at most 0.26 % of the rise), hotter; times to 63 % -1.0 to +0.002 % | the 3D solid is not touched; imported boards not measured; the refreeze folds a pending file (README 7.3) |
| contact + sheet weights | 0 of 30 | 0.0000 K | moves only vias whose footprint touches partial copper |
| unit cell (2.2) | | mean error 4 and 6 layers, 35 um and more: -9.1 % -> +0.8 % (range -32.8 .. -0.6 % -> -4.6 .. +11.8 %) | 18 um copper: +1.4 % -> +3.8 % mean, max +29 -> +35 % (the target radius, README 7.1 (4)) |
| independent 3D cell (README 7.1) | | 35 um and more: -14.2 % -> -1.8 % mean (planes whole), -15.5 % -> -3.4 % (inner planes drilled); worst -6.5 % | |
| partial copper, FVM at 1 mm, K (per cent of the rise) | | outside the edge +2.90 (+3.5) -> -1.05 (-1.3); track -8.55 (-9.4) -> -5.95 (-6.5); quarter -3.62 (-6.0) -> +2.32 (+3.8) | the cold spot is gone (3.4) |

## 3. Recommendation (reviewer)

* **Constant a: 0.5.** Against two independent references (the axisymmetric cell and the Cartesian 3D cell with the plating resolved, README 7.1) the a that zeroes the error is 0.44 to 0.48 and 0.50 to 0.82; 0.5 lies between the two (at the lower end of the 3D cell), removes 62 to 99 % of the deficit and leaves at most -3.9 % (planes whole) or -6.5 % (inner planes drilled) of the via resistance on the unsafe side. **The earlier text here called a = 0.25 'the safer choice, cannot overshoot': that was wrong**; overshooting is the safe side (the part reads hotter) and 0.25 leaves twice the unsafe error. Do not use a(t_cu) or tune a on the 18 um / solder cases: their positive error is the target radius (A14), not the barrel.
* **Adopt the barrel rule in 2.6.0: yes**, on a `fix/` branch, in every model that uses `k_cu A / d` (FVM and FDM through `viawell.build`, the Lumped through `viaconstriction`, the Analytic in `analytic.py`; one place: the barrel length of a gap), not in the 3D solid (its barrel crosses the copper slabs already). Frozen impact (README 4 and 7.3): 30 FVM/FDM and 30 Lumped/Analytic steady maxima of the five via boards up by +0.016 to +0.159 K (at most 0.26 % of the rise), all 36 times to 63 % of those boards by -1.0 to +0.002 %, a pending file and the refreeze at 2.6.0. Measure on the branch: the imported boards (hundreds of vias), and the Lumped/Analytic calibrations that were fitted against the FVM with the old barrel (`docs/theory.md` 5.1, 6.1).
* **Uncouple a layer whose rim touches no copper: yes**, with the program's own weights (variant `contact_geo`), on its own or with the barrel rule: it removes the worst unsafe error of the set (+2.90 K -> -1.05 K at 1 mm, via outside a copper edge), creates no unsafe case (quarter -3.62 -> -4.30 K, track -8.55 -> -10.29 K, both on the safe side), moves no frozen record; it needs the rim share of imported masks before it can reach a Gerber board.
* **Weights by sheet conductance: not as the default now.** They remove the cold spot (a safe-side defect) at the price of an unsafe error at a copper corner (+2.32 K at 1 mm, 3.8 % of the rise, a lower bound since the 3D reference is not converged) and of the 'bare' board of `via-star-coupling` 5.2 (via effect 84 to 93 % too weak), with positive matrix entries left (292 at 0.125 mm). Keep the cold spot as the documented limit (`docs/theory.md` 2.2) with the partial-copper warning, and take the weights up again with the local upscaling of section 4, which has to fix the corner first.
* **Corner case**: a limit, not an accepted default: with the program as it is (and with `contact_geo`) the corner is on the safe side; if the sheet weights are adopted later, the partial-copper warning must name the corner case and its sign.
* **Not recommended**: the star (no-go, `via-star-coupling`), a clip of the temperature, and scaling the well by `f` alone (vacuous at fine cells, README 3.1).

## 4. Next step (the sector well)

A local numerical upscaling: for every via and layer a fine raster of the zones around the barrel (cells of `h/4`), a solve with the barrel at one potential and the footprint cells as the coarse side, and the conductances from the Schur complement; checked on the fifteen boards and the cold-spot board, with the imported masks read at the same raster. Open until measured: whether it removes the quarter's unsafe error without the star's in-plane short; whether the maximum principle holds by construction (it would, the Schur complement of a resistor network is an M-matrix; the star failed for another reason, the weights).

## 5. Risks

* The constant `a` rests on two references that agree within 0.1 to 3.2 % (README 7.1), but on 15 + 5 cases of the second, not the 720; the thin-copper, thin-gap, large-via boards get worse with the rule (+29 -> +35 % of the via resistance at 18 um); an `a(t_cu)` would hide a different term (doubt 2).
* The fifteen boards are small and two-layer; the partial-copper behaviour on multilayer boards and on imported masks is unmeasured; the rim share ignores imported masks.
* Interaction with the edge image (`viawell.edge_term`, `well_conductance(..., c)`): the contact must multiply the well after the edge term; the footprint enlargement for the edge also changes the weights. Not tested together here (the cases of the set have no edge image within reach except the last two, which are unchanged).
* The branch `feature/via-star-coupling` edits the same function; the two cannot both be adopted.
* Moves numbers: the 2.6.0 refreeze with a pending file for the barrel rule; the contact change moves none of the 17 frozen boards.
