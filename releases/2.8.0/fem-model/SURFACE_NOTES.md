# Surface read-out: progress notes (branch fix/thick-plate-surface-estimate)

Plan: pcbthermal/thickness.py (offsets, attach for FVM/FDM from net.K couplings, Analytic from the uniform gap conductances, blocks);
SolverOptions.readout; apply_readout in api.simulate; CLI; GUI combo + Layer entries; checks text; tests; docs.
Models: FVM, FDM, Analytic get arrays; Lumped and 3D solid do not (no per-cell face flux): readout 'surface' leaves them on the column and says so.
Partial cell: mean = f*c + face_mean, peak = max(c, face_peak) (literal spec, not validated against patterned 3D).
Log below.
- thickness.py written (FVM/FDM only, thick >105um), analysis.surface_stats, api report lines; Muzychka case2 surface diff +0.57/+1.26/+1.03/+0.80 reproduced. Spec corrected by coordinator: NO readout option/CLI/combo/key; view only.
- GUI: layerchoice SURFACE_BASE 200, results_view.surface_faces + draw_surface + heater table columns, tips; report lines.
- tests/test_thickness.py + published case 2 surface test committed. Next: docs, diagram, stress scenario, compat.
- docs written (theory 1.2, models 4b.1, validation 55.6, guide, tests/test_help words, README, CHANGELOG, versions, CLAUDE.md), fig_50. Next: stress scenario, compat note, full test sets.
- stress scenario added; compat test unnecessary (no key). Waiting for broad test batch (bat3b1klj).
