# Entering the program: the Analytic model on partial copper

The work is not in the program. Nothing here edits `pcbthermal/`; the candidate is `lib/defect.py`, measured on copies. Three proposals, in the order of cost; the evidence is in README sections 4 to 6.

## P1. A better warning (no physics, no risk)

* **What.** The Analytic's existing input warning ("copper coverage varies strongly around the heaters", spread of the weighted fill above 0.25, `analytic._effective_sheet`) fires on 16 of the 18 pad boards of README 4.5 and on every board whose error is beyond 6.1 %. It says the uniform-sheet assumption is weak and the FVM is more reliable. Add what was measured: on a copper pad over bare laminate the Analytic can be **too cool by up to 65 %** (two layers, bare second, 6 mm pad) and **too hot by up to 9 %** (one layer, 40 mm pad), and the same physical board entered with one layer or with two gives results up to 1.8 times apart.
* **Impact.** Text only; results bit-identical. A test that the warning text carries the new numbers (and `tests/test_help.py`, the user guide section on the Analytic model, `docs/validation.md`, `docs/models.md` limits).
* **Risk.** None. It does not remove the error.

## P2. The candidate in the Analytic model, steady state (a `feature/` item)

* **What.** For a layer whose copper is not uniform: (a) laminate nodes through the thickness as extra layers of the modal system (a one-layer board gets `n` laminate nodes instead of the series film `laminate.series_bottom_problem`; a multilayer board gets `n - 1` interior nodes per gap), the same node construction as the FVM (`laminate.py`; A1 of `gap-subdivision` and A11 of the roadmap decide `n`: the Analytic must use the number the FVM uses, because the candidate equals the FVM with the same nodes to 0.1 to 0.7 %); (b) the series solved for the weakest sheet of each node (the bare laminate), the copper put back as a lateral conductance on the links of a tile grid through the tile Green-function system that `solve_steady` already has for vias, blocks and heatsinks (`C` gets lateral entries); (c) the K0-weighted fill and its warning no longer decide the sheet of a layer that has the defect; a layer with uniform copper takes the program's path unchanged.
* **Measured impact** (README 5, `data/`):
  * 52 pad rows of the baseline of `gap-subdivision` (graded 3D reference): Analytic -66.7 to +1.3 % (mean absolute 17.9 %, 32 rows beyond 10 %), candidate with 2 nodes -5.7 to +0.5 % (1.68 %, none beyond 10 %), with 4 nodes -2.9 to +2.1 % (0.83 %, 46 rows where it runs).
  * 18 pad boards of 6 to 40 mm (60 mm board, one and two layers, three second layers): program -65.3 to +8.6 %; candidate with 4 nodes -2.5 to +1.4 % at a 1 mm tile (-5.5 to -1.5 % at a converged tile for pads of 6 to 20 mm, README 5.4).
  * 13 out-of-sample cases (board, part, thickness, films, copper, laminate): -0.4 to -3.6 % against -4.6 to -46.1 %.
  * Off-centre pad, part off the pad, two pads: -1.5 to -2.6 % with 4 nodes against -21 to -22 %; a 6 mm window in full copper: -6.0 % against -56.7 % (the FVM -20.2 %).
  * 44 uniform rows: unchanged by n = 1 (the program's result), 0.29 to 0.06 % mean absolute at n = 2; a uniform board with the simple stack-up moves by 0.3 to 0.6 points (the candidate uses the advanced stack-up's slabs).
* **What does not change.** The Lumped, FVM, FDM and the 3D solid; the Analytic on boards with copper everywhere (to 0.3 points), the transient (see risks), the API.
* **Risks and open points.**
  * **Cost**: the dense tile system has (tiles with a defect) x (nodes carrying one) unknowns: one layer, 1 mm tiles, pads of 10 / 20 / 40 mm: 140 / 480 / 1760; with a 0.5 mm tile (needed for a part of 3 mm) 480 / 1760 / 6720; a part of 6 mm on a board with 40 x 40 mm of patterned copper is a few thousand unknowns; a Gerber board with many small pads and fine tracks is **not** within reach of this construction (thousands of tiles per layer; the research code stops at 6000). A policy is needed (tile adaptive to the copper, or fall back to the program's path and warn).
  * **The tile rule** (at most a sixth of the part; three tiles across overshoots by 13 to 18 %) was found on two boards; the mixed effect of `n` and the tile needs a sweep on more boards before it is a rule of the program. A coarse tile can be right for the wrong reason.
  * **Combination** with vias, metal blocks, heatsinks (the same Woodbury system: the lateral entries and the vertical ones share `C`; not measured), outlines (the Analytic runs on the equivalent rectangle), heaters on inner layers (the candidate takes the first layer only), several heaters.
  * **The transient** of the Analytic uses the fill and the layer capacity `c_l` of the uniform sheet; it would not follow the steady state.
  * **The layered limit remains**: the candidate is the FVM's model and carries its error (-0.9 to -3.4 % with 4 and 8 nodes on pads of 10 to 20 mm; -3.6 % on a 6 mm pad with 8 nodes), which `gap-subdivision` and `bare-spot-under-source` (P1 to P3 of its INTEGRATION) treat.
  * **Memory**: `n_terms^2 x nodes^2` doubles for the modal matrices (300 x 300 x 15 squared is 160 MB; 8 layers with 2 nodes per gap is 15 nodes).
* **Tests the adoption needs**: the candidate against the FVM with the same nodes on every pad row (0.1 to 0.7 % measured), the uniform boards bit-identical, an energy balance, the independent solver of `tests/helpers/layered3d.py` on the one-layer pad of `tests/test_layered_vs_3d.py` (documented limit -28.8 % there becomes the candidate's), the one-layer and the two-layer-bare entries of the same board within 0.2 points.

## P3. If P2 is not adopted: state the limit

* Keep the program's model and document in `docs/validation.md` and `docs/models.md` the Analytic's behaviour on pad boards (README 3: -65 to +9 %; shortfall for pads up to 20 mm and, on a one-layer board, an excess for 30 and 40 mm; the dependence on how the layers are entered; the dependence on the laminate in-plane conductivity: -9.0 % against -28.3 % for the 20 mm pad with 0.9 and 0.3 W/mK), with P1's warning. The FVM (-0.5 to -18 % on the same boards, better with the laminate nodes of A1 and A11) is the model to use for partial copper.

## Decisions left to the maintainer

1. P1 (the text of the warning): adopt now?
2. P2: a `feature/` after the reviewer's opinion and after A1 and A11 fix `n`? Or P3?
3. The default `n` of the Analytic follows the FVM's (2 for a one-layer board today). At `n = 2` the candidate is -3.9 to -8.8 % on pads of 14 to 6 mm: the Analytic would then be as good as the FVM, not better.
