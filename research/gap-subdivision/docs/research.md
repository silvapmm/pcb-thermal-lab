# Summary for `docs/research.md`: the gap of multilayer boards (A1)

**Question.** Does cutting the dielectric gap of multilayer boards into more than one node through the thickness remove the error against a resolved 3D solution, and what are the program's numbers on simple boards?

**Read and reproduced.** Muzychka, Culham, Yovanovich (2003) Eq. 27 and Yovanovich, Muzychka, Culham (1999) Eqs. 14 to 18 (open copies of the Waterloo group) are reproduced by an exact layered series (`research/gap-subdivision/lib/series.py`) to 7e-6 and 2.4e-6; a graded 3D solver written for pads agrees with the series within 0.04 % on uniform boards of 2, 4 and 8 layers.

**Results.**

* Boards with copper in every cell: FVM and FDM -0.72 to +1.04 %, Analytic -0.91 to +0.02 %, 3D solid 0 to +1.33 %, Lumped -1.70 to +4.14 % against the exact series (44 boards; 300 more in a grid: FVM errors above 2.5 % only for a 2 mm source on a 1 mm cell). The gap nodes change those numbers by 0.0 to 0.26 points.
* The 2-layer FVM shortfall is a bare-laminate effect around a pad with a thick gap: -10.5 to -0.3 % for pads of 6 to 26 mm (1.6 mm gap), -0.2 to +0.3 % with a 0.1 to 0.4 mm gap, -10.2 % at 3.2 mm; the Analytic is -13 to -46 % on small pads.
* Cause: lateral conduction in the bare laminate across the gap (in-plane conductivity to 0.01 W/mK removes it; through conductivity sets its size; nodes under the pad do nothing; the reading of the surface at the node is 0.04 points).
* Extra nodes in the cells that show laminate remove the gap error like 1 / n (70 % at n = 4 graded, 90 % at n = 8); the total error depends on the cell (the in-plane error has the opposite sign, +1.3 % at 0.5 mm).
* Validation rows and examples move +0.0 to +0.9 %; on three real windows the gap error is 12.8 to 15.9 % where the hottest cell is bare and n = 8 halves it, while the scalar copper fill is the larger error.

**Open.** The decision on the nodes (P2, one change with A12 and A11); the FDM, the transient, vias, blocks and outlines with extra nodes; the other real boards.
