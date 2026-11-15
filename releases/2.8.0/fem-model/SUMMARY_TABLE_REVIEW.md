# Review of the Results Summary table

Tree: `development` at `6c225276`. Read-only review (no program file changed). Questions of the maintainer: (1) what are `Tmax °C` and `Tmean °C` of the Summary table and do the headers say it; (2) why the table looks badly formatted next to the command-line output and how to fix it.

Looked at offscreen (cell 2 mm): the example board with six models (windows 1500 x 900 and 1200 x 800) and the 50 x 50 x 10 mm plate of Muzychka case 2 (FVM and FEM, 1500 x 900); the CLI run once. Images: `figures-summary/`.

## 1. What the columns are

All columns come from `Simulation.table()` (`pcbthermal/api.py`), one row per model. The window, `to_text`, `to_markdown` and `summary.json` use the same rows.

| Column | What it is | Read-out | Cells |
| :-- | :-- | :-- | :-- |
| `Tmax °C` | hottest temperature of the model | column (a copper layer averaged through its thickness) | every copper layer, every cell inside the outline; metal blocks excluded |
| `Tmean °C` | mean temperature | column | mean over all copper layers together (each layer equal weight), inside each layer weighted by the area inside the outline; blocks excluded |
| `ΔT °C` | `Tmax - ambient` (a difference: unit K) | column | as Tmax |
| `Rθ K/W` | `ΔT / power`: board resistance from the hottest column value to the air (not a junction value) | column | as Tmax |
| `Power W` | power injected | - | - |
| `Balance` | `(out - in) / in`, relative | - | - |
| `Error vs ref` | `ΔT / ΔT_ref - 1` in %: error of the rise, not of Tmax, against the reference model (FVM when it runs) | column | - |
| `Time s` | wall time | - | - |

Per model: FVM, FDM, 3D solid: largest cell (FDM node) of the copper layers; Tmean cover-weighted mean of the copper layers. FEM: the column field is the volume mean over the copper slabs of each layer shared to the plan cells; the hottest node and the surfaces are in the report, not in the table. Lumped: Tmax is the peak of the ring network at the heater (centre ring + footprint peak correction + rise from the other heaters), a column value but not the maximum of a map; Tmean the plain mean of its map. Analytic: maximum and plain mean of the series on its grid (rectangle of the same area when there is an outline).

Both numbers are column read-outs; the surface is never in the table. On the Muzychka plate the table shows FVM 99.22 °C and FEM 99.16 °C while the report gives the top surface at 105.1 °C (FVM estimate) and 103.68 °C (FEM, resolved), the FEM hottest node 103.88 °C: a user who reads only the table underestimates the hottest face by about 5 K.

**Do the headers say it?** Only the tooltip (`MODEL_TABLE_TIP`, `gui/tips.py`). The header text is `Tmax °C`; the Components tables write `Max °C\n(column)`. The Summary is the one temperature table whose read-out is hidden.

Labels to correct: `ΔT °C` should be `ΔT K` (also `dT C` in the text report and `ΔT [°C]` in the Markdown); `Tmean` is the mean of all copper layers together, not "over the board" as the tooltip says (on a 4-layer board it mixes the hot top layer with cool inner planes); `Error vs ref` does not name the reference nor say it is the error of ΔT; `Rθ K/W` is not a junction value; the tooltip calls the Lumped Tmax a "cell or node" value, which is close but not exact.

## 2. What is badly formatted

1. **Cut headers and cells**: every column but the first is `QHeaderView.Stretch` (`results_view.py`), no horizontal scroll or minimum width. At 1200 x 800 the table is 528 px wide, 53 px a column: headers read `max °C`, `mean °`, `ower W`, `or vs r`; balance cells `+111.1...`. At 1500 x 900 it fits.
2. **The table is shown twice and the two copies disagree** (Qt table vs the `to_text` table under it): `FVM` vs `fvm`, `reference` vs `+0.0%`, `Error vs ref` vs `vs fvm`, `ΔT °C` vs `dT C`; the 81-character text line wraps at 1200 x 800.
3. **The text table is misaligned** (also `report.txt`): the balance field is 9 characters, `+111.10E-15` has 11.
4. **The balance shows round-off noise** (`+111.10E-15`, `-35.72E-12`), no unit; for the FEM it changes between runs.
5. The read-out is not in the header and `ΔT` has the wrong unit.
6. An empty row is left (`_fit_height(min_rows=3)`).

The CLI looks better because it prints `to_markdown()` (nothing cut, units in brackets, `Error vs fvm`), but it keeps model keys, `ΔT [°C]`, `+111.10E-15` and no read-out in the header. There is no shared formatter: `to_markdown`, `to_text` and `ResultsView.set_simulation` each format the same row with their own f-strings.

## 3. Options

* **(a) Fix the Qt table** (S, risk low): headers in two lines naming the read-out (`Tmax °C\n(column)`, `Tmean °C\n(all layers)`, `ΔT K`, `Error vs FVM\n(of ΔT)`); columns `ResizeToContents` with a minimum width and a horizontal scroll bar, only the last stretches; balance as a percentage with a floor (`0.00 %`), raw value in the cell tooltip; `min_rows` equal to the number of rows. Changes: tests (`tests/test_gui.py`, `tests/test_fem_gui.py`, a new no-cut test at 1200 x 800), `tips.MODEL_TABLE_TIP`, the Summary row of the help, screenshots `results_summary*.png`, CHANGELOG.
* **(a+) (a) plus one column definition** (M, risk low to medium): one list in `api.py` (key, header, unit, read-out, formatter) used by `to_text`, `to_markdown` and the Qt table, widths from the longest cell; the on-screen report stops repeating the table. The text of `report.txt` and of the CLI changes (check `test_numfmt.py`, `test_report_disclaimer.py`, `test_gui_boxes.py`, `test_stackimpedance.py`); frozen numbers do not read the report.
* **(b) HTML/text table in a `QTextBrowser`** (S to M, risk medium): loses header tooltips, selection and copy; an HTML table still wraps.
* **(c) A library** (tabulate MIT, rich MIT, prettytable BSD-3; licences from memory): a dependency for what two f-strings do; none draws in Qt.

## 4. Recommendation

**(a+), effort M** (branch `fix/summary-table`, executor then reviewer). No library. No number moves, so no pending file.

## 5. Decisions (maintainer, to be answered by the reviewer)

1. (a) only or (a+). 2. Drop the copy of the table from the on-screen report (recommended), keep it in `report.txt`. 3. Header words. 4. Balance as a percentage with a floor, raw value in the tooltip and `summary.json`. 5. Add a column with the top surface peak for FVM/FDM/FEM so the 5 K of the plate are visible (needs its own decision: the surface read-out is a view).

## 6. Not verified

Licences of the libraries (from memory; none installed); only the dark theme and two window sizes offscreen (native macOS fonts are wider); Lumped and Analytic Tmean on a board with an outline read in the code, not run; the fix was not implemented.
