# Integration: via contact geometry and barrel length

Status: **a proposal, not yet reviewed**. Nothing in `pcbthermal/`, `tests/`, `examples/` or `ico/` was changed; the variants are copies in memory (`lib/barrel.py`, `lib/contact.py`). The numbers are those of `README.md` (sections in brackets).

## 1. What would change (all in `pcbthermal/viawell.py`, FVM and FDM)

1. **Barrel length (A22).** In `build`, the barrel conductance of every gap becomes `k_cu A / (d_k + 0.5 t_bar,k)`, with `t_bar,k` the mean of the thicknesses of the two copper layers around the gap (`lib/barrel.py` does it by scaling `gv` before `kron_barrel`). One constant, `0.5`, measured (README 2.2).
2. **Weights by sheet conductance for a footprint that is not uniform (A20).** The per-layer weights `w^l_a` proportional to the geometric weight times the sheet conductance of the cell in that layer; the footprint enlarged until the weighted effective radius reaches `e^(-1/4) r_via`; a footprint with uniform sheet conductance and full copper rim is built by the program's own code (bit-identical). This is variant (a) of `via-partial-copper`.
3. **Contact (A20).** The share `f` of the rim of the drill (48 samples, the copper of a layer as the union of its zones) that touches copper multiplies the well; `f = 0` leaves the layer uncoupled. Needs the zones of the problem inside `build` (it already receives the problem); imported masks need a sample of the mask instead (not done).
4. Tests: a via outside a copper edge never heats the board and reads no cooler than the program's value (`research/via-contact-geometry/tests`), the cold-spot board of `tests/test_maximum_principle.py` keeps no cold spot, the unit-cell sweep as a test of the barrel rule on three stacks (a small version of `study_barrel_length.py`).
5. Documents (when adopted): `docs/theory.md` 2.6 (the barrel length, the weights, the contact; the text is in `docs/for-the-project-documents.md`), `docs/validation.md` (a section with the tables 2.2, 3.3 and 3.4), `docs/versions.md`.

## 2. Measured impact

| change | frozen records that move | size | other |
| :-- | --: | :-- | :-- |
| barrel rule `a` = 0.5 | 30 of 30 steady maxima of the five via boards (FVM and FDM, 2, 1, 0.5 mm) | +0.028 to +0.149 K (0.04 to 0.25 % of the rise), hotter | the times to 63 % of those boards, the Lumped (its `gz_via` uses the same barrel) and the 3D solid not measured; the refreeze folds a pending file |
| contact + sheet weights | 0 of 30 | 0.0000 K | moves only vias whose footprint touches partial copper |
| unit cell (2.2) | | mean error 4 and 6 layers, 35 um and more: -9.1 % -> +0.8 % (range -32.8 .. -0.6 % -> -4.6 .. +11.8 %) | 18 um copper: +1.4 % -> +3.8 % mean, max +29 -> +35 % |
| partial copper, FVM at 1 mm, K (per cent of the rise) | | outside the edge +2.90 (+3.5) -> -1.05 (-1.3); track -8.55 (-9.4) -> -5.95 (-6.5); quarter -3.62 (-6.0) -> +2.32 (+3.8) | the cold spot is gone (3.4) |

## 3. Recommendation

* **A22: adopt the barrel rule on a `fix/` branch for 2.6.0, with the constant stated as measured**, after the reviewer settles doubt 1 (README 7): the axisymmetric cell supports `a` = 0.5, the not-converged 3D solid supports less. If the reviewer cannot settle it, the safer choice is `a` = 0.25 (it removes about half of the deficit on every board of the sweep and cannot overshoot: the mean error at a = 0.25 on 4 and 6 layers is -4.1 %, against +0.8 % at 0.5), or to document the limit and keep the program (the shift is under 0.25 % of the rise on the frozen boards and the error is on the unsafe side, the part reads cooler than it is, by up to 9 % of the via resistance on multilayer boards, which in the temperature of the part is a few per cent of the via effect).
* **A20: adopt the two safe pieces, not the quarter.** (i) Uncouple a layer whose rim touches no copper: it moves 0 frozen records, removes the worst unsafe error of the set (+2.9 K to -1.05 K) and is a one-line condition once the rim share exists. (ii) The weights by sheet conductance for non-uniform footprints only **together with** (i): alone they worsen the via outside the edge (+2.9 -> +6.7 K) and the maximum principle is not restored by structure (8 positive entries on the cold-spot board, 292 at 0.125 mm). They remove the cold spot (-7.94 K at 0.5 mm, -14.43 K at 0.25 mm) and make the via effect cell-independent. The cost, stated in the release note: the corner of a copper region moves from the safe to the unsafe side by about 2.3 K at 1 mm (3.8 % of the rise) until the sector well exists.
* **Not recommended**: the star (no-go, `via-star-coupling`), a clip of the temperature, and scaling the well by `f` alone (vacuous at fine cells, 3.1).

## 4. Next step (the sector well)

A local numerical upscaling: for every via and layer a fine raster of the zones around the barrel (cells of `h/4`), a solve with the barrel at one potential and the footprint cells as the coarse side, and the conductances from the Schur complement; checked on the fifteen boards and the cold-spot board, with the imported masks read at the same raster. Open until measured: whether it removes the quarter's unsafe error without the star's in-plane short; whether the maximum principle holds by construction (it would, the Schur complement of a resistor network is an M-matrix; the star failed for another reason, the weights).

## 5. Risks

* The constant `a` rests on one reference (README 2.2 and doubt 1); the thin-copper, thin-gap, large-via boards get worse with the rule (+29 -> +35 % of the via resistance at 18 um); an `a(t_cu)` would hide a different term (doubt 2).
* The fifteen boards are small and two-layer; the partial-copper behaviour on multilayer boards and on imported masks is unmeasured; the rim share ignores imported masks.
* Interaction with the edge image (`viawell.edge_term`, `well_conductance(..., c)`): the contact must multiply the well after the edge term; the footprint enlargement for the edge also changes the weights. Not tested together here (the cases of the set have no edge image within reach except the last two, which are unchanged).
* The branch `feature/via-star-coupling` edits the same function; the two cannot both be adopted.
* Moves numbers: the 2.6.0 refreeze with a pending file for the barrel rule; the contact change moves none of the 17 frozen boards.
