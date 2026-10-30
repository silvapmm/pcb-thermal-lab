# Integration: a spot without copper under a source (A12)

How to bring the results of this folder into the program, what each change costs and what it does to the numbers. Nothing here is implemented: every number was measured on copies in memory (`lib/layered.py`, `lib/treatments.py`) and `pcbthermal/` is untouched. The evidence is in `README.md` (section numbers in brackets); the text for the project documents is in `docs/`.

## 1. What the study found, in four lines

* Where the hottest cell under a part has no copper, the layered models read **cool**: FVM -18.4 % of the peak (cell 0.5 mm, two layers 1.6 mm, 6 mm window under a 6 mm part), -3.8 % for the 4-layer typical stack-up, -3.7 % for the 6-layer one; the FDM is 3 to 9 points worse; the 3D solid is within 0.2 to 2 %, and within 0.4 % once its reported value is moved from the centre of the top copper slab to the face [README 3, 9]. The reference used by the sweeps is 0.3 to 2.2 % above the converged value (review, README 9): every error here is that much too negative.
* Two causes, separable by experiment [README 4, 5]: (a) the vertical path of a bare cell lacks the laminate that replaces the copper (half the thickness of each adjacent layer, `d + t_a/2 + t_b/2` instead of `d`), and the part sits on the face, `t/2` above the node: 3 to 4 points on every stack-up with a thin gap, **all** of the error of a 4- or 6-layer board; (b) on a board with a thick gap the node of the top layer has the temperature of the hot surface but the lateral conductance of half the gap, and the heat leaves sideways through a path that does not exist in the laminate: 8 to 18 points more, only for gaps above about 0.7 mm (two-layer boards), growing with the gap over the window size.
* Treatment [README 6]: **(1) a vertical correction without a new unknown** (a) and **(2) laminate nodes only in the gaps next to bare cells, with a margin of about a gap thickness** (b): the FVM error of the two-layer 1.6 mm board goes from -18.4 % to -3.1 % (n = 4) and the 4- and 6-layer boards from -3.8 / -3.7 % to -0.3 / +0.1 %; the real-board windows of the zone-union study from -12.8 / -15.3 % to -7.3 / -4.1 % (n = 4) and -5.7 / -2.7 % (n = 6) of the solver on the same cell fill (re-run by the review; the first version of this line was printed before the face term was in the code).
* Boards with no cell below fill 1 are the program's own to the last bit by construction (the refined set is empty), and the examples and the 19 validation scenarios move by 0.00 to 0.08 K, except the three rows that have bare cells under the part (heater straddling the copper edge +4.2 to +5.4 K, no copper on the heater layer +4.4 to +4.6 K, hatched copper +1.5 to +1.6 K; towards the face value of the 3D solid on the first two, which they still do not reach (-1.8 and -0.6 % of its rise), past the 3D solid by 1 K on the third because of the face term on a partly covered cell) [README 7, 9].

## 2. Proposals

### P1. Vertical correction (no new unknown, local, recommended)

**What.** In `fvm.Network` and `fdm.Network`, for a gap between layers `a` and `b` with copper fills `f_a`, `f_b` in a cell:

* the vertical conductance of the cell becomes `k_z A / (d + (1 - f_a) t_a / 2 + (1 - f_b) t_b / 2)` (a cell with fill 1 in both layers keeps `k_z A / d`: the board without bare cells is bit-identical); the via barrels stay in parallel as now;
* the reported temperature of a heated cell of the top layer adds `Q (1 - f) t / (2 k_z A)` (half the thickness of the top layer, where the part sits on the face), only for the maximum and the footprint results, not for the field.

**Impact (measured, `README` 6.1).** FVM peak error, cell 0.5 mm: 4-layer typical -3.8 % -> -0.6 %, 6-layer -3.7 % -> -0.1 %, two layers 0.8 mm -6.6 % -> -4.6 % (6 mm window), two layers 1.6 mm -18.4 % -> -17.2 % (against the converged reference of README 9: -3.4 -> -0.3 %, -3.4 -> +0.2 %, -6.3 -> -4.2 %, -17.6 -> -16.4 %). About half of the gain is the link, half the face term. Exact in 1D (a bare top layer under a uniform flux: +0.09 %, the share of the heat that the top film takes before the half layer). Cost: none (no unknown, no time).

**Points to settle before the fix (review, README 9).**

* **The face term on a partly covered cell.** The hatched scenario overshoots the 3D solid by 1 K (+1.2 % of the rise). The cause is the face term `Q (1 - f) t / (2 k_z A)` (1.17 K), not the mean thickness of the link (the parallel of the two paths differs from it by `f (1 - f) (t/2)^2 / d`, nothing). For a part on a fine hatch or on a partly covered cell the heat enters the copper directly; the 3D solid and the resolved reference (conductivities mixed arithmetically) have no face drop there. A choice for the maintainer: apply the face term only where `f` is 0 (or below a threshold), or as `(1 - f)`; the measured difference is 1.2 K on the hatched row and 1 % on a real window with fill 0.31.
* **The 3D solid must report the same face.** `solid3d.solve_steady` gives `t_max` at the centre of the top copper slab; over a bare cell the face is `q t / (2 k_z)` higher (1.6 K for 1 W over 36 mm2, 2.3 K for 4 W over 100 mm2). With P1 alone the FVM of the validation rows would read above the 3D solid that is the program's own check (the row with no copper: 154.6 against 153.2 °C, while the 3D face is 155.5 °C). The fix should add the same face term to the 3D solid's maximum (or its top-face temperature), so that the comparison model and the layered models report the same quantity.
* **Which rows of `docs/validation.md` move** (section 2, FVM at 1 mm): heater straddling the top-copper edge 143.89 -> 148.05 °C, no copper on the heater layer 150.16 -> 154.58 °C, hatched 105.78 -> 107.25 °C (106.08 without the face term on the partial cell); the FDM moves by a similar amount (not measured); the 3D solid column moves by +2.33 K on the first two rows if it gets the face term; every other row of section 2 and the example projects move by at most 0.01 K. No test of `tests/` pins these values (checked by name); `tests/test_layered_vs_3d.py` and the stack-up tests use full copper.

**Does not change.** Boards with copper in every cell, the example boards (0.00 to 0.02 K), anything with fill 1 under the part.

### P2. Laminate nodes next to bare cells (local, for gaps above about 0.5 mm)

**What.** For every gap, the cells in which either adjacent layer has a fill below 1, plus a margin of `ceil(d / dx) + 1` cells, get `n` nodes in the gap (`n` equal sub-gaps) with the construction of `laminate.py` applied to a gap: the copper node keeps the copper and half the first sub-gap, each new node holds one sub-gap (half a sub-gap on either side) with the lateral conductance `k_xy` times that thickness, consecutive nodes are joined by `k_z A / s`, the barrels of vias join the two copper nodes. In the other cells the single link stays. Suggested rule for `n`: 1 for `d` up to 0.3 mm, 2 up to 0.8 mm, 4 above (the typical 4- and 6-layer stack-ups never refine; the two-layer boards of 0.8 and 1.6 mm get 2 and 4).

**Impact (measured, `README` 6.2, 7).** With P1 included, cell 0.5 mm, windows of 6 and 12 mm: two layers 1.6 mm -18.4 / -10.4 % -> -3.1 / -0.8 % (n = 4); two layers 0.8 mm -6.6 / -3.9 % -> -1.6 / -0.5 % (n = 2); unknowns of n = 4 are 1.18 and 1.46 times the program's for the 1.6 mm board and 1.12 and 1.36 for the 0.8 mm board (n = 2 costs less; the cost grows with the bare area; a fully bare 20 mm window costs 2.0 times). Real board (Stormduino windows, FVM against the solver on the same cell fill): -12.8 -> -7.3 % (n = 4) and -15.3 -> -4.1 % (n = 4, -2.7 % with n = 6) on the two windows whose hottest cell is bare (re-run by the review); nothing changes where the hottest cell is copper (-0.3 -> -0.1 %).

**Risks and open points.**

* The transient models need the heat capacity of the new nodes (the slab each one holds is known: `rho_cp s`); not built in the copy, which is steady state only.
* The error does not converge fast with `n` (about 1 / n: the singular edge of the window): `n = 4` leaves 2 to 5 points on a thick-gap board and 9 points when the window is narrower than the gap (2 mm under a 6 mm part on 1.6 mm). More nodes there cost more than the cell would; the honest statement is a limit, not a cure.
* The FDM was not measured with the construction (its error over a bare window is larger than the FVM's: 3 to 9 points); the node-centred FDM has half cells at the boundary of the refined zone to be thought through.
* The metal-block layers (`blocks.py`) and the one-layer laminate nodes (`laminate.py`) are not part of the copy; the construction should reuse `laminate.extra_layers` generalised to a gap and a cell mask, which is also the way to treat A11 (patterned copper on a one-layer board: the same mask, the two nodes everywhere replaced by n nodes where the copper is partly absent; **not measured here**).
* An empirical cut of the lateral conductance (a thinner path without new nodes) was tried and **rejected**: the thickness that gives zero error is 0.10 to 0.30 of the gap depending on the window and the board [README 5.2].

### P3. A warning in the input checks (small, independent)

Where the hottest cell under a part has a copper fill below 0.5 in the top layer, `checks.py` can say "the part sits on bare laminate: the layered models (FVM, FDM, Lumped, Analytic) read lower than the 3D solid; use the 3D solid for the final value". Measured sizes for the text: 0 to 4 % for the typical 4- and 6-layer stack-ups, 4 to 18 % on 0.8 and 1.6 mm two-layer boards, up to 30 % for the FDM and narrow windows; the Lumped and Analytic are worse and not systematic (below). The text for the check and for `docs/models.md` is in `docs/for-the-project-documents.md`.

## 3. What remains for Lumped and Analytic (A2, A6)

Not treated here, measured only [README 3.2, 3.3]. The **Analytic** averages the copper fill of each layer with the influence of the heaters over the whole board, so a window of 2 to 20 mm in a 30 mm board is averaged away: -11 to -63 % on every stack-up for windows up to 12 mm (-31 to -54 % for two layers 1.6 mm), -4 to -6 % on the 4- and 6-layer boards with a 20 mm window; it needs a stated limit or a local fill under the part (A2). The **Lumped** builds its rings from the footprint and its error changes sign with the window (-43 % to +7 %); its cause was not separated. Neither is fixed by the nodes of P2, and P3 should name both.

## 4. Order of work if the maintainer adopts it

1. `fix/bare-spot-vertical` : P1 in `fvm.py` and `fdm.py` (a few lines each), the reported peak, tests: the copy's regression (`tests/test_layered.py` of this folder: copper everywhere bit-identical, series circuit, via barrels), the 6-layer window against the resolved reference within 1 %; documents `docs/models.md`, `docs/theory.md` (the vertical path of a bare cell), `docs/validation.md`.
2. `feature/gap-nodes-under-bare-cells` (or inside A11): P2 for FVM and FDM, steady state first, then the transient capacity; stress scenarios of `tests/test_gui_stress.py` for a board with a window.
3. P3 whenever; independent of both.

The reviewer is called before every merge, with the numbers of `README.md` 6 and 7.
