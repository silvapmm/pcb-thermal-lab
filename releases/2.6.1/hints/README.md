# Shorter hints (2.6.1)

Branch `fix/shorter-hints-261`, from `develop`. The maintainer asked for every tooltip of the application to be as short as possible while keeping what the control means, its unit, a typical range or source, and what it is used for (`CLAUDE.md`, "Before every commit", item 4). Kept on purpose: destructive or undoable effects (Load typical stack-up, Delete row, Switching to a source clears the component fields), the keys of commands, and the reasons of greyed controls (the `Greyed:` suffixes, shortened but kept). Not touched: the warnings of the checks and their tooltips, the full text of elided labels (their tooltip is the text itself), Matplotlib's own toolbar hints, and the descriptions of the re-import dialog (shown as text under each choice).

No hint was removed: every control that had a tooltip before has one after (`missing_after` is empty), and `tests/test_tooltips.py` passes.

## How it was measured

`scripts/collect_hints.py collect <out.json>` opens, offscreen, the main window (empty and with the block example board), every inspector form, the advanced stack-up, the Power profile page in its three profile kinds, the Results tabs after a run, the Display panel, the Power Calculator, Preferences, the New board, Background image and Export package dialogs and the three steps of the Gerber import window, and records the tooltip of every widget and menu action. It was run on `develop` (6bdef422) and on the branch; `scripts/collect_hints.py compare before.json after.json` gives the numbers below. Lengths are in characters, over the distinct texts (a hint shown by several controls counts once).

| | Before | After |
| :-- | --: | --: |
| Controls with a tooltip (all contexts) | 1707 | 1707 |
| Distinct hints | 338 | 336 |
| Mean length | 131 | 79 |
| Median length | 84 | 66 |
| Longest | 928 | 331 |
| Longer than 200 characters | 62 | 11 |
| Longer than 100 characters | 142 | 83 |
| All hints together | 44 385 | 26 578 |

248 distinct hints changed; 90 were already short and stay as they were. Two pairs of hints became one each (the Width and Height of a rectangle had a form label hint with the unit and a field hint without it; both now say "mm").

## The 20 largest cuts

One row per hint (its greyed and JSON-key variants count once).

| # | Where | Control | Before | After | Cut |
| --: | :-- | :-- | --: | --: | --: |
| 1 | Stack-up | Inner copper (0.5 oz / 1 oz) | 928 | 252 | 676 |
| 2 | Simulation | Laminate sub-gaps (with the greyed reason) | 868 | 290 | 578 |
| 3 | Board, Environment | Vertical natural convection | 787 | 243 | 544 |
| 4 | Simulation | 3D solid model | 691 | 204 | 487 |
| 5 | Preferences, Project package | Largest package (MB) | 672 | 197 | 475 |
| 6 | Import window, step 2 | Exposed pad or tab | 560 | 176 | 384 |
| 7 | Board, Environment | Orientation | 487 | 146 | 341 |
| 8 | Heatsink (metal block) | Interface material | 436 | 171 | 265 |
| 9 | Heatsink | Cooling model | 400 | 140 | 260 |
| 10 | Preferences, Solver | Memory limit | 581 | 331 | 250 |
| 11 | Power Calculator | Board description | 357 | 125 | 232 |
| 12 | Heater (component) | θ junction-pad | 433 | 210 | 223 |
| 13 | Heater (component) | Power coefficient | 363 | 141 | 222 |
| 14 | Results | Equiv. rect. | 402 | 187 | 215 |
| 15 | Import window, step 2 | Parts table | 369 | 154 | 215 |
| 16 | Simulation | Laminate sub-gap (with the greyed reason) | 494 | 291 | 203 |
| 17 | Simulation | Thermal network (LPTN) model | 337 | 136 | 201 |
| 18 | Power profile | Oscillation threshold | 350 | 150 | 200 |
| 19 | Via | Fill | 348 | 148 | 200 |
| 20 | Power profile | Decision table | 331 | 135 | 196 |

## What was left out of the hints, and where it still is

The shortened hints dropped measured examples and background that the user guide (`pcbthermal/help/index.html`) and `docs/` already hold: the island-board errors of the laminate sub-gaps, the board thicknesses of the 1 oz inner copper, the Churchill and Chu comparison numbers, the 74 test cases of the metal block in the reduced models, the size of a real package, and the cell rule of the zonal Lumped model. The longest hint left (memory limit, 331 characters with its JSON key and the detected memory) keeps the environment variable for containers.

## Tests kept consistent

The strings that tests look for were kept: the prefixes the stress and inspector tests search (`X of`, `Width of`, `Heatsink resistance`, `Extra heat transfer`, `Resistance from a heatsink on top`, `Junction-to-case`, `Resistance per area of the interface between the package top`, `Maximum junction temperature`, `Height of the plate fins`, `Thickness of one fin`, `Distance between the axes`, `Area of the package top`, `Estimate θJC(top)`, `Conductivity of the fill`), `Greyed`, `metal block`, `Results tab`, `Gerber`, `held in memory`, `64 to 4096`, `0.01 to 2 MB`, `twice`, `not saved in project files`, `Off by default`, `Help us test your CAD tool` and `Markers:`. No test was changed.
