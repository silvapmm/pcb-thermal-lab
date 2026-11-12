# Integration: via well sheet order

## Recommendation: KEEP (do not change the order); document it and pin it

Reading the sheet after the laminate rule moves the hottest rise by +0.002 to +0.036 K (0.004 to 0.044 % of the rise; up to 2.8 % of the via effect on a 2-layer hatched board at 1 mm)
in the FVM, 3 to 6 times less in the FDM, 0 on interior vias, and is never closer to the resolved 3D reference on full copper (equal or worse by 0.0 to 0.35 points of E, at most 0.005 K).
Changing it would move one frozen hottest-temperature value of the harness (`example_cut_to_T` 2 mm, +0.00088 K) and the via-board records near an edge, for no gain.

## Sentence for `docs/theory.md` 2.6 (after the Peaceman well)

"`S_l` is the sheet of the copper node before the laminate rule of 1.4 moves the laminate of the interior nodes out of it (only in the cells the rule flags: 0.5 to
1.3 % of the sheet on full 35 um copper, 2.7 to 6.2 % at fill 0.2). Reading the reduced sheet instead makes the well softer and the hottest rise higher by at most 0.04 K; against a
resolved 3D barrel the order used is equal or closer by at most 0.005 K, so it is kept (`research/via-well-sheet-order`)."
(Review: the first text justified the order by the laminate 'belonging to the well'; the interior laminate nodes still reach the wells through the copper nodes, so that argument is not
established, and the sentence rests on the measurement.)
Also replace the comment at `fdm.py` ~193 "as in the FVM" by "the same convention as the FVM (theory 2.6)".

## Test that pins the convention (to enter `tests/`, e.g. `tests/test_via_well_sheet_order.py`)

`research/via-well-sheet-order/tests/test_order_pin.py`: a spy on `viawell.build` shows the sheet handed to the wells is at least the node's and larger (> 0.5 %) in the edge band;
and the other order is bounded (< 0.05 K and 0.1 % of the rise, FVM and FDM). The first half is the one to adopt (it fails if someone reorders the calls); the second needs
`order_patch.py` and may stay in the research folder.

## If the maintainer prefers the other order

Move the `viawell.build` call after `_add_ladder` in `fvm.py` (the arrays S[:L] are then the reduced ones; `gz_via` is read by the Lumped, unchanged) and the call after `laminate.build` in
`fdm.py` with `S[:L]` of the rule; refreeze the via records near an edge (hottest rise +0.001 to +0.036 K), re-run `research/via-edge-image` and `via-contact-geometry` numbers that use edge boards.

## Not verified

See the README, last section: hatched boards have no usable reference; imported copper, Lumped, Analytic and the transient records were not run.
