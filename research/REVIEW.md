# Review register of the investigations

What the independent `reviewer` agent has checked in each folder, so that a later session continues where the last one stopped; the chapter `N. Review` of each folder's README holds the status, the independent checks, the limits (what was not verified) and the defects of the program found; this file only registers them. Status `reviewed` means the findings are fixed and the numbers of the documents are the ones the scripts print now. Program version is the last commit of `develop` that touched `pcbthermal/` when the studies were last run. Update a row in the commit of the review it records; what is left to finish is `ROADMAP.md` section 1.

| Folder | Status | Program version | Open points (details in the README of the folder) |
| :-- | :-- | :-- | :-- |
| `solid3d-verification/` | reviewed | `6eb9adf` | none; the cost caption and documents corrected after the long runs |
| `models-comparison/` | reviewed | `0ea5f07` | none |
| `effective-conductivity/` | reviewed | `6eb9adf` | F1: the Culham and Yovanovich shortfall above Biot 60 is not closed |
| `outline/` | reviewed | `0ea5f07` | edge loss on grid lines: corrected in the program |
| `stackup/` | reviewed | `0ea5f07` | none |
| `block-and-fins/` | reviewed | `a9c1cd1` | fin ratio on the sides: corrected in the program; a block beyond the outline pinned to the ambient: corrected in the program (`fix/block-beyond-outline`) |
| `component-heatsink/` | reviewed | `1674d52` | top-path loop: corrected in the program |
| `power-calculator/` | reviewed | `6eb9adf` | none; the band does not hold the true power for a drawing error (D4) |
| `via-fill/` | reviewed | `6eb9adf` | open: the point via does not converge with the cell (A5); the 3D solid clips a via larger than its cell; the tooltip says "finished hole" while the model uses the drill; Lumped and Analytic overstate vias (A6) |
| `theory/` | reviewed | `3e90a7f` | open: `Heater.top_resistance()` uses `theta`, `analysis.part_split` uses `junction_theta()` |
| `gerber-import/` | reviewed | `a6f822b` | none in the program (no model involved) |
| `gerber-models/` | reviewed | `a6f822b` | open: zones combined by the maximum per cell (-8.2 % FVM, -19.1 % FDM on abutting strips); two laminate nodes 5.5 to 13.6 % cool on patterned copper (A11); the laminate of a one-layer board in the 3D solid is corrected |
| `gerber-nets/` | reviewed | not applicable (no electrical code in `pcbthermal/`) | none in the program; limits: return current in the ground net, resistivity, plated outer copper |

Program defects found by a review are never corrected from a research branch: they are items of `docs/versions.md` ("Planned") or are marked "corrected in the program" above.

## Decisions left to the maintainer

Row 4 of `ROADMAP.md` section 1; the recommendation to start from is after each.

* gerber-nets: the ground return current (not yet; list it as a limit); the copper resistivity (1.72e-8 ohm m with 0.393 %/K, editable); whether the rho(T) loop reuses `api._solve_with_tc` (reuse, evaluated on the hottest track cell, iterated to convergence).
* gerber-models: the default mapping of an import (flow-based faces for patterned copper, the fill as the fast fallback); a `fix/` branch for the union of zones per sample point; refine the laminate nodes (investigate first, A11); the 42-window studies on the program's network.
* via-fill: the point via (A5), the label of the via diameter (drill), Lumped and Analytic overstating vias (A6), the 3D clip of a large via.
* block-and-fins: the 4 mm threshold of the fin warning or a channel correlation (C3).
* gerber-import: the reader accepting LM/LR/LS and aperture blocks (E10).
* the other folders: the items in each folder's `INTEGRATION.md` and in `docs/versions.md` ("Planned").
