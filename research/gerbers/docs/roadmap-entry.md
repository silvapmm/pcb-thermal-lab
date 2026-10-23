# Roadmap entry for the research branch

Ready to apply to `docs/roadmap.md` when the maintainer adopts the work (against the text of `develop` on 2026-10-23).

**Replace** the bullet "**Gerber and Excellon import** of the copper per layer (candidate library `gerbonara` [1]) ..." under "Import of copper and parts" with:

* **Gerber and Excellon import** of the copper per layer, **researched on `research/gerbers`** (`research/gerbers/CONCLUSIONS.md`): the files are read without third-party libraries (NumPy only: copper layers, drills, X2 attributes), drawn as a coverage mask at 0.1 mm (pixel at most half the thinnest track) and mapped to the face conductances of the grid with the flow-based method (lambda 0.5 as the quick mode), because the plain fill fraction per cell is 10 to 23 % too cool on real copper (it hides connectivity). Imported copper is its own element (`Zone.fill` keeps its formula; zones are one polygon without holes and are combined per cell with a maximum); FVM, FDM and the 3D solid take the faces from the mask, Lumped reads the FVM conductance, Analytic gets one effective conductance per layer. Plated holes become vias (drill file plus the aperture function `ViaPad`), and the X2 net names tie the polygons to nets. Needs a layer-assignment step (file function or name, confirmed by the user), the unit of a drill file without one, and a validation on a board with a measurement. Stages and risks in `research/gerbers/INTEGRATION.md`.
* **Nets and the heat of a net** (new): the current of a net between two terminals gives the Joule heat per cell (`research/gerbers/lib/joule.py`, exact I²R); missing: the current per net or pad, vias between layers, rho(T) coupling and the interface.

**Replace** the bullet "**Orthotropic copper** from the raster (conductivity along x and along y of a cell with traces)." with: **Orthotropic copper** is part of the import above (directional face conductances; the two Wiener bounds and the flow-based faces were compared on 42 real windows and on stripes across and along the heat flow).

**Add** under "What has been implemented" nothing yet (nothing of this research is in the program).
