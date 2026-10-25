# Phase 2: applying the copper mapping in the program (design, not implemented)

Questions from the maintainer: *how is the mapping applied, do the algorithms change, or is there an intermediate layer?*

Short answer: **the solvers keep their algorithms; a small intermediate module decides the conductance of every cell, and each model asks it instead of computing `S` by hand.**
Tried in `prototype_in_program.py` and `lib/faces.py`: the program's own `fvm.Network` (cells, heater, losses, laminate nodes, assembly, sparse solve) was used unchanged and only the lateral conductances of the copper layers were replaced; with the program's own formula as faces it reproduces the program's run to 1e-6 K. (It agreed with the one-sheet research solver to 3e-12 before the program gave a one-layer board laminate nodes; the subclass had to keep the program's extra links since, README Review R1.)

**Important correction after the tests (`README.md` 4.10, 4.11): the formula of `Zone.fill` must not change.** Putting the geometric mean in `fvm.py:78` and `fdm.py:134` moves a hatched zone by +26 % (fill 0.75),
+45 % (0.5) and +42 % (0.25), and four exact-value tests by 0.05 to 0.07 K. A zone fill is a density typed by a person; its pattern is unknown, and no function of the fraction is right for a grid, stripes and islands
(7 to 43 % too cool with the arithmetic value, -20 to +22 % with the geometric one). The imported copper therefore gets **its own element**, and the zone fill keeps its meaning.

*Phase 2 of three of the Gerber research (`research/gerber-import`, `research/gerber-models`, `research/gerber-nets`); the section numbers of the README (4.x) are those of the original single study.*

## 0. Why not import the copper as polygons (zones), and why an interface at all

*Answer to "do the models have to change, or an intermediate layer?" (README 4.31 and 4.34): both, in a fixed order. The intermediate layer is the importer (`lib/faces.py` today (reading is `research/gerber-import/lib/importer.py`), `pcbthermal/copper.py` in the design below): it turns files into per-layer face conductances, vias and nets and hands the model data it already understands, so the program's physics and file format do not change. The FVM then needs only to accept faces instead of the harmonic mean of cell values (done in the prototype by the `FaceNetwork` subclass, without editing `fvm.py`); the FDM and the 3D solid need the same small change; the Lumped and the Analytic cannot take faces and need their own reduction of the mask. Handing every model a cell value instead (the cheap way, no model change) was measured on our board: +14 to +24 % in the FVM and FDM, +29 to +43 % in the Lumped (re-run by the review, README 4.34).*

*Status: the import stage itself exists as research code, `lib/faces.py` (README 4.31, figure 3): reading, vias, face conductances and a `FaceNetwork` for the FVM. The interface (layer confirmation, outline, heaters) and the FDM/3D faces are still design only.*

The question ("is a Gerber not just copper as polygons, like the zones we draw?") has a short answer: **in geometry yes, in what the solver does with it no, and the solver is where the work is.** Facts checked in the code and by tests (README 4.27):

1. **`Zone` is one polygon and a scalar fill**: `Zone(layer, polygon (n, 2), fill, name)`, no holes and no islands. Gerber copper is polygons with holes (one layer of an Uno clone: 103 polygons, 80 holes, 43 285 vertices, `research/gerber-import/README.md` 4.1), so a layer would be thousands of zones, with holes cut by splitting.
2. **Zones are combined per cell with a maximum, not a sum** (`fvm.py:77`, `fdm.py:136`, `solid3d.py:159`, `analytic.py:133` and `216`, `checks.py:37` on `develop` at `a6f822b`): two zones that each cover half a cell give half a zone's copper. Copper tiled in many abutting polygons therefore loses copper in every shared cell: +7 % (FVM) to +17 % (FDM) hotter for the same copper cut into strips (`tests/test_program_union.py`). Drawn zones are usually few and large, so it rarely shows today.
3. **Each cell takes the fraction of copper and mixes it arithmetically** (`S = f k_cu t_cu + k_lam (slab - f t_cu)`, the coverage sampled 4 x 4 per cell). For a big solid zone the cells are 0 or 1 except at the edges and this is exact; for fine copper (tracks, clearances, hatch) almost every cell is partial and the arithmetic mix is cool: 16 to 18 % against the program's own pixel run and 24 to 26 % against an independent 3D solution of real one-layer copper (README Review R2; 10 to 23 % in the one-sheet studies). So polygons would work mechanically, with a different union rule and holes, and still give the biased answer.
4. **What changes is the mapping from geometry to conductance, not the format.** The copper can be held as polygons (shapely) or as a mask; what matters is that it is drawn on a fine grid (coverage mask, README 4.26) and mapped to the faces of the model's own grid. The same engine could serve the drawn zones too (rasterise the polygon finely, map the cells; the exact-aligned rectangles stay exact), which would give one mapping for drawn and imported copper; `fill < 1` (hatching) keeps its formula or gets a declared pattern.
5. **Why an interface**: not for the physics, but for what the files do not say (layers, drill units, outline, which holes are vias, stack-up, nets, the pixel the thinnest track needs); the list and the form of the confirmation step are the import's, `research/gerber-import/INTEGRATION.md` section 2.

## 1. Where the copper fraction enters (line numbers of `develop` at `a6f822b`, checked by the review)

| File | Lines | What happens |
| :-- | :-- | :-- |
| `pcbthermal/fvm.py` | 73-78 | `f` per layer and cell: the union (`max`) of the zones, each `coverage_fraction * z.fill` |
| | 80-84 | `S = (f k_cu t_cu + k_lam (slab - f t_cu)) * cover` (sheet conductance; on a one-layer board `slab` is the copper node, copper plus half a laminate gap, the rest is in the laminate nodes of `laminate.py`) and `C` (heat capacity, arithmetic: right as it is) |
| | 257-258, 324-325 | the faces: `harmonic(S[...], S[...]) * dy/dx` and `* dx/dy` (two assemblies) |
| `pcbthermal/fdm.py` | 134-137 | the same `fill` at the nodes, the same formula for `S` and `C`; the face is the arithmetic or harmonic mean of two nodes |
| `pcbthermal/solid3d.py` | 157-159, 173-181 | `fill`; the copper slab gets `kx = f k_cu + (1 - f) k_lam` (the through value `kz` is a different question) |
| `pcbthermal/lumped.py` | 184 | reads `net.S` of the FVM network: it gets any change of `S` for free |
| `pcbthermal/analytic.py` | 131-143, 213-216 | the fraction is averaged with the influence of the heaters, then `S = f_avg k_cu t_cu + ...` |
| `pcbthermal/blocks.py` | 121-123 | the contact of a metal block uses `f` as the area fraction over copper: arithmetic is right |
| `pcbthermal/checks.py` | 34-37, 63-68 | `f` for the warnings (copper edge under a heater, no copper): unchanged |

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

Only where the cell conductances are read, and only when imported copper exists. Without imported copper nothing changes: the zones, the fill formula and every test stay as they are. With it: `fvm.py`, `fdm.py` and `solid3d.py` take the face conductances of the layer from the mask instead of the harmonic mean of the cell values (about one function each, the matrices keep their shape and the solvers are untouched); `lumped.py` needs nothing, it already reads `net.S` of the FVM network; `analytic.py` gets one effective conductance per layer (influence-weighted geometric-type mean) instead of the average fraction. A heat source from a net (`joule.py`, `research/gerber-nets/README.md` 4.20, picture: `../gerber-nets/figures/fig_02_nets_and_joule.png`) enters as ordinary power per cell and needs no model change at all.

### What each model does

* `fvm.py`: after `self.S`, if a layer has a mask, store its face conductances (`gx`, `gy` per layer); `_assemble` (lines 210-213 and 277-280) uses the stored faces for those layers and the harmonic mean of `S` for the others. The vias, the vertical links, the losses, the blocks and the capacity are untouched.
* `fdm.py`: the same on the nodes (the face between two nodes comes from the mask); `solid3d.py`: `kx`, `ky` per slab from the cell conductances; `lumped.py`: reads `net.S`: give it the mean of the two directional values of the layer (measured against the program's pixel run: 27.7 % falls to 15.5 to 17.9 %, `README.md` 4.16); `analytic.py`: keeps ONE effective conductance per layer, but not the arithmetic fraction (30.4 % too cool): the mean weighted by the heater's influence K0(r/lambda), as a power mean with p = -0.2 (MAE 8.8 %), or the flow-based conductance of the window (10.0 %); per-cell values do not help it (22 to 23 %).
* The GUI: an element "Imported copper" per layer (a preview of the mask, the pixel size, the layers assigned), the zone's `pattern` and `pitch`, tooltips and the user guide (CLAUDE.md rules).

## 3. Storage and import

* The masks themselves (pixel size, storage in the project file, the reader, the layer assignment, which holes are vias): `research/gerber-import/INTEGRATION.md` section 1. This folder takes the mask of every layer as given.
* Cost per layer, paid once at import and cached with the project: 0.1 s (200 000 pixels) to 1.1 s (1.6 million = 100 x 160 mm at 0.1 mm) for the flow-based faces on a quiet machine (README 4.15); memory about 1.4 KB per pixel (strips for larger boards); the quick mode costs 0.02 s.

## 4. Choosing the mapping

| Mapping | Accuracy (see `README.md`) | Cost | Role |
| :-- | :-- | :-- | :-- |
| flow-based faces | one-sheet studies: single layer 0.6 to 0.9 %, two layers 0.4 to 1.3 %, four layers 0.3 to 2.0 %, regular patterns 0.9 to 3.4 %; the program now: 2.3 % on eleven boards, 1.1 to 1.5 % on seven real windows | a few seconds per layer | **default** for imported copper |
| bounds, lambda 0.5 | one-sheet: 1.0 to 1.3 % on single layers, 0.5 to 1.0 % two layers; 1.3 to 7.5 % on a four-layer board with planes; diagonal copper +10 to +12 % at 0.6 mm; the program now: 2.4 % on eleven boards | negligible | quick preview, fallback |
| geometric mean | 2 to 3 % on random real copper, -20 to +22 % on regular patterns (one-sheet); 7.9 % on eleven boards in the program | none | last fallback when no mask is kept (random copper only) |
| arithmetic fraction (the program's) | 10 to 11 % too cool on real copper in the one-sheet studies, 16 to 18 % in the program now, 24 to 26 % against an independent 3D solution; 7 to 43 % on patterns | none | only for the zones as typed |

*All accuracies are against a resolved mask of the same layered model; the program's own pixel run is 5.5 to 13.6 % cool on patterned one-layer copper against an independent 3D solution (README Review R2), an error no mapping removes.*

## 5. What a change does to the program's tests

* A scratch copy of the program with the geometric mean in the zone formula (`README.md` 4.10): 321 tests pass, 6 fail (two only because the documents are not in the copy; four exact-value tests move by 0.05 to 0.07 K), the hatched zones move by 26 to 45 %.
* The design above leaves every existing board unchanged, so the existing tests and examples do not move; new tests are needed for the mask element, the mappings (the research tests are a start: `research/gerber-models/tests`), the import and the GUI.
* To validate in the repository's way: a `docs/validation.md` section with the tables of the studies, the equations in `docs/theory.md`, a thick-copper multi-layer board of a real design, and the comparison with a measurement if one becomes available.

## 6. Risks and open questions

* The flow-based faces and every other mapping were validated against a **finer simulation of the same model**, never against a measurement; all the boards are public hobby designs. One independent check (README Review R2): against a 3D solution the program's two laminate nodes are 5.5 to 13.6 % cool on patterned one-layer copper (half a laminate gap at the copper's temperature bridges the clearances; more nodes close the gap: 1.9 and 5.3 % with eight). Imported copper would make this limit of the program visible; a finer laminate under patterned copper is a decision for the program.
* Diagonal copper is limited by the five-point stencil (no cross terms): about 1 to 3 % for the flow-based faces, up to 12 % for lambda.
* Heat capacity and the through-thickness conduction stay arithmetic; the time response follows the steady one (`study_transient.py`).
* How the Lumped and Analytic models should use a mask is open: they average over rings or regions much larger than a cell.
* The zone `pattern` needs a decision of the maintainer: which patterns, which default for files that already use `fill` below 1 (kept as it is, with a warning that the arithmetic value is the optimistic limit?).

## 8. Two corrections to the program found by the research, with their measured impact (README 4.39)

1. **Combine zones by the maximum per sample point, not per cell** (`geometry.zone_fill`, used by `fvm.py`, `fdm.py`, `solid3d.py`, `analytic.py`, `checks.py` in place of the loop with `np.maximum`). Copper tiled in abutting zones is no longer lost (-8.2 % FVM, -19.1 % FDM, -8.3 % 3D on 0.5 mm strips: back to the single-zone value); overlapping zones keep the larger fill (the FDM moves by -0.5 % on a partly overlapping pair, from its node averaging); **the example boards do not move at all**. The simpler additive rule double counts overlap (-8.2 %) and failed four program tests: not proposed.
2. **Laminate under a single copper layer in `solid3d.py`**: **done in the program** (`develop` `0ea5f07`, FR-4 slabs under the copper of a one-layer board). The peak of a single-layer pad board went from 346 to 174.5 K (the same board with a second, empty layer: 174.5 K).

The first was applied to copies of the program outside the repository (re-made by the review on `develop` at `a6f822b`: strips -8.2 % FVM, -19.1 % FDM, -8.8 % Lumped, -7.4 % Analytic, -8.3 % 3D; overlapping zones and the example boards unchanged); adopting it is a normal change on a `fix/<topic>` branch with the documentation, tests and whole battery (rules in CLAUDE.md).

## 9. Diagonal faces in the network (design, prototype `lib/diagonal.py`, README 4.44)

* **What changes in the program**: `fvm.py` `_assemble` (and `fdm.py`, `solid3d.py` for the plan couplings) add, per cell, two diagonal couplings (`[i, j]` to `[i + 1, j + 1]` and `[i, j + 1]` to `[i + 1, j]`) with their own conductance arrays; a model without them is the present five-point network, so every existing board is unchanged (the prototype's `solve9` with zero diagonals equals the five-point solver to 1e-9).
* **What the import gives**: the flow-based axial faces as in section 2, and the diagonal conductance of each cell from the cell tensor (`diagonal.hybrid_faces`), multiplied by a share (0.5 in the experiment). Zones drawn by the user have no diagonal faces.
* **What the experiment says**: a lone diagonal track is reproduced at 64 to 94 % (45 degrees, share 0.5) instead of 37 to 84 %, the 42 real windows stay at 1.77 % (1.85 % without); with the whole missing conduction the windows get worse (3.1 %, -2.8 % bias). **Not ready for the program**: the share is a fudge factor, and the detector tried (README 4.48) failed the held-out test (4.50); the Lumped and the Analytic would not use the diagonal faces.

