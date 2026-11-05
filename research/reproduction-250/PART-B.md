# Part B of the reproduction pass of release 2.5.0: the Gerber folders

Folders: `gerber-cad-profiles`, `gerber-import`, `gerber-models`, `gerber-nets`, `gerber-real-boards`.

Tree under test: `develop` at `e97b62f`, a detached worktree. Interpreter: `.venv-research` (the Gerber libraries are there). Data: the open boards of the other
checkouts, linked into the folders' `data/` (git-ignored, not committed): `gerber-real-boards/data`, `gerber-cad-profiles/data` (82 sample sets, 966 files) and
`gerber-import/data`. The program was not touched. One heavy job at a time; the runner was paused (SIGSTOP) twice, for about 3 and 2 minutes, when the load average
of the machine (other testers) went to 16 and 38; swap used was 10 to 13 GB at the start (the macOS figure stays high) and fell to 1.9 GB.

Terms: LAM is the laminate rule with sub-gaps of 2.4.5 (`e9f4df2`), COVER the 8 x 8 board cover of 2.4.5 (`7a5b0ee`), TOL the Gerber reader tolerances and detector
fixes of 2.5.0 (`fix/gerber-reader-tolerances`), GUARD the memory guard of 2.5.0.

## 1. Totals

Counted in comparison units (one table, one group of numbers or one file of output compared with the README of the folder).

| Folder | Checked | Unchanged | EXPLAINED | UNEXPLAINED | NOT RUN |
| :-- | --: | --: | --: | --: | --: |
| gerber-cad-profiles | 10 | 6 | 4 | 0 | 4 scripts (do not import the program) |
| gerber-import | 0 | 0 | 0 | 0 | 15 scripts (do not import the program); tests run |
| gerber-models | 12 | 3 | 9 | 0 | 2 imports of the program (needs variants of the program) and about 25 scripts that do not import it |
| gerber-nets | 0 | 0 | 0 | 0 | 4 scripts (do not import the program); tests run |
| gerber-real-boards | 13 | 11 | 2 | 0 | 8 scripts that do not import the program |
| **all** | **35** | **20** | **15** | **0** | |

The program-run units are about 350 individual numbers in the explained groups (every table cell of the studies below) and about 600 numbers in the unchanged groups.
The tests of the five folders: 37 + 57 + 34 + 18 + 51 = **197 passed, 0 skipped** with the data present (the first run, before the data were linked, was 186 passed and
11 skipped: the skips are the tests that need the downloaded boards). `gerber-import` and `gerber-nets` have no study that imports the program (checked with grep:
`pcbthermal` appears nowhere in their `scripts/`, `lib/` or `tests/`), so only their tests were run.

**UNEXPLAINED: 0.** Every shift was tied to an item, and the larger ones were bisected on `git archive` copies of earlier commits (section 3).

## 2. Results by folder

### 2.1 gerber-cad-profiles (the program's reader and parts on 966 files of 82 sets)

| Study | README | now | Item | Status |
| :-- | :-- | :-- | :-- | :-- |
| `study_adjustments.py` A: outline files that fail at 0.01 mm | 13 files listed, 11 that fail in 7 tools; pruning closes 6 of 11 | the same 13 files, the same loop counts (2/28/30, 1/0/2, 26/2/33, 25/24/33, 1/4/1, 1/0/2, 1/1/2), same boxes | none | unchanged |
| the same, B: Xpedition NC drills with `G93X0Y0` removed in memory | 16 files read, 14 802 holes and slots, 0 outside the box; the punch file stays refused | the same 16 files and hole counts (4, 3, 1941, ..., 9690, ...), the punch file refused | none (the program itself now accepts `G93X0Y0`, see the next row) | unchanged |
| the same, C: Upverter with macro names and `M71,TZ` rewritten | 63 holes, 7 files, 0.04 to 0.24 % against gerbonara | 63 holes, 7 files, 0.04 to 0.24 % (306.81 / 306.42 ... 161.99 / 161.74) | none | unchanged |
| `study_reader.py`, table 4 (966 files by tool) | kind right by name only 692 (82 %), by name and head 752 (89 %), read ok 937, refused 29 | 709, 763, 959 and **7** refused (Xpedition 17 refused to 1 (the punch file), Upverter 6 to 0, Proteus name 31 to 38, pcb-rnd 10 to 13, Allegro 52 to 54, PADS 8 to 10, Zuken 2 to 4) | TOL (`G93X0Y0`, `M71,TZ`, hyphenated or dotted macro names, the generic detector rule that took masks and assembly files for copper) | EXPLAINED |
| the same: the dangerous files (taken for copper without being copper) | 9 files | **0** files found as copper that are not (`grep -- "-> copper"` on the list of wrong kinds finds none) | TOL (the review of the branch) | EXPLAINED |
| the same: copper areas against gerbonara + shapely | 175 files, 174 within 3 %, median 0.03 %, worst 3.4 % (`hw0004/Layer4.gdo`) | 177 files, 176 within 3 %, median 0.03 %, worst 3.4 % (the same file) | TOL (two more files readable) | EXPLAINED |
| the same: outline files | 11 fail at 0.01 mm | the same 11 fail | none | unchanged |
| `study_parts.py` table 1 (`TO.C` counts, by position, bottom convention) | CMM2 494 of 494, ISASTM 772 of 772, OSW 206 of 206, CO60 0 of 489 (191 of 193 by position), RP2040 0 of 129 (27 of 30), LibreVNA 0 of 1872 (559 of 568), StickHub 264, Watchy 0 of 290, oneinchEye 362, badgemagic 1138, VoltLink 0 of 114; Pulsonix placement refused | every count the same; Pulsonix still refused | none | unchanged |
| the same: bottom convention in the main table | "as is" for ISASTM (the README: a defect of the script, the convention was not checked for parts matched by `TO.C`) | ISASTM "negated X", the others as before, the second table (0 / 6, 10 / 0, 473 / 0) the same | TOL (`info["convention"]` of the `TO.C` parts is checked or "not checked") | EXPLAINED |
| An extra check that the study did not make: the program's own `detect_profile` against the research table on the 54 development sets | research 54 of 54 | the program 52 of 54; the two that differ are the emulated Zuken sets (profile `zuken` against `unknown`) | CAD profiles: no Zuken profile on purpose (the emulation is not a source of markers) | EXPLAINED (decision of the branch) |

### 2.2 gerber-models (the five models and the program's FVM on imported copper)

The README of this folder was re-run by its reviewer on a tree before the 2.4.5 laminate rule. `git archive` copies of `a6f822b`, `7a5b0ee`, `e9f4df2~1`, `e9f4df2`, `v2.4.5`
were run with the **current** scripts (`PYTHONPATH` = the copy; the scripts append the repository root last, so the copy wins). The result: `a6f822b` reproduces the
README of 4.14, 4.16 and R2 to the digit, and the current tree gives **exactly** the numbers of `v2.4.5` (`diff` of the whole output, 4.16 and R2), so every shift in this
folder is an item of 2.4.5 (LAM, and COVER for the FDM column), and none is new in 2.5.0 except the memory-guard refusals.

| Study (README section) | README | now | Item | Status |
| :-- | :-- | :-- | :-- | :-- |
| `study_scalar_formulas.py` (4.5) | arithmetic 9.7 / 11.3 / 11.1, Bruggeman 2.4 / 2.7 / 3.7 ... (7 rows) | identical | none | unchanged |
| `study_heater_size.py` (4.8) | 9 rows from 10.3 / 4.4 / 5.0 / 5.8 / 3.8 down to 7.3 / 1.6 / 0.7 / 0.7 / 0.5 | identical, all 9 rows | none | unchanged |
| `study_import_end_to_end.py` (4.31) | Stormduino -15.1, -2.1, -5.3, -2.1, -5.1 %; our board -4.8, +7.3, +5.2, +11.0, +10.0 % | Stormduino -14.3, -1.7, -4.9, -1.8, -4.8; our board -2.4, +7.3, +5.2, +11.0, +10.0 | LAM (faces unchanged, only the program's own fill run moves; the same values as the pass of 2.4.5) | EXPLAINED |
| `study_models_our_board.py` (4.34), fine rows | FVM 130.5, FDM 123.0, Lumped 115.9, Analytic 97.6, 3D solid refused (800 000 unknowns) | FVM 134.7, **FDM fine refused** (`MemoryGuardError`: 804 005 unknowns, about 11.7 GB), Lumped 115.9, Analytic 97.6, 3D solid **140.0** (ran, 24 s) | FVM: LAM; the FDM refusal and the 3D solid run: GUARD (a memory estimate against 0.60 of the physical memory replaced the 250 000-unknown window; the study asks for the 3D solid through the window) | EXPLAINED |
| the same, 1 mm rows (arithmetic / geometric / lambda / faces) | FVM 124.3, FDM 110.8, Lumped 117.2, Analytic 97.9, 3D 131.5; +23.9 / +17.9 / +14.2 % in the FVM | FVM 128.5, FDM 112.6, Lumped 117.2, Analytic 97.9, 3D 131.5; +23.5 / +17.4 / +13.7 % | LAM (one-layer board) | EXPLAINED |
| `study_models_rect_board.py 2` (4.35), 2 layers | FVM 98.0, FDM 96.9, Lumped 82.5, Analytic 72.2 (0.1 mm); 1 mm FVM +1.3 % / -6.9 % (shift 0.4); FDM -9.0 / -11.3; 3D solid +2.6 / -7.3 (0.25 mm) | 103.2, 101.9, 82.5, 72.2; FVM +2.2 / -8.3; FDM -11.8 / -14.5; the 3D solid fine run **refused by the memory guard** (720 000 unknowns, 10.6 GB), so its columns are `nan`; Lumped and Analytic unchanged | LAM for the FVM and FDM; GUARD for the 3D solid (the README said "refused by the 250 000 limit": the same outcome, another rule) | EXPLAINED |
| `study_rect_convergence.py` (4.37) | FVM 94.90 / 99.32 / 98.43 / 98.12 / 98.00 K at 2 / 1 / 0.5 / 0.25 / 0.1 mm; FDM 83.45 ... 96.97 | 98.11 / 105.47 / 103.93 / 103.40 / 103.20; FDM 82.92 / 89.88 / 94.90 / 99.87 / 101.91; 3D solid 100.50 / 109.22 / 107.33 / 106.49 (0.1 mm refused); Lumped -20.0 %, Analytic -30.1 %, 3D +3.2 % against the FVM | LAM; the Lumped and Analytic columns (82.5, 72.2) unchanged | EXPLAINED |
| `study_lumped_analytic.py` (4.16 and 4.27) | FVM 21.3 / 5.6 / 7.6 / 9.6, FDM 26.3 / 12.7 / 15.3 / 15.9, Lumped 27.7 / 15.5 / 17.6 / 17.9, Analytic 30.4 / 22.0 / 23.3 / 23.4, 3D 19.4 / 7.0 / 7.5 / 8.7 %; one effective conductance for the Analytic 8.8 % (p = -0.2) | FVM 17.5 / 7.7 / 6.9 / 7.2, FDM 23.3 / 9.0 / 11.4 / 12.0, Lumped 25.5 / 13.1 / 15.0 / 15.3, Analytic 28.3 / 19.7 / 20.9 / 21.1, 3D 17.4 / 8.6 / 7.7 / 7.9; p = -0.2: 9.5 %, p = -0.1: 8.7 % | LAM, all columns. **FDM column bisected**: `a6f822b` gives 12.2 / 17.2 / 15.9 / 17.3 (hot), `7a5b0ee` (COVER) and `e9f4df2~1` give the README column 26.3 / 12.7 / 15.3 / 15.9, `e9f4df2` (LAM) gives the current numbers. The zone union is not involved (the same output with an additive-union copy) | EXPLAINED (COVER for the FDM, LAM for all) |
| `study_laminate_reference.py` (Review R2): the program's FVM on the 0.2 mm pixels against the independent 3D solver | -9.8 % (-13.6 to -5.5); fill 0.8 / 1.2 mm -23.9 / -25.8 %; flow -9.4 / -9.2 %; fill against its own fine run -15.8 / -17.8 %; IC board -7.6, -12.2 | -11.9 % (-16.7 to -6.9); fill -24.9 / -26.6; flow -11.5 / -11.2; own fine -14.8 / -16.8; IC board fine 119.80 K (-12.3 %) and fill -16.4 %; the research solver against 3D -21.8 % unchanged | LAM; `a6f822b` reproduces the README column to the digit (-9.8, 23.9 / 25.8, 9.4 / 9.2, IC 126.19 K), `v2.4.5` equals the current output | EXPLAINED |
| `prototype_in_program.py` and `--all` (4.14, R3): fill / geometric / lambda / cell problem / flow on 42 windows at 0.6 / 1.0 / 2.0 mm | fill 18.6 / 21.3 / 21.7, geometric 5.2 / 5.6 / 6.6, lambda 2.4 / 3.0 / 5.0, cell 2.7 / 3.6 / 6.7, flow 1.5 / 1.9 / 4.1 %; "up to 0.24 (relative)" | fill 17.5 / 20.0 / 20.4, geometric 4.8 / 5.3 / 6.3, lambda 2.3 / 2.9 / 5.1, cell 2.6 / 3.6 / 6.9, flow 1.4 / 1.8 / 4.2; 0.21 | LAM; `a6f822b` reproduces the README to the digit (18.6 / 21.3 / 21.7 ..., 0.24); `v2.4.5` gives the current output unchanged (`diff` empty) | EXPLAINED |
| `study_fix_impact.py` | the impact of the zone union and the 3D solid laminate | not run: it needs one run per variant of the program (`max`, `additive`, `union`, `union_lam`) and a patched copy | the two changes it measures (the zone union, the 3D solid laminate) were adopted before 2.4.5 | NOT RUN |

About 25 other scripts of this folder (coverage, diagonal, track width, patterns, transient, `study_models_self.py`, `study_diagonal_heldout.py`, ...) were not run: they use
the research solver and not the program, or need a patched copy of it (`study_models_self.py`, about 20 minutes).

### 2.3 gerber-real-boards (the import, parts, copper mapping, the program's FVM on real windows)

| Study (README section) | README | now | Item | Status |
| :-- | :-- | :-- | :-- | :-- |
| `study_heater_shape.py` (docs/heater-shape-opinion.md table): 11 parts, 7 shapes | 69 rows of area and T_max (RP2040 U3 hull 57.18 mm2 46.4 K, exposed pad 5.49 mm2 63.7 K, SOT-223 tab +44.3 %, ...) | **69 of 69 rows identical** (area to 0.01 mm2, T_max to 0.1 K, by a script that parses the table of the document and the output) | none (the exposed-pad rule is already in the program the README was written on) | unchanged |
| `study_heater_margin.py` (docs/heater-modes-for-the-user.md table): margins 0.2 to 1.0 mm | RP2040 U1 -1.8 / -3.1 / -5.0 / -9.8 and exposed -5.1 / -8.3 / -12.9 / -21.8; U5, U3, U15, U4 rows | identical (the five rows checked cell by cell) | none | unchanged |
| `study_lumped_analytic_rule.py` (4.5): 24 windows | Lumped -6.0 % (-1.4 to -12.4), Analytic -6.3 % (-0.9 to -15.7); one window above 15 % (RP2040 at (75.2, -110.7): -15.7 / -12.4); calibration threshold 0.79, recall 1.0, 0.26 false alarms | identical window by window (-15.7 % / -12.4 %); threshold 0.794, recall 1.00, false alarms 0.26 | none | unchanged |
| `study_program_cells.py --part mapping` (`docs/validation.md` 27.1): 12 mm windows | 24 values of the table (faces 0.15 / 0.27 ... fill 4.77 / 7.83 ...) | identical, all 24 | none | unchanged |
| `study_program_cells.py --part ref3d` (27.2) | 16 values (faces 1.36 / 1.55 ... naive 4.31 / 4.87 ...) | identical, all 16 | none | unchanged |
| `study_rule_on_faces.py --part synthetic / real / holes` (4.1 B, README 10) | real: two layers 0.6 / 1.2 mm fill 5.27 -> 3.59, faces 1.64, lambda 1.30; four layers 2.83 / 1.29 ...; with holes 3.72 / 4.79, 1.66 / 1.21, 1.20 / 0.78; 4 layers 2.82 / 2.86, 1.30 / 1.21, 1.23 / 0.98; synthetic 18 cases | identical on every printed group (the synthetic ones by the weighted mean of the 2 and 4 layer rows: flow 1.16 / 1.53) | none | unchanged |
| `study_transient_fine.py` (4.3) | six rows: +11.6, +18.3, +19.2, +9.7 %, tau -9.8 % (1 mm) ... +3.8, +4.2, +4.8, +3.9 %, tau -11.7 % (0.25 mm, bare capacity); reference 7.99 / 27.24 / 37.14 / 73.66 K, tau 57.1 s | identical, all 6 rows and the reference | none | unchanged |
| `study_grid_error_drawn_copper.py` (Decisions Log, `docs/validation.md`) | +0.54 / +2.17 % at 1 / 2 mm with full copper, +3.66 / +11.77 % bare | the six rows identical (L2 full +0.11 / +0.54 / +2.17, bare +0.85 / +3.66 / +11.77; L4 +0.11 / +0.52 / +2.04 ...) | none | unchanged |
| `study_x3_components.py` (4.4): 6 X3 files, 434 parts | 420 Courtyard + 14 Footprint; courtyard over the paste box in the part frame 1.57, by side 1.49 / 1.73 ...; StickHub bottom 0.74 on the board axes | 420 + 14; 1.49 (StickHub top), 1.73 and 0.74 (bottom); counts of components, pins and refs the same | none | unchanged |
| `study_time_memory.py` (4.2): unknowns of the faces and of the program's count | ISASTM 41 616 / 72 828 (1 mm), 166 464 / 291 312 (0.5), CMM2 53 972 / 94 451, 214 020 / 374 535, OSW 5 476 ... | the same counts; peak 0.8 / 1.7 / 0.9 / 1.9 GB against 0.86 / 1.96 / 0.90 / 1.96 (a loaded machine, 8 % to 13 %); one extra case (ISASTM 0.25 mm: 662 596 unknowns, 59 s for the faces, 5.9 GB); fit 8.57 KB per unknown (252 % worst) against 9.7 KB (211 %) with another case set | none; peaks are load and case set | unchanged (a timing and a case set) |
| `study_project_file.py` (4.8) | the file round trip | **fails at once**: `ProjectFormatError: format 2 project file without its "project" section`: the study writes the flat layout of the research prototype and reads it with `load_project` | project format 2 is nested under `project` (the research prototype of the flat layout was superseded, Decisions Log); the script and its README section 4.8 describe a format that does not exist | EXPLAINED (the script needs updating by its owner; the program is right) |
| `study_conformance_rare.py`, `study_odb_structure.py`, `study_paste_footprints.py`, `study_fine_copper_warning.py` | | | they use the research libraries (`lib/`), not the program | NOT RUN |

## 3. Why the shifts of gerber-models are 2.4.5 and not 2.5.0 (the bisection)

`study_lumped_analytic.py` (4.16) on the same 42 windows, the current script, the program from `git archive`:

| Program | FVM fill / geo / lam / dual | FDM | Lumped | Analytic | 3D solid |
| :-- | :-- | :-- | :-- | :-- | :-- |
| README | 21.3 / 5.6 / 7.6 / 9.6 | 26.3 / 12.7 / 15.3 / 15.9 | 27.7 / 15.5 / 17.6 / 17.9 | 30.4 / 22.0 / 23.3 / 23.4 | 19.4 / 7.0 / 7.5 / 8.7 |
| `a6f822b` (before the 2.4.5 items) | 21.3 / 5.6 / 7.6 / 9.6 | **12.2 / 17.2 / 15.9 / 17.3** | same as README | same | same |
| `7a5b0ee` (COVER) | same as README | **26.3 / 12.7 / 15.3 / 15.9** | same | same | same |
| `e9f4df2~1` | same as `7a5b0ee` | | | | |
| `e9f4df2` (LAM) | 17.5 / 7.7 / 6.9 / 7.2 | 23.3 / 9.0 / 11.4 / 12.0 | 25.5 / 13.1 / 15.0 / 15.3 | 28.3 / 19.7 / 20.9 / 21.1 | 17.4 / 8.6 / 7.7 / 7.9 |
| `v2.4.5` and `e97b62f` (this tree) | identical to `e9f4df2` | | | | |

Shifts with an additive zone union (the program does a per-sample maximum since 2.4.3, the README ran 4.27 on a patched copy): the same output with a patched copy
(`np.maximum` replaced by `np.minimum(window + mask * fill, 1)` in `geometry.zone_fill`, in the scratchpad), because the study draws one zone per cell and the zones do not overlap.

## 4. What was not run and what the reviewer should look at

* `gerber-import` and `gerber-nets`: no study imports the program; only their tests ran (51 and 18 passed).
* `gerber-cad-profiles`: `study_markers.py`, `study_heldout.py`, `study_conventions.py`, `study_gerbonara_crosscheck.py` use the research table (`lib/cadprofiles.py`), not the program;
  the program's `detect_profile` was compared with that table on the 54 development sets (section 2.1, last row), the 28 held-out sets were not.
* `gerber-models`: `study_fix_impact.py` (variants of the program) and `study_models_self.py` (a patched copy, about 20 minutes) were not run; the other studies use the research solver.
* `gerber-real-boards`: `study_transient_fine.py` ran the default board only; the 0.25 mm whole board and CO60 / RP2040 / vstcm of 4.2 are the README's own "not run".
* **Stale text, for the reviewer (no README was edited by this pass):** `gerber-models` README 4.14, 4.16, 4.27, R2, 4.31 and 4.34 to 4.37 quote numbers of the program before the 2.4.5
  laminate rule (the 2.4.5 pass listed them); 4.34 and 4.35 say the 3D solid and FDM fine runs are "refused by the limit of 250 000 unknowns", now by the memory guard
  (`MemoryGuardError`, the FDM fine run of 4.34 is refused and the 3D solid runs); `gerber-real-boards` `study_project_file.py` and README 4.8 describe the flat project layout, which the program
  no longer reads.
* The first `study_lumped_analytic.py` run ended with return code 1 after the runner had been paused and resumed (the output was complete); the run on the patched copy,
  the runs on the archives and the run on `v2.4.5` all ended with 0 and gave the same numbers.
