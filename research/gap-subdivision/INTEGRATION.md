# Integration: the gap of multilayer boards, and the baseline (A1)

How to bring the results of this folder into the program, what each change costs and what it does to the numbers. Nothing here is implemented: every number was measured on copies in memory (`lib/gapnodes.py` on `research/bare-spot-under-source/lib/layered.py`) and `pcbthermal/` is untouched. The evidence is in `README.md` (section numbers in brackets); the baseline that the 2.5.0 proposals are to be judged against is in `baseline/` and is re-run with `scripts/rerun_baseline.py`.

## 1. What the study found, in five lines

* On a board with copper in every cell the layered models are within about 1 % of an exact series solution (FVM and FDM -0.72 to +1.04 %, 44 boards, 2 to 8 layers, gaps 0.1 to 3.2 mm; the energy balance is 1.5e-11); cutting the gaps into more nodes changes them by 0.0 to 0.26 points [3.1, 5.1]. **No change is needed there.**
* The 2-layer shortfall of the FVM (-2.3, -3.8, -7.7 % recorded before) reproduces on designed boards with a copper pad on the top layer: -0.9 % (20 mm pad), -4.7 % (10 mm), -10.5 % (6 mm), 1.6 mm gap, 3 mm source; it is -0.2 to +0.3 % with a 0.1 to 0.4 mm gap and -10.2 % with 3.2 mm; the Lumped (-8 to -14 %), the Analytic (-13 to -46 %) and the FDM (-7 to -16 %) are worse on the same boards [3.2].
* The cause is the lateral heat flow in the bare laminate across the thickness of the gap, which one node per layer cannot hold (single-effect probes: `k_xy` -> 0.01 W/mK removes the error, `k_z` sets its size, nodes under the pad do nothing, the reading of the surface at the node is 0.04 points) [4].
* Extra nodes in the gap of the cells that show laminate (plus a margin of a gap thickness) remove the through-thickness part like `1 / n` (70 % at n = 4 graded, 90 % at n = 8); the total error depends on the cell because the in-plane error of the cell has the opposite sign [5.2 to 5.4].
* On the validation rows and the examples the same nodes move the peak by +0.0 to +0.9 %; on a real layout (three windows of the Stormduino) they remove 32 to 76 % of the gap error on the two windows whose hottest cell is bare, and the scalar fill of the cell stays the larger error [6].

## 2. Proposals

### P0. The baseline as the common reference of 2.5.0 (no program change)

**What.** `baseline/uniform.csv` (44 boards), `baseline/uniform_grid.csv` (300), `baseline/pads.csv` (52) hold the board, the cell, the independent reference (exact series for uniform boards, converged graded 3D solver for pad boards) and the peak of every model of the program on develop at 2.4.4. `scripts/rerun_baseline.py [--update]` re-runs the models and prints the movement of every row and the error before and after.

**How to use it.** Before a change of `pcbthermal/` is merged, run it on the branch: the uniform rows and the pad rows with a full-copper layer on both sides of the gap must not move by more than the round-off of the change (a via fix, a SOR fix, a Lumped fix touch none of them: none of the baseline boards has a via); the pad rows with bare laminate must move towards the reference or not at all. `tests/test_baseline.py` is a tripwire (two rows reproduced to 1e-4, the sign structure of the errors): it fails on purpose when a change moves them, and `--update` records the new numbers once they are understood.

**Cost.** Two minutes of run time; no code in the program.

### P1. Document the limit and warn (no change of the numbers, recommended now)

**What.** (a) Replace the paragraph `docs/validation.md` 21.1 (the 2-layer error "documented, not corrected", whose script was not in the repository) by the reproducible text of `docs/validation-21-1.md`: the errors against the converged reference, their dependence on pad, gap, `k_z`, `k_xy` and h, the statement that the error is the bare laminate and not the number of layers. (b) A pre-run note in `checks.py`: a heater whose copper footprint (the extent of the copper of the layer it sits on, around the part) is smaller than about 8 gap thicknesses, with a gap of 0.4 mm or more, reads 3 to 10 % cool in the FVM and by more in the other models [3.2, figure 9]. The rule is a screen from the pad and gap sweeps (a 3 mm source, `k_z` 0.3, `k_xy` 0.9, h 10 to 100), not a fitted law; the conductivities of the probes (4) move the threshold, which is why the text says "about".

**Impact.** None on results. **Risk.** A false alarm on a thick board with a large pad and a small source (the rule uses the pad, not the board); a quiet board with a pad and a thin gap does not fire.

### P2. Extra nodes in the gap of the cells that show laminate (a decision for the maintainer; the same change as A12 P2 and A11)

**What.** For every gap, the cells in which either adjacent layer has a copper fill below 1, plus a margin of `ceil(d / dx) + 1` cells, get `n` laminate nodes through the gap (n = 3 or 4, symmetric geometric grading 2:1 from the copper faces); every other cell keeps the single link. The construction is that of `laminate.py` for a one-layer board applied to a gap (the copper node keeps its copper and half the first sub-gap; each new node holds `(s_j + s_{j+1}) / 2` of laminate and conducts sideways with `k_xy` times that thickness); the via barrels stay in parallel between the copper nodes. It is the change that `bare-spot-under-source` proposes (P2) and the mask that `gerber-models` R2 and A11 want for the one-layer laminate nodes: **one implementation for the three**, and the vertical correction of A12 (P1 there) goes with it for a part over a window.

**Where in the code.** `fvm.Network` and `fdm.Network` (the node numbering becomes ragged: unknowns for the extra nodes only in the flagged cells; the `layered.py` copy builds exactly that matrix), the transient machinery (`fvm.transient_from_network`, the steps and the profile runner: the heat capacity of a new node is `rho cp s_j A`, taken from the copper nodes' laminate share, as `laminate.py` does for one-layer boards), `results.py` (the extra nodes are not layers: keep them out of the per-layer arrays and the plots), `api.SolverOptions` (n and the margin), Preferences (a section "Laminate nodes", with tooltips and a user-guide paragraph), `docs/theory.md` 4 and 5 (the construction and the 1 / n tail, with a picture: figures 1 and 2 of this folder), `docs/validation.md` (the pad rows).

**Impact (measured on copies, steady state, cell 0.5 mm).**

| | now (n = 1) | n = 3 gr | n = 4 gr | n = 8 gr |
| :-- | --: | --: | --: | --: |
| pad 10 mm, 1.6 mm gap, bottom full: error against the converged 3D solver (total) | -4.73 % | -0.83 | -0.23 | +0.78 |
| same: the gap alone (against the same-cell 3D solver) | -5.94 | -2.10 | -1.50 | -0.50 |
| pad 10 mm, 3.2 mm gap | -10.21 | -2.83 | -1.66 | +0.34 |
| 4 layers, 1.6 mm gaps, top pad | -4.63 | -0.82 | -0.23 | +0.76 |
| thin gap (0.1 to 0.4 mm), pad 10 | +0.32 / -0.20 | +0.37 / +0.46 | +0.38 / +0.55 | +0.39 / +0.69 |
| validation rows, 23 boards, 1 mm cell (change of the peak) | 0 | | +0.00 to +0.90 % | |
| three real windows (the two bare ones, 0.5 and 1 mm cells), the gap alone (z), equal sub-gaps | -12.8, -15.3, -15.9 % | | -8.7, -5.5, -6.6 % (equal) | -6.3, -3.7, -4.4 % (equal) |
| unknowns, example board (4 layers) | 1.00 | | 1.47 (bare cells + margin) | |
| unknowns, 2-layer board all bare | 1.00 | | 2.46 | 4.40 |

**Does not change (bit for bit).** Every board whose layers next to every gap have copper fill 1 in every cell (the refined set is empty and the copy takes the program's path: `tests/test_references.py`), the Lumped, the Analytic, the 3D solid, the examples to 0.1 % (they move by +0.06 to +0.09 %).

**Risks and open points.**

* **The 1 / n tail.** No n reaches zero: n = 4 graded leaves -1.5 % of the gap error on the base pad board and n = 8 -0.5 % (2 to 3 % on a 3.2 mm gap). The number of nodes is a cost-accuracy choice; the table gives n = 3 as the knee (the error falls by 65 % for 2.0 times the unknowns in bare cells).
* **The total error is a cancellation at the cell.** The FVM at 0.5 mm is +1.3 % too warm in the plane on the base pad board; with n = 4 at a 4 mm source the total is +0.6, -0.7 and -1.1 % at 1, 0.5 and 0.25 mm: the stated accuracy of the node count is the gap column, not the total. On boards with a thin gap the node count moves the total by +0.2 points the wrong way (the single node is right there by the same cancellation) [5.2, 5.4].
* **The margin matters**: with none the nodes of the bare cells next to a copper cell are walled in and the result overshoots (+3.8 % at n = 8); the default of a gap thickness plus a cell is within 0.1 point of every cell refined [4].
* **The transient** needs the capacity of the new nodes (not built in the copy, which is steady state). The one-layer boards already have it (`laminate.py`).
* **The FDM** has its own pad-edge floor (-10 % with a bare bottom at every gap [3.2]); extra nodes in the FDM were not measured.
* **Lumped and Analytic** have no nodes through the gap; their pad errors (-8 to -46 %) are not removed by this and are items of their own (A2).
* **The simple stack-up** with 3 or more layers allocates the laminate unequally between the layer nodes (0.75 d for an outer node of 4 layers); it costs up to 0.5 points at a 1.6 mm gap [3.3]. A subdivision defines the nodes after the allocation of the advanced mode; the simple mode would have to be converted or documented.
* **Real layouts**: where the copper is a pattern finer than the cell (hatching, tracks) the scalar fill is the larger error and the nodes do not touch it [6.2].

**Tests for the adoption.** The invariance of a uniform board (n = 1 and the empty mask equal the program, bit for bit); a small uniform board against the exact series (`lib/series.py` ships as a test helper with its published checks); a small pad board whose z error falls monotonically with n against the converged graded solver (`tests/test_references.py` has the small-board version); the baseline tripwire; the whole battery.

### P3. Subdividing every gap of every board (the A1 question as asked): not recommended

Same code as P2 without the mask. On uniform boards it moves the peak by 0.0 to 0.26 points (and by up to +1.5 points towards the in-plane limit with a 2 mm source), costs `1 + (n - 1)(L - 1) / L` times the unknowns (2.5 for 2 layers, 3.25 for 4, 3.6 for 8 at n = 4) and changes nothing that is wrong [5.1, 5.5].

## 3. Decisions left to the maintainer

1. P0: adopt `baseline/` as the common reference of the 2.5.0 changes (the numbers are of develop at 2.4.4).
2. P1: the text and the screening rule (the threshold of 8 gap thicknesses, the gap of 0.4 mm or more).
3. P2: whether to implement the nodes now, with A12's vertical correction and the A11 laminate nodes as one change on a `feature/` branch, and n = 3 or 4.
4. Which of the open items it unblocks: A1 closes with this folder once the reviewer has read it; A11 (the number of laminate nodes for patterned copper) and A12 (P1 and P2 there) are the items that implement it.
