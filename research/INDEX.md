# Index of the investigations (by area of the program)

This file is the index; `research/README.md` holds the layout rules, the rules for figures and the licence notes of the pictures. One folder per investigation, named after the question, with the same layout everywhere: the root holds what is read (`README.md` with the numbered results, `INTEGRATION.md` or `IMPLEMENTED.md`, `LOG.md`), plus `figures/`, `docs/`, `tests/`, `scripts/` (all the executable Python) and `lib/` (shared code, only when needed).

| Area | Folder | Status | Question |
| :-- | :-- | :-- | :-- |
| Import | `gerbers/` | open (start with `gerbers/CONCLUSIONS.md`) | How to turn Gerber copper into grid conductances: an independent reader without licences, the mappings compared on real boards and in all five models, nets and the heat of a net, vias, a board of our own as a test bench. |
| Parts | `component-heatsink/` | implemented in part (2.3.0, 2.4.0); junction node and heatsink scenarios open | The part, its top path, interfaces, heatsinks and the metal block. |
| Tools | `power-calculator/` | implemented (2.4.0) | The watts of a part from a measured temperature: validation, sensitivity, how to reduce the error. |
| Models | `models-comparison/` | implemented (repeated at each change) | The five models against the FVM on 19 scenarios, the grids, the solvers and the time results. |
| Models | `solid3d-verification/` | implemented (2.3.0, 2.4.0) | Does the 3D solid reproduce an exact solution; how far are the layered models from a 3D solution. |
| Models | `block-and-fins/` | implemented (2.3.0, 2.4.0) | Metal block and fins: the fin formula, and the block in the Lumped and Analytic models. |
| Board | `outline/` | implemented (2.4.0) | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| Board | `via-fill/` | implemented (2.4.0) | What fills a via barrel and how much it matters. |

Third-party boards used to validate studies are downloaded by a script into the folder's git-ignored `data/` and are never committed; each folder's README states their licences.
