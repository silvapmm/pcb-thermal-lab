# Text for `CHANGELOG.md` (Unreleased), if the maintainer adopts P1

### Documentation

- The error of 2-layer boards (`docs/validation.md` 21.1) is rewritten with reproducible numbers: it belongs to boards with bare laminate around a copper pad and a thick gap (FVM -10.5 to -0.3 % for pads of 6 to 26 mm on a 1.6 mm gap), not to every 2-layer board; the cause is the lateral heat flow in the bare laminate across the gap. Boards with copper in every cell are within about 1 % of an exact series solution in the FVM, Analytic and 3D solid, 1.3 % in the FDM.

### Checks

- A note before the run when a heater sits on a copper footprint smaller than about 8 gap thicknesses, about 12 when the far side of the gap has no copper (only if P1 is adopted).

(No change of any result: P1 is text and a check; P2, extra nodes in the gap of the cells that show laminate, is a separate decision.)
