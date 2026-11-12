# Integration: strong cooled edge (closes Planned item 21 as a stated limit)

## Recommendation

1. **No fix to the models.** The error is a converged property of the layered idealisation where copper reaches a wall cooled above about 500 W/m2K. Measured
   candidates (README 4, 6): more sub-gaps (8 instead of the default 2) remove two thirds of the plate error but not the residual -4 to -6 % at 1000 and -8 to -10 % at
   2000 W/m2K; a wider edge band changes nothing (24.52 to 24.53 K); removing the cut-cell edge film makes it worse (-10 %). A non-air edge (a rail at a fixed
   temperature) should be modelled as a heatsink or a pin, not an `h_side` above 500 W/m2K.
2. **Change the warning text only** (`checks.check_edge_laminate`, `checks.EDGE_LAMINATE_H` stays 200). Replace the measured sentence by the numbers of this study (S1 board,
   FVM, against an independent 3D solver) and add the via clause. Proposed text (the existing 3.2 mm numbers may stay as a second sentence):

   > "Edge coefficient above 200 W/m2K: the edge laminate is under-resolved (the default cuts a gap of 0.4 to 0.8 mm into 2 sub-gaps) and the FVM and FDM read the board too
   > cool: on a 1.6 mm four-layer board at a 0.25 mm cell about -2 % of the rise at 200 W/m2K, -5 % at 500, -9 % at 1000 and -14 % at 2000 with the default, -1 %, -2.6 %, -4.9 %
   > and -8.5 % with eight sub-gaps; refining the cell or the sub-gaps does not remove the last part. The effect of a via is a small difference of two temperatures and reads
   > lower still: about 4 % low at 200 W/m2K, 15 % at 500, 25 to 35 % at 1000 and 40 to 50 % at 2000 (a quarter low at 1000 W/m2K), also for a via several millimetres from the
   > edge; the via helps more than shown. A board in air has 5 to 50 W/m2K, where the error is within 3 %."

   Numbers behind it: plate 0.25 mm default -1.8 / -4.8 / -8.9 / -14.4 %, 8 sub-gaps -1.0 / -2.6 / -4.9 / -8.5 % at 200 / 500 / 1000 / 2000; via effect 0.25 mm default
   -8.3 / -19.3 / -34.0 / -51.4 %, 8 sub-gaps -6.5 / -14.3 / -25.5 / -41.1 % (README 4, 5; against the resolved copper cylinder; against the older link reference subtract
   about 6 points). The sign of the via effect is the safe side for via design and the unsafe side for the board rise.
3. **Optional, small and measured, not recommended for 2.7.0:** a default of 4 sub-gaps for boards with an edge coefficient above 200 W/m2K. It moves the plate at 0.25 mm and
   1000 W/m2K from -8.9 % to -5.5 % and E from -34 % to -27.5 %, costs unknowns (README `laminate.py` note: 4 costs 1.0 to 2.5 times) and moves frozen numbers only for
   boards with `h_side` > 0 and two or more layers; it leaves the converged residual. The user can already do it (`laminate_n_max`, `laminate_s_max_mm`).
4. Correct the labels of the earlier notes (default = 2 sub-gaps on a 0.487 mm gap, not 4); `docs/validation.md` 28 and 36 should quote the numbers of README 4 and 5 and say
   the 2.5.x agreement was a cancellation of the plate error (+5 % at 1 mm with many sub-gaps).
5. Open (for `research/ROADMAP.md`, not the release gate): the origin of the converged -4 to -6 %; a second structurally different 3D solver (finite elements) for E.

## Impact

Documentation and warning text only; no frozen number moves; the program and its tests are untouched by this branch.
