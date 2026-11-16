# Integration: how to show the surface and the mean in the theory and in the program

Nothing here is implemented by this folder; the program is untouched. The program side is being built on `fix/thick-plate-surface-estimate` after the design note `releases/2.8.0/fem-model/READOUT_SELECTOR.md` (branch `docs/readout-selector`). This file is the ONE design that reconciles that note with the studies of this folder (review, README 7).

## 1. Decision and recommended form (reconciled)

* **The layer mean (the column, the node) stays the number of every table**: the part rows, `t_max`, Tj, the margin, the power limit, the top-path split, the power coefficient loop, the Power Calculator, calibrate, the profile decision, every model comparison. Like for like across the five models; the frozen numbers stay (README 4.1: a surface in their place would move 20 of 20 harness boards by 0.57 to 3.79 mK).
* **The surface is a VIEW and a second number, never a mode**: no `SolverOptions` field, no project key, no Preferences entry, no command-line switch. It is computed beside the column (`arrays["T_surface"]`) for the FVM and FDM steady results when an outer copper layer is thicker than 105 um, and shown where it exists.
* **Withdrawn from the first version of this file** (review): the Display-popover combo 'Read temperature as: Layer mean / Surface (estimate)' that applied to 'the heater rows, the part table, Tj and margin', and the `--read surface|mean` option. Reason: `analysis.heater_stats` is read inside the solve (`api._top_path_split`, `api._solve_with_tc`), so a read-out that switches Tj would move the board field with a display choice (`READOUT_SELECTOR.md` 1.2, risk 1). The Display popover holds properties of the picture (underlay, opacity, view, colour map) that apply to every map; a surface map is another quantity, like 'Metal block (top)', so it belongs in the Layer box. No combo is added to the Display popover.
* **The surface is an estimate and says so**: the parabola `T_surf - T_col = t (2 q_top - q_bot) / (6 k)`, within 7 % of the true difference for t/a <= 0.5 and an upper estimate beyond (README 4.3; `research/through-thickness-readout` 4.2); the FEM resolves it.

## 2. What this folder adds to the branch `fix/thick-plate-surface-estimate` (instructions for the executor)

The branch already follows `READOUT_SELECTOR.md` (no mode, Layer-box entries, the 'Hottest surface' line, `(column)`/`(surface)` headers, steady only, FVM and FDM). Add or change only this:

1. **Summary line only when it is worth reading**: print 'Hottest surface (top|bottom)' only when, at the hottest part, (surface - column) is at least 1 % of the column rise above the ambient; otherwise nothing (and the Layer entries stay, they are harmless). Reason: below 1 % the difference is smaller than the discretisation error of the node itself (the copper-core top node is 1.5 % low at 0.25 mm, README 4.4) and than the parabola error on case 2 (0.8 to 1.6 % of the rise); a 210 um outer layer on FR-4 passes the 105 um gate and would otherwise print a line that differs by milli-kelvins. Put the share in the line: 'Hottest surface (top): 103.6 °C (estimate, +2.4 K = 3.1 % of the rise above the layer mean 101.2 °C)'.
2. **'estimate' everywhere the surface is shown**: the Layer-box entry text stays 'Surface (top)' / 'Surface (bottom)' (short), but its tooltip, the card suffix (' · surface (top), estimate'), the plot title (already 'estimate' / 'estimate, upper side'), the part-table header ('Max °C (surface, estimate)') and the report line carry the word; 'upper side' when t/a > 0.5.
3. **`check_thick_plates` text**: keep the bound as the trigger; when the result has `T_surface`, quote the estimate and add 'the share grows with Bi = h t / k, with t/a and with the plate width (Biot map in the user guide)'.
4. **References**: `pcbthermal/thickness.py` docstring cites 'validation 56.1'; sections 56 and 57 are reserved for the FEM campaign (`COMPARE_PLAN.md`): cite 55.6. In `docs/validation.md` the new 55.6 is placed before 55.5: move it after 55.5. This folder's text goes in **55.7** (section 4 below).
5. **Tooltip of the entries** (`tips.LAYER_TIPS`): the text of section 5 below.
6. Nothing else: no Display-popover control, no CLI option, no project key (as the branch already does).

## 3. Texts proposed for the theory (docs/theory.md 1.2, the layer node)

Ready text in `docs/theory-text.md` (the three conventions, the parabola, when it matters with Bi, t/a and the plate width, the busbar closed form, sources by key with the reading status). Figures to copy to `docs/images/`: `fig_01_where_read.png` (where each convention reads), `fig_02_decision.png` (decision), `fig_03_biot_map.png` (map, drawn for a plate 5 a wide).

## 4. Validation (docs/validation.md 55.7)

Ready text in `docs/validation-text.md` (the series against the independent 3D, the node against the 3D column mean, the thin-copper bound against the 3D, the plate-width dependence).

## 5. User guide and tooltips

* **Guide, Results chapter, after the paragraph of the surface read-out** (the branch writes it): 'Which temperature to compare with a measurement. A thermocouple, an IR camera and the board temperature of a datasheet (psi_JB on the centre pin, psi_JT on the top of the package) read a surface; the program's layer temperature is the mean through the thickness of the copper. On 35 to 105 um copper the two differ by milli-kelvins and you can compare directly. On a thick plate, block or pour cooled through a film (a copper core, an aluminium base, a cold plate) the surface under a part is hotter: 3.5 to 12 % of the rise for 1.5 to 2 mm of metal under a 4 to 5 mm part, 13 to 54 % for a 10 mm plate, more on a wider plate; use the Surface entry of the Layer box there. Picture: the decision chart and the Biot map.'
* **Tooltip of 'Surface (top)' / 'Surface (bottom)'**: 'Temperature of the outer face of the copper, estimated from the layer mean and the heat flowing in and out; it is what a thermocouple or an IR camera on the metal reads. Milli-kelvins from the layer mean on ordinary copper; percent of the rise on thick metal. Tables, Tj and margins use the layer mean. Steady state only.'
* **README line (Features)**: 'Surface read-out of thick copper: the outer-face temperature (an estimate) beside the layer mean, for comparison with a thermocouple or an IR camera.'

## 6. Measured impact

README 4.1: none on the 20 harness boards (no array below 105 um; frozen numbers unchanged). Thick plates: 3.5 to 54 % of the rise between the surface and the mean (4.2, 4.3), depending on Bi, t/a and the plate width.

## 7. Risks

Two meanings of 'mean' (through the thickness and in the plane over the source) and of 'surface' (centre, centroid, maximum) must not be confused: the summary line names the layer, the quantity and the axis. The parabola over-reads for t/a above 0.5 and for k below about 50 W/mK. The Lumped and Analytic offer no surface (the Lumped's own column error on case 2 is of the size of the term). An MCPCB with an aluminium base needs two metal conductivities, which the program does not have (one `k_copper`); a block model carries it. A wide plate under a small source reads a larger share than the 5 a map (README 4.2).

## 8. Open decisions for the maintainer

1. Accept the reconciled design (view, not mode; no Display-popover combo; no CLI switch). Impact: none on any number.
2. The 1 % threshold of the summary line (section 2.1). Impact: none on any number; it hides a line on thick-but-harmless outer copper.
