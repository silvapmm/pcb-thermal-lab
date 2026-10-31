# Real boards: importing a Gerber set without blowing the memory (investigation plan, prepared, not run)

**Status: prepared.** Every study below has its script and tests written and compiled; **none of them has been run** (the machine was busy and the maintainer wants the runs after the 2.4.5 release). So this README has no result tables yet: each section says the question, the method, the reference, the success criterion (fixed before the run) and what the study will not verify. When the runs are made, the numbers the scripts print are pasted into the "Results" line of each section and the last section is updated. Nothing in `pcbthermal/` is changed (the program is only imported).

Release theme this serves: **2.5.0, "real boards"**: import a Gerber set (our own reader, no third-party dependency), turn it into the program's model, and do it without exhausting the memory. Decisions of the maintainer that bound the work: our own reader (the independent NumPy reader of `research/gerber-import`, validated pixel by pixel there); no physical board is available yet (so nothing here is a measurement, and the models keep their limits, which the program warns about); tests are local only.

Sections of this README: 1 question and what would answer it; 2 what the earlier research already settled; 3 the boards and the sources; 4 the studies (4.1 to 4.8); 5 how to run; 6 what the preparation found on the way; 7 decisions left to the maintainer; 8 what was read and what was not verified.

## 1. The question, and what would answer it

*Can a real board (several copper layers, hundreds of parts, 0.1 mm tracks) go from its Gerber files to a thermal model in the program, with a stated accuracy and a stated cost, and can the program tell the user when the answer is not to be trusted?*

It breaks into eight questions, each with its own study (section 4):

| Study | Question | What would answer it |
| :-- | :-- | :-- |
| 4.1 copper mapping | Which conductance does an import give each cell by default: the arithmetic fill fraction (what the program does for zones), the flow-based faces, or another? | error of each mapping against a resolved reference on real copper, with the program of 2.4.5 |
| 4.2 time and memory | What does a whole real board cost at 0.5 and 0.25 mm cells, and how many bytes per unknown does the memory guard need now that the laminate nodes exist? | peak resident memory and seconds, phase by phase, in fresh processes, and a fit |
| 4.3 transient | Does the step response of an imported board converge with the cell size, and what is missing for a transient? | step responses at three cell sizes against a pixel-grid reference |
| 4.4 paste, placement, X3, ODB++ | Can the paste layer become component footprints and heat sources by a click, with reference designators and positions from the files? | groups, references, registration, the click, the heat-source shape |
| 4.5 Lumped and Analytic | When should the program warn, and when refuse, to run these two models on imported copper? | their error on real windows against the indicators of fine copper |
| 4.6 conformance and rare primitives | Does our reader agree with the Ucamco test files, and do real files use what it refuses (aperture blocks, LM/LR/LS)? | the files themselves |
| 4.7 fine-copper warning | Which indicator and which threshold say "the copper is finer than the cell"? | a calibration of two indicators on the measured errors |
| 4.8 project file | How big is a project that embeds the imported copper, and does the format migration lose nothing? | sizes on real boards and a round trip |

### 1.1 Diagrams

![The chain from the files of a board to the models](figures/fig_01_import_chain.png)

*Figure 1 (`figures/fig_01_import_chain.png`): the chain this investigation tests, from the Gerber set and the placement data to the program network and the project file. Grey boxes are not built (ODB++ is planned, the project file is a prototype).*

![The paste layer as a component](figures/fig_02_paste_to_footprint.png)

*Figure 2 (`figures/fig_02_paste_to_footprint.png`): a QFN seen from above. Left, the paste openings (perimeter pads and an exposed pad split into four windows, as CAD tools do). Middle, the three footprints a group can give the heat source: bounding box, convex hull, the exposed pad. Right, the click that picks the group, whose reference comes from `TO.C` in the file or from the placement file. Schematic, no data.*

![Copper finer than the cell](figures/fig_03_fine_copper_cell.png)

*Figure 3 (`figures/fig_03_fine_copper_cell.png`): the same stripes under a 1 mm and a 0.2 mm cell. At 1 mm every cell is mixed and all the copper is thinner than the cell: the conduction across the stripes is what the cell conductance can only approximate (study 4.7). Schematic, no data.*

The data figures 4 to 7 (mapping errors, memory per unknown, step responses by cell size, the fine-copper threshold) are drawn by `scripts/make_figures.py` from the result files once the studies have run.

## 2. What the earlier research already settled (and what this adds)

From `research/gerber-import` and `research/gerber-models` (read for this preparation; their numbers were not re-run here):

* the NumPy-only reader draws the same pixels as gerbonara + shapely, refuses what it cannot do (aperture blocks, transformed apertures, image offset, mirror, scale and rotation, the moire primitive) and reads net names (`TO.N`); the pixel must be at most half the thinnest track; a coverage mask beats a binary one;
* the program's arithmetic fill fraction is biased cool on real copper (clearances cut paths): 16 to 18 % against the program's own pixel run, 24 to 26 % against an independent 3D solution, on seven real windows; the flow-based faces (Sampson's method, not ours) were within 1.1 to 1.5 % (mean) of the pixel run; lambda 0.5 is the cheap alternative; diagonal copper on a coarse grid is the largest residual error, and the diagonal gate did not hold up on held-out windows;
* the program's network takes face conductances without a change of algorithm (`faces.FaceNetwork`, reproducing the program's own formula to 1e-6 K);
* the Lumped and Analytic models were 16 % and 26 % below the FVM on the rectangle board, and no more than a warning is possible for them.

What was **not** done there and is prepared here: a 0.05 mm pixel with the nine-point reference on windows of boards with paste layers; the program of 2.4.5 (laminate rule, point via) in the loop; whole boards at 0.25 mm; the memory per unknown with laminate nodes; the transient of an imported board; the paste layer, the placement files and ODB++; the warn-or-refuse rule for the two simple models; the rare primitives in real files; a detector for fine copper; the project-file format.

## 3. The boards and the sources

Real open boards with **paste layers and a placement file** (found by a search of GitHub through the `gh` tool; licences are the spdx identifiers of the repositories; nothing is stored in this repository, `scripts/fetch_boards.py` downloads into `data/`, which is git-ignored):

| Key | Project | Licence | Layers | What it holds | Status of the facts |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `isastm` | Manawyrm/ISASTM, STM32 ISA-over-USB adapter, KiCad 5.1.6 | GPL-3.0 | 4 | copper (F, In1, In2, B), edge cuts, PTH and NPTH drills, **F_Paste and B_Paste with `TO.C` per part**, `all-pos.csv` (KiCad) and `cpl_jlc.csv` (JLCPCB), a Gerber job file (101.65 x 101.65 mm, 1.6 mm), `.xml` | file list, licence and the heads of the paste, position and job files read (R) |
| `cmm2` | Manawyrm/CMM2-JLC, Colour Maximite 2, revision E | GPL-3.0 | 4 | copper (F, GND, POWER, B), paste, PTH, `all-pos.csv`, `cpl_jlc.csv` | file list and licence (S); size read at fetch |
| `oswlight` | Open-Smartwatch/open-smartwatch-light | GPL-3.0 | 4 | every KiCad layer as `.gbr`, paste, PTH drill, `both_pos.csv`, BOM | file list and licence (S) |
| `rp2040` | tommy-gilligan/RP2040-minimal-design, KiCad 7 | BSD-3-Clause | 2 | copper, paste, PTH, `top-pos.csv`; an exposed-pad QFN | file list and licence (S) |
| `co60` | jmdaly/CO60, 60 % keyboard | CC-BY-SA-4.0 | 2 | large two-layer pours, paste (bottom only), `bottom-pos.csv` | file list and licence (S) |
| `vstcm` | english1234/vstcm, colour vector generator | GPL-2.0 | 2 | copper, empty paste files, `all-pos.csv`, job file | file list and licence (S) |
| `stickhub` | Ucamco's Gerber X3 sample (KiCad 8.99), a USB hub | not stated | 2 | copper, paste with `TO.C`, **an X3 component layer** (reference, footprint, value, rotation, origin, courtyard, pins), job file (16.6 x 40.1 mm), Gerber-format drill | the heads of the component layer, the paste file and the job file read (R) |

Also found, **not** used as boards: brickbots/PiFinder (GPL-3.0) and Duckle29/Vitamins-included (BSD-3-Clause) publish zips only; the other Ucamco archives (`fetch_boards.py --ucamco`): the layer-format test files (21 files, rare primitives), two fabrication examples with **IPC-2581** files (4 and 10 copper layers) and two more X3 samples; ODB++ samples of the library mcix/odbpp (MIT; the archives' own licence is not stated): `sandbox-odb_wifi.tgz` 69 kB, `flat_hierarchy-odb.tgz` 242 kB, `sandbox-odb_pc4.tgz` 630 kB, `video-odb.tgz` 1.2 MB, `designodb_rigidflex.tgz` 11.6 MB (`fetch_boards.py --odb` takes the first three). The licences of GPL boards bind a redistribution of the files, not the statistics a study quotes; no file is committed.

**What the paste layer and the files give** (checked on the real files above, not from the specification): in KiCad output the paste file carries the Gerber X2 component attribute `%TO.C,<ref>*%` before the openings of each part, so the reference designator, the bounding box and the centre of a part are in the file itself; the placement files give reference, value, package, position, rotation and side (KiCad: `Ref,Val,Package,PosX,PosY,Rot,Side`; JLCPCB: `Designator,Val,Package,Mid X,Mid Y,Rotation,Layer`; Altium and EasyEDA use `Mid X`/`Mid Y` with unit suffixes); an X3 component layer adds footprint, value, rotation, the origin of the part, a courtyard outline and the pins. ODB++ holds components, packages and nets in a directory tree (section 4.4, from memory, to be checked on the samples).

## 4. The studies

Every script is run from the repository root with `.venv-research/bin/python research/gerber-real-boards/scripts/<script>` (the Gerber studies use `.venv-research`, see `CLAUDE.md`, "Commands"; the environment is **not** created now). Outputs go to `out/` (git-ignored). Tests: `cd research/gerber-real-boards && ../../.venv-research/bin/python -m pytest -q tests` (the tests on synthetic data need no download; those on the boards are skipped with the message "no board in research/gerber-real-boards/data: run scripts/fetch_boards.py" when `data/` is empty). Run the studies one at a time on a quiet machine: the times and memory would be wrong otherwise.

### 4.1 The default copper mapping of an import (`study_copper_mapping.py`)

* **Question.** For an imported copper layer, which cell conductance is the best default: the arithmetic fill fraction (the program's `Zone.fill` formula applied to each cell), the flow-based faces, lambda 0.5, or the geometric mean? And does half the diagonal coupling help on real windows?
* **Method.** Part A, one conducting sheet (isolates the mapping): 6 windows of 36 mm per board cut from the top copper of every board of section 3 (`onesheet.cut_windows`, the selection rule of `gerber-models`), coverage mask at **0.05 mm** (the earlier studies used 0.1 mm), cells 0.5 and 1.0 mm, 6 mm heater. Part B, the program of 2.4.5 (every copper layer, plated holes as vias, the laminate rule) on 3 windows of 24 mm of each multilayer board, pixel 0.05 mm, cells 0.5 and 1.0 mm: the program as it is (one zone per cell, fill = coverage), the flow-based faces and lambda 0.5 through `faces.FaceNetwork`.
* **Reference.** Part A: the five-point **and the nine-point** pixel solution (`diagonal.pixel_reference9`; the nine-point stencil is closer to the continuum on tilted thin copper). Part B: the program's own network on the pixel grid (`faces.solve_fine`), which is the reference the earlier studies used; an independent 3D solver was the check of that reference in `gerber-models` and is not repeated here.
* **Success criterion** (fixed before the run). The default is the method with the smallest mean absolute error of the heater mean in Part B, provided its worst window is within 10 % and it beats the fill fraction by a factor of 2 in the mean; Part A with the nine-point reference decides ties.
* **Script, tests.** `scripts/study_copper_mapping.py [--quick] [--part A|B]` (about two hours on a quiet 10-core machine with 16 GB; `--quick` is a smoke run); tests: `test_onesheet_and_real_boards.py` (a uniform window gives the same answer for every mapping; stripes across the heat make the fill fraction cooler than the pixel reference and the flow-based faces better).
* **Not verified.** Any measurement on a physical board; copper thickness other than the program's default; a heater other than a 6 mm square on the top layer; the 3D solver as an independent check of Part B (done in `gerber-models`, not repeated); the diagonal gate (its held-out test failed there).
* **Results.** Not run.

### 4.2 Time and memory of real boards, and the memory per unknown (`study_time_memory.py`)

* **Question.** What does a whole 4-layer board (ISASTM 101.65 x 101.65 mm and the others) cost at 1.0, 0.5 and 0.25 mm cells, by phase (import, faces, assembly, solve), and how many bytes per unknown does the memory guard of 2.5.0 need? The older coefficients predate the laminate nodes: 2.8 KB per unknown for the layered FVM on a plain board (2.7 GB at 992 000 unknowns, `solid3d-verification`), 7 GB per million measured by the maintainer on refined boards, 6.6 to 19.3 KB for the 3D solid.
* **Method.** One fresh child process per case (board, cell) so that the peak resident size is the peak of the case; pixel = cell / 10; coverage masks; the flow-based faces of every layer; the face network; a direct steady solve. Recorded after each phase: seconds and the peak resident size so far; the unknowns of the network and the program's own count with the laminate rule (`fvm.unknowns`, which is ragged: the laminate nodes exist only in cells with absent copper) so that the guard can be fed either; the number of non-zeros.
* **Reference.** The earlier coefficients above; no external reference (it is a measurement).
* **Success criterion.** One coefficient with at most 25 % scatter over the cases, so that the guard can use `baseline + unknowns x coefficient`; otherwise the guard needs the structure (layers, non-zeros). A case whose peak is close to the physical memory is flagged (it may have paged).
* **Script, tests.** `scripts/study_time_memory.py [--cells 1.0 0.5 0.25] [--boards isastm cmm2 oswlight] [--max-gb 12]`; tests: `test_fine_memory_format_odb.py` (the fit recovers a known coefficient and refuses empty input; the peak size is read).
* **Not verified.** Paging effects; other machines; the 3D solid on an imported board; the GUI process on top of the calculation process; the layered models' time at one million or more unknowns on these boards beyond the cases run.
* **Results.** Not run.

### 4.3 The transient of an imported board with fine cells (`study_transient_fine.py`)

* **Question.** Does the step response of the heater converge with the cell (1.0, 0.5, 0.25 mm), and is the heat capacity of the copper a problem?
* **Method.** A 30 mm window of a multilayer board, a 4 mm heater of 1 W stepping on, the program's transient machinery (implicit Euler, doubling steps) on the pixel grid (reference) and on the flow-based face networks, each with the capacity of the face network as it comes and with the copper capacity set from the coverage (`boardrun.set_capacity`).
* **A finding of the preparation.** The face network of `research/gerber-models` has no zones, so the program computes its capacity as bare laminate (no copper). This does not matter for the steady state and does matter for a transient: copper is up to a sixth of a board's capacity per layer pair. The study measures how much it moves the time constant; if it is over 5 % the import must set the capacity.
* **Reference.** The pixel-grid network (0.1 mm); a closed form for the time constant exists only for a rectangle (`fvm.board_time_constant`), not for imported copper.
* **Success criterion.** Step responses at 0.5 and 0.25 mm within 3 % of the reference at 0.1, 1, 10 s and the end, and within 2 % of each other.
* **Script, tests.** `scripts/study_transient_fine.py [board] [--quick]` (about 20 minutes); no separate test (the pieces are tested in 4.1 and 4.2).
* **Not verified.** A measured step response; power profiles (square waves) and the animation on imported boards; computed heat transfer coefficients (h is typed, 10 W/m2K).
* **Results.** Not run.

### 4.4 Solder paste, reference designators and positions, X3 and ODB++ (`study_paste_footprints.py`, `study_odb_structure.py`)

* **Question.** Can a paste polygon become a component footprint and a heat source by a click (and automatically for every part), and where do the reference designators and positions come from?
* **Method.** (A) Pad groups: `paste.by_proximity` (openings closer than a link distance of 0.3, 0.6, 1.0 or 1.5 mm are one group) and `paste.by_reference` (the `TO.C` attribute, by rewriting `TO.C` to the net attribute the reader already keeps per object); how the two agree. (B) Placement files (`pnp.read_placement`: KiCad CSV and text, JLCPCB, Altium, EasyEDA variants): `pnp.register` finds the translation and the sign of Y from the data (a histogram vote), then counts the parts within 0.5, 1 and 2 mm of a group and compares the references of the placement file with those of `TO.C`. (C) The click: `paste.pick` on every group. (D) The heat-source shape: 1 W on the three biggest groups as the bounding box, the convex hull and the largest opening, at 0.5 mm cells with the flow-based faces, comparing the hottest cell and the mean over the bounding box. (E) The X3 component layer (`x3.components`) against the paste references. (F) ODB++: `study_odb_structure.py` prints what the three small sample archives hold (steps, layers of the matrix, components with package, side and position, the profile, whether `eda/data` and netlists exist) and stops when a components file exists and the reader found nothing.
* **Reference.** The files themselves: references written in two independent places (the paste file and the placement file) must agree; the picture of the click is checked on every group.
* **Success criterion.** With the best link distance at least 95 % of the references of `TO.C` land in exactly one group; at least 90 % of the placement parts are within 2 mm of a group of their side after registration; the click at the centre of the largest opening picks the right group in 100 % of the trials; the footprint choice moves the hottest cell by a figure the README can state (the choice is then the maintainer's). ODB++: components with references, positions and a side in every sample that has them.
* **Script, tests.** `scripts/study_paste_footprints.py [board ...]` (about 15 minutes), `scripts/study_odb_structure.py` (seconds); tests: `test_paste_pnp.py` (synthetic paste file with two parts, link distances, shapes, the click, four placement formats, the registration of a shifted and flipped list, an X3 part) and `test_fine_memory_format_odb.py` (the ODB++ record layout as written from memory), plus the board tests, skipped without data.
* **Not verified.** Parts with no paste opening (through-hole, bottom parts of a board with a top-only paste file, parts glued instead of soldered); rotated large parts whose bounding box is much larger than the hull; the junction temperature (the paste group gives a footprint, not a package); the position frame of an ODB++ job against its Gerber (no Gerber set of the sample jobs is available); **IPC-2581 is not read at all** (two `.ipc` examples exist in the Ucamco fabrication examples). The ODB++ record layout in `lib/odb.py` is from memory and the specification was not obtained (it needs a registration).
* **Results.** Not run.

### 4.5 Lumped and Analytic on imported copper: warn or refuse (`study_lumped_analytic_rule.py`)

* **Question.** The two simple models were 16 % and 26 % below the FVM on the rectangle board. On real windows, can an indicator tell when they are unusable, so that the program refuses above a threshold and warns between two?
* **Method.** 24 mm windows of every board, cell 1.0 mm, the imported window turned into one zone per cell with the coverage as fill (the only description these two models take), `lumped.solve_steady` and `analytic.solve_steady` against the face-conductance network and the pixel run; the error is set against `fine_copper.indicators` (partial_share, thin_share), the copper fraction and the heater-block fraction, with `fine_copper.calibrate` at a 15 % error limit.
* **Success criterion.** A rule on one indicator that separates the windows with error above 15 % from the rest with recall at least 0.9 for the warning and no refused window below 25 % error; if no indicator does, the rule is "always warn, never refuse" and this README says so.
* **Script.** `scripts/study_lumped_analytic_rule.py [--quick]` (about 30 minutes).
* **Not verified.** Non-rectangular outlines (the two models use the equivalent rectangle), parts with a top path, large via arrays; the models are run as the program runs them for zones, not on the face conductances.
* **Results.** Not run.

### 4.6 Conformance with the Ucamco test sets and the rare primitives (`study_conformance_rare.py`)

* **Question.** Does our reader agree with Ucamco's own test files and with a second reader (gerbonara + shapely), and do real files use the features it refuses (aperture blocks `AB`, the transformations `LM`, `LR`, `LS`, the moire primitive)?
* **Method.** Every Gerber file of the Ucamco archives and of the open boards: read or refused (with the message), copper area at 0.05 mm against the second reader, and a text count of the rare features (`rare_features.count`) over all real files. Earlier, 161 of 164 comparable gerbonara test files agreed within 3 % and 6 were refused (`gerber-import` 4.17): this extends it to the specification's own tests.
* **Success criterion.** Every Ucamco test file is read with the area within 3 % of the second reader or refused with a specific message (never silently wrong); the real board files use none of `AB`, `LM`, `LR`, `LS`.
* **Script, tests.** `scripts/study_conformance_rare.py` (minutes); `test_fine_memory_format_odb.py::test_rare_feature_counts`, `test_onesheet_and_real_boards.py::test_every_board_has_its_files_and_reads`.
* **Not verified.** The Ucamco pictures (`.png`, the correct renderings) are not compared, only the area; polarity-changing files with transformed apertures beyond what the area shows; Excellon files; the drill in the Gerber format that KiCad's X3 output writes (a plated-hole file with `TF.FileFunction,Plated,...` as `.gbr`): the importer's drill reader is written for Excellon, so `registry.roles` keeps such files apart (`drills_gerber`) and the study reports them.
* **Results.** Not run.

### 4.7 The fine-copper warning (`study_fine_copper_warning.py`)

* **Question.** Which indicator, and which threshold, says that the copper of a layer is finer than the cell and the result is approximate?
* **Method.** The one-sheet physics of 4.1 on windows of every board at cells 0.5, 1.0 and 2.0 mm; two indicators on the same coverage mask: `partial_share` (the share of the copper in cells that are neither empty nor full) and `thin_share` (the share of the copper that disappears under an opening with a disc of the cell's half-width); `fine_copper.calibrate` gives, for error limits of 5 and 10 %, the threshold that warns about at least 90 % of the bad cases and the share of good cases warned too; the heater-block copper fraction is the simple rival.
* **Success criterion.** One indicator with recall 0.9 and false alarms under 0.3 for the 10 % limit at all three cell sizes with one threshold; a threshold that moves with the cell is a function of the cell and the warning must say so (graded warning).
* **Script, tests.** `scripts/study_fine_copper_warning.py [--quick]` (about an hour); `test_fine_memory_format_odb.py` (solid copper is not fine, stripes are, the same stripes are not fine for a cell as narrow as they are, the calibration recovers a known threshold).
* **Not verified.** Other heater sizes; other copper thicknesses; the multilayer stack (a layer under another is less sensitive: this is the one-sheet error, an upper bound); tilted copper (the indicator does not look at direction, and the diagonal residual of `gerber-models` 4.42 is a different failure).
* **Results.** Not run.

### 4.8 The project file (`study_project_file.py`, `lib/project_format.py`)

* **Question.** How big is a project that embeds the imported copper as masks, against one that keeps references to the Gerber files, and does the migration from format 1 to 2 lose nothing?
* **Method.** Every board at pixels of 0.1, 0.05 and 0.025 mm: the binary mask packed (bits, deflate, base64) and the 8-bit coverage mask, per layer and per board, against the size of the Gerber sources; the round trips (binary exact, coverage within 1/255); the migration 1 to 2 and back.
* **Success criterion.** A 4-layer board of about 100 x 100 mm at 0.05 mm embedded as binary masks under 20 MB of JSON; the round trips exact.
* **Script, tests.** `scripts/study_project_file.py` (minutes); `test_fine_memory_format_odb.py` (round trip, migration, the downgrade that refuses a project with imports, a reference-only record).
* **Not verified.** The load time in the program; projects with several imported boards; the behaviour of a program older than the change when it opens a format 2 file (see `INTEGRATION.md`, risks).
* **Results.** Not run.

## 5. How to run, in this order

1. `python3 -m venv .venv-research && .venv-research/bin/pip install -r requirements.txt -r research/gerber-import/requirements.txt` (once; not done now).
2. `.venv-research/bin/python research/gerber-real-boards/scripts/fetch_boards.py --odb --ucamco` (network; boards, X3 sample, ODB++ and Ucamco archives into `data/`).
3. The tests: `cd research/gerber-real-boards && ../../.venv-research/bin/python -m pytest -q tests`.
4. In this order, one at a time on a quiet machine: `study_conformance_rare.py`, `study_odb_structure.py`, `study_project_file.py`, `study_paste_footprints.py`, `study_fine_copper_warning.py`, `study_copper_mapping.py`, `study_lumped_analytic_rule.py`, `study_transient_fine.py`, `study_time_memory.py` (last: it needs the machine free).
5. `.venv/bin/python research/gerber-real-boards/scripts/make_figures.py` (the data figures), then paste the printed numbers into the "Results" lines above and update section 8.

## 6. What the preparation found on the way

* The paste file written by KiCad carries the reference designator of each part (`TO.C`), and an X3 component layer carries much more; the reference does not have to come from a placement file (section 4.4).
* The face network of `research/gerber-models` has no copper in its heat capacity (no zones): irrelevant for the steady state, relevant for a transient (section 4.3). The research code that proposes the import must set it.
* The flow-based faces need an even number of pixels per cell; with `pixel = cell / 10` that always holds.
* A drill file in the Gerber format (KiCad X3 output) is not read by the Excellon reader of the importer; the registry keeps it apart.
* `fvm.unknowns` counts the laminate nodes of the 2.4.5 rule only where they exist (ragged), while the face network built with the rule off has `layers x cells`: the memory guard must say which count it uses (section 4.2 records both).
* The Ucamco X3 sample's licence is not stated on the download page; the study uses it from `data/` only and quotes statistics.

## 7. Decisions left to the maintainer

See `INTEGRATION.md`, section 6: the default mapping (after 4.1), embedded masks or file references in the project (after 4.8), what a format 2 file does in an older program, the paste footprint shape (after 4.4), whether Lumped and Analytic refuse or only warn (after 4.5), whether `TO.C`, placement files, X3 and ODB++ all enter 2.5.0 or only the first two, and the specification reading (the attribute sections and the aperture-block sections) that must precede the code.

## 8. What was read and what was not verified

*Read in full (R), from a summary (S), from memory (M), not obtained (N); the entries are in `research/theory/BIBLIOGRAPHY.md`, section 22.*

* **R**: the heads of the paste file, the two placement files and the job file of ISASTM; the head of the component layer, the paste file and the job file of the Ucamco X3 StickHub sample; the GitHub metadata (licence, file lists) of the open boards; the member lists of the Ucamco archives.
* **S**: the Ucamco downloads page (through the fetch tool); the README of mcix/odbpp and ODBPy, a search summary on ODB++ and its free specification; search summaries on the X2/X3 attributes (Eurocircuits, Pulsonix, KiCad source file name); the file lists (not the contents) of CMM2-JLC, open-smartwatch-light, RP2040-minimal-design, CO60 and vstcm; the READMEs, CONCLUSIONS and INTEGRATION files of `gerber-import` and `gerber-models` (the parts quoted: not re-run).
* **M**: the ODB++ record layout of `lib/odb.py` (`CMP`, `TOP`, `PRP`, the tree of `steps/`).
* **N**: the Gerber specification text (the 2024.05 PDF was fetched as a binary file and its text layer could not be extracted here: the attribute sections, the component-layer section and the sections on aperture blocks and transformations are still to be read before the code is adopted); the ODB++ specification (needs a registration); IPC-2581 (no file opened); the contents of the Ucamco test files and of the other X3 and fabrication samples.
* **Nothing was run**: no study, no test (the scripts and tests were compiled with `py_compile` only, and the three diagrams were drawn). The tests were checked by reading against the code, which is not the same as running them; expect to correct a few expectations at the first run (for example the margin of the stripe tests) and record each correction here.
* **Reproduction of a published case** (the literature-check rule): the published cases of this topic are the Ucamco test files and the specification's examples (study 4.6, with a second reader as the independent solver) and Sampson's method (reproduced in `gerber-models`); the cases of the Electronics Cooling articles were not re-opened here.
