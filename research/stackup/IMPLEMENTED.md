# Stack-up: what entered the program

Released in **2.4.0** (2026-10-22).

| What | Where |
| :-- | :-- |
| `Board.dielectrics` (None = simple stack-up) and the four helpers every model reads (copper per layer, gap thickness, gap conductivities, density and specific heat) | `pcbthermal/model.py` |
| Advanced stack-up in FVM, FDM, 3D solid, Lumped and Analytic; `combine_sheets` for gaps made of several sheets | `pcbthermal/fvm.py`, `fdm.py`, `solid3d.py`, `lumped.py`, `analytic.py`, `model.py` |
| Typical stack-up templates (2 to 8 layers, loaded when the layer count changes) | `pcbthermal/data/stackups.json`, `pcbthermal/defaults.py` (`stackup_file`) |
| Dielectric presets (library `dielectrics`, editable in Preferences) | `pcbthermal/data/defaults.json`, `model.DIELECTRICS` |
| Stack-up tab (cross-section, simple and advanced modes) | `pcbthermal/gui/stackup.py` |
| Tests | `tests/test_stackup.py` (exact series circuit, trends in the five models) |
| Project documents | `docs/validation.md` sections 12 and 14, `docs/models.md`, `docs/theory.md`, `CHANGELOG.md`, `docs/versions.md`, `pcbthermal/help/index.html` |

Not implemented: blind and buried vias, sequential lamination, heavy-copper and metal-core fabricator tables.
