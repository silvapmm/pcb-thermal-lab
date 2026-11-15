# Integration: how to show the surface and the mean in the theory and in the program

Nothing here is implemented; this is the design for a `feature/` branch after the maintainer decides. The program is untouched.

## 1. Decision and recommended form

* **Default: Layer mean**, unchanged (like for like across the five models; the frozen numbers stay). **Add 'Surface' as a second reading, shown only where it can differ**: a layer or block whose `thickness / conductivity` criterion says so (see 3). Not a global switch: on 35 to 105 um copper it moves 0.6 to 8.8 mK (README 4.1).
* **The surface is an estimate and says so**: the parabolic read-out (`research/through-thickness-readout` `surface_readout.offsets`), within 7 % of the true difference for t/a <= 0.5, over-reading beyond (README 4.3); with the FEM model (`docs/fem-model-design`) the surface is the FEM's own `T_surface` and needs no estimate.
* Recommendation to the maintainer: adopt in this order, each its own `feature/` or `fix/` branch: (a) the texts and the figure (theory and user guide, no number moves); (b) the summary line; (c) the selector.

## 2. Texts proposed for the theory (docs/theory.md, section on the layer node)

Ready text in `docs/theory-text.md` (the three conventions, the Biot criterion, the map, the busbar closed form, sources by key). Figures to copy to `docs/images/`: `fig_01_where_read.png` (where each convention reads), `fig_02_decision.png` (decision), `fig_03_biot_map.png` (map).

## 3. Display in the program (exact elements)

1. **Display popover** (`gui/display.py`), new combo 'Read temperature as': `Layer mean` (default) / `Surface (estimate)`; applies to the heater rows, the part table, Tj and margin, and the Results summary; greyed with the tooltip 'This layer is thin for the heat (Bi h t/k = ..., t/a = ...): the surface is within X mK of the mean' when the bound `q'' t / 2k` of every heater is below 1 % of the rise (the check `checks.check_thick_plates` already computes the bound at 5 %).
2. **Results summary line** (one per run, only when above 1 % of the rise): 'Heater U1, layer 2: layer mean 9.6 K, surface 10.3 K (estimate, t/a 0.4); a probe on this metal reads the surface.' With the same text for the part rows' hover.
3. **Warning text of `checks.check_thick_plates`** extended with the Biot figure: 'surface minus mean is X % of the rise (Biot map in the user guide)'.
4. **User guide and tooltips**: the decision picture (fig 2) and the map (fig 3) in the Results chapter; tooltip of the combo: 'Layer mean is what every model computes; Surface is what a thermocouple or IR camera on the metal reads. They differ by milli-kelvins on 35 um copper and by 3 to 41 % of the rise on thick metal.'
5. **Command line**: `--read surface|mean` (default mean) for `run` and a column `T_surface` in the CSV beside `T_mean` only when the check fires.

## 4. Measured impact

README 4.1: heater rows move by 0.57 to 3.79 mK on 20 of 20 harness boards if the surface replaced the mean (so it is not the default; frozen numbers unchanged when it is an added array); thick plates 3 to 41 % of the rise (4.3).

## 5. Risks

Two meanings of 'mean' (through the thickness and in the plane over the source) and 'surface' (centre, centroid, maximum) must not be confused: the summary line names the layer, the quantity and the axis. The parabola over-reads for t/a above 0.5 and for k below about 50 W/mK. The Lumped model has its own column-mean error (0.2 to 0.8 K on case 2) and should not offer the selector. An MCPCB with an aluminium base needs two metal conductivities, which the program does not have (one `k_copper`); a block model carries it.
