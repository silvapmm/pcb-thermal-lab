# Outline on the Lumped and Analytic models: what entered the program

Released in **2.4.0** (2026-10-22).

| What | Where |
| :-- | :-- |
| `Problem.equivalent_rectangle()` (box and positions scaled by √(area ratio), parts keep their size) | `pcbthermal/model.py` |
| The two models run on that rectangle and the field is stretched back; the warning in the Results summary | `pcbthermal/api.py` (`RECTANGLE_ONLY`) |
| No time simulation for these two models on an outline | `pcbthermal/api.py` (`_run_profiles`, `usable`) |
| The outline in the FVM, FDM and 3D solid (cell cover) | `pcbthermal/model.py` (`Board.cover`), the three solvers |
| Outline tool, presets and vertex table in the Board panel | `pcbthermal/gui/panels.py`, `pcbthermal/gui/canvas.py` |
| Tests | `tests/test_outline.py` |
| Project documents | `docs/validation.md` section 13, `docs/models.md`, `docs/theory.md`, `CHANGELOG.md`, `docs/versions.md`, `pcbthermal/help/index.html` |

Not implemented: scaling about the area centroid of the outline (tried, no consistent gain), parts inside the cut region, holes.
