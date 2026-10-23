# Index of the investigations (by area of the program)

This file is the index; `research/README.md` holds the layout rules, the rules for figures and the licence notes of the pictures. One folder per investigation, named after the question, with the same layout everywhere: the root holds what is read (`README.md` with the numbered results, `INTEGRATION.md` or `IMPLEMENTED.md`, `LOG.md`), plus `figures/`, `docs/`, `tests/`, `scripts/` (all the executable Python) and `lib/` (shared code, only when needed).

| Area | Folder | Status | Question |
| :-- | :-- | :-- | :-- |
| Import 1 | `gerber-import/` | open (start with `gerber-import/CONCLUSIONS.md`) | What can be taken from Gerber and Excellon files: an independent NumPy-only reader, holes, pads, vias and nets, nets checked against a KiCad project, boards of our own as test benches. Needs no program. |
| Import 2 | `gerber-models/` | open (start with `gerber-models/CONCLUSIONS.md`) | The copper in the simulation models: mapping of fine copper to the conductances of the grid (fill fraction against flow-based faces, lambda, cell problem), the five models on real boards and on our own, the import to the program's FVM, two corrections found in the program. |
| Import 3 | `gerber-nets/` | open (start with `gerber-nets/CONCLUSIONS.md`) | Nets with voltage and current: the Joule heat of a net, tracks at any angle, sources, sinks and links between pieces of one net (design and prototype). |
| Parts | `component-heatsink/` | implemented in part (2.3.0, 2.4.0); junction node and heatsink scenarios open | The part, its top path, interfaces, heatsinks and the metal block. |
| Tools | `power-calculator/` | implemented (2.4.0) | The watts of a part from a measured temperature: validation, sensitivity, how to reduce the error. |
| Models | `models-comparison/` | implemented (repeated at each change) | The five models against the FVM on 19 scenarios, the grids, the solvers and the time results. |
| Models | `solid3d-verification/` | implemented (2.3.0, 2.4.0) | Does the 3D solid reproduce an exact solution; how far are the layered models from a 3D solution. |
| Models | `block-and-fins/` | implemented (2.3.0, 2.4.0) | Metal block and fins: the fin formula, and the block in the Lumped and Analytic models. |
| Board | `outline/` | implemented (2.4.0) | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| Board | `via-fill/` | implemented (2.4.0) | What fills a via barrel and how much it matters. |

Third-party boards used to validate studies are downloaded by a script into the folder's git-ignored `data/` and are never committed; each folder's README states their licences.
