# Text for the project documents (to adopt later; nothing here is in `docs/` yet)

## For `docs/validation.md` (a section on published strip, trace and plate cases)

* **Strip on a flux channel** (Yovanovich, Muzychka and Culham 1999, Tables 2 and 3): the printed table follows the equations (24), (27), (28) to the last digit; the equation (26) row is a truncated sum below `eps` = 0.08; the second row of Table 3 is the mean of equations (24) and (27), not (24) and (26). An independent 2D finite-volume solve agrees with equations 23, 24 and 27 to +0.07 to +0.20 %. The program's layered models are within 3 % of `psi` for a thin slab (t/c = 0.1) and lose the through-thickness spreading for t/c >= 0.5 on bare laminate (fvm/fdm -36 to -44 % at t/c = 3; the 3D solid +66 to +96 % with four slabs, +6 to +11 % with sixteen).
* **Trace cells** (Lemczyk and others 1992): Table 1 Q_a, Q_b, Q_d to 1.1, 1.2, 2.4 %; Tables 2 and 3 to 0.8 to 1.0 % on average; case (c) was computed with Bi1 = 0.001, not h1 = 0; the R of Table 4 is the mean temperature of the whole top face. The 3-layer board of Table 4 is representable in the program (undrawn outer layers) and the fvm, fdm, solid3d agree with the independent solver to 1.7 %.
* **Coupon** (Culham and Yovanovich 1998): the base stack is representable (outer FR-4 as undrawn 36 um layers with the advanced stack-up gaps); R_solid of the fvm and fdm within 0.6 % of the independent solver for sources of 10 to 52 % of the board, k_e 7.79 W/mK against the printed 8.28 (the independent solver is itself 5.7 % below the paper).
* **Vias** (Shen and others 2020): the closed-form numbers of section II are reproduced (optimal diameters 0.250 and 0.788 mm, +43.4 and +22.4 %, the 47 / 89.5 / 46.4 / 62 % reductions are Pattern II's); the CFD without vias needs k_FR4 = 0.35 W/mK. The program's via arrays read the array resistance 6 to 8 % low (FVM, air-filled) against an independent unit cell (square Cartesian and axisymmetric agree within 0.5 %).
* **Plate near an edge** (Seri Lee 1998): the exact thin-plate cosine series gives Rc 0.664 / 1.280 / 2.270 K/W for the centre, the edge midpoint and the corner against the printed 0.66 / 1.29 / 2.38 (the printed corner is 4.6 % above). FVM, FDM, 3D solid and Analytic agree with the series within 0.5 % at every gap from the edge or corner; the Lumped reads the footprint mean -5 % at the centre and -18 to -24 % within 6 mm of an edge or corner (one aluminium plate; not measured on a PCB).

## For `docs/theory.md` 7.5 and 11 (wording)

The plate model reproduces Seri Lee's plate to the exact thin-plate series within 0.5 % in the FVM, FDM, 3D solid and Analytic; the numbers of the correlation (0.66, 1.29, 2.38) are the article's, 0 to 5 % from the exact plate.

## For the user guide, via section (after the maintainer decides)

In a dense via array (pitch of a few via diameters, copper planes on every layer) the FVM and FDM read the resistance of the array 6 to 8 % low against an independent unit cell; use the 3D solid or leave a margin.

## For `docs/research.md`

Open: the cause of the dense-array deficit of the via model; the Lumped near an edge on PCB-like boards; the face term with a film under the source. Folder: `research/published-cases-followup/`.
