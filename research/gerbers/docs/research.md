# Research notes: Gerber import and the mapping of copper to the grid

Moved here from `docs/research.md` (maintainer's rule, 2026-10-23: the project documents stay untouched on this branch; research documents live in `research/`). Details, tables and sources: [`../README.md`](../README.md); design of the integration: [`../INTEGRATION.md`](../INTEGRATION.md).

## Open now: Gerber import and the mapping of copper to the grid (2026-10-22)

Branch `research/gerbers`; scripts, tests, tables, sources and the design of the integration are in [`research/gerbers/README.md`](../research/gerbers/README.md) and [`research/gerbers/INTEGRATION.md`](../research/gerbers/INTEGRATION.md). Summary:

**Question.** A Gerber is vector data, the FVM works on square cells and knows only the copper *fraction* of each cell (and the fill of a zone). Can the vectors be converted exactly, without third-party licences, and how should they feed the grid?

**Answers.**
* **Vectors to polygons: exact** (gerbonara + shapely, holes and islands kept), and **not needed**: a mask at 0.1 mm (9 to 12 KB per layer) is enough. **Reading without libraries: done** (`native_gerber.py`, NumPy only; within 0.9 % of the copper area of the gerbonara route, same boxes and drills, unsupported features reported); only NumPy and SciPy are needed for the import.
* **The pixel matters little, the mapping matters a lot.** The area is within 0.2 % at 0.1 mm pixels; a binary raster only interrupts traces thinner than about 1.4 pixels (use a pixel of at most half the thinnest trace).
  On 42 windows of 7 real boards (reference: the mask solved pixel by pixel) the fill fraction the FVM uses is **10 to 11 % too cool** (up to 18 % with 140 µm copper, 14 % with plated holes on two layers, 3 to 7 % on a real four-layer board, **7 to 43 % for regular 50 % patterns**): clearances cut the paths that the average assumes connected.

| Mapping of the cell | Real copper 0.6 / 1.0 mm | Two layers + holes | Four layers (real) | Regular patterns, 1 mm | Needs |
| :-- | --: | --: | --: | --: | :-- |
| fill fraction (today) | 9.7 / 11.3 % | 13.6 / 14.9 % | 3.0 / 4.6 % | 7 to 43 % | `f` |
| geometric mean | 2.2 / 2.4 % | 3.9 / 4.1 % | 0.4 / 1.5 % | -20 to +22 % | `f` only |
| directional `sqrt(low*up)` (lambda 0.5) | 1.0 / 1.3 % | 1.0 / 1.0 % | 1.5 / 2.8 % | 0 to 2.4 % (diagonal +12 % at 0.6 mm) | fine mask |
| **flow-based faces** | **0.6 / 0.9 %** | 1.3 / 0.4 % | **0.3 / 1.1 %** | 0.9 to 3.4 % | fine mask, local solves (5.5 s per 100 x 160 mm layer, once) |

  (mean absolute error of the heater-block temperature; `study_mapping.py`, `study_two_layer.py`, `study_multilayer_real.py`, `study_patterns*.py`.)
* **Cautions investigated.** Thick copper: the ranking holds from 18 to 140 µm; heater size: small heaters (1 to 3 mm) are the hard case, the flow-based faces best; time response: capacity stays arithmetic and the response follows the steady one; hatched zones: **the zone fill must keep its formula**: the geometric mean in the program's `S` moves a hatched zone by +26 % (0.75), +45 % (0.5), +42 % (0.25) and four exact-value tests by 0.05 to 0.07 K, and no function of the fraction is right for a grid, stripes and islands, so the pattern has to be declared; through the program's own `fvm.Network` the mappings reproduce the research numbers and the research solver agrees with the program to 3e-12.

* **Lumped and Analytic** (`study_lumped_analytic.py`, 42 windows, 1 mm cells, through the public API with one zone per cell): the Lumped model reads the FVM sheet conductance, so a better `S` takes it from 13 % to 4.8 % (its own model error); the Analytic model sees the board as one uniform sheet, so per-cell conductances leave 12 % and it needs ONE effective conductance weighted by the heater's influence K0(r/lambda): arithmetic 18.6 % too cool, geometric-type power mean (p -0.2 to -0.1) 5.9 %, flow-based window conductance 7.1 %, harmonic 24.7 % too warm. No literature found on the copper fraction in lumped or cosine-series PCB models.
* **Reader conformance** (`study_reader_conformance.py`, gerbonara's own 272 test files): 149 of 164 comparable files agree within 3 % of the area (median 0.04 %), 6 refused (5 Upverter non-standard `Rect` apertures, 1 image mirror), 82 left out as thinner than 1.5 pixels; the 15 that disagree are mostly silkscreen/outline files, two follow the spec text where gerbonara does not. Four defects found and fixed (macro comments, interpolation mode after a region, non-standard aperture reported as unsupported).

**Proposal** (nothing implemented): keep `Zone.fill` as it is; an element "imported copper" (a fine mask per layer, from a Gerber or from a declared zone pattern) whose face conductances come from the flow-based mapping (lambda 0.5 as quick mode); zones with a `pattern` use the same path; import with the NumPy reader, layer assignment pre-filled from the X2 attribute or the name, plated holes as vias (filtered). Details, lines and costs in `INTEGRATION.md`.

**Other projects** (read for ideas only; FYPA and padne are AGPL-3.0): FYPA and padne keep shapely polygons with holes and build a triangular mesh (`triangle`, CGAL) for a FEM solve; two KiCad plug-ins rasterise to a binary grid (0.1 mm, or 0.5 to 0.3 mm with adaptive merging). The mesh libraries are a licensing problem for a closed product (Triangle restricts commercial use, the CGAL mesh packages are GPL), which is one more reason to stay on the square grid.

**Open.** Which stage enters the program and the decision on the zone `pattern` (and what to do with existing files that use `fill` below 1: the arithmetic value is the optimistic limit); validation on a thick-copper multi-layer board of a real design and against a measurement (none exists in the project); the layer-assignment dialog; what the Lumped and Analytic models do with a mask; processing of very large boards in strips. When it is implemented the findings fold into `models.md`, `theory.md` and `validation.md`, and this section is removed.

## Update 2026-10-23

* **Scope** (`study_reader_scope.py`): copper layers 50 of 52 non-empty classified files drawn (2 Upverter files refused); Excellon files 38 of 38 read, and on the 35 that gerbonara also reads the holes are identical. The comparison found and fixed real defects (inverted `TZ`/`LZ`, format pattern, `M71`/`M72`, tool lines with `F`/`S`, multi-segment routes); a drill file without a unit is refused.
* **Nets**: the reader keeps the X2 net of every object. Pads and tracks carry it in KiCad files, zone fills did not in the test set, so the net of a piece of connected copper is taken from the labelled objects it contains. `joule.py` solves the current of a net between two terminals and gives `I²R` per cell (checked against closed forms). Missing for a real feature: the current per net/pad, vias between layers, `rho(T)` coupling, the interface.
* **Literature**: the three Electronics Cooling articles and the Ucamco text could not be opened (network policy); see `literature.md` for what is confirmed and what is still from memory.

