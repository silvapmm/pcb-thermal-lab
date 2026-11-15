# Surface read-out: documentation audit and additions (`docs/surface-readout-help`)

Tree: `development` dfde802b plus this branch. Text, tooltips and one screenshot only; no physics or number changed.

## 1. What existed before this branch

| Place | What it said |
| :-- | :-- |
| User guide (`pcbthermal/help/index.html`) | one long bullet in 'Limits and good practice' (what the two numbers are, the formula, where it shows, the 7 % and the upper estimate); the thick-plate bullet and a row in the glossary of warnings; no section of its own, no worked example, no film term, no FAQ, no picture |
| Tooltips | `tips.SURFACE_ENTRY_TIP` on the Layer-box entries, the Temperature entry of `LAYER_TIPS`, one tooltip on the last header of the Components table; none on the renamed (column) headers or the surface mean header |
| Warning (`checks.check_thick_plates`) | the bound, Bi, t/a, the side of the source, the surface estimate; no sentence on what to do |
| `docs/models.md` | 4b.1 (the read-out, long, one paragraph); the module-map line of `thickness.py`; no table of what each model returns |
| `docs/theory.md` 1.2c | formula, derivation, fluxes, partly filled cells, range, not modelled, status 'derived'; no error direction, warnings, sources or where validated stated in one place |
| `docs/validation.md` | 55.6 (case 2, six more plates, heat balance, threshold). There is no section 55.7 in the tree. |
| README | one feature line without a link |
| `docs/calculators.md` | nothing |
| CHANGELOG, versions, decisions log | the merge entries |

## 2. What this branch added

* User guide: section 'Surface temperature and column mean (thick plates)' (id `surface`, in chapter 10): the two numbers, the formula, when it matters, where it appears, what stays on the column and why, which models, the limits, the worked example (case 2: column 1.96 / 4.62 / 3.73 / 2.85 K below the paper's surface; surface within +0.56 / +1.26 / +1.03 / +0.80 K of the independent 3D at 0.5 mm, numbers from `validation.md` 55.6 and `research/muzychka-case2-analytic`), the film term `t/(2k)` (a row of the Environment table too), two screenshots; a FAQ line 'My result differs from the paper' in the limits; a pointer from the old bullet.
* Tooltips: `tips.COLUMN_HEADER_TIP`, `SURFACE_MEAN_TIP`, `SURFACE_MAX_TIP` on the four temperature headers of the Components table. The headers now break into lines (the surface ones were cut off at the width of the stretched columns, seen in the screenshot); `tests/test_gui_stress.py` line 706 checks the pieces of the new text.
* Warning text: a 'What to do' sentence in `check_thick_plates` (read the surface in the Layer box or the table where the result has it; otherwise the FVM or FDM estimate or the 3D solid).
* `docs/models.md` 4b.2 'Read-outs: column, surface, point' (what each model returns); `docs/theory.md` 1.2c (error direction, warnings, sources by key with status, where validated); `docs/calculators.md` (the Power Calculator uses the column); README link; CHANGELOG, versions, decisions log.
* `examples/make_screenshots.py --surface [folder]`: the 4-layer example board with 2 mm outer copper, 400 W/m2K, 20 W on U1; writes `results_surface.png` (Layer box on Surface (top)) and `results_surface_table.png` (Components table with the column and surface columns), copied to `docs/images/` and `pcbthermal/help/`. Both were looked at.

## 3. Leftovers

* The request named `validation 55.7`: it does not exist; nothing was invented.
* The FEM is not selectable on `development` (only `femcore.py` and `femmesh.py`, which puts up to 8 elements through a thick copper layer): the guide and models 4b.2 say it *will* resolve the thickness; turn this into the present tense when the FEM model branch is merged.
* The metal-block surface, partly filled cells and imported copper are not validated against a 3D solver (stated in the guide and in 1.2c).
* The Components table header 'Power limit W' is cut at the same widths (older, not touched).
* The Summary tab and the report lines are not screenshots; the report line text is quoted in the guide only in words.
* The model tooltip of the Temperature tab does not say 'column'; the column read-out has no label on the maps other than the Surface ones.

## 4. Review

Checked against the code (`thickness.py`, `analysis.surface_stats`, `api`, `plots.draw_surface`, `checks.check_thick_plates`, `gui/results_view.py`, `gui/layerchoice.py`, `solid3d.py`, `femmesh.py`) and `docs/validation.md` 55.2 and 55.6. Case 2 re-run on this tree (FVM and FDM, 0.5 mm): surface minus the independent 3D surface +0.56 / +1.26 / +1.03 / +0.80 K, column 1.97 / 4.62 / 3.73 / 2.85 K below the 3D surface (1.96 / 4.59 / 3.70 / 2.84 K below the paper's values), surface minus column 2.53 to 5.88 K. Film term from the pending file `face-film-half-slab` (the 142 records not also moved by another item): median 2.1e-5 K on the hottest temperature, all towards hotter, at most 0.040 K (finned block). Corrections made by the review:

* Guide, worked example: the column differences were said to be below the paper's tabulated surface; they are below the independent 3D surface (they differ from the paper by up to 0.03 K); 'within +0.56 ...' read as 'reads +0.56 ... above'; the tree named.
* Guide, models 4b.1: the Animation and Profiles were said to 'say so' (that they show the column); no such label exists in the code; reworded (the Surface entries exist only in the Temperature tab).
* Guide, models 4b.2: 'the FEM resolves' became 'will resolve' (not selectable yet).
* Warning 'What to do' and the glossary row: 'the 3D solid resolves the thickness' is wrong for copper (one cell through each copper slab); the text now separates thick copper (read the FVM/FDM surface) from a metal block (the 3D solid slabs a block at about 1 mm), and says the surface columns appear only above the display threshold.
* `docs/calculators.md`: a thermocouple reading the surface makes the calculator return a power a little HIGH (the sentence said the board reads 'a little low', ambiguous).
* Theory 1.2c: an unbalanced parenthesis, the status of [Muzychka2003] (R for the worked cases and Tables 1 to 4, not 'read in full'), the larger overshoot with 16 sub-slabs, the tree of the numbers.
* Tooltips: unit (degC), the meaning of each symbol of the formula (the old text gave the top-face form also for a part on the bottom), the 3D solid in the list of models without the read-out.
* Guide, film term: 'ordinary boards ... at most 0.04 K on the finned block' became 'the 17 boards of the frozen numbers'.
* `make_screenshots.py --surface`: the docstring named one picture of two; the comment claimed 1 K or more (the picture shows 0.3 K, 2 % of the rise).

Screenshots looked at: `results_surface.png` shows the Layer box on Surface (top) and the title 'surface (top), estimate, max 42.1 degC (layer mean 41.8 degC)'; `results_surface_table.png` shows the two (column) and two (surface, estimate) headers on several lines and 'Power limit W' still cut.
