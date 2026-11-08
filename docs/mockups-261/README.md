# GUI mock-ups approved for 2.6.1

These pictures are **mock-ups** made from the real Qt widgets, drawn offscreen, to
decide the look of the boxes and of the warnings. They are **not the implementation**:
nothing here is in the program yet. The maintainer approved them (2026-11-08) for
implementation in 2.6.1 (`docs/versions.md`, 'Planned: 2.6.1', items 6 to 9).
Every picture exists in a `_light` and a `_dark` version.

## Images

| Files | What they show |
| :-- | :-- |
| `round2_A2_allcollapsed_*` | Accordion of warnings (A2), every topic collapsed: one line per warning with its title and severity. |
| `round2_A2_oneopen_*` | The same list with one topic opened (its text under the title). |
| `round2_A2_allopen_*` | The same list with every topic open. |
| `round3_summary_B2_warnings_box_*` | The Results Summary with its warnings in a 'Warnings (N)' box (B2), collapsed topics inside. |
| `round3_summary_B2_one_topic_open_*` | The same box with one topic open. |
| `round4_properties_heater_*` | Properties of a heater as boxes: Heater (name, layer, type), Power, Interface under the part, Heatsink on top, Junction, Position and size. |
| `round4_simulation_dock_warnings_box_*` | Simulation settings: Models, Settings and Warnings (N) boxes; the opened warning has a 'Select heater U1' button. Run, progress and status stay outside the boxes at the top. |
| `round4_full_window_*` | The whole window with the new boxes. |

## Decisions

* **A2**: the warnings are an accordion, listed collapsed at the start, inside a **B2** box titled 'Warnings (N)'.
* **B2 without arrow**: a group box whose title row is the button (bold, hover, pointing hand, accent underline when open, dashed line and '...' when collapsed).
* **The same style for every box** of Board settings (Size, Board outline, Environment), Simulation settings (Models, Settings, Warnings (N)), Properties (every box collapsible) and the warnings of the Results Summary.
* In the opened warning of the Simulation dock a **'Select heater U1' button** replaces the click on the list.
* **The on-screen text report** drops the `WARNING:` lines when the box is used and ends with the line `(N warnings: see the Warnings list above; the saved report keeps them.)`. The saved report keeps all of them.
* State (open or collapsed) is kept in `QSettings`, by key per dock and section.
* **Layer keys** (separate item): L / Shift+L step through the layers, 0 shows all, 1..N select a layer.

## Findings for the implementation

* The checks return plain strings. A `(title, severity, text)` record touches about 40 call sites (6 to 8 h); a classifier on the first words takes about 2 h and is brittle.
* The real widget must wrap the group box: `BoardPanel._show_modes` hides the group box.
* The Properties form is rebuilt on every edit, so the section state is kept by key, not by widget.
* The footer of the Simulation dock moves above the scroll area.
* Settings could split into Cell, Solvers and Laminate.
* Estimate: about 2 working days.
* Not verified on macOS (the mock-ups are offscreen).
