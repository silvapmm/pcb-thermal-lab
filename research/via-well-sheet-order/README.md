# Via well and the laminate rule: which sheet does the well read?

## 1. Question

`fvm.Network.__init__` calls `viawell.build(..., self.S, ...)` with the sheet conductance of the copper nodes BEFORE `_add_ladder` (`laminate.build`) moves the laminate of the
interior sub-gap nodes out of them; the plane node the via is attached to carries the REDUCED sheet. `fdm.py` does the same on purpose ("as in the FVM"). Since 2.6.0 the edge band
flags every cell near an edge, even over full copper. Is the mismatch (a) intended and right, (b) an inconsistency with a measurable effect, (c) hidden by the laminate nodes?
(Finding 3 of the independent review of 2.7.0.) The program was not edited: `lib/order_patch.py` makes the wells read the sheet after the rule, in memory, in the FVM order
(wells first, refilled in place) and in the FDM order (rule first).

## 2. Size of the mismatch (measured, `tests/test_order_pin.py`)

Ratio of the sheet the well reads to the sheet the node keeps, in the cells flagged by the rule: 1.0127 (2 layers, full copper), 1.0054 (4 layers), 1.062 (2 layers, fill 0.2),
1.027 (4 layers, fill 0.2). The review quoted 3.7 % and 15 to 20 %; on this board (35 um, 1.6 mm, four sub-gaps at most) it is 0.5 to 1.3 % and 2.7 to 6.2 %.

## 3. Effect on the program (`scripts/study_order_program.py`, 192 FVM cases, 32 FDM)

Board: 10 x 10 mm, 2 and 4 layers, fill 1 and 0.2, h_side 10 and 200 W/m2K, one via or a 2 x 2 block at d = 0.16, 0.5, 1, 3 mm from the edge, cells 1, 0.5, 0.25 mm. The
"after" order always reads HOTTER (the well is softer).

| layers | fill | max shift of the hottest rise, FVM | % of the rise | % of the via effect E | FDM max shift |
| --: | --: | --: | --: | --: | --: |
| 2 | 1 | 0.013 K | 0.025 | 0.33 | 0.003 K |
| 2 | 0.2 | 0.036 K | 0.044 | 2.8 | 0.005 K |
| 4 | 1 | 0.002 K | 0.004 | 0.07 | 0.0006 K |
| 4 | 0.2 | 0.010 K | 0.013 | 0.7 | 0.002 K |

The largest is a 2-layer hatched board at 1 mm cell; it falls with the cell (0.036, 0.021, 0.008 K at 1, 0.5, 0.25 mm). h_side 200 halves it. Interior vias (outside the band, fill 1): identical.
The effect is small because the well is a log term in a chain dominated by the barrel and the plane spreading: a 1.3 % stiffer well moves E by 0.3 %.

## 4. Against the resolved 3D reference (`lib/ref3d_via.py`, `scripts/study_order_reference.py`)

An independent 3D finite-volume solver (half board, barrel drawn at real size as an area mixture, real laminate sub-slabs, films on faces and sides, 1/16 mm, imports nothing from
the program; without the via and the film the rise agrees with the program's FVM at 0.25 mm to 0.08 %, E to 0.7 %; 1/8 against 1/16 mm: T0 changes by 0.0001 K, E by 0.2 %).
Full copper, one via, 2 and 4 layers, h_side 10 and 200, d = 0.16 to 3 mm, cells 0.5 and 0.25 mm (32 rows):

* error of the hottest rise: before and after differ by at most 0.008 K (0.01 to 0.02 % of the rise, at 0.5 mm; equal to 0.002 K at 0.25 mm). At h_side 10 both are within 0.05 % of
  the rise; at 200 both are 0.6 to 1.3 % cool (the laminate/edge residual of `laminate-edge-band`, not the well: identical in both orders).
* error of E: after is equal or worse by 0.0 to 0.35 points of E (e.g. -1.52 % to -1.67 %, -1.07 to -1.22 %); never better. At 0.25 mm the two agree within 0.06 points.

So on full copper the BEFORE order (today) is equal or marginally closer, and the difference is 0.005 K at most, far below the residual against the reference. Hatched rows
(fill 0.25 as real stripes in the 3D) are not usable: the smeared fill of the program is 58 to 64 % off the stripes for the idealisation, 100 K, 20 times anything the order does
(the order shifts them by at most 0.01 K); stated, not a finding. A hatched board therefore has NO independent reference here that can decide an effect of 0.036 K.

## 5. Frozen numbers (`scripts/study_order_frozen.py`, 17 harness boards, FVM and FDM, 2 and 1 mm)

Of 68 hottest-temperature values one moves: `example_cut_to_T` at 2 mm, FVM and FDM, +0.00088 K. Via boards without an edge film or partial copper (the example, plate vias, lone via) do not
move at all, because no cell is flagged. The records of the other quantities (via-board means, Lumped, times) were not run; they are the same quantity at the same wells.

## 6. Why the FDM reads before

The comment in `fdm.py` says only "as in the FVM": there is no independent rationale. The FDM shift is 3 to 6 times smaller than the FVM's (nodes on the edge, no film on the laminate nodes).

## 7. Reading (answer)

(a)/(c): intended and defensible, and the effect is negligible. The barrel is in contact with the whole laminate thickness of the layer (the plated wall runs through the sub-gaps), so
the heat that the laminate carries sideways into the barrel wall belongs to the well; the interior laminate nodes have no well of their own. Reading the sheet before the rule credits that
share to the well; the reduced sheet would drop it. Measured: before is equal or closer to the 3D reference, by at most 0.005 K. Not a defect of consequence.

## What was read and what was not verified

Code read: `fvm.py` 195 to 360, `fdm.py` 160 to 250, `laminate.py` build, `viawell.py` build, `docs/theory.md` 1.4 and 2.6 headings. No literature opened (none needed). The 3D reference was
checked against the program (above) and by its own energy-balance in the solver; it has no stand-alone test of a series circuit (not written). Not done: hatched boards against a resolved
reference that represents the smeared fill; 3 mm via at cell 0.25 in the FDM; imported copper; the Lumped and Analytic (no wells of this kind); times to 63 % and profile records.
The "theory" justification of section 7 is an argument, not a computed split of the laminate flux into the barrel.
