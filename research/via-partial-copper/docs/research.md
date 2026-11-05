# Text for the project documents (to adopt later; nothing here is in `docs/` yet)

## For `docs/research.md` (summary while the work is open)

**Via on a plane with copper over part of its footprint.** The mean-potential via (`viawell.py`) draws from each footprint cell a flux equal to its fixed weight times the difference of the plane means. On a plane whose copper covers only part of the footprint the bare cells cannot supply it and fall below the barrel temperature (the FVM cold spot of 8 K at 0.5 mm and 14 K at 0.25 mm on the board of `theory.md` 2.2, reproduced to the digit). The via effect is misread in both directions: against a 3D solid that has converged (1/16 and 1/20 mm agree to 0.2 % on a copper edge) the FVM reads it 31 to 47 % low on a copper edge through the via and 45 to 68 % low on a track ending at the via, and 3 to 4 times high for a via just off a copper edge at a cell of 0.5 mm or coarser. The earlier statement that it is "exaggerated 2.5 to 4 times" compared with a 3D solid at 0.5 mm that had not converged and is withdrawn. Antipads (clearances) are not a cause (no cold spot, 0.1 to 0.7 K of 44 to 64 K from sub-cell resolution). Corrections measured on a copy: weights by sheet conductance per layer (cold spot removed, copper-edge error -37 % to +5 %, zero shift on the 17 frozen boards) and a star coupling (an M-matrix by construction, moves every via board by up to 0.7 K). Proposed: a text-only warning for 2.5.0, the weights fix after the edge image and a check on the imported windows. Evidence: `research/via-partial-copper`.

## For `docs/theory.md` 2.2 (replacement of the limit paragraph, when B or C is adopted; until then the existing text stays with one correction)

Correction now: delete "on that board the via cools the part by 7.7 K (FVM, 0.25 mm) where the 3D solid gives 2.9 K (0.5 mm)" or add "the 3D solid had not converged there (0.70, 2.86, 7.20, 10.74 K at 1, 0.5, 0.25, 0.125 mm); the FVM reads the via effect low against the converged 3D solid on 10 mm boards, so the dip is a defect of the field, not an overstated via".

## For `docs/versions.md` ('Planned'), replacement of the item "Via footprint weights on a plane with copper only under part of the footprint"

* **Via on a plane with copper over part of its footprint** (after the investigation `research/via-partial-copper`): the live warning first (2.5.0: a footprint whose sheet conductance varies by more than a factor of two; 0 false alarms on the frozen boards), then weights by sheet conductance per layer (`fix/via-partial-copper`, after `feature/via-edge-image`; bit-identical where the footprint is uniform; validate on the imported windows) or the star coupling (an M-matrix, a model change that moves every via board by up to 0.7 K). The statement "exaggerates the via effect 2.5 to 4 times" is not supported and is removed.

## Warning text (proposal A)

"N vias have copper over only part of their footprint (a copper edge, a track end or a clearance within about one cell). The via effect may be misread, either too weak or too strong, and the FVM can show a local dip in the temperature. Refine the cell, or draw a pad around the via."
