# Simulation panel: which setting serves which model, and a grouped layout

Review of the Simulation dock (`pcbthermal/gui/panels.py`, class `SolverPanel`) on `development` at `6c225276`, for two requests of the maintainer:
(1) group the settings by the models they influence, with a frame around each group; (2) show the memory lines ('FVM: 1793 unknowns, about 0.2 GB of ...') in a smaller font.

Nothing in the program was changed. The layouts below were built as a throwaway prototype on `tmp/settings-layout-proto` (not for merge): first round A, B, C (commit `a1522a3d`, `PCBT_PANEL_LAYOUT=A|B|C`, sections 2 to 5); second round P1 to P8 after the maintainer's answer (commits `db90e857` and `ca481f1f`, new file `pcbthermal/gui/panel_variants.py`, `PCBT_PANEL_LAYOUT=P1..P8`, `PCBT_PANEL_SP` for the room around the Settings toggle; section 7). **Section 7 supersedes the recommendation of section 5.**

## 1. What each control of the dock really feeds

Read from the code: `SolverOptions` (`api.py` 54-68), the dispatch of the steady models (`api.py` 826-836), of the step responses (`api.py` 1028-1033) and of the time runs (`api.py` 1070-1080), the memory guard (`memory.py` 710-823), `laminate.uses_rule` and the per-control greying of `SolverPanel._update_availability` (`panels.py` 1673-1691).

| Control (option key) | FVM | FDM | Lumped | Analytic | 3D solid | FEM | Steady / time | Notes |
| :-- | :--: | :--: | :--: | :--: | :--: | :--: | :-- | :-- |
| Models checkboxes (`models`) | x | x | x | x | x | x | both | 3D solid and FEM are steady only on this tree (left out of the time run, `SKIPPABLE_MODELS`) |
| Cell size, Auto (`cell_mm`) | x | x | clipped | clipped | x | x | both | Lumped: `lumped.cell_for` clips to 0.5-1.0 mm (0.5 mm or finer when a part is zoned or small); Analytic: clipped to 0.5-1.0 mm sampling grid. Grid of FVM, FDM, 3D solid; base element of the FEM mesh |
| Memory lines (read-only) | x | x | - | - | x | x | steady | Only the guarded models (`GUARDED_MODELS`); none for Lumped and Analytic |
| FVM solver (`linear_solver`) | x | - | - | - | - | - | steady only | The FDM is direct only (`fdm.Network.solve_steady`); the FVM time run and animation factorise on their own and ignore it |
| Laminate sub-gap, sub-gaps (`laminate_s_max_mm`, `laminate_n_max`) | x | x | - | - | - | - | both | Not on a board with a metal block (`laminate.uses_rule`); the 3D solid has its own slab rule (`solid3d.py` 50), the FEM its gap elements. Also counted by the memory guard and by Auto |
| Lumped rings (`lumped_rings`) | - | - | x | - | - | - | both | Steady, step response and time run |
| Analytic modes (`analytic_modes`) | - | - | - | x | - | - | both | Steady, step response and time run |
| Local via and heatsink corrections (`analytic_local_corrections`) | - | - | - | x | - | - | steady only | The analytic step response and time run are always local (`api.py` 1033, 1080 do not pass it); forced on with a metal block (`analytic.py` 653) |
| FEM gap elements, FEM refinement (`fem_gap_elements`, `fem_refine`) | - | - | - | - | - | x | steady | Also counted by the memory guard (`fem_params`) |
| Hotspot limit (`hotspot_c`) | x | x | x | x | x | x | both | A read-out of the results (hotspot list, overlay, profile plots), not a solve input |

Settings that are elsewhere and stay there: the time-run settings and the steady power of a profile (`profile`, `steady_power`) on the Power profile page; the memory limit (`memory_fraction`) in Preferences. The dock has no SOR omega, tolerance or iteration count (they are constants of `fvm.py`).

Side observations found while reading (not fixed here, `development` is frozen for the window test):
- **Auto ignores the FEM mesh numbers.** `_auto_cell` passes `laminate_params` to `suggest_cell_mm` but not `fem_params` (`panels.py` 1795; `suggest_cell_mm` has no such argument, `api.py` 528), so with 24 gap elements Auto may propose a cell that the memory line then marks red for the FEM. Small `fix/` item, or say so in the Auto tooltip.
- **'Local via and heatsink corrections' affects the steady run only**, but its tooltip and the guide row do not say so; the time run is always local. One sentence in the tooltip and in the guide.
- The 'Greyed' tooltip of the laminate on a board with a metal block says 'used only by a board with a metal block, where the rule does not apply' (`panels.py` 1682 and 1691): the sentence reads backwards. Suggested: 'not used on a board with a metal block'.

## 2. Layout options

All three keep the option keys, the project format and the field labels (the warnings quote 'Laminate sub-gap' and 'Laminate sub-gaps', `uicontext.laminate_where`; the guide quotes the others), keep every tooltip, and keep the per-control greying with its 'Greyed: used only by ...' tooltip.

- **A. Frames per group, greyed (recommended).** Inside the Settings box, one frame (`QGroupBox`, already styled by the theme) per group: 'All models' (Cell size with Auto, the memory lines, Hotspot limit), 'Finite volume (FVM)' (FVM solver), 'Laminate (FVM, FDM)', 'Thermal network (LPTN)' (Lumped rings), 'Analytical' (modes, local corrections), 'Finite elements (FEM)' (gap elements, refinement). A frame whose models are not ticked is greyed as a whole and its title gets ': not ticked'; the laminate frame is also greyed on a board with a metal block. The label column is the same width in every frame so the fields line up. Nothing moves when a model is ticked; every setting stays visible. Cost: about 160 px taller (the panel scrolls, the Run button stays above).
- **B. Frames per group, hidden.** As A, but the frames of the models not ticked are hidden. Shortest panel, but a setting disappears from sight (the user cannot set the FEM mesh before ticking the FEM), the panel jumps at every tick, and the guide's 'greyed' rule (section 'Greyed fields') would need an exception.
- **C. Settings under each model.** The Models box lists each model with its own settings indented under its checkbox, shown only while it is ticked; the Settings box keeps only Cell size, the memory lines and Hotspot limit. Clearest link between a model and its numbers, but: the FDM checkbox moves next to the FVM (the order of the list changes), the laminate rows are shared by two models and need their own 'Shared by the FVM and the FDM' line, the labels inside lose their prefixes ('Rings', 'Modes'), and the Models box changes size at every tick. More work for the guide and the screenshots.

## 3. The memory lines

In all three prototypes:
- the label takes the theme's hint style (`theme.hint`: 11 px, colour `hint`, 5.3:1 on the light window and 6.3:1 on the dark one, already used for the small notes), about 2 px below the dock font;
- each row starts with a dot in the verdict colour (`ok`, `warn`, `bad`); a fitting model ('ok') has its text in the hint colour, so the line reads as secondary; a slow or refused model keeps the whole row in the verdict colour, as today;
- compact form: `FVM: 39052 unknowns · 0.3 of 10.3 GB` instead of `FVM: 39052 unknowns, about 0.3 GB of 10.3 GB`; 'at least' becomes '≥'. The counts keep **no thousands separator** (the rule of every count shown, checked by `tests/test_gui_stress.py`), so not '39 052'. The refusal sentence ('above the memory limit, it will not run: use a cell of ...') and the FEM pyamg sentence are kept word for word (the tests read them);
- word wrap stays on; the label is hidden when no guarded model is ticked (it left an empty strip under Cell size with only Lumped and Analytic).

## 4. Screenshots

Simulation dock at the default window width (1480 px window, dock 340 px), the example 4-layer board, light and dark themes; the whole dock (window made tall). Three cases: FVM + FEM at 1 mm; Lumped + Analytic only (the greyed groups); FVM + 3D solid + FEM at 0.3 mm (two red memory rows, before and A only).

| | Light | Dark |
| :-- | :-- | :-- |
| Before, FVM + FEM | ![](figures-panel/before_light_fvm_fem.png) | ![](figures-panel/before_dark_fvm_fem.png) |
| A, FVM + FEM | ![](figures-panel/optA_light_fvm_fem.png) | ![](figures-panel/optA_dark_fvm_fem.png) |
| Before, Lumped + Analytic | ![](figures-panel/before_light_lumped_analytic.png) | ![](figures-panel/before_dark_lumped_analytic.png) |
| A, Lumped + Analytic | ![](figures-panel/optA_light_lumped_analytic.png) | ![](figures-panel/optA_dark_lumped_analytic.png) |
| Before, fine cell | ![](figures-panel/before_light_fine_cell.png) | ![](figures-panel/before_dark_fine_cell.png) |
| A, fine cell | ![](figures-panel/optA_light_fine_cell.png) | ![](figures-panel/optA_dark_fine_cell.png) |
| B, FVM + FEM | ![](figures-panel/optB_light_fvm_fem.png) | ![](figures-panel/optB_dark_fvm_fem.png) |
| B, Lumped + Analytic | ![](figures-panel/optB_light_lumped_analytic.png) | ![](figures-panel/optB_dark_lumped_analytic.png) |
| C, FVM + FEM | ![](figures-panel/optC_light_fvm_fem.png) | ![](figures-panel/optC_dark_fvm_fem.png) |
| C, Lumped + Analytic | ![](figures-panel/optC_light_lumped_analytic.png) | ![](figures-panel/optC_dark_lumped_analytic.png) |

*Files in `figures-panel/`, named `<before|optA|optB|optC>_<light|dark>_<case>.png`.*

On the prototype (layout A and layout C), `tests/test_tooltips.py` and `tests/test_gui.py::test_docks_open_wide_enough_and_keep_the_run_button_in_sight` pass; the panel's minimum width is 319 px with A and B (as before, the dock is 340 px) and 282 to 290 px with C.

## 5. Recommendation of the first round (superseded by section 7)

**Layout A with the smaller memory lines.** It answers the request directly (a frame per group, with the models in its title), nothing moves or disappears when a model is ticked, the field labels the warnings and the guide quote stay the same, and it reuses the existing frame style and greying. B hides settings the user may want to prepare; C is clearer but reorders the model list and costs more in the guide and the tests.

Effort: **S** (half a day) for A and the memory lines on a `feature/` branch (a GUI change, so a minor item under the numbering rule; it can ride with 2.8.0). The prototype's frame code is close to final; it needs the docstrings, a group-level regression test and the documents below. C would be **M**.

What changes with A:
- `pcbthermal/gui/panels.py` (`SolverPanel.__init__`, `_update_availability`, `_update_cells`); the per-control tooltips stay; the frames need no tooltip of their own (a `QGroupBox` title is not a control; check `tests/test_tooltips.py` still passes, it did on the prototype).
- Tests: `tests/test_gui.py::test_docks_open_wide_enough_and_keep_the_run_button_in_sight` (passes unchanged), `tests/test_fem_gui.py` (reads `cells_label` for 'FEM:', '275724 unknowns', 'above the memory limit, it will not run', 'pyamg', 'will be left out': kept), `tests/test_gui_stress.py` 1183-1217 (reads 'FVM:', 'GB', 'will not run', the verdict hex colours, no thousands separator: kept), `tests/test_theme_coherence.py` 211-214 (verdict text changes with the theme: kept); add a test that a frame greys with its models and the laminate frame with a metal block, and a stress scenario in `tests/test_gui_stress.py`.
- Guide `pcbthermal/help/index.html` section 8: one sentence on the frames ('the settings are grouped by the models they serve; a group is greyed when none of its models is ticked'), the compact memory line, 'steady run only' for the local corrections; the picture `simulation_fem.png` (made by `examples/make_screenshots.py`, the FEM pictures function) and the dock in `editor.png`, `editor_warnings.png` and their dark variants in `docs/images/` and `pcbthermal/help/` are regenerated and looked at; `tests/test_help.py` if a new word is checked.
- `README.md` screenshots (the same files), `CHANGELOG.md` (Unreleased), `docs/versions.md`, `docs/decisions-log.md`.

## 6. Open decisions for the maintainer

1. The layout: P8 recommended, P1 if frames are wanted (section 7).
2. The memory lines: taken as in the prototype (dot in the verdict colour, compact form, hint style), the maintainer's answer.
3. Whether to fix the two small points of section 1 (Auto ignoring the FEM mesh numbers; the local-corrections tooltip) in the same branch.

## 7. Second round: eight aligned variants (P1 to P8)

The maintainer kept the memory lines of section 3 as they are (the dot in the verdict colour, the compact form) and turned down layout A as drawn: the labels, the fields and the group titles did not share common left edges, and the first frame sat too close to the Settings toggle. Eight variants were built with one rule: **one label column of one width (the longest label, 'Laminate sub-gaps', plus 6 px) and one field column, the same in every group**. In the grid variants (P2, P3, P5, P6, P8) all groups are rows of ONE `QGridLayout`, so the alignment holds by construction; in the framed ones (P1, P7) every frame has the same inner margins and a fixed label width. Every variant keeps the option keys, the field labels (the warnings quote them) and the tooltips (a grid row gets the tooltip `tips.apply` gave to a form row), and greys a group whose models are not ticked (the laminate group also on a board with a metal block).

| Variant | What it is | Label x / field x (px, from the panel edge) | Minimum width (dock 340) | Remarks |
| :-- | :-- | :-- | :-- | :-- |
| P1 | Titled frames (`QGroupBox`), labels left-aligned; inner left margin 13 px, so the title text, the labels, the memory lines and the checkbox start at the same x (title and label glyphs both at x 23, measured on the grab) | 22 / 148 | 331 | Closest to A, now aligned; frames cost about 10 px per group in height and 14 px in width |
| P2 | No frame: small bold capitals title and a thin rule per group | 8 / 134 | 308 | Compact; capitals are loud in the dark theme |
| P3 | Collapsible groups (chevron header), the groups of the ticked models open, the others closed and greyed | 8 / 134 | 308 | Shortest panel; settings of a model not ticked need a click to be seen; the open/closed state would be overwritten at every tick (prototype) |
| P4 | Common settings above, one tab per model group (FVM, Laminate, LPTN, Analytic, FEM), a tab disabled when its models are not ticked | 8 / 134 | 312 | Hides most settings behind tabs; a disabled tab looks almost like an inactive one in this theme |
| P5 | One flat form, a small tag at the right of each row (FVM, FVM·FDM, LPTN, Analytic, FEM) | 8 / 134 | 329 | No grouping, the tag column steals room: the solver list shows 'Sparse direct (e…' cut |
| P6 | The group name as a narrow left column (small bold), labels and fields in the next two columns, a rule between groups | 65 / 189 | 333 | Opens at 355 px by its own size; at 340 px the solver list is cut and the cell box shrinks to 72 px; tight |
| P7 | Frames as P1 with right-aligned labels and every field 160 px wide (the cell box and Auto together 160 px) | 22 / 148 (right edge of the labels 140) | 325 | Right-aligned labels do not start under the frame title, the request asks for common left edges |
| P8 | No frame: the group title in bold with the models it serves at the right in the hint colour, a thin rule under it; rows below; a group not ticked has its title, tag and rows greyed | 8 / 134 | 308 | Clean, aligned by construction, the narrowest, nothing moves when a model is ticked |

The x positions above were printed by the screenshot script for every case and both themes (`QWidget.mapTo` of every visible label and field to the panel): each variant has exactly one label x and one field x, in all three cases, except the dark P6 (65 and 66, one pixel from the theme font). Both prototype tests (`tests/test_tooltips.py`, `tests/test_gui.py::test_docks_open_wide_enough_and_keep_the_run_button_in_sight`) pass with each of P1 to P8.

**Room around the Settings toggle**: 6, 10 and 14 px were tried above the toggle and between it and the first group (P1 and P8). 6 px leaves the first frame title touching the accent underline; 14 px separates the toggle from what it opens; **10 px** is chosen for every variant.

![Room around the Settings toggle, P8 at 6, 10 and 14 px](figures-panel/spacing_p8.png)
*spacing_p8.png: P8 with 6, 10 and 14 px around the Settings toggle (light theme).*

![Room around the Settings toggle, P1 at 6, 10 and 14 px](figures-panel/spacing_p1.png)
*spacing_p1.png: the same for P1 (frames).*

![The eight variants, FVM and FEM ticked](figures-panel/panel_variants.png)
*panel_variants.png: P1 to P8 with the FVM and the FEM ticked, light theme on top and dark below, cut at the Settings box (the Models box and Run are the same in all).*

![The eight variants, only Lumped and Analytic ticked](figures-panel/panel_variants_lumped.png)
*panel_variants_lumped.png: the same with only the Lumped and the Analytic ticked, showing the greyed groups.*

![The eight variants, fine cell](figures-panel/panel_variants_fine_cell.png)
*panel_variants_fine_cell.png: FVM, 3D solid and FEM at a 0.3 mm cell, with two red memory lines.*

The recommended variant at full size (whole dock, 340 px):

| | Light | Dark |
| :-- | :-- | :-- |
| P8, FVM + FEM | ![](figures-panel/p8_light_fvm_fem.png) | ![](figures-panel/p8_dark_fvm_fem.png) |
| P8, Lumped + Analytic | ![](figures-panel/p8_light_lumped_analytic.png) | ![](figures-panel/p8_dark_lumped_analytic.png) |
| P8, fine cell | ![](figures-panel/p8_light_fine_cell.png) | ![](figures-panel/p8_dark_fine_cell.png) |
| P1 (alternative), FVM + FEM / Lumped + Analytic | ![](figures-panel/p1_light_fvm_fem.png) | ![](figures-panel/p1_dark_lumped_analytic.png) |

### Recommendation

**P8**, with 10 px around the Settings toggle and the memory lines of section 3. It answers both objections: every label and every field starts at one x in every group (one grid), the group titles start at the same x as the labels, and the toggle has room. It needs no frame, so it is the narrowest variant (308 px, against 331 for P1) and the shortest of those that show every setting; each group says which models it serves (the tag at the right), a group not ticked is greyed, not hidden, as the guide's 'Greyed fields' rule says, and nothing moves when a model is ticked. If the maintainer wants boxes, **P1** is the aligned framed version.

Effort: **S** (half a day) on a `feature/` branch: the prototype's P8 code (`panel_variants.py`) folds into `SolverPanel` with docstrings; one regression test for the alignment (every visible label at one x, every field at one x, the code of the screenshot script) and one for the greying of a group with its models and of the laminate group with a metal block; a stress scenario; the documents and pictures of section 5 ('What changes'), the same list.
