# Metal block and fins: what entered the program

Released in **2.3.0** (the block in FVM, FDM and 3D solid) and **2.4.0** (the block in Lumped and Analytic, steady state; fin validation).

| What | Where |
| :-- | :-- |
| Heatsink with `thickness > 0` as a heat spreader: an extra node layer in FVM and FDM, real slab in the 3D solid; heat enters only where the block overlaps copper | `pcbthermal/blocks.py`, `fvm.py`, `fdm.py`, `solid3d.py` |
| Fins as an area gain and an efficiency: `blocks.fin_ratio` | `pcbthermal/blocks.py` |
| Lumped: the block as one more layer of the ring network | `pcbthermal/lumped.py` |
| Analytic: a graph of tiles condensed by the Schur complement into the Green-function correction | `pcbthermal/analytic.py` (`_block_tiles`) |
| No time simulation with a block in these two models (`blocks.require_no_blocks`, `require_rectangle`; `api._run_profiles` excludes them with a warning) | `pcbthermal/blocks.py`, `pcbthermal/api.py` |
| Fields for the block (box *Metal block*, fins) | `pcbthermal/gui/panels.py` |
| Tests | `tests/test_block_models.py`, `tests/test_fin_model.py`, `tests/test_heatsink_part.py` |
| Project documents | `docs/validation.md` sections 12 D, 15, 17; `docs/models.md`; `docs/theory.md`; `CHANGELOG.md`; `docs/versions.md`; `pcbthermal/help/index.html` |

Not implemented: the channel effect between fins; a time simulation with a block in Lumped and Analytic.
