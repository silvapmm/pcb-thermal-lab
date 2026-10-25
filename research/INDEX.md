# Index of the investigations (by area of the program)

This file is the index; `research/README.md` holds the layout rules, the rules for figures and the licence notes of the pictures. One folder per investigation, named after the question, with the same layout everywhere: the root holds what is read (`README.md` with the numbered results, ending with what was read and what was not verified; `INTEGRATION.md` when the work is not in the program yet), plus `figures/`, `docs/`, `tests/`, `scripts/` (all the executable Python) and `lib/` (shared code, only when needed).

**Plans and review.** What is left to finish in the research, in the order recommended, and the pool of open questions by area is [`ROADMAP.md`](ROADMAP.md) (section 1 "Next work, in the order recommended"); what the independent reviewer checked in each folder is the review register [`REVIEW.md`](REVIEW.md). What we want to implement in the program is `docs/roadmap.md`.

| Area | Folder | Status | Question |
| :-- | :-- | :-- | :-- |
| Import 1 | `gerber-import/` | open; start with `gerber-import/REPORT.md` | Reading the Gerber and Excellon files and importing the board: an independent NumPy-only reader and its conformance, holes, pads, vias, the nets written in the files checked against a KiCad project, the board outline, the comparison with other readers pixel by pixel, boards of our own as test benches. Needs no program. The map of the sections of the three Gerber folders is in `README.md`. |
| Import 2 | `gerber-models/` | open; start with `gerber-models/REPORT.md` | The copper in the simulation models: mapping of fine copper to the conductances of the grid (fill fraction against flow-based faces, lambda, cell problem), the five models on real boards and on our own, the import to the program's FVM, two corrections found in the program, diagonal faces, the laminate reference of the review. |
| Import 3 | `gerber-nets/` | open, early; start with `gerber-nets/CONCLUSIONS.md` | Nets with voltage and current: the Joule heat of a net, tracks at any angle, sources, sinks and links between pieces of one net, electro-thermal feedback (design and prototype of `Problem.electrical`). |
| Parts | `component-heatsink/` | implemented in part (2.3.0, 2.4.0); junction node and heatsink scenarios open | The part, its top path, interfaces, heatsinks and the metal block. |
| Tools | `power-calculator/` | implemented (2.4.0) | The watts of a part from a measured temperature: validation, sensitivity, how to reduce the error. |
| Theory | `effective-conductivity/` | closed; the optional proposals are adopted on `develop` (thick-plate warning, `Board.natural_form`, reference solver in the tests) | Published test cases (effective conductivity of a laminate, spreading resistance of a source on a plate) reproduced with an independent 3D solver; the five models on the same boards; where one temperature node through the thickness stops being valid; the natural convection forms; the channel correlations between vertical plates. |
| Theory | `theory/` | open | What each model, equation and planned method is: one file per topic with a picture, the formulation, limits, tests, paths to the investigations and sources; one bibliography with the reading status of every source. |
| Models | `models-comparison/` | implemented (repeated at each change) | The five models against the FVM on 19 scenarios, the grids, the solvers and the time results. |
| Models | `solid3d-verification/` | implemented (2.3.0, 2.4.0; one-layer laminate corrected after 2.4.1) | Does the 3D solid reproduce an exact solution; how far are the layered models from a 3D solution. |
| Models | `block-and-fins/` | implemented (2.3.0, 2.4.0) | Metal block and fins: the fin formula, and the block in the Lumped and Analytic models. |
| Board | `outline/` | implemented (2.4.0; time constant corrected after 2.4.1) | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| Board | `via-fill/` | implemented (2.4.0) | What fills a via barrel and how much it matters. |

Everything in `research/` that is ours (documents, scripts, figures) is MIT like the rest of the repository (see the README of the project). Third-party boards used to validate studies are downloaded by a script into the folder's git-ignored `data/` and are never committed; each folder's README states their licences.
