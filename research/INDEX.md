# Index of the investigations (by area of the program)

This file is kept apart from `research/README.md` (which the Gerber branch keeps editing) and will be merged into it later. One folder per investigation, named after the question, with the same layout everywhere: the root holds what is read (`README.md` with the results in numbered sections, `LOG.md` with what was read and how and what was not verified, and `IMPLEMENTED.md` when the work is in the program or `INTEGRATION.md` and `docs/` when it is open), `figures/` the pictures and `scripts/` all the Python (`lib/` only for shared code). Run a script from the repository root, for example `.venv/bin/python research/via-fill/scripts/study_via_fill.py`.

| Area | Folder | Status | Question |
| :-- | :-- | :-- | :-- |
| Import | `gerbers/` | open, **lives on the branch `research/gerbers`** (not in `develop`) | How to turn Gerber copper into grid conductances. |
| Parts | `component-heatsink/` | implemented in part (2.3.0, 2.4.0); junction node and heatsink scenarios open | The part, its top path, interfaces, heatsinks and the metal block. |
| Tools | `power-calculator/` | implemented (2.4.0) | The watts of a part from a measured temperature: validation, sensitivity, how to reduce the error. |
| Models | `models-comparison/` | implemented (repeated at each change) | The five models against the FVM on 19 scenarios, the grids, the solvers and the time results. |
| Models | `solid3d-verification/` | implemented (2.3.0, 2.4.0) | Does the 3D solid reproduce an exact solution; how far are the layered models from a 3D solution. |
| Models | `block-and-fins/` | implemented (2.3.0, 2.4.0) | Metal block and fins: the fin formula, and the block in the Lumped and Analytic models. |
| Board | `outline/` | implemented (2.4.0) | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| Board | `via-fill/` | implemented (2.4.0) | What fills a via barrel and how much it matters. |

Everything in `research/` that is ours (documents, scripts, figures) is MIT like the rest of the repository (see the README of the project). Third-party boards used to validate studies are downloaded by a script into the folder's git-ignored `data/` and are never committed; each folder's README states their licences.
