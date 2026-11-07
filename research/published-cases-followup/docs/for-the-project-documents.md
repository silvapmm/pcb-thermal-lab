# Text for the project documents (to adopt later; nothing here is in `docs/` yet)

## For `docs/validation.md` (a section on published strip, trace and plate cases)

* **Strip on a flux channel** (Yovanovich, Muzychka and Culham 1999, Tables 2 and 3): the printed table follows the equations (24), (27), (28) to the last digit; the equation (26) row is a truncated sum below `eps` = 0.08; the second row of Table 3 is the mean of equations (24) and (27), not (24) and (26). An independent 2D finite-volume solve agrees with equations 23, 24 and 27 to +0.07 to +0.20 %. The program's layered models are within 3 % of `psi` for a thin slab (t/c = 0.1) and lose the through-thickness spreading for t/c >= 0.5 on bare laminate (fvm/fdm -36 to -44 % at t/c = 3; the 3D solid +66 to +96 % with four slabs, +6 to +11 % with sixteen).
* **Trace cells** (Lemczyk and others 1992): Table 1 Q_a, Q_b, Q_d to 1.1, 1.2, 2.4 %; Tables 2 and 3 to 0.8 to 1.0 % on average; case (c) was computed with Bi1 = 0.001, not h1 = 0; the R of Table 4 is the mean temperature of the whole top face. The 3-layer board of Table 4 is representable in the program (undrawn outer layers) and the fvm, fdm, solid3d agree with the independent solver to 1.7 %.
* **Coupon** (Culham and Yovanovich 1998): the base stack is representable (outer FR-4 as undrawn 36 um layers with the advanced stack-up gaps); R_solid of the fvm and fdm within 0.6 % of the independent solver for sources of 10 to 52 % of the board, k_e 7.79 W/mK against the printed 8.28 (the independent solver is itself 5.7 % below the paper).
* **Vias** (Shen and others 2020): the closed-form numbers of section II are reproduced (optimal diameters 0.250 and 0.788 mm, +43.4 and +22.4 %, the 47 / 89.5 / 46.4 / 62 % reductions are Pattern II's); the CFD without vias needs k_FR4 = 0.35 W/mK. The program reads a via 6 to 8 % too conductive (FVM, air-filled, 70 um copper on four layers) against an independent unit cell (square Cartesian and axisymmetric agree within 0.5 %); the same per via in an array and alone: the barrel is counted over the dielectric gaps only, the copper thickness is crossed at no resistance (a barrel over the gap plus half a copper thickness reads -0.3 to -0.5 %).
* **Plate near an edge** (Seri Lee 1998): the exact thin-plate cosine series gives Rc 0.664 / 1.280 / 2.270 K/W for the centre, the edge midpoint and the corner against the printed 0.66 / 1.29 / 2.38 (the printed corner is 4.6 % above). FVM, FDM, 3D solid and Analytic agree with the series within 0.5 % at every gap from the edge or corner; the Lumped reads the footprint mean -5 % at the centre and -18 to -24 % within 6 mm of an edge or corner of that plate, and on a 100 mm two-layer 35 um board with a 5 mm part -2.3 % at the centre, -9 to -10 % at an edge, -12 to -14 % at a corner (a sample, not a bound).

## For `docs/theory.md` 7.5 and 11 (wording)

In 2.6 (the via): the barrel conductance is `k_cu A / d` over the dielectric gap; the copper layer is a node, so the barrel crosses the copper thickness at no resistance (a limit; 6 to 8 % on a 4-layer board of 70 um copper). In 1.7 or wherever the face term of a part is written: the term assumes all the heat of the part crosses the half outer layer; the heat that the film under the part takes directly does not (+2.3 % on a coupon whose source covers the board, about one per cent of the term for a real part).


The plate model reproduces Seri Lee's plate to the exact thin-plate series within 0.5 % in the FVM, FDM, 3D solid and Analytic; the numbers of the correlation (0.66, 1.29, 2.38) are the article's, 0 to 5 % from the exact plate.

## For the user guide, via section (after the maintainer decides)

The FVM and FDM count the barrel of a via across the laminate only, not across the copper layers: with thick copper and thin laminate a via reads a few per cent too conductive (6 to 8 % on a 4-layer board of 70 um copper against an independent unit cell); leave a margin.

## For `docs/research.md`

Open: the barrel length rule of the via (cause located, rule to measure on a sweep of stacks); the Lumped near an edge on more boards and part sizes. The face term with a film under the source is explained (it charges all the heat of the part through the half outer layer; a few per cent of a small term for a real part). Folder: `research/published-cases-followup/`.
