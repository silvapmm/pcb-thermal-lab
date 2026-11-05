# Roadmap entries (text for `docs/versions.md`, chapter "Planned", and for `research/ROADMAP.md`)

*Draft; to be adopted by the maintainer. No dates. The branches in small steps are in `INTEGRATION.md` section 9.*

## For `docs/versions.md` ("Planned"), after the investigation `research/gerber-real-boards`

* **Import of a Gerber set** (feature, 2.5.0): our own reader (NumPy only, from `research/gerber-import`), `TO.C`/`TO.N`/`TO.P` kept apart, the pixel from the thinnest feature, imported copper as an element with its heat capacity, plated holes as vias, the default mapping decided by the study of the faces with the laminate rule (the flow-based faces if confirmed), a refusal message naming the file and the feature.
* **Parts from the paste layer** (feature, 2.5.0): `TO.C` groups, placement files (KiCad, JLCPCB, Altium, EasyEDA CSV) matched by name, a click that creates the part with a box or a hull; proximity groups only as a marked fallback; the X3 component layer in 2.5.0 or 2.6.0; ODB++ and IPC-2581 after their specifications are read.
* **Memory guard with the import terms** (feature, with the guard already planned): the raster (about 55 bytes per pixel per layer in the research pipeline) and the face construction, re-measured on the implementation.
* **Project file format 2** (feature): written only with imports, the problem nested under a key so that 2.4.x refuses the file instead of dropping the imports, a `.bak` before the first format 2 save, refusal of newer formats; embedded binary masks (0.16 MB for a 4-layer 100 mm board at 0.05 mm).
* **Lumped and Analytic on imported copper**: always warn (1 to 16 % cool in 24 windows), never refuse.

## For `research/ROADMAP.md`

* The flow-based faces with the laminate rule on, against an independent 3D reference, on two-layer and four-layer windows (decides the default mapping).
* A transient reference whose mask resolves the thinnest track, and a second board for the transient.
* Read the rest of the Gerber specification with the page numbers written down: the attribute dictionary, the aperture-block usage, the transformations and the paste file functions.
* Obtain the ODB++ specification (a registration) and read IPC-2581 before any reader of them is written.
* Measure a physical board (no board exists yet): every accuracy statement of the import is against another model of the same physics.
* Diagonal copper on a coarse grid (the largest residual error of the cell models) remains open.
