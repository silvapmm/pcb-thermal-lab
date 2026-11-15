# Merge notes: feature/fem-model + feature/surface-always-both (tmp/merge-fem-surface)

Order: `git merge --no-ff feature/fem-model` (clean, tree 5570935d), then `git merge --no-ff feature/surface-always-both` (5 conflicts). Resolutions, keeping both sides:

| File | Hunk | Kept |
| :-- | :-- | :-- |
| CHANGELOG.md | Added, first entries | the FEM entry, then the surface-always entry (both bullets) |
| docs/decisions-log.md | top of Entries | the FEM branch 4 entry, blank line, then the two surface entries |
| pcbthermal/api.py | import line | the surface side (no `thickness`) plus `fem, femcore` |
| pcbthermal/api.py | `surface_report_lines` | the surface side (diff in K, patterned note); the "how" text is "resolved by the finite elements" for model fem, else the estimate text |
| pcbthermal/api.py | heater line in `report_text` | the surface side (`if "t_max_surface" in h`, no `thickness.SHOW_*` test); note = "resolved" for fem |
| pcbthermal/cli.py | `--model` help | the FEM help text (six models) plus the `--surface-files` option of the surface side |
| tests/test_help.py | guide word list | the surface list plus the FEM words 'Finite elements (FEM), comparison', 'surface read-out</b> (the face', 'pyamg', '--model fem' |

Glue (small, done in the merge commit and one follow-up commit, ~12 lines): the FEM already fills `T_surface`, `T_surface_mean`, `T_surface_flag`, `t_max_surface_top/bottom` (fem.py 259-270); `surface_report_lines`, `heater_rows` (analysis.surface_stats) and the report read them unchanged. Wording only:
- api.py: "resolved" in the surface lines, the heater lines and the read-outs header; "steady FVM, FDM and FEM" in the no-surface line.
- plots.py `plot_surface`: label and title say "resolved" for model fem.
- cli.py: the printed line says "FEM surface (resolved)".
- pcbthermal/help/index.html: "it will resolve" -> "it resolves"; "the FEM will fill" -> "the FEM fills".
- docs/models.md surface row: the FEM is a model that fills the arrays now (no "will fill ... in review").
No other 'will resolve' / 'vai resolver' in guide, models, theory, tips.

## Stale tests found by the whole battery (4 failures, all test text, no physics)
| Test | Cause | Owner | Fix |
| :-- | :-- | :-- | :-- |
| tests/test_fdm.py::test_fdm_is_selectable_through_the_api_and_runs_the_time_simulation | expected `SolverOptions(models=("fem",)).validate()` to raise; the FEM is selectable | feature/fem-model alone (fails there too) | the FEM validates; an unknown model name still raises |
| tests/test_fem_model.py::test_the_surface_and_the_column_agree_on_thin_copper_and_the_point_is_the_hottest_node | expected no surface line; the surface is always reported now | interaction of the two branches | expects two lines, "resolved by the finite elements", "+0.000 K" |
| tests/test_fem_model.py::test_a_one_layer_board_reads_the_copper_face_not_the_laminate_bottom | same | interaction | two lines, resolved, "0.000 K" |
| tests/test_single_layer.py::test_the_lists_in_each_context | Layer box of the Temperature tab now ends with 'Surface (top)', 'Surface (bottom)' | feature/surface-always-both alone (fails there too) | the expected list has the two entries |
