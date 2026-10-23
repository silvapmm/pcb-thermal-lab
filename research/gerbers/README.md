# research/gerbers (moved)

The Gerber research (branch `research/gerbers`) was one study until 2026-10-23, when it was split in three folders, each with its own README, conclusions, integration design, log, tests, figures and docs:

| Phase | Folder | Subject |
| :-- | :-- | :-- |
| 1 | [`../gerber-import`](../gerber-import/README.md) | Reading the files: copper, drills, nets and vias, nets checked against a KiCad project (no program needed). |
| 2 | [`../gerber-models`](../gerber-models/README.md) | The copper in the simulation models: mapping to conductances, the five models, the import to the program's FVM, two corrections found in the program. |
| 3 | [`../gerber-nets`](../gerber-nets/README.md) | Nets with voltage and current: Joule heat, links, sources and sinks. |

The section numbers (4.1 to 4.40) of the original README were kept; the README of each folder has a table with the folder of every section. This folder only keeps the git-ignored virtual environment of the research (`.venv/`, created with `python3 -m venv research/gerbers/.venv && research/gerbers/.venv/bin/pip install -r research/gerber-import/requirements.txt`); any virtual environment with the same packages works.
