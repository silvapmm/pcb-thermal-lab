# Text for the project documents (bare spot under a source)

To be folded into the project documents when the work is adopted (or, for the limit text, when the maintainer decides to document the limit only). Numbers are those of `../README.md`.

## For `docs/theory.md` (layered idealisation, limits) and `docs/models.md`

**A part over a spot without copper.** In the layered models a layer node holds the copper and the laminate around it, and its temperature is the mean through that thickness. Under a part on bare laminate this has three consequences, measured against a resolved 3D solver (the 3D solid of the program agrees with it within 0.2 to 2 %, and within 0.4 % once its maximum is taken at the face of the board rather than at the centre of the top copper slab):

1. the vertical path between two copper nodes crosses, where a layer has no copper, the laminate that replaces the copper (half the thickness of each adjacent layer, `d + t_a / 2 + t_b / 2` instead of `d`), and the part sits on the face of the board, `t / 2` above the node of the top layer; with 0.115 to 0.21 mm gaps (the typical 4- and 6-layer stack-ups) this is the whole error, about 3.5 % of the rise; about half of it is the half layer between the node and the face, which the 3D solid misses too when it reports the centre of its top copper slab;
2. on a board with a thick gap (two layers, 0.8 or 1.6 mm) the node of the top layer has the temperature of the hot surface but the lateral conductance of half the gap, so the heat leaves sideways through the bare node into the neighbouring copper by a path that the laminate does not have: the FVM reads 6.6 % (0.8 mm) and 18.4 % (1.6 mm) low for a 6 mm window under a 6 mm part at a 0.5 mm cell, 3.9 % and 10.4 % for a 12 mm window; the error does not depend on the cell (-16.7 to -19.3 % from 2 to 0.25 mm) and does not come from the discretisation of the window edge;
3. the FDM is 3 to 9 points lower than the FVM in the same situation, the Analytic averages the copper over the board and does not see a window of a few millimetres (-11 to -63 % for windows up to 12 mm), and the Lumped is not systematic (-43 % to +7 %).

A board with copper under the part (fill 1 in the hottest cell) is not affected (0.0 to 0.4 points). The input check warns when the part sits on bare laminate (P3 of `INTEGRATION.md`).

*Picture for the section:* `figures/fig_01_part_over_bare_window.png` (the section with the heat paths) and `figures/fig_02_nodes_of_the_layered_model.png` (the nodes of the program and the nodes proposed).

## For `docs/validation.md`

New section "A part over a window without copper": the sweep of `README` 3 (four stack-ups, windows 0 to 20 mm, cells 1 and 0.5 mm, five models against the resolved reference), the table of the treatments of `README` 6 and the rows of `README` 7. The reference of the sweeps is 0.3 to 2.2 % above the converged value (`README` 2.2 and 9); quote the converged values of `README` 9 where they exist.

## For `docs/versions.md`, chapter "Planned"

Replace the item "A spot without copper under a source" by two items: **fix/bare-spot-vertical** (the vertical correction of P1, no new unknown; evidence `research/bare-spot-under-source/README.md` 6.1) and **after the investigation A11: laminate nodes next to bare cells** (P2: gaps above 0.5 mm get 2 to 4 nodes in the cells with bare copper and a margin; evidence README 6.2), plus the input-check warning (P3).

## For `docs/research.md`

Summary in `research.md` of this folder.
