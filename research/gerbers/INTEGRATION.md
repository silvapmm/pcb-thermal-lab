# Applying the copper mapping in the program (design, not implemented)

Questions from the maintainer: *how is the mapping applied, do the algorithms change, or is there an intermediate layer?*

Short answer: **the solvers keep their algorithms; a small intermediate module decides the conductance of every cell, and each model asks it instead of computing `S` by hand.**
Tried in `prototype_in_program.py`: the program's own `fvm.Network` (cells, heater, losses, assembly, sparse solve) was used unchanged and only the conductances were replaced; the result is the
same as the research solver to 3e-12.

**Important correction after the tests (`README.md` 4.10, 4.11): the formula of `Zone.fill` must not change.** Putting the geometric mean in `fvm.py:78` and `fdm.py:134` moves a hatched zone by +26 % (fill 0.75),
+45 % (0.5) and +42 % (0.25), and four exact-value tests by 0.05 to 0.07 K. A zone fill is a density typed by a person; its pattern is unknown, and no function of the fraction is right for a grid, stripes and islands
(7 to 43 % too cool with the arithmetic value, -20 to +22 % with the geometric one). The imported copper therefore gets **its own element**, and the zone fill keeps its meaning.

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
