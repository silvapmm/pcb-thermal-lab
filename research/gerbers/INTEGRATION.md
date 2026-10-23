# Applying the copper mapping in the program (design, not implemented)

Questions from the maintainer: *how is the mapping applied, do the algorithms change, or is there an intermediate layer?*

Short answer: **the solvers keep their algorithms; a small intermediate module decides the conductance of every cell, and each model asks it instead of computing `S` by hand.**
Tried in `prototype_in_program.py`: the program's own `fvm.Network` (cells, heater, losses, assembly, sparse solve) was used unchanged and only the conductances were replaced; the result is the
same as the research solver to 3e-12.

**Important correction after the tests (`README.md` 4.10, 4.11): the formula of `Zone.fill` must not change.** Putting the geometric mean in `fvm.py:78` and `fdm.py:134` moves a hatched zone by +26 % (fill 0.75),
+45 % (0.5) and +42 % (0.25), and four exact-value tests by 0.05 to 0.07 K. A zone fill is a density typed by a person; its pattern is unknown, and no function of the fraction is right for a grid, stripes and islands
(7 to 43 % too cool with the arithmetic value, -20 to +22 % with the geometric one). The imported copper therefore gets **its own element**, and the zone fill keeps its meaning.

## 0. Why not import the copper as polygons (zones), and why an interface at all

*Answer to "do the models have to change, or an intermediate layer?" (2026-10-23, README 4.31 and 4.34): both, in a fixed order. The intermediate layer is the importer (`lib/importer.py` today, `pcbthermal/copper.py` in the design below): it turns files into per-layer face conductances, vias and nets and hands the model data it already understands, so the program's physics and file format do not change. The FVM then needs only to accept faces instead of the harmonic mean of cell values (done in the prototype by the `FaceNetwork` subclass, without editing `fvm.py`); the FDM and the 3D solid need the same small change; the Lumped and the Analytic cannot take faces and need their own reduction of the mask. Handing every model a cell value instead (the cheap way, no model change) was measured on our board: +8 to +13 % in the FVM and FDM, +35 % in the Lumped.*

*Status 2026-10-23: the import stage itself exists as research code, `lib/importer.py` (README 4.31, figure 7): reading, vias, face conductances and a `FaceNetwork` for the FVM. The interface (layer confirmation, outline, heaters) and the FDM/3D faces are still design only.*

The question ("is a Gerber not just copper as polygons, like the zones we draw?") has a short answer: **in geometry yes, in what the solver does with it no, and the solver is where the work is.** Facts checked in the code and by tests (README 4.27):

1. **`Zone` is one polygon and a scalar fill**: `Zone(layer, polygon (n, 2), fill, name)`, no holes and no islands. Gerber copper is polygons with holes (one layer of an Uno clone: 103 polygons, 80 holes, 43 285 vertices, README 4.1), so a layer would be thousands of zones, with holes cut by splitting.
2. **Zones are combined per cell with a maximum, not a sum** (`fvm.py:72`, `fdm.py:133`, `solid3d.py:91`, `analytic.py:134` and `216`, `checks.py:34`): two zones that each cover half a cell give half a zone's copper. Copper tiled in many abutting polygons therefore loses copper in every shared cell: +7 % (FVM) to +17 % (FDM) hotter for the same copper cut into strips (`tests/test_program_union.py`). Drawn zones are usually few and large, so it rarely shows today.
3. **Each cell takes the fraction of copper and mixes it arithmetically** (`S = f k_cu t_cu + k_lam (slab - f t_cu)`, the coverage sampled 4 x 4 per cell). For a big solid zone the cells are 0 or 1 except at the edges and this is exact; for fine copper (tracks, clearances, hatch) almost every cell is partial and the arithmetic mix is the 10 to 23 % cool bias of the research. So polygons would work mechanically, with a different union rule and holes, and still give the biased answer.
4. **What changes is the mapping from geometry to conductance, not the format.** The copper can be held as polygons (shapely) or as a mask; what matters is that it is drawn on a fine grid (coverage mask, README 4.26) and mapped to the faces of the model's own grid. The same engine could serve the drawn zones too (rasterise the polygon finely, map the cells; the exact-aligned rectangles stay exact), which would give one mapping for drawn and imported copper; `fill < 1` (hatching) keeps its formula or gets a declared pattern.
5. **Why an interface**: not for the physics, but for what the files do not say. Which file is which copper layer (the X2 file function usually tells, older sets only the name), units of a drill file without one, the board outline, which plated holes are vias (aperture functions tell when written), the stack-up (the Gerber job file may carry thicknesses, to be checked), the nets (when written), and the pixel that the thinnest track needs (a warning to the user). A first version can be a command-line import with the defaults and a confirmation list; a dialog is for confirming and correcting those guesses, and for showing the copper that was understood (a preview of the mask and the nets).

## 1. Where the copper fraction enters today

| File | Lines | What happens |
| :-- | :-- | :-- |
| `pcbthermal/fvm.py` | 68-73 | `f` per layer and cell: the union (`max`) of the zones, each `coverage_fraction * z.fill` |
| | 76-79 | `S = (f k_cu t_cu + k_lam (slab - f t_cu)) * cover` (sheet conductance) and `C` (heat capacity, arithmetic: right as it is) |
| | 210-211, 277-278 | the faces: `harmonic(S[...], S[...]) * dy/dx` and `* dx/dy` (steady and transient assembly) |
| `pcbthermal/fdm.py` | 130-136 | the same `fill` at the nodes, the same formula for `S` and `C`; the face is the arithmetic or harmonic mean of two nodes |
| `pcbthermal/solid3d.py` | 88-91, 152-153 | `fill`; the copper slab gets `kx = f k_cu + (1 - f) k_lam` (the through value `kz` is a different question) |
| `pcbthermal/lumped.py` | 156 | reads `net.S` of the FVM network: it gets any change of `S` for free |
| `pcbthermal/analytic.py` | 130-139, 166, 216-219 | the fraction is averaged with the influence of the heaters, then `S = f_avg k_cu t_cu + ...` |
| `pcbthermal/blocks.py` | 110-112 | the contact of a metal block uses `f` as the area fraction over copper: arithmetic is right |
| `pcbthermal/checks.py` | 31-34, 60-65 | `f` for the warnings (copper edge under a heater, no copper): unchanged |

## 2. The intermediate layer: `pcbthermal/copper.py` (new, no Qt)

```python
def phase_conductances(tc, slab, k_cu, k_lam):          # (L,) each -> copper phase a = k_cu tc + k_lam (slab - tc), laminate phase b = k_lam slab
class CopperMask:                                       # one fine boolean mask per layer (origin, pixel size) from a Gerber or from a pattern
    def fraction(self, nx, ny, dx, dy): ...             # f per cell: for the capacity, the blocks and the checks (arithmetic, as today)
    def conductances(self, nx, ny, dx, dy, a, b): ...   # (gx, gy) face conductances of the grid of the run: the flow-based faces; or (Sx, Sy) with lambda 0.5 as the quick mode
def pattern_mask(kind, pitch, fill, polygon, pixel):    # hatch lines, cross-hatch, islands, perforated: the mask of a patterned zone
```

* **Zones without a pattern** (all the existing files): nothing changes, bit for bit.
* **Imported copper and patterned zones**: the model takes the face conductances from `CopperMask.conductances` instead of the harmonic mean of `S`.

### Do the current models have to change?

Only where the cell conductances are read, and only when imported copper exists. Without imported copper nothing changes: the zones, the fill formula and every test stay as they are. With it: `fvm.py`, `fdm.py` and `solid3d.py` take the face conductances of the layer from the mask instead of the harmonic mean of the cell values (about one function each, the matrices keep their shape and the solvers are untouched); `lumped.py` needs nothing, it already reads `net.S` of the FVM network; `analytic.py` gets one effective conductance per layer (influence-weighted geometric-type mean) instead of the average fraction. A heat source from a net (`joule.py`, `README.md` 4.20, picture: `figures/fig_02_nets_and_joule.png`) enters as ordinary power per cell and needs no model change at all.

### What each model does

* `fvm.py`: after `self.S`, if a layer has a mask, store its face conductances (`gx`, `gy` per layer); `_assemble` (lines 210-213 and 277-280) uses the stored faces for those layers and the harmonic mean of `S` for the others. The vias, the vertical links, the losses, the blocks and the capacity are untouched.
* `fdm.py`: the same on the nodes (the face between two nodes comes from the mask); `solid3d.py`: `kx`, `ky` per slab from the cell conductances; `lumped.py`: reads `net.S`: give it the mean of the two directional values of the layer (measured: 13 % falls to 4.8 %, `README.md` 4.16); `analytic.py`: keeps ONE effective conductance per layer, but not the arithmetic fraction (18.6 % too cool): the mean weighted by the heater's influence K0(r/lambda), as a power mean with p between -0.2 and -0.1 (MAE 5.9 %), or the flow-based conductance of the window (7.1 %); per-cell values do not help it (12 %).
* The GUI: an element "Imported copper" per layer (a preview of the mask, the pixel size, the layers assigned), the zone's `pattern` and `pitch`, tooltips and the user guide (CLAUDE.md rules).

## 3. Storage and import

* A mask at 0.1 mm of a 70 x 50 mm layer is 9 to 12 KB as PNG (0.3 to 0.5 MB as polygons in WKB); in the project file: packed bits, zlib, base64, plus the origin and the pixel size.
* Pixel size: at most half the thinnest trace (0.05 mm for 0.1 mm traces, 0.1 mm for 0.2 mm); the program can read the smallest stroke width from the file and suggest it.
* Import with the NumPy-only reader (`native_gerber.py`): copper, outline and Excellon holes; the layer assignment is pre-filled from the X2 file function or the file name (`classify`); the plated holes become `Via` elements (a Gerber cannot tell vias
  from component pads: a minimum-diameter filter and a preview; a `.kicad_pcb` can); a feature the reader does not support (aperture blocks, transformed apertures, the moire primitive) is reported and the file refused.
* Cost per layer, paid once at import and cached with the project: 0.6 s (200 000 pixels) to 5.5 s (1.6 million = 100 x 160 mm at 0.1 mm) for the flow-based faces; memory about 830 bytes per pixel (strips for larger boards); the quick mode costs 0.02 s.

## 4. Choosing the mapping

| Mapping | Accuracy (see `README.md`) | Cost | Role |
| :-- | :-- | :-- | :-- |
| flow-based faces | single layer 0.6 to 0.9 %, two layers 0.4 to 1.3 %, four layers 0.3 to 2.0 %, regular patterns 0.9 to 3.4 % | a few seconds per layer | **default** for imported copper |
| bounds, lambda 0.5 | 1.0 to 1.3 % on single layers, 0.5 to 1.0 % two layers; 1.3 to 7.5 % on a four-layer board with planes; diagonal copper +10 to +12 % at 0.6 mm | negligible | quick preview, fallback |
| geometric mean | 2 to 3 % on random real copper, -20 to +22 % on regular patterns | none | last fallback when no mask is kept (random copper only) |
| arithmetic fraction (today) | 10 to 11 % too cool on real copper, 7 to 43 % on patterns | none | only for the zones as typed |

## 5. What a change does to the program's tests

* A scratch copy of the program with the geometric mean in the zone formula (`README.md` 4.10): 321 tests pass, 6 fail (two only because the documents are not in the copy; four exact-value tests move by 0.05 to 0.07 K), the hatched zones move by 26 to 45 %.
* The design above leaves every existing board unchanged, so the existing tests and examples do not move; new tests are needed for the mask element, the mappings (the research tests are a start: `research/gerbers/tests`), the import and the GUI.
* To validate in the repository's way: a `docs/validation.md` section with the tables of the studies, the equations in `docs/theory.md`, a thick-copper multi-layer board of a real design, and the comparison with a measurement if one becomes available.

## 6. Risks and open questions

* The flow-based faces and every other mapping were validated against a **finer simulation of the same model**, never against a measurement; all the boards are public hobby designs.
* Diagonal copper is limited by the five-point stencil (no cross terms): about 1 to 3 % for the flow-based faces, up to 12 % for lambda.
* Heat capacity and the through-thickness conduction stay arithmetic; the time response follows the steady one (`study_transient.py`).
* How the Lumped and Analytic models should use a mask is open: they average over rings or regions much larger than a cell.
* The zone `pattern` needs a decision of the maintainer: which patterns, which default for files that already use `fill` below 1 (kept as it is, with a warning that the arithmetic value is the optimistic limit?).

## 7. The electrical side: sources, sinks and links (design, prototype in `lib/pdn.py`, README 4.40)

* **What is added**: `Problem.electrical` with named terminals (position and size of a pad, net) and the elements `vsource` (volts), `isink` (amps) and `link` (ohms between two terminals); the part (`Heater`) may carry a `current` and a `net`. Absent = nothing changes, bit for bit.
* **Where it plugs in**: after the copper mask exists (the same pixels that give the face conductances), `pdn.solve` gives the potential, the Joule heat per pixel and the power of every link; `joule.to_cells` adds it to the source term of the thermal grid; the existing fixed-point loop of `api._solve_with_tc` adds the resistivity of copper rising 0.39 %/K. The thermal models do not change: the heat enters as one more source.
* **Why the links matter**: in the prototype scenario a 0.1 ohm link carries 18 times the heat of all the copper of a 1.5 A rail; pieces of one net that are not joined by copper are normally joined by such a part, so the part list (value of the 0 ohm, ferrite, shunt or fuse) is what the electrical side needs from the design.
* **Inputs, to be decided later** (maintainer, 2026-10-23): the electrical data may be passed as an extra argument of the import (a sidecar file next to the project, or a KiCad netlist plus part fields) or typed in a pads table; the research leaves the form open.
* **Open**: vias in the network; regulators (load as constant power); time dependence; ratings (IPC-2152).

## 8. Two corrections to the program found by the research, with their measured impact (README 4.39)

1. **Combine zones by the maximum per sample point, not per cell** (`geometry.zone_fill`, used by `fvm.py`, `fdm.py`, `solid3d.py`, `analytic.py`, `checks.py` in place of the loop with `np.maximum`). Copper tiled in abutting zones is no longer lost (-7.8 % FVM, -17.5 % FDM, -10 % 3D on 0.5 mm strips: back to the single-zone value); overlapping zones keep the larger fill; **the example boards do not move at all**. The simpler additive rule double counts overlap (-7.8 %) and failed four program tests: not proposed.
2. **Laminate under a single copper layer in `solid3d.py`**: one slab of the laminate below the copper when `layers == 1` (it was a bare 35 µm sheet). The peak of a single-layer pad board goes from 346 to 174 K (the same board with a second, empty layer: 174.5 K); nothing else moves.

Both were applied to copies of the program outside the repository; adopting them is a normal change on a `fix/<topic>` branch with the documentation, tests and whole battery (rules in CLAUDE.md).

