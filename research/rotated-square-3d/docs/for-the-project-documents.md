# Text for the project documents (when the work is adopted or the limit is documented)

## `docs/theory.md`, section of the 3D solid, edge loss on an outline (limit, valid today)

On a board with an outline the 3D solid gives every cell it cuts the conductance `1 / (1 / (h_side L dz) + 0.25 (dx + dy) / (kx L dz))` per slab, with `L` the outline length in the cell and `kx` the in-plane conductivity multiplied by the cover of the cell. For a cell the outline leaves whole this is the half-cell series; for a cut cell the distance to the edge stays half a cell and the conductivity is divided by the cover, so the conduction to the edge is too resistive by `1 / cover`. At the default edge coefficient (10 W/m2K) the effect is below 0.3 K; at 100 to 5000 W/m2K it makes the answer depend on where the edge falls against the grid (a square turned by 20 degrees: +1 to +3 K at 1 mm cells for a 40 mm board, still +2 K at 160 cells per side for a 20 mm board; `research/rotated-square-3d/README.md` 2 to 4), and on a round board it is +6 % at 1 mm and `h_side` 1000 against an axisymmetric reference (README 5). The FVM and the FDM attach the edge film to the node directly and show it much less (README 7).

## `docs/validation.md`, a row for the outline

| case | 3D solid | FVM | FDM | note |
| :-- | --: | --: | --: | :-- |
| 40 mm square turned 20 degrees, 1 mm, `h_side` 10 / 100 / 1000, minus the aligned square | +0.06 / +1.28 / +3.12 K | +0.01 / +0.08 / +0.33 K | +0.00 / -0.00 / -0.01 K | part on the grid, 2 W in 6 mm |

## `docs/versions.md`, chapter 'Planned', an entry (after the decision)

* **Cut cells in the 3D solid** (`fix/solid3d-cut-cells`, after the investigation `research/rotated-square-3d`): the cover is sampled with the centroid of the board part and the aperture of every face; the links between cells run through the aperture over the distance between the centroids, the edge term over half the depth of the board strip; the conductivity is no longer multiplied by the cover. Evidence and measured impact: `research/rotated-square-3d/INTEGRATION.md`.

## `research/ROADMAP.md` (kept on the research side)

A3 closed by this folder once the maintainer decides P1 or P2; the open questions left: a patterned-copper board against an independent reference, the cells with two edges (T board +0.2 K at the default coefficient), and the 45 degree residual of a turned part (README 4.4).
