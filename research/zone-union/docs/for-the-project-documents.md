# Text for the project documents (when the work is adopted)

Drafts only; the project documents are not edited from the research branch. The numbers are those of the [README](../README.md); the pictures are `../figures/fig_01_cell_two_zones.png`, `../figures/fig_02_rules_at_a_point.png` and `../figures/fig_03_hatched_pour.png` (copy to `docs/images/` on adoption).

## `docs/theory.md`, in the section on the layered idealisation: the copper of a cell

The copper fill `f` of a cell of layer `k` is the mean over the cell of the **largest fill at every point**: with sub-sample points `p` (4 x 4 per cell), `f = (1 / 16) sum_p max_i [ p in zone_i ] fill_i`, where the maximum runs over the zones of layer `k` that contain `p` (a point in no zone has fill 0). Solid zones (fill 1) that overlap or abut therefore give exactly the geometric union of their areas, which is what the copper of a board is (Gerber: the filled area of a region is "the union of the filled areas of each individual contour"; KiCad and Altium: overlapping zones of one net are one copper). Taking the larger of the zones' shares of the whole cell instead (the rule of versions up to 2.4.2) lost the copper of the smaller zone in every cell where two zones meet: 10 % of the rise (FVM) and 28 % (FDM) on a 20 mm board drawn as 0.5 mm strips over 1 mm cells.

A `fill` below 1 stands for the **share of the area** that a hatched or perforated pour covers; its pattern is not stored (a hatched zone in KiCad or Altium is a pattern of lines of given width and pitch). Two zones of fill below 1 that overlap take the larger fill at every point: exact when their patterns are the same or nested, and the least copper of the union rules when they are not (two patterns shifted by half a pitch together make a solid sheet, two crossed ones a grid; no scalar rule is right for all three, README 4.6). Where one zone is solid the union is solid.

The sub-sample lattice (4 x 4) puts the copper area of a cell to within 0.0036 on average of the exact union and the peak rise to within 0.3 % of the rise for a clearance of 0.25 mm between zones over 1 mm cells (README 5).

*Figure*: `fig_01_cell_two_zones.png` (a cell with two zones and the lattice).

## `docs/models.md`, the zone

A zone is a polygon on one layer with a fill between 0 and 1. The zones of a layer are united: where they overlap or touch, the copper of a point is the largest fill of the zones that contain it. Draw zones as you like (one zone, or pieces that meet or overlap): the same copper gives the same temperatures. A hatched zone is a density (fill = the share of copper); two overlapping hatched zones do not add up (the larger fill is used), so draw the combined copper as one zone with the fill you want.

## `docs/validation.md`, a new table

"Zones that meet or overlap" (peak rise against the independent 3D solver on the resolved copper, 20 x 20 mm, 1 mm cells; old = versions up to 2.4.2): one seam, a T or a corner of four: old +0.4 to +1.1 % (FVM), union -0.09 % (the model's own error on the board); 40 abutting strips of 0.5 mm: old +9.95 % FVM, +28.0 % FDM, +11.8 % Lumped, +9.1 % Analytic, +10.0 % 3D solid, union -0.08 % (FVM); example boards: unchanged to 0.0000 K. Overlapping zones of fill 0.5 equal one zone of fill 0.5 (the additive rule gave -8.2 %). On the Stormduino drawn as polygons the copper of the densest 24 mm window is 0.531 of the cells under the old rule, 0.591 under the union, 0.596 resolved; the peak rise of the five models is 10 to 35 % below the independent solver in both, 0.1 to 1.6 points more so with the union (the scalar fill overstates the conduction of patterned copper).

## `docs/versions.md`

*Zones of a layer are united per sample point*: `geometry.zone_fill` (new), `geometry._sample_mask` (helper of `coverage_fraction`), used by `fvm.Network`, `fdm.Network` (area sampling), `solid3d.Solid`, `analytic._effective_sheet` and `_block_tiles`, and `checks.check_problem`; tested by `tests/test_zone_union.py` (abutting zones, overlapping zones of equal fill, disjoint cell-aligned zones equal the old rule, layers independent, the five models). Measured in `research/zone-union/`.

## `CHANGELOG.md`, Unreleased

* Fixed: the zones of one layer that meet or overlap inside a cell are combined per sample point (the union of their copper) instead of keeping the larger share of the cell; boards drawn as pieces gave up to 10 % (FVM) and 28 % (FDM) too much temperature rise and a false "copper fill 0.50" warning. Boards whose zones do not share a cell, and the example boards, are unchanged.

## User guide (`pcbthermal/help/index.html`), the zone row

"Copper zone (Z): copper area on one layer (any polygon). Zones of the same layer that overlap or touch are united. Copper fill: 1 = solid, 0.5 = hatched (the share of the area that is copper; the pattern is not drawn); where two zones overlap the larger fill is used, so two hatched zones do not add up to a solid one. A copper edge or a hatching across a heater's footprint makes the Lumped and Analytic models unreliable." New words for `tests/test_help.py`: "united", "larger fill".

## Tooltip of the zone fill (`gui/tips.py`)

"Share of the zone's area that is copper (1 = solid, 0.5 = a hatched pour of half copper). The pattern is not stored. Where two zones overlap the larger fill is used."

## `CLAUDE.md`, Decisions Log

"Zones of a layer are united per sample point (maintainer, branch `fix/zone-union`, investigation `research/zone-union`): the copper of a cell is the mean over its 4 x 4 sample points of the largest fill of the zones that contain the point (`geometry.zone_fill`), not the larger of the zones' shares of the cell. The old rule lost the copper of the smaller zone where two zones meet inside a cell (10 % FVM and 28 % FDM on 0.5 mm strips over 1 mm cells); the example boards do not move. The additive, probabilistic, summed and priority rules were tested and are wrong for overlapping partial fills or for solid copper under a hatched zone; for overlapping hatched zones no scalar rule is right (the pattern would be needed). On a board drawn as many polygons the change makes the program cooler, which is farther from the independent solver, because the scalar fill already overstates the conduction of patterned copper."

## `docs/roadmap.md`, entry

"Zones of a layer united per sample point (fix, after the investigation `zone-union`): evidence in `research/zone-union/`; open: warnings for self-intersecting zones and overlapping hatched zones; the pattern attribute of the gerber-models investigation is the real answer for hatched pours."

## `docs/research.md`, summary

"zone-union: the union of the zones of a layer. Read: the Gerber specification (the filled area of a region is the union of its contours; overlapping dark objects), summaries of the KiCad and Altium documentation (same net: one copper; priority only between nets; hatched = pattern). Measured against an independent 3D solver: the per-cell maximum loses the copper where zones meet inside a cell (10 % FVM, 28 % FDM on strips); the per-point maximum gives the one-zone value in the five models; no scalar rule is right for overlapping hatched zones. Open: the memory of the lattice, the two warnings, the pattern attribute."

## Literature status (`literature.md`)

Gerber specification revision 2026.05: read for polarity, regions, self-intersection and the Hatched layer type; revision 2016.01: the same passages; KiCad 9 zone page and zone filler source, Altium polygon pour page: summaries only; Clipper2, Vatti, Weiler and Atherton, Greiner and Hormann: not opened beyond summaries; IPC on hatched copper: not obtained. Keys in `research/theory/BIBLIOGRAPHY.md`: Gerber2026, Gerber2016Mirror, KiCadZones9, KiCadZoneFillerSource, AltiumPolygonPour, Clipper2, Vatti1992, GreinerHormann1998, WeilerAtherton1977, Shapely.
