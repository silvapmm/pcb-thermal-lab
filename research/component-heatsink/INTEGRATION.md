# The part and its heatsinks: what entered the program and what is open

## Implemented (2.3.0 and 2.4.0)

| What | Where |
| :-- | :-- |
| θ junction-pad (worst case: all the power enters the board), `Tj = T_board,max + P·θ`; the junction limit with margin and power limit; `ψJB` ring estimate; power temperature coefficient (`power_tc`, fixed-point loop, runaway detection) | `pcbthermal/model.py` (`Heater`), `pcbthermal/analysis.py`, `pcbthermal/api.py` (`_solve_with_tc`) |
| Package families (typical θ, θJC(top), Tj max; library `package_theta`) | `pcbthermal/data/defaults.json`, `model.PACKAGE_THETA` |
| The top path: θJC(top) + interface/contact area + θSA in parallel with θ, solved as a fixed-point loop around any model (`analysis.part_split`); steady state only | `pcbthermal/analysis.py`, `pcbthermal/api.py` |
| The interface as one dielectric sheet (`pad_thickness`, `pad_k`), the interface under a pure heat source (`base_interface*`), presets (library `interfaces`) | `pcbthermal/model.py` |
| Heater type: heat source or component; typical heatsinks (library `heatsinks`, heatsink and air flow) | `pcbthermal/gui/panels.py`, `pcbthermal/data/defaults.json` |
| The metal block under the board (see `../block-and-fins/`) | `pcbthermal/blocks.py` |
| Tests | `tests/test_component.py`, `tests/test_heatsink_part.py`, `tests/test_gui_stress.py` |
| Project documents | `docs/validation.md` section 9, `docs/models.md`, `docs/theory.md`, `docs/versions.md`, `CHANGELOG.md`, `pcbthermal/help/index.html` |

## Open (in `docs/roadmap.md`)

* **Junction node (JESD15-3 two-resistor)**: only worth it with a heatsink on top (this folder: 3 K without, a factor of two with).
* **Heatsink scenarios**: θSA scaled with the temperature rise from a reference rise, an "other speed (estimated)" factor, the flow linked to the board air speed, heatsinks with a fan, a heatsink from its geometry with the channel effect, comparison with catalogue curves. `heatsink_convection_study.py` is the first look at the scaling and the forced factors.
* **Foster chain / heat capacity of the junction and the heatsink** for transient work with a part.
* **Top path in the time simulation** (steady state only today).
* **A heatsink larger than its contact** and a plate layer on top of a package (`NOTES.md` R3 and R8).
