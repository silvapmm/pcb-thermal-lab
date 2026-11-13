> Tester report kept as a release record: bisect of the 11 stale-expectation failures of candidate 06cb04d6 (detached worktree at 4d98d71b).

# Battery 2.7.0 failures (candidate 06cb04d6, re-checked on develop 4d98d71b)

Bisect by probing the numbers at every first-parent merge since v2.6.0 (not by git bisect run; one probe is a few seconds).
All stale expectations, no physics defect found. Two items cause everything:

1. fix/simple-stackup-physical-layers (merge 35f242aa; simple stack-up with 3+ copper layers takes the physical slabs; boards with 4 layers, e.g. the example board):
   example FVM 2 mm 85.203472 -> 85.293805 (+0.0903 K), FDM 2 mm 84.453212 -> 84.528388 (+0.0752), Lumped no-via 0.5/1.0 mm 94.693179/96.510345 -> 94.841459/96.660887,
   Analytic (insulated) 0.5/1.0 mm 94.714973/94.558017 -> 94.856398/94.698697; 2-layer boards (heatsink case) unchanged.
2. fix/drawn-layers-edge-film-centroid (merge b24c43fc): centroid film for drawn layers on outline boards (documented first-order hot error, up to +1.5 %).

Failures (candidate): cause / item / kind / new number
- test_inspector_sections ...change_the_result_sensibly: example FVM 2 mm base now 85.293805 (was 85.20 +-0.05) / item 1 / stale / rebaseline 85.29.
- test_part_across_outline ...unchanged[fvm], [fdm]: FVM 85.20347171898253 -> 85.29380457046574, FDM 84.45321208048577 -> 84.52838812731213 / item 1 / stale (solid3d unchanged).
- test_results_views byte_identical (the 'field' hash): changes exactly at 35f242aa (example field moved) / item 1 / stale: new 'field' sha a32414ed17a349d01fa6453f2f972c4aef94036b0a670ca270eefdbc1e3cadf4 (was 489e1bd3...).
- test_via_constriction boards_without_vias: new values (t_max, t_mean): lumped 0.5 (94.84145917899876, 50.40807990502485); lumped 1.0 (96.66088737731312, 50.400228636199266);
  analytic 0.5 (94.85639828629249, 50.84230763456435); analytic 1.0 (94.69869707407254, 50.84230891300549); the heatsink 2-layer rows are unchanged / item 1 / stale. Not the lone-via grouping (no vias on that board).
- test_outline time constant x4: fvm.board_time_constant vs closed form is now +0.70 % (disc 1 mm), +0.34 % (disc 0.5), +0.78 % (ellipse), +0.76 % (turned square); test bound rel 3e-3 / item 2 /
  stale: the time constant moved (disc 1 mm 76.65 -> 77.08 s) at b24c43fc, which did not touch the test; it is the accepted centroid-film error, not a time-simulation break. Rebaseline: rel=1e-2 (measured max 0.78 %) with that written reason.
- test_via_barrel_and_rim frozen_example_board_shift (FDM shift 0.1356 vs 0.146 +-0.005) and [sor] (350.4109727800 vs ...7789 +-1e-9): both PASS on the tip 4d98d71b (re-baselined in 6e66ae05, after the candidate). Item 1 explained the FDM shift.

Not in the battery but found in the research tests (tip 4d98d71b):
- research/strong-edge-laminate test_review_the_simple_stackup_slabs_are_the_residual: simple/ref-1 is now -0.35 % (asserts < -4 %): item 1 removed the residual it documents; stale, restate.
- research/cut-cell-links test_review::test_sliver_anomaly_against_independent_reference: jump of the program's hottest point between covers 0.01 and 0.02 is 0.591 K (bound 0.5 K); passes at b24c43fc^1, fails from b24c43fc (item 2). Bound is stale, but it is a measurable side effect of the centroid film on a 2-layer sliver: reviewer should decide (restate bound 0.6 or accept).

Runs on 4d98d71b, one at a time: tests/regression PCBT_FROZEN_CELLS=2,1,0.5 with the 3 pending files: 317 passed (129.7 s). test_format_compat_245 (PCBT_COMPAT_V245=1): 5 passed. test_no_secrets (PCBT_SCAN_KEY_VALUES=1): 4 passed.
Research tests: analytic-edge-and-transient 9, laminate-slabs-and-local-rule 7, lumped-zones-adoption 20, lumped-via-groups 16, fast-wave-oscillation 13, imported-copper-edge-film 5+1 skipped, via-well-sheet-order 2, imported-via-rim 2,
small-model-defects 9, laminate-edge-band 7, via-edge-image 7 passed; cut-cell-links 1 failed 29 passed; strong-edge-laminate 1 failed 5 passed; fdm-inset-edge (no such folder), models-comparison and stackup (no tests dir): not run.
Whole battery not re-run on the tip.
