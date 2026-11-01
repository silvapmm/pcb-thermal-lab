# Integration: CAD profiles in the Gerber import

Design for entering the program (`pcbthermal/gerber/` on `develop`, the parts rules of `feature/paste-parts`). **Nothing here is implemented in the program**; the prototype is `lib/cadprofiles.py` with the data in `lib/cad_markers.json` and `lib/cad_conventions.json`, tested by `tests/test_cadprofiles.py` (35 tests). Numbers are those of `README.md`.

## 1. What a profile is, and what it is not

A **CAD profile** is a named bundle of *defaults* for reading the files of one eCAD program: how to recognise its files, what its layer names mean, which quirks of its drill and Gerber files to tolerate, where its outline is, what its placement file looks like. It is **never an authority**: the X2 attribute and the Excellon header of a file always win over the profile; the user's choice always wins over the detection; a profile never hides a refusal (the message stays); and a profile is not a physics model, so no temperature depends on it except through *which layers are taken as copper and which outline is used*.

## 2. Design

### 2.1 Data (`pcbthermal/data/cad_profiles.json`)

The two files of `lib/` merged into one, same schema:

* `profiles.<key>`: `name`, `kind` (`ecad` or `cam`), optional `parent` (CircuitMaker over Altium), `markers` (id, scope, regular expression, weight, version group, status of the evidence), and `conventions` (see 2.4).
* The shipped file is read like `defaults.json`; a user file with only the differences (a new tool, a changed rule) is merged by key, in the way `pcbthermal/defaults.py` already does, so a user can add a program (or a fabricator's output) without a new release.
* `generic`: the conventions of an unknown program (X2, then the names of `functions.py`).

### 2.2 Detection (`pcbthermal/gerber/profiles.py`)

```
detect_profile(files: dict[name -> first 8 kB]) -> ProfileResult
ProfileResult(profile, name, confidence, version, evidence, candidates, declared)
```

Same rule as the prototype (README 2.3): weights, decisive at 9, variant over parent, CAM tool never over eCAD, confidence high / mixed / medium / low / declared / unknown. No I/O in the module (the caller reads the heads, as `functions.detect_file` and `GerberArchive` already do: the headers of the members of a ZIP are read without extracting). It is run once per import on the names and the first 8 kB of every member, at the cost of about a regular expression pass per file (measured: the 764 files of the 54 development sets take 0.11 s once the heads are in memory; a 1.2 MB line of repeated `G04 ` and a 1 MB line of `A` take under a millisecond, because only the first 8 kB is looked at).

### 2.3 Where it enters the import window

* One line above the layer assignment list: **"Detected: Altium Designer 24.5.2 (TF.GenerationSoftware, high confidence)   [change ...]"**. The `[change ...]` opens a combo with every profile of the table, "Unknown program (generic)" and the profiles of the user file; the choice is stored in the project (`cad_profile`, plus the table version) and used on re-import.
* Evidence line (tooltip or "why?"): the marker ids and the version, **never the text of the file**. Xpedition's banner holds `G04 Job   : C:\...\PCB.pcb*` and `G04 User  : <computer>:<user>*` (the path, the user and the computer name): showing the matched text would show them. The prototype keeps the matched text for the study; the program must keep only `marker` and `version`.
* Mixed or medium or low or declared: the line is orange and says what to check ("Files from several programs: KiCad (10), Allegro (1)", "Probably Fritzing, header sequence only", "Declared by the files: Acme BoardPlot 3.1, no profile").
* The assignment dialog keeps being a default the user confirms (as now); the profile changes the defaults it proposes.

### 2.4 What each field changes

| Field of the profile | Consumer | Effect |
| :-- | :-- | :-- |
| `layer_rules` (regex, kind, side) | `functions.detect_function` | **after** the X2 attribute and the Excellon header and **before** the generic name rules: `EtchLayerTop.gdo`, `lyr2.art`, `SMB.art`, `.Top`, `Conductive-1.fph` and the like get a kind and a side. The largest measured gain (README 4: 752 of 844 right by name plus head, 692 by name alone) |
| `layer_order` (Altium `Layer_Physical_Order`) | stack order | the copper layers of an Altium set without X2 FileFunction are ordered by that comment (32 files carry it) |
| `ignore` (kinds not read: assembly, fab, drill drawing) | the reader | the file is listed, not parsed: no refusal for `%MIA1B0*%` assembly films; `DRILL.gdo` (a drawing) is not taken for a drill file |
| `drill.tolerate` (`G93X0Y0`, `M71,TZ`, leading `%` before `M48`, tools without T codes) | `excellon.py` | accepted as a tool quirk when the profile is the tool's (see 3.2 for the recommendation to make the first three general) |
| `drill.plated_from` | `excellon.drill_function` | order of the sources for the plating: X2 comment, `;TYPE=`, per-tool comment, file name |
| `outline.rule` (`file`, `prune`, `none`) | `outline.py` | which file(s), and whether dangling segments are pruned before chaining (README 5.1); `none` for Allegro (no outline file in 6 sets) so that the dialog asks for a rectangle or a drawing instead of failing |
| `gerber.macro_names` | `parser.py` | Upverter's hyphens in macro names read as the name they are |
| `paste.to_c` | `parts.py` | "optional by plot option": the rule order does not change, the dialog may say why there are no references (KiCad: "plot option 'include netlist attributes' was off") |
| `placement` (preamble lines, header aliases, "Part Name" as package, units) | `parts.parse_placement` | Pulsonix's four preamble lines are skipped and "Part Name" is the package; KiCad's is the default |
| `placement.bottom_x` | `parts.bottom_convention` | **always "detect"**: not a property of the tool (README 6, two KiCad 5.1 boards with opposite signs) |
| `units`, `format_seen` | the warnings | a file whose unit or format is not what the tool writes (e.g. a KiCad file in inches is allowed; an Altium file with no unit is not) gets a warning, not a refusal |
| `x2`, `x3`, `odb` | the dialog | which attributes to expect; "X3 component layer expected" for KiCad 8; ODB++ `misc/info` as one more marker |

### 2.5 Unknown programs

Nothing matches: profile `unknown`, `generic` conventions: the order is the X2 attribute, the Excellon header, the name rules of `functions.py`, as today. If an X2 generator is declared but not in the table ("declared") the window shows the text and the same generic conventions; **no result changes**. A user may save the choice for the project, and a user-file profile (JSON, only the differences) makes it permanent. For a set where nothing is recognised and the names are not understood, the dialog asks for each file, as now.

### 2.6 Tests

* **Per profile, synthetic files made from the real banners**: the 23 cases of `tests/test_cadprofiles.py` (`CASES`: the banner lines read in real files, one per marker family) must be recognised from that single file with high confidence and the right version; the program's tests would carry them as strings (no board data).
* The confidence rule: mixed (two programs), CAM tool never over eCAD, variant over parent, unknown, declared, name only; the ODB++ `misc/info`; the file scope (Gerber, Excellon with comments or a leading `%`, other text).
* The table: every regular expression compiles, ids unique, weights 1 to 10, status starts with R, D or M, every profile has conventions, every conventions rule compiles.
* The conventions on the layer names, one test per rule family, from the sample names (strings only): `EtchLayerTop.gdo` is copper top under Xpedition and unknown under generic.
* The held-out check stays a research study (`study_heldout.py`); the program's suite must not need the downloaded sets.
* GUI: the combo, the line, the stored choice, a re-import with the stored choice (`tests/test_gui_stress.py` scenario for the import window, as for any new control), the tooltip of the combo.

### 2.7 Documents to write when it is adopted

User guide `pcbthermal/help/index.html` (a section "Which program made these files": the detected line, the combo, what the profile changes, how to add a program in the user file) and its test words; `docs/models.md` (the import chapter: the profile layer, the order of trust X2 > header > profile > generic names); `docs/theory.md` has no physics to add (a one-line statement that no model depends on the profile); `docs/versions.md` (what was implemented, tests); `docs/research.md` (reset); `CHANGELOG.md` (Unreleased); `CLAUDE.md` (structure, decision). Text for them is in `docs/` of this folder.

## 3. Measured impact of each proposal

All on the sample sets (README sections 3 to 6; no board of the maintainer, no measurement).

| Proposal | Before | After | Where |
| :-- | :-- | :-- | :-- |
| Detect the program (markers, rule) | n/a | 54 of 54 development sets, 28 of 28 held-out sets, high confidence; fit on the first, test on the second | README 3.3 |
| Layer function by profile names | 752 of 844 judged files right (name + head), 692 by name alone; Xpedition 61 of 98, Allegro 52 of 78, PADS 8 of 14, Target 3001 1 of 10, Zuken 2 of 10 | the 92 wrong files are exactly those the profile rules of `lib/labels.py` cover; **an upper bound, not a measurement** (the rules were written with the names in view); the names that are new to a rule family were not tested out of sample | README 4 |
| Tolerate `G93X0Y0` in Xpedition NC drills | 17 of 17 files refused | 16 of 17 read (the 17th, a punch file, stays refused); 14 802 holes, 0 outside the board box | README 5.2 |
| Tolerate `M71,TZ` and macro names with a hyphen (Upverter) | 6 of 11 files refused | all read; 63 holes; copper areas within 0.04 to 0.24 % of gerbonara | README 5.3 |
| Outline: prune stubs and duplicates before chaining | 11 outline files refused ("not a closed contour") in 7 tools | 6 closed with a box that agrees with the copper box within 2 % (12 % for one), 1 closes with a join tolerance of 0.1 mm, 1 closes on the wrong layer, 3 stay open | README 5.1 |
| Ignore assembly films, `DRILL.gdo` drawings | 2 Allegro assembly films refused, 1 Xpedition drawing taken for a drill file | not read | README 4, 5.4 |
| Pulsonix placement preamble and "Part Name" as package | the file refused | 86 parts read; the envelope rule matches 8 of 86 without the package alias (the rule needs the tool's package naming) | README 6 |
| Allegro drill without `M48` and T codes | refused | not implemented here (comments give the sizes; counts allow a check) | README 5.4 |

## 4. Recommendation for each decision

1. **Detection and the line in the import window: adopt** (2.1 to 2.3). It is cheap, the evidence is measured on 82 sets, and it never changes a result by itself.
2. **Layer-name rules per profile: adopt**, with the rules of the 19 tools with real samples and the honest status of each (R for rules checked against a tool's own listing: Altium's extension report, Allegro film names; M for PADS and EAGLE until a document of the tool is opened). This is the part that makes Xpedition, Allegro, PADS and Target 3001 sets usable without the user assigning every file.
3. **Reader tolerances**: `G93X0Y0` (a zero shift), `M71,TZ` and a leading `%` before `M48` are *general* Excellon facts, not tool facts: recommend adding them to `excellon.py` for every file (with the same refusal for a non-zero shift) rather than behind a profile; the macro-name tolerance and the outline pruning stay behind the profile or a warning ("the outline had loose ends and was cleaned: check the board size"), because they change what is read.
4. **Placement and bottom X**: keep the detection from the data; add the Pulsonix preamble and column aliases only with a real second file of that tool; do **not** preset the bottom X sign for any tool.
5. **Zuken, CADSTAR, PADS Professional, Allegro X, OrCAD X, JLCEDA Pro, Horizon**: ship them as "no profile" until a real file exists; the user can add one in the user file. Ask the maintainer (or users) for the files listed in README 7; **do not ship the Zuken emulation as a Zuken profile with a high confidence**: the table marks it medium and `D`.
6. **Version of the program**: this is a feature (2.5.0, with the Gerber import), after the reader and the paste parts are in `develop`.

## 5. Risks

* **A wrong profile with high confidence**: a fabricator or a CAM tool can re-export a set and keep or replace the banner (CAM350 files in a folder called OrCAD). Mitigations: a CAM banner is reported as such, the profile only supplies defaults, X2 and headers win, and the user can change it. Residual: a set in which every file was re-exported by a tool that copies another tool's banner would be mislabelled; none was seen.
* **A banner that carries private text** (path, user name, computer name, project name): the program shows marker ids and versions, not matched text (2.3); the project file stores the profile key and the table version only.
* **A hostile or huge file**: detection reads 8 kB per file, uses linear regular expressions (no nested quantifiers; the table is tested for compilation, and `test_hostile_head` of the prototype's tests runs a 1.2 MB line of repeated `G04 ` and a 1 MB line without line ends through the detector in well under a second), and no file is executed; downloaded sets were opened with `python -I`.
* **Maintenance**: a tool changes its banner in a new version. Mitigations: markers are data; the user file can add one; an unrecognised banner falls back to "declared" or "unknown", never to a wrong profile.
* **Trademarks**: the tool names are used descriptively; the table is ours (MIT); no vendor file is copied.
* **Licences of the samples**: the data stays git-ignored; the tests of the program use strings made from banner lines, not files.
* **ODB++**: only `misc/info` fields seen in a real file are used; the specification (confidential) is not copied.

## 6. What is not in this design

IPC-2581, ODB++ reading, Allegro drills without T codes, the placement files of tools not seen, the Zuken profile from a real file, and anything about temperatures.
