# Roadmap entries (text for `docs/versions.md`, chapter "Planned", and for `research/ROADMAP.md`)

*Draft; to be adopted by the maintainer after the studies have run. No dates.*

## For `docs/versions.md` ("Planned"), after the investigation `research/gerber-real-boards`

* **Import of a Gerber set** (feature, 2.5.0): our own reader (NumPy only, from `research/gerber-import`), imported copper as an element that hands the models face conductances (the flow-based faces as the default if study "copper mapping" confirms it), plated holes as vias, the heat capacity of the copper from the coverage, a fine-copper warning, a refusal message naming the file and the feature for what the reader does not implement.
* **Parts from the paste layer** (feature, after the investigation): paste groups as footprints, reference designators from the Gerber X2 `TO.C` attribute, from placement files (KiCad, JLCPCB, Altium, EasyEDA CSV) and from the X3 component layer; a click on a group creates the part; ODB++ and IPC-2581 only after their specifications are read.
* **Memory guard with the measured coefficient for imports** (feature, with the guard already planned): the bytes per unknown for the face network with the laminate nodes, adjustable in Preferences.
* **Project file format 2** (feature): `imports` list, embedded or referenced masks, migration 1 to 2.
* **Lumped and Analytic on imported copper**: warn (and refuse above the threshold of the study) instead of running silently.

## For `research/ROADMAP.md`

* Read the Gerber specification sections on attributes, the component layer, aperture blocks and transformations (the PDF text must be extracted in an environment with a PDF library).
* Obtain the ODB++ specification (a registration) and read IPC-2581 before any reader of them is written.
* Measure a physical board (no board exists yet): every accuracy statement of the import is against another model of the same physics.
* Diagonal copper on a coarse grid (the largest residual error of the cell models) remains open.
