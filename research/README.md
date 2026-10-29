# research/

Studies that are not part of the program, one folder per investigation, named after the question. Nothing here changes `pcbthermal/`; a study imports the program, measures, and proposes. The rules are in `CLAUDE.md`, "Research branches".

| Folder | Status | Question |
| :-- | :-- | :-- |
| [`gerber-import/`](gerber-import/README.md) | open | Reading Gerber and Excellon files: an independent NumPy-only reader, holes, pads, nets, the outline, other readers pixel by pixel. Holds the map of the sections of the three Gerber folders. |
| [`gerber-models/`](gerber-models/README.md) | open | The copper in the five models: mapping fine copper to grid conductances, the import into the FVM, corrections found in the program. |
| [`gerber-nets/`](gerber-nets/README.md) | open, early | Nets with voltage and current: Joule heat, tracks at any angle, sources, sinks, electro-thermal feedback. |
| [`component-heatsink/`](component-heatsink/README.md) | implemented in part; junction node and heatsink scenarios open | The part, its top path, interfaces, heatsinks and the metal block. |
| [`power-calculator/`](power-calculator/README.md) | implemented | The watts of a part from a measured temperature: validation, sensitivity, error. |
| [`effective-conductivity/`](effective-conductivity/README.md) | closed; proposals adopted | Published laminate and spreading cases reproduced with an independent 3D solver; where one node through the thickness stops being valid. |
| [`theory/`](theory/README.md) | open | The explained theory: one topic file per model, equation or planned method, with a picture and a bibliography. |
| [`models-comparison/`](models-comparison/README.md) | implemented, repeated at each change | The five models against the FVM on 19 scenarios, grids, solvers and time. |
| [`solid3d-verification/`](solid3d-verification/README.md) | implemented | Does the 3D solid reproduce an exact solution; how far are the layered models from it. |
| [`block-and-fins/`](block-and-fins/README.md) | implemented | Metal block and fins: the fin formula, the block in the Lumped and Analytic models. |
| [`outline/`](outline/README.md) | implemented | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| [`stackup/`](stackup/README.md) | implemented | The advanced stack-up in the five models, its sensitivity, the typical templates against fabricators. |
| [`via-fill/`](via-fill/README.md) | implemented | What fills a via barrel and how much it matters. |
| [`fin-channel/`](fin-channel/README.md) | open, reviewed | The channel effect between close fins of the finned block: Elenbaas and composite correlations read and reproduced, measured fin arrays, the program's block with the channel coefficient, a rule for the warning and a correction. |
| [`fin-channel-sources/`](fin-channel-sources/README.md) | open | The sources `fin-channel` could not open: Elenbaas and Bar-Cohen and Rohsenow through the papers that print them, the array of Bar-Cohen, Iyengar and Kraus reproduced, Ostrach's table, measured arrays on a horizontal base. |
| [`zone-union/`](zone-union/README.md) | open, reviewed | How the zones of one copper layer are combined into the copper of a cell: what the CAD tools mean, which rule is right, the five models against an independent solver, sampling, cost, edge cases. |

* [`ROADMAP.md`](ROADMAP.md): what is left to finish, in the order recommended, and the pool of open questions to investigate.
* [`REVIEW.md`](REVIEW.md): the register of what the independent reviewer checked in each folder.

**How a folder is laid out** (the same everywhere; rules in `CLAUDE.md`, "Research branches"):

* The root holds `README.md` (numbered results; a chapter `N. Review` by the reviewer; last section: what was read and what was not verified) and `INTEGRATION.md` when the work is not yet in the program.
* `figures/` (`fig_NN_topic.png`, committed), `docs/` (text for the project documents), `scripts/` (all the executable Python), `lib/` (shared code, only when needed), `tests/`.

**Figures.** Data figures (`scripts/make_figures.py`) and diagrams (`scripts/make_diagrams.py`, shapes in `diagram_kit.py`) share one numbering per folder and are linked from the README. Check them with `.venv/bin/python research/check_figures.py`; the rules are in `CLAUDE.md` and in the docstring of that script.

**Licences.** Everything of ours here is MIT. The Gerber figures render our own boards or the MIT Stormduino board; the details are in section 9 of `gerber-import/README.md`.
