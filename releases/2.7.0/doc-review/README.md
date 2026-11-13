# Documentation review of 2.7.0 (step 6b of the release gate)

Status: **not started**. Mandatory before 2.7.0 is merged into `main` (`CLAUDE.md`, 'Agents and workflow', 'A release'). The `maintainer` agent does it, with the `reviewer` for the numbers of the theory and the validation. For every line: what was checked, what was changed, what is stale and left on purpose (with the reason).

| # | Document | What to check | Checked | Changed | Stale on purpose |
| --: | :-- | :-- | :-- | :-- | :-- |
| 1 | `README.md` | features, usage, badges (version, test count), versions list, screenshots | | | |
| 2 | `pcbthermal/help/index.html` | every new control, key, menu and table of limits of 2.7.0 (boxes, Warnings accordion, layer keys, cut overlay, markers, holes, edge warnings) | | | |
| 3 | the calculator help (`pcbthermal/help/calculator.html`) | numbers and steps against the program | | | |
| 4 | `docs/images/` and `pcbthermal/help/` pictures | regenerate with `examples/make_screenshots.py` those that show a screen that changed (neutral paths asserted); LOOK at each changed picture | | | |
| 5 | `docs/versions.md` | the 2.7.0 chapter, the summary, 'Planned: 2.8.0' | | | |
| 6 | `docs/models.md` | physics and API of the changed models | | | |
| 7 | `docs/theory.md` | every changed model section (with the reviewer) | | | |
| 8 | `docs/validation.md` | sections 38 to 47 and the numbers that the 2.7.0 items moved (with the reviewer) | | | |
| 9 | `docs/calculators.md` | the numbers that the face-down law and the other items moved | | | |
| 10 | the tooltips table (`pcbthermal/gui/tips.py`) | every new control has one; the hints are short | | | |
| 11 | the keyboard list (`SHORTCUTS_HTML`) | L, Shift+L, 0 to 9, D, T, M and the others | | | |
| 12 | the About box (`pcbthermal/gui/help.py`) | version, author, licence | | | |
| 13 | `CHANGELOG.md` | the 2.7.0 section is consistent with the code and the documents | | | |
| 14 | `research/README.md` | the index and 'Which folder is current' | | | |
