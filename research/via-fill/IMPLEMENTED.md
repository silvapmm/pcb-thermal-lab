# Via fill: what entered the program

Released in **2.4.0**.

| What | Where |
| :-- | :-- |
| `Via.fill_k` (conductivity of the fill, W/mK) and `Via.fill` (name), `Via.thermal_area(plating, k_cu)` | `pcbthermal/model.py` |
| The list of fills (open, epoxy resin 0.3, conductive paste 8, copper 385): library `via_fills`, editable in Preferences | `pcbthermal/data/defaults.json`, `model.VIA_FILLS` |
| JSON keys `fill`, `fill_k_w_per_mk` of a via | `pcbthermal/model.py` (read and write) |
| The via's *Fill* list and *Fill conductivity* field | `pcbthermal/gui/panels.py` |
| The same barrel area in every model (FVM, FDM, 3D solid, Lumped, Analytic) | the models read `Via.thermal_area` |
| Tests | `tests/test_via_fill.py` |
| Project documents | `docs/validation.md` section 18 (summary and numbers), `docs/models.md`, `CHANGELOG.md`, `docs/versions.md`, `pcbthermal/help/index.html` |

Not implemented: the plated cap over a capped via, the solder resistance of a via-in-pad.
