# How real-board import would enter the program (design, not implemented)

*Release 2.5.0, theme "real boards: import a Gerber set without blowing the memory". This is a design; the first block of studies has run (paste groups, placement files, X3, ODB++, conformance and rare primitives, the project file) and section 7 says what it confirmed and what it changed; the other studies (copper mapping, time and memory, transient, Lumped and Analytic rule, fine-copper warning) have not run, so every statement that waits for them says so. The earlier design documents are `research/gerber-import/INTEGRATION.md` (files to masks, holes, nets, outline) and `research/gerber-models/INTEGRATION.md` (the copper mapping in the models); this one adds the parts, the project file, the memory guard and the warnings.*

Short answer: **a small import package with no new dependency (our own reader), an imported-copper element that hands the models face conductances, a paste-to-part step that turns paste groups into parts, a guard that estimates the memory before building, and a project-file format 2 that stores what the import understood.** The physics of the models does not change; zones keep their formula.

## 1. What changes in `pcbthermal/`

| Where | Change | Depends on |
| :-- | :-- | :-- |
| new `pcbthermal/gerber/` (reader) | the independent reader of `research/gerber-import/lib/native_gerber.py` (about 1000 lines, NumPy only) moved in, with the importer (box, masks, holes matched to pads and nets); a refused feature is reported with the file and the feature | study 4.6 (conformance, rare primitives) |
| new `pcbthermal/gerber/parts.py` | **the parts named in the paste layer (`paste.by_reference`, `TO.C`) first; proximity groups only as the fallback when the file names nothing (and marked approximate)**, the placement files (`pnp.read_placement`; matched **by reference designator**, with the identity frame as the default and the mirrored X of KiCad's bottom side), the X3 component layer (`x3.components`), later ODB++; the result is a list of candidate parts with reference, footprint and shapes | study 4.4 (run: section 7) |
| `pcbthermal/model.py` | an imported-copper element per layer (`ImportedCopper`: the mask at the import pixel, the box, the layer index; the mask is binary or 8-bit coverage); `Problem.imports` (list) and its JSON | study 4.8 |
| `pcbthermal/copper.py` (new) | the mapping from the masks to the face conductances of a grid (the flow-based faces as the default, lambda 0.5 as the quick mode; the arithmetic fill stays for zones), and the copper capacity per cell | study 4.1 |
| `pcbthermal/fvm.py`, `fdm.py`, `solid3d.py` | accept the faces of the imported layers in place of the harmonic mean of the cell values (the research prototype is a subclass that replaces `_assemble`; in the program it is an optional argument), and take the heat capacity of the copper from the coverage (`boardrun.set_capacity` in the research folder: without it a transient of an imported board has no copper capacity) | studies 4.1, 4.3 |
| `pcbthermal/lumped.py`, `analytic.py` | no change of algorithm: they are run on the cell fill of the import and **warn or refuse** by a rule on the fine-copper indicators | study 4.5 |
| `pcbthermal/checks.py` | the fine-copper warning (a detector on the masks, the threshold from the calibration), the unsupported-feature refusal, the plated-hole and paste checks | study 4.7 |
| memory guard (the item of `docs/versions.md`, "Planned") | the estimate `baseline + unknowns x coefficient` with the coefficient measured on imports, adjustable in Preferences; refuses before the mask is drawn at a pixel the board cannot afford | study 4.2 |
| `pcbthermal/project.py` | format 2 (section 3) | study 4.8 |
| `pcbthermal/gui/` | an import dialog (a layer table to confirm roles and order, the units of a drill file, the outline, which holes are vias, the paste layer and the placement file), a preview of the masks with the fine-copper cells marked, "create part from paste" by clicking a group and "create all parts", tooltips, user guide, `tests/test_gui_stress.py` scenarios | decisions of section 6 |

## 2. What does not change

* The physics of every model; `Zone.fill` and the union of zones (the evidence that a fill must keep its formula is in `gerber-models` 4.10, 4.27, 4.39); existing projects open and give bit-identical results (a project with no import takes the old code path).
* The program has no new dependency: the reader is NumPy only; gerbonara and shapely stay a test reference in the research environment.
* A part imported from the paste layer is an ordinary heater/component of the program (the worst-case convention: all the power enters the board; the junction resistance and the top path are the user's, as for a drawn part).

## 3. The project-file format 2

*Prototype: `lib/project_format.py` (pack, unpack, migration, downgrade), measured by `scripts/study_project_file.py`; the tests are in `tests/test_fine_memory_format_odb.py`.*

* **Format key.** Format 1 is `pcbthermal-project-1` (`pcbthermal/project.py`: the problem JSON plus `solver`, `view` and `app_version`); format 2 is `pcbthermal-project-2` and keeps every key of format 1 and adds one list, `imports`. **Migration 1 to 2** adds an empty list and changes the key (exact, tested); **2 to 1** is refused when the list is not empty (the copper would be lost), otherwise exact. A file with no `format` key (a plain native file) is read as format 1.
* **What an import record stores** (one per imported board): the name, the pixel of the masks, the box in the file coordinates, the settings of the import (layer roles and order, the units of the drill file, the outline choice), per copper layer its name, role and mask, the plated holes (position, diameter, via or component hole), the imported parts (reference, footprint, the paste-group box and the shape chosen), the warnings of the import, and **the source files by name, size and SHA-256 (never by path of the user's disk)**.
* **Embedded or referenced masks.** Embedded: the mask is packed (bits for binary, a byte for coverage, deflate, base64) in the record; the project is self-contained, opens on another machine and does not depend on files that may have moved or may not be redistributed. Referenced (`"embed": false`): only the roles and the file identities; the mask is redrawn from the Gerber files when the project opens, which needs them and costs the import time. **Proposed default: embedded at the pixel of the import, binary masks**; the size on seven real boards (study 4.8) is 0.02 to 0.43 MB at 0.05 mm (0.16 MB for a 4-layer 100 x 100 mm board; criterion 20 MB) and 0.04 to 0.87 MB at 0.025 mm, so **the "reference only" option is not needed for the size**; the 8-bit coverage mask costs 1.5 to 2 times the binary one after compression (not eight times), so what the 8 bits are worth against the 1 bit is decided by study 4.1 alone.
* **A program older than the change opening a format 2 file (measured).** Opening a file with `"format": "pcbthermal-project-2"` and an `imports` list in the released 2.4.5 raises no error and no message, **drops the imports, and a Save writes the project back as format 1 without them** (study 4.8; unknown keys inside `board` and inside a zone are accepted as well). So a format 2 file in an older program is a data-loss path, not only a missing layer. Options for the maintainer: (a) accept it and say so in the release notes; (b) write next to `imports` a coarse zone fallback that older programs read (a cell-sized zone per mixed cell: large, and a different physics); (c) a **different file extension or name for projects with imports**, so the older program does not offer the file in its dialogs by default (it still opens it by hand: this lowers the risk, does not remove it); (d) a patch release of 2.4.x whose `project_from_dict` refuses a `format` it does not know (it protects only the machines that install the patch). The investigation's recommendation after the measurement: **(c) plus the new version writing a visible message and a `.bak` copy of the older file when it migrates**, and (d) if the maintainer wants the old versions covered; (a) alone is not recommended now that the loss on Save is known.

## 4. Memory (what the guard needs from the studies)

* The unknowns of an imported board are `layers x cells` for the face network; the program's own count with the laminate rule is ragged (`fvm.unknowns`). The coefficient to use (bytes per unknown, with the laminate nodes and imported faces) and its scatter come from study 4.2; the older figures (2.8 KB per unknown for the layered FVM on a plain board, 7 GB per million measured on refined boards, 6.6 to 19.3 KB for the 3D solid) are not used until it has run.
* The mask itself is memory too: a coverage mask at 0.025 mm of a 100 x 100 mm layer is 16 million pixels (128 MB as float64, 16 MB as bytes) before the supersampling transient of the reader (a binary canvas at the sub-pixel); the importer must draw layer by layer and keep bytes, not float64.
* The guard refuses **before** drawing: pixel, cell and layers give the estimate; the message says which cell fits.
* **Measured in the first block**: the research importer holding every layer's binary and coverage arrays together reached about 6.5 GB for the seven boards at three pixels (the largest case is probably CO60 at 0.025 mm: 285 x 95 mm); a guard for the *mask* is needed besides the one for the unknowns, and the importer should draw layer by layer and keep bytes (the per-board figure is the study 4.2 job, not run).

## 5. Risks and limits (stated, not hidden)

* **Fine copper**: the cell models are approximate when the copper is finer than the cell; the warning (4.7) says so, with a threshold from the calibration; isolated diagonal copper on a coarse grid is the largest residual error known and is not fixed by the faces (the diagonal gate failed its held-out test in `gerber-models` 4.50).
* **Lumped and Analytic** are 16 % and 26 % below the FVM on the rectangle board; on imports they warn or refuse (4.5).
* **No measurement**: no physical board exists yet; every accuracy statement is against another model of the same physics. The documents must say so.
* **A part from the paste is a footprint, not a package**: the junction resistance, the top path and the power are the user's; a part with no paste opening (through-hole, glued) is not found; placement origins differ between tools (the registration finds the offset from the data and reports how many parts matched).
* **Copper thickness and stack-up** are not in the Gerber copper files: the program's stack-up (typical templates, the Gerber job file's board thickness and layer count when present) supplies them; the user confirms.
* **Plated holes become vias** (open barrels of the hole's diameter; a component lead is not modelled); a via and a component hole are told apart by the aperture function when written and by a diameter filter and a preview when not.
* **Licences of user files**: nothing of a third party's board is stored by the program except what the user's project embeds (the user's own files); the research folder stores none.
* **Placement frames**: on the five boards that name their parts the placement frame equals the Gerber frame (offset below 3 micrometres, no sign flips) except that **KiCad's combined position file mirrors X on the bottom side**; the vote registration on unnamed proximity groups returned wrong offsets on two of five boards, so it must not be the default. Without names (RP2040, CO60, vstcm) the match is approximate and the program says so.
* **A line thinner than the pixel is silently lost**: a 0.01 mm line at a 0.05 mm pixel with supersampling 2 gave an area of 0 (exact 0.400 mm2); the importer must derive the pixel from the thinnest feature of the layer or warn.
* **Specification only partly read**: the component-layer, `.C`/`.Cxxx` attribute and `AB` overview sections of revision 2026.05 were read (README section 8); the attribute dictionary, the aperture-block usage and transformation chapters and the file functions of paste layers were not, and must be read before the refusal of `AB`, `LM`, `LR`, `LS` is lifted.

## 6. Decisions for the maintainer

1. The default mapping (after study 4.1) and whether the flow-based faces need an optional mode switch in Preferences.
2. Embedded or referenced masks by default, and the pixel stored (after 4.8); coverage or binary.
3. What to do about a format 2 file in an older program (section 3).
4. The paste footprint that a click gives the heat source: bounding box, hull or the largest opening (after 4.4).
5. Refuse or only warn for Lumped and Analytic on imports (after 4.5).
6. The scope of 2.5.0: `TO.C` and the placement files are cheap; X3 and ODB++ are more; IPC-2581 is not read at all.
7. The order of the specification reading and who obtains the ODB++ specification (a registration is needed).
8. Whether the research code is moved into `pcbthermal/` as it is (the reader is validated; the face network, the paste and the placement code are prototypes with tests but no run).

## 7. What the first block of studies confirmed and changed

| Design choice | Evidence | Status |
| :-- | :-- | :-- |
| Own reader, no new dependency | 105 of 108 comparable files within 3 % of gerbonara + shapely, the 3 others explained (an outline stroke twice, a file with step-and-repeat that the second reader ignores and where ours matches the specification's picture); 2 files refused with a message (aperture blocks); no real board of the seven uses `AB`, `LM`, `LR`, `LS`, the moire macro, image polarity or the deprecated commands | **confirmed**; lifting the `AB` refusal is not needed for 2.5.0 |
| Paste layer gives the parts | proximity groups reproduce the part in 50 % (ISASTM) to 0 % (StickHub) of the cases at their best link distance: criterion 95 % **failed everywhere** | **changed**: the part comes from `TO.C` where the file has it (4 of 7 boards), proximity is a marked fallback, and the user can correct a group by hand |
| Placement file registered from the data | the vote on unnamed groups was wrong on 2 of 5 boards; by name the frames agree to micrometres | **changed**: match by reference designator, identity frame by default, mirrored X for the bottom side of KiCad's combined file, a visible count of matched parts |
| Footprint of the heat source | bounding box against convex hull: hottest cell +5 to -1 %, mean over the box 1 to 7 %; the largest opening alone 1.6 to 3.9 times hotter | **bounding box or hull**; never a single opening; the choice is left to the maintainer (decision 4) |
| X3 component layer | 35 of 35 parts with origin, courtyard, pins; all named in the paste file | **confirmed as cheap** (reference, footprint, value, rotation, courtyard; `.CHgt` and `.CMnt` exist in the specification) |
| ODB++ | the record layout from memory worked on 3 archives from 2 exporters; components, paste, copper and stack-up order in one frame (pins on paste flashes to 1.5 micrometres), no registration; heights in 2 of 3 | **feasible for a later release**; needs the specification (registration) and a Gerber set of the same job to verify the frame |
| Embedded masks in format 2 | 0.16 MB for a 4-layer 100 x 100 mm board at 0.05 mm against a 20 MB criterion; round trips exact; migration lossless | **confirmed**; the risk of an older program (section 3) is real and measured |
| Memory | the research importer reached 6.5 GB on the project-file run | **open**: the guard must also cover the masks; study 4.2 not run |

Decisions that the numbers now let the maintainer take: 2 (embedded binary masks), 3 (the old-program path: the loss on Save is measured, recommend (c) plus the message), 4 (bounding box or hull), 6 (scope: `TO.C` and placement by name are cheap and robust; X3 cheap; ODB++ later). Still waiting for the heavy block: 1 (the default mapping), 5 (refuse or warn for Lumped and Analytic) and the memory guard coefficient.
