# Reviewer opinion: vector polygons for imported copper, and the BOM item (read-only)

Tree: `development` after v2.7.0. Nothing edited in the repository.

## A. Vector polygons for imported Gerber copper

What exists today:
- Parts are polygons (paste hull / dominant group / box, X3 Body etc.; `gerber/parts.py`, `components.py`).
- Board outline is a polygon (`gerber/outline.py`), used exactly: `geometry.exact_coverage`, `face_apertures`,
  `signed_distance_to_outline`, the centroid edge film.
- Drawn zones are polygons.
- Imported copper is a one-byte coverage raster at pixel `min(m w/4, cell/10)`, typically 0.05 mm, with the outline
  applied per pixel by its exact share (`copper.CopperSource._outline_faces`, validation 38).

Evidence that vectors add nothing to the physics:
- Reader area against exact vector areas: -0.026 to +0.18 % on 109 files (versions.md, Gerber reader).
- gerber-models README 809: our reader vs gerbonara+shapely: area +0.07/+0.11 %, heater temperature 0.01 to 0.04 %.
- gerber-models README 900: "a vector is not needed (a mask at 0.1 mm is enough and smaller)".
- imported-copper-edge-film and validation 38/39: the residual edge bias (-2.2 % then fixed by the centroid film)
  was the film placement in the cut cell, not the resolution of the copper; the pixel is 20x finer than the cell.
- strong-edge-laminate: the 1000 W/m2K residual was the simple stack-up slabs, not the copper geometry.

What vectors would add: exact copy for export to other tools, crisp display at deep zoom (canvas is reduced to
2048 px anyway), picking a copper island. Editing is better served by painting/erasing the mask (feature 3, no
polygons). Cost: 6 to 9 days, shapely+GEOS (LGPL) as a new dependency or own polygon booleans (risky), no
frozen-number gain, a second representation to keep in sync.

Verdict: drop now; no study needed (the question "does the raster limit accuracy" is already answered by the
evidence above). Reopen only on a concrete need (export to another tool, KiCad import as polygons).

## B. BOM

A BOM cannot give powers (no column for them; 1 real BOM in the library, Pulsonix). The placement file already
gives designator, value, footprint. What a BOM could add later: DNP marks, MPN for a datasheet theta lookup,
grouped values. All marginal without a power source.

The useful thing is a POWER LIST: CSV `designator, power_W[, duty, period_s or profile]`, matched to parts by
designator in step 2 or by an Import power list action on any project with named heaters. Not a BOM reader;
small (S): reader with the preamble tolerance of `parts.parse_placement`, a match report (unknown / missing
designators), tests. It also works for hand-drawn boards and is the bridge to the later electrothermal item.

Remains of the BOM in the tree: `package.KINDS` "bom" and the SOURCES_TIP text (keep: a label of a stored
file, harmless, and packages already written may carry it); `research/bom-role-and-close-hook` (keep as the
record); `research/ROADMAP.md` E14 (close it, pointing to the power list); versions.md Planned item 5 and the
'Import' line.

Recommendation: rename and narrow. Replace item 5 by "Power list import (CSV by designator)"; drop the BOM
role; the branch `feature/bom-role-and-close-hook` stays as the record.

Sentences:
- docs/versions.md (Planned): "Power list import (feature, S): a CSV of designator, power in W and an optional
  duty, matched to the parts by designator with a report of unmatched names; the BOM role is dropped (a BOM has
  no powers and the placement file already carries designator, footprint and value; code kept on
  `feature/bom-role-and-close-hook`)." And for item 10: "Dropped: the raster at the default pixel already
  matches the vector areas within 0.2 % and the temperatures within 0.04 % (gerber-models 809); reopen only for
  export or a polygon import."
- CLAUDE.md Decisions Log: "Vector copper dropped and the BOM role replaced by a power-list import (maintainer,
  on the reviewer's opinion): the raster is not the accuracy limit, and only a list of powers by designator
  adds information the placement file lacks."
