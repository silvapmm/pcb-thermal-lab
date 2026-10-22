# Gerber import: from copper vectors to the conductances of the grid

Research branch `research/gerbers` (started 2026-10-22). **Nothing in `pcbthermal/` was changed**: this folder holds the studies, their tests and the
conclusions, so that the work can be repeated and the decision taken later. The summary for the project documents is in `docs/research.md`
(section "Gerber import").

## 1. The question

A Gerber file is vector data: strokes with a width, flashes and filled regions. The program's finite-volume model works on a grid of square cells and,
today, knows only one number per cell and layer: the **fraction of copper**. Two questions follow.

1. *Can the Gerber be converted to exact polygons, including holes and islands?* Yes (section 4.1).
2. *How should the polygons (or a raster of them) be turned into the conductances of a grid of squares?* The fill fraction is badly biased; better
   mappings exist and are cheap (sections 4.3 to 4.7). The pixel size of the raster matters much less than the mapping.

## 2. Findings in short

| Item | Result |
| :-- | :-- |
| Vector to polygons | Exact with `gerbonara` (Apache-2.0) + `shapely`: the polarity-aware union keeps holes and islands. One Uno-clone layer: 103 polygons, 80 holes, 43 285 vertices. |
| Raster area | Within 0.2 % at 0.1 mm pixels, and 0.0 to 0.1 % at 0.05 mm; error per 1 mm cell 0.02 (RMS) at 0.1 mm. |
| Thin traces | A binary raster keeps the area but **interrupts** traces thinner than about 1.4 pixels: use a pixel of at most half the thinnest trace (0.05 mm for 0.1 mm traces). |
| **Fill fraction (today)** | **10 to 11 % too cool** on average (35 µm copper, single layer, 42 windows of 7 real boards), 14 to 15 % with plated holes, up to 18 % with 140 µm copper: connectivity is overstated because the clearances cut the paths. |
| **Geometric mean** | `S = S_cu^f * S_lam^(1 - f)`, from the fill fraction alone: 2.2 to 3.0 % error (single layer), 2.8 to 4.1 % with holes. No new data needed. |
| **Directional bounds, lambda = 0.5** | Sx, Sy per cell from the fine mask, `sqrt(low * up)`: 1.0 to 1.3 % at 0.6 and 1.0 mm cells, 0.5 to 1.0 % with holes. Closed formulas, no local solves. |
| Flow-based faces | The best at small cells (0.6 to 0.9 %), but about 1 point better than lambda = 0.5 at the cost of local solves. |
| Cell size | 0.6 and 1.0 mm cells map well; at 2 mm every method is limited by the grid itself (the heater has 3 x 3 cells). |

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `gerber_geometry.py` | Gerber -> shapely (polarity-aware union), board outline, centre-sampled mask, drill holes. |
| `conduction.py` | The conduction solvers (one and two layers) and **every mapping**: power mean, bounds, lambda, cell problem, flow-based faces. |
| `fetch_boards.py` | Downloads the public test boards into `data/` (git-ignored; licences differ, see section 8). |
| `windows.py` | Cuts 42 windows of 36 x 36 mm (0.1 mm pixels) out of 7 boards; fixed seed. |
| `study_raster_error.py` | Area, thin-trace and pixel-size studies (section 4.2, 4.3). |
| `study_mapping.py` | All mappings on the 42 windows (section 4.4). |
| `study_fine_scan.py` | Fine scan of the exponent `p` and of `lambda` (section 4.5). |
| `study_contrast.py` | Copper 18 to 140 µm (section 4.6). |
| `study_two_layer.py` | Two layers with plated holes, on the Stormduino (section 4.7). |
| `tests/` | 19 fast tests: exact and limiting cases of the solvers and mappings, and the Gerber reader on synthetic files. |
| `requirements.txt` | Extra packages (gerbonara, shapely, pillow, scipy, pytest). |

## 4. How to run, and the results

```sh
python3 -m venv research/gerbers/.venv && research/gerbers/.venv/bin/pip install -r research/gerbers/requirements.txt
cd research/gerbers
.venv/bin/python fetch_boards.py                 # once
.venv/bin/python -m pytest -q tests              # 19 tests, about 1 s
.venv/bin/python study_raster_error.py           # about 3 min
.venv/bin/python study_mapping.py                # about 2 min (4 cores); builds the windows on first use
.venv/bin/python study_fine_scan.py              # about 2 min
.venv/bin/python study_two_layer.py              # about 2 min
.venv/bin/python study_contrast.py               # about 6 min
```

All the studies use one copper sheet of 35 µm (385 W/mK) on 1.6 mm of FR-4 (0.9 W/mK in plane), 10 W/m²K on each face, and compare the temperature of a
heated block (mean and maximum) with a **reference**: the copper mask solved as it is, pixel by pixel, at 0.1 mm. The coarse grids (0.6, 1.0, 2.0 mm cells)
are built from the same mask, so the error of a mapping is isolated from the fidelity of the pixels. `MAE` is the mean of the absolute errors; `bias` is the
mean signed error (negative = too cool = optimistic).

### 4.1 Vectors to polygons (Stormduino, an Arduino Uno clone)

`gerbonara` turns every draw, flash and region into primitives; `shapely` unions them in file order, adding dark and subtracting clear polarity. The top
layer has 6 654 primitives (6 117 are 0.254 mm strokes: the copper pour is drawn as hatch lines) and unions into **103 polygons with 80 holes and 43 285
vertices** (12 462 after simplifying by 5 µm, with 0.07 % less area); the bottom layer 69 polygons, 44 holes, 26 288 vertices. Stored as WKB the polygons are
300 to 500 KB; the same layer as a 0.1 mm PNG mask is 9 to 12 KB.

### 4.2 Raster against the exact area (`study_raster_error.py`)

| Pixel (mm) | Area error, top / bottom | RMS error per 1 mm cell (top) | Max error per 1 mm cell (top) |
| --: | --: | --: | --: |
| 0.2 | +0.18 % / +0.48 % | 0.0375 | 0.180 |
| 0.1 | -0.19 % / -0.02 % | 0.0200 | 0.101 |
| 0.05 | 0.00 % / +0.08 % | 0.0080 | 0.064 |
| 0.025 | +0.02 % / +0.03 % | 0.0036 | 0.023 |

Anti-aliasing (4 x 4 samples) at 0.1 mm gives the same as a binary raster at 0.025 mm: only the number of samples matters.

### 4.3 Thin traces and the pixel (`study_raster_error.py`)

Binary raster, synthetic traces at random sub-pixel offsets and two angles (200 each). Mean area kept is always about 100 %; the share of traces that come
out **interrupted** is what counts:

| Trace (mm) | Pixel 0.2 | Pixel 0.1 | Pixel 0.05 | Pixel 0.025 |
| --: | --: | --: | --: | --: |
| 0.05 | 86 % | 26 % | 0 % | 0 % |
| 0.075 | 27 % | 16 % | 0 % | 0 % |
| 0.10 | 24 % | 0 % | 0 % | 0 % |
| 0.15 | 15 % | 0 % | 0 % | 0 % |
| 0.20 and wider | 0 % | 0 % | 0 % | 0 % |

The reference itself depends a little on the pixel (single layer, 5 x 5 mm heater, `study_raster_error.py` section 3): 0.2 mm +2.1 %, 0.1 mm +0.2 % against 0.05 mm.

### 4.4 The mappings on 42 windows (`study_mapping.py`)

Methods (all give the face conductances the solver uses; for the first four the face is the harmonic mean of the two cells, as the FVM does):

* **pmean(p)**: cell sheet conductance = `(f S_cu^p + (1 - f) S_lam^p)^(1/p)`, from the fill fraction `f` alone. `p = 1` is the program's fill fraction, `p = 0` the geometric mean, `p = -1` the harmonic mean.
* **lam(l)**: directional, `low^(1 - l) * up^l` per direction, with `low` = rows in parallel of series chains (no cross flow, a lower bound) and `up` = series of parallel columns (equipotential column faces, an upper bound).
* **cellnum**: numerical upscaling, a local conduction problem on the cell (potential fixed on two faces, the other two insulated).
* **dual(m)**: flow-based face conductance, a local problem on the window that spans the centres of the two cells, with `m` rows of oversampling margin (transmissibility upscaling, as for reservoir grids).

MAE of the mean-temperature error (%), with the bias in brackets:

| Method | 0.6 mm cells | 1.0 mm | 2.0 mm |
| :-- | --: | --: | --: |
| pmean 1 (fill fraction, today) | 9.7 (-9.7) | 11.3 (-11.3) | 11.1 (-11.0) |
| pmean 0 (geometric mean) | 2.2 (-1.0) | 2.4 (-0.8) | 3.0 (+1.7) |
| pmean -1 (harmonic) | 10.2 (+10.2) | 13.7 (+13.7) | 21.0 (+21.0) |
| lam 0 (low) | 2.6 (+2.6) | 4.5 (+4.5) | 9.5 (+9.5) |
| **lam 0.5** | **1.0 (+0.2)** | **1.3 (+0.7)** | 3.2 (+3.2) |
| lam 0.75 | 1.5 (-0.9) | 2.0 (-1.0) | 2.1 (+0.4) |
| lam 1 (up) | 2.3 (-1.9) | 3.1 (-2.6) | 3.6 (-2.2) |
| cellnum | 1.1 (+0.8) | 1.7 (+1.5) | 4.2 (+4.2) |
| dual, m = 0 | 0.6 (-0.1) | 0.9 (+0.4) | 3.6 (+3.6) |
| dual, m/n about 0.2 | 0.7 (-0.4) | 0.8 (+0.2) | 3.1 (+3.1) |

Per board (MAE over the three sizes), the fill fraction is 6.7 to 15.2 % off on every board; lambda = 0.5 is 1.1 to 2.3 % on six boards and 4.4 % on the
sparse one (`fritz`, 18 % copper), where the flow-based faces are best (2.3 to 2.9 %).

### 4.5 Fine scan of the parameters (`study_fine_scan.py`)

* Exponent `p`: the minimum is at **-0.05 to 0** for 0.6 and 1.0 mm (MAE 2.1 to 2.4 %); at 2 mm it moves to +0.10. So the geometric mean (`p = 0`) is the natural choice.
* Weight `lambda`: the minimum is at **0.5 to 0.6** (average MAE 1.6 to 1.8 %); 0.5 is best at 0.6 and 1.0 mm, 0.7 at 2 mm.

### 4.6 Copper thickness (`study_contrast.py`)

MAE (bias) of the mean-temperature error for 18, 35, 70 and 140 µm of copper (contrast copper / laminate 4.8, 9.4, 18.7, 37.4):

| Copper | Method | 0.6 mm | 1.0 mm | 2.0 mm |
| --: | :-- | --: | --: | --: |
| 18 µm | fill fraction | 5.7 (-5.7) | 6.4 (-6.3) | 5.1 (-4.8) |
| | geometric mean | 1.1 (-0.3) | 1.3 (+0.3) | 3.5 (+3.4) |
| | lam 0.5 | 0.6 (+0.3) | 1.1 (+1.0) | 4.1 (+4.1) |
| 35 µm | fill fraction | 9.7 (-9.7) | 11.3 (-11.3) | 11.1 (-11.0) |
| | geometric mean | 2.2 (-1.0) | 2.4 (-0.8) | 3.0 (+1.7) |
| | lam 0.5 | 1.0 (+0.2) | 1.3 (+0.7) | 3.2 (+3.2) |
| 70 µm | fill fraction | 13.0 (-13.0) | 15.1 (-15.1) | 15.6 (-15.6) |
| | geometric mean | 3.4 (-1.7) | 3.7 (-1.8) | 3.9 (-0.1) |
| | lam 0.5 | 1.5 (+0.3) | 2.0 (+0.6) | 2.9 (+2.4) |
| 140 µm | fill fraction | 14.9 (-14.9) | 17.0 (-17.0) | 17.8 (-17.8) |
| | geometric mean | 4.4 (-2.3) | 4.8 (-2.6) | 4.9 (-1.4) |
| | lam 0.5 | 2.1 (+0.4) | 2.6 (+0.5) | 3.2 (+1.8) |

The fill fraction gets worse as the copper gets thicker; the ranking of the methods does not change.

### 4.7 Two layers with plated holes (`study_two_layer.py`)

Stormduino, both layers resolved, 109 drilled holes as copper barrels (25 µm plating), FR-4 0.3 W/mK through the 1.53 mm gap, 6 x 6 mm heater on the top
layer at three random places. MAE (%) of the mean-temperature error:

| Method | 0.6 mm | 1.0 mm | 2.0 mm |
| :-- | --: | --: | --: |
| fill fraction | 13.6 | 14.9 | 14.4 |
| geometric mean | 3.9 | 4.1 | 2.8 |
| **lam 0.5** | **1.0** | **1.0** | **0.5** |
| lam 0.6 | 1.6 | 1.9 | 1.0 |
| cellnum | 0.2 | 0.5 | 2.2 |
| dual, m = 0 | 1.3 | 0.4 | 1.2 |

Reference values: 50.81, 46.72 and 54.67 K (mean of the heated block) at the three places.

## 5. Proposal for the program (not implemented)

1. **Stage 1, no new data: the geometric mean.** In the cell conductance replace `f S_cu + (1 - f) S_lam` by `S_cu^f S_lam^(1 - f)`: 10 to 14 % bias down to 2 to 4 %.
   It is the exact result for a symmetric two-phase medium in 2D (Dykhne) and is the exponent `p = 0` the scan found best. Caution: it was validated on
   Gerber copper (pours with clearances, traces); a hand-drawn zone with a hatch fill below 1 is a set of parallel stripes (conducts as the arithmetic mean along
   them and the harmonic mean across) and was **not** tested; for `f = 0.5` the geometric mean of phases equals the geometric mean of those two directions.
2. **Stage 2, the recommended default: directional conductances with lambda = 0.5.** Store the copper per layer as a fine mask (0.1 mm, or 0.05 mm for
   traces thinner than 0.1 mm), compute `low` and `up` per cell for the chosen cell size, and give the FVM `Sx`, `Sy` per cell (the face keeps the harmonic mean).
   1 % at 0.6 and 1.0 mm cells, no local solves. Changes: a copper raster element in `Problem` (mask or polygons with holes), `fvm.py` and `fdm.py` with
   conductance per direction, the 3D solid with in-plane `kx`, `ky`; the Lumped and Analytic models keep using the average fill.
3. **Stage 3, optional: flow-based faces** for the last point of accuracy (about 4 fine-grid solves per layer).
4. **Before any change**: a validation section in `docs/validation.md`, the equation in `docs/theory.md`, tests, and a check on a **thick-copper** and a
   **multi-layer** board with vias on a real design, plus the hatch fill case above.
5. **Import**: Gerber (any CAD) for the copper and the outline, Excellon for the holes (vias are not told from component pads in a Gerber), KiCad
   (`.kicad_pcb`, text) for parts, stack-up and the distinction vias/pads. The layer assignment needs a small dialog.

## 6. How other projects do it (read on 2026-10-22; for ideas only, no code copied)

| Project | Geometry | Grid or mesh |
| :-- | :-- | :-- |
| [FYPA](https://github.com/Tomachie/FYPA) (AGPL-3.0) | gerbonara primitives to shapely; polarity-aware union per layer in batches; arcs by chords of 0.025 mm; Clipper2 for a fast union on a 1 µm integer grid (non-zero fill, holes rebuilt from the poly-tree) with a `verify` mode against shapely | triangular mesh (`triangle`) and a sparse FEM solve |
| [padne](https://github.com/atx/padne) (AGPL-3.0) | shapely (multi)polygons with holes; Gerber through `pygerber`; via holes punched out | CGAL constrained Delaunay mesh: minimum angle 20°, maximum size 0.6 mm, finer near points of interest; disconnected copper meshed more coarsely |
| [kicad-electrothermal-sim](https://github.com/krosa-laboratory/kicad-electrothermal-sim) | filled zones, tracks and pads from the KiCad API, shapely | raster grid, 0.1 mm "usually sufficient", islands flagged |
| [KiCad_Thermal_Sim](https://github.com/Dietschi10/KiCad_Thermal_Sim) | KiCad filled zones and tracks | regular grid of 0.5 then 0.3 mm; an adaptive mode keeps the fine cell at copper edges and merges uniform interiors up to 8 times larger |

None of them used a mapping like the ones above: the mesh projects either follow the polygons exactly (triangles) or rasterise to a binary grid.
A 2017 [Electronics Cooling article](https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/) on PCB conductivity warns that volume-weighted
"smearing" gives serious errors and recommends conductances between neighbouring nodes, which agrees with what was measured here.

**Licences of the mesh libraries** (summaries read, not the licence texts): Shewchuk's *Triangle* restricts commercial use without permission, and the
CGAL mesh packages are GPL; either one is a problem for a closed product. `shapely` is BSD but its wheels bundle GEOS (LGPL); Clipper2 was not checked.
The square-grid route of this folder needs none of them (gerbonara, Apache-2.0, is only needed to read the files).

## 7. Limits of this study

* One copper sheet on laminate for the 42-window studies; two layers with holes on **one** board (three places).
* The reference is the 0.1 mm mask, which is about 0.2 to 1 % hotter than a 0.05 mm one; a cell never sees detail below that.
* Heated block of 6 x 6 mm, uniform face coefficient (no edge loss, no copper on the other layers in the single-layer test).
* Results at 2 mm cells include the error of the coarse grid itself (3 x 3 cells under the heater), not only the mapping.
* The 1 mm cell results in an earlier two-layer run (cells of 0.5, 1 and 2.5 mm) showed an irregular behaviour that was not explained; the present grids (0.6, 1.0, 2.0) do not.
* The boards are public designs, mostly hobby boards; no power or industrial boards, no heavy-copper or metal-core boards.
* Not tested: hatched zones, thermal-relief patterns made by hand, the Lumped and Analytic models, the time simulation.

## 8. Test boards and licences

The files are **not** in the repository (`data/` is git-ignored). `fetch_boards.py` downloads them for private use; the results quoted here are statistics.

| Key | Board | Licence (as stated by the source) |
| :-- | :-- | :-- |
| `storm` | Stormduino Rev 2.2, an Arduino Uno clone (KiCad), 68.6 x 53.4 mm, 2 layers | MIT |
| `chibi` | chibi_2024 (KiCad), 100 x 78 mm | CC BY-SA |
| `easyeda` | an EasyEDA export | not stated |
| `pcbrnd` | epl_isolatedpwr (pcb-rnd) | GPL-2 |
| `pcad` | zxnet_usb (P-CAD) | GPL-3 |
| `dip` | FD1 mainboard (DipTrace) | BSD |
| `fritz` | analog_gyro_2021 (Fritzing) | MIT |

The latter six come from the test resources of gerbonara (https://gitlab.com/gerbolyze/gerbonara), each with the licence of its own folder.

## 9. Sources

* gerbonara, https://pypi.org/project/gerbonara/ (Apache-2.0).
* shapely and GEOS, https://shapely.readthedocs.io/.
* Durlofsky, *Upscaling and gridding of fine scale geological models for flow simulation* (2005), https://pangea.stanford.edu/departments/ere/dropbox/SmartFields/SFC_publications/2005_Durlofsky_upsc_grid_review_ifrs.pdf (local, extended-local and global upscaling; transmissibility).
* Power-law averaging of permeability (exponents between -1 and 1; the geometric mean for isotropic 2D media), https://ccg-server.engineering.ualberta.ca/CCG%20Publications/Other/CVD%20Papers/02-Conference/2002/power-law-averaging02.PDF. The 2D two-phase result of Dykhne (1971) is quoted from memory and was not checked against the paper.
* Electronics Cooling, *Problem: effective thermal conductivity* (2017), https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/.
* The four projects of section 6 (repositories linked there).
