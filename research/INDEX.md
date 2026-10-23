# Index of the investigations (by area of the program)

This file is kept apart from `research/README.md` (which the Gerber branch keeps editing) and will be merged into it later. One folder per investigation, named after the question; every folder has a `README.md` (results in numbered sections), `LOG.md` (what was read and how, what was not verified), figures in `figures/` and, when the work is in the program, `IMPLEMENTED.md`; open work has `INTEGRATION.md` and `docs/` instead.

| Area | Folder | Status | Question |
| :-- | :-- | :-- | :-- |
| Import | `gerbers/` | open | How to turn Gerber copper into grid conductances. |
| Models | `block-and-fins/` | implemented (2.3.0, 2.4.0) | Metal block and fins: the fin formula, and the block in the Lumped and Analytic models. |
| Board | `outline/` | implemented (2.4.0) | Which rectangle for the Lumped and Analytic models on a board with an outline. |
| Board | `via-fill/` | implemented (2.4.0) | What fills a via barrel and how much it matters. |

Third-party boards used to validate studies are downloaded by a script into the folder's git-ignored `data/` and are never committed; each folder's README states their licences.
