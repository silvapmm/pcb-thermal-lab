# Conclusions, phase 1: reading the files

Written on branch `research/gerbers` (phase 1 of three of the Gerber research, split from one study: `research/gerber-import`, `research/gerber-models`, `research/gerber-nets`; the section numbers 4.1 to 4.40 are those of the original study, see the table in `README.md`). The evidence is gathered in [`REPORT.md`](REPORT.md). Everything quoted here has a section of `README.md` (numbers, tables, limits), a script (`scripts/`) and, where it is a claim that can break, a test (`tests/`, 41 tests in about 8 s; `cd research/gerber-import && python -m pytest -q tests`; one geometry test needs shapely and the KiCad check needs the Stormduino files from `scripts/fetch_boards.py`). Nothing in `pcbthermal/` was changed.

## 1. Where we stand

1. **Reading is solved without third-party libraries for what the program needs** (copper layers and drills). The NumPy-only reader (`native_gerber.py`) gives the same raster as gerbonara + shapely at the pixel, is faster, refuses what it cannot do, and reads the net names (`TO.N`). It is a smaller reader, not a better one (README 4.17 to 4.19, 4.22, 4.24).
2. **Vias and nets map from the files**: plated holes (X2 file function of the drill file) matched to the via pads (aperture function) and their nets give the program's vias and the connection of polygons across layers; on a real 4-layer KiCad board 225 of 225 vias have the same net on all four layers (README 4.29).
3. **The nets agree with the CAD file of a real project** (Stormduino, KiCad 5, MIT; README 4.33): every object of the `.kicad_pcb` lies on the copper read (1380 of 1380 track points, 48 of 48 via points, 281 of 281 pad points), no piece of copper or group joined through the 109 plated holes holds two nets, and 55 of 56 nets without a zone fill split into the same pieces as in the CAD file. The one difference (`Net-(J2-PadA7)`) is most probably the crude overlap test of the CAD side; it was not examined.
4. **The files give what the next phases need**: `importer.import_board` returns the box, a binary and a coverage mask per layer (pixel at most half the thinnest track, with a warning), the holes with pad, kind and net, and warnings; no program is needed (README 4.30, `tests/test_importer.py`).
5. **Same copper, pixel by pixel** (README 4.45, figures 9 to 12): drawn by four tools the layer looks the same, and against the vector truth the independent reader differs in 85 of 4.76 million copper pixels on 12 layers of 8 boards, all within 0.042 pixel of an exact edge; most of what remains is the truth's own 16-segment circles (with 128 segments, 12 pixels differ on the Stormduino top layer instead of 478).
6. **The nets against the KiCad project, pixel by pixel** (README 4.46, figures 13 and 14): drawn from its own `.kicad_pcb`, 99.998 % of the 2.25 million pixels the CAD file assigns to the 57 nets of the Stormduino lie on Gerber copper, and the Gerber copper without a CAD object farther than a pixel is 0.13 % (top) and 0.16 % (bottom).
7. **The pixel matters more than the reader**: another reader (gerbonara + shapely) changes the thermal result by 0.01 to 0.04 % (phase 2, 4.31); binary masks lose or invent area on thin copper and a lattice-aligned track as wide as the pixel can vanish (`tests/test_reader_claims.py`); a coverage mask keeps the area.

## 2. The validated numbers

| Claim | Number | Where | Test |
| :-- | :-- | :-- | :-- |
| Vias and nets: 225 vias of a 4-layer KiCad board, net equal on all four layers | 225 of 225; 68 of 68 plated component holes of the X2 test set agree on both layers | 4.29 | `study_vias_nets.py`, `tests/test_nets.py` |
| Reader area vs gerbonara + shapely, 8 real boards | 0.0 to 0.9 % average per board | 5 | `study_native_check.py` |
| Reader on 14 files of known area: same raster as gerbonara + shapely and pcb-tools (binary) | to the digit; error is the pixel | 4.22 | `compare_readers.py`, `tests/test_native_gerber.py` |
| Reader, files of gerbonara's test set | 161 of 164 comparable within 3 % (149 before the vector reference was fixed) | 4.17 | `study_reader_conformance.py` |
| Drills, 34 files read by both tools | 34 identical (36 of 38 read, 2 without a unit refused) | 4.19 | `study_reader_scope.py`, `test_excellon_*` |
| gerber-writer files: arcs and thermal macros | -0.04 % (gerbonara -0.00 %; an earlier -8.57 % was our wrapper ignoring arcs) | 4.24 | `study_gerber_writer.py`, `test_vector_reference_includes_the_circular_tracks` |
| Net pieces by connectivity; wire keeps its net | | 4.20 | `test_net_pieces_are_found_by_connectivity_and_a_thin_wire_keeps_its_net` |
| Our IC board as a bench: nine nets in one piece each and no short, 16 holes with the right nets | 2 tests | 4.30 | `tests/test_our_board_bench.py` |
| Nets of the Stormduino against its `.kicad_pcb` | 1380/1380, 48/48, 281/281 objects on copper; 0 pieces or groups with two nets; 55 of 56 nets split alike | 4.33 | `study_kicad_nets.py`, `tests/test_kicad_nets.py` |
| Nets of the Stormduino against its `.kicad_pcb`, every pixel | 2,246,366 of 2,246,416 CAD pixels of the 57 nets on Gerber copper; Gerber copper without a CAD object farther than 1 px: 0.13 % (top), 0.16 % (bottom) | 4.46 | `study_kicad_pixels.py`, `tests/test_kicad_pixels.py` |
| Reader with another reader in the whole thermal chain | 0.01 to 0.04 % in the heater temperature (phase 2) | 4.31 | `gerber-models/scripts/study_import_readers.py` |

## 3. What is not validated, and the limits

* The reader is checked against other readers (gerbonara + shapely, pcb-tools, pygerber) and against files of known area and against a CAD file, never against a manufactured board.
* The reader: no aperture blocks, mirrored/rotated/scaled apertures, moire or image mirror; a drill file with no unit is refused; net names exist only when the CAD tool writes them (zone fills often have none); the Ucamco specification and test files were not read (host blocked).
* The nets were compared with a CAD file on **one** board and KiCad 5 only; zone fills were not compared net by net.
* Board outline polygons (non-rectangular boards) are not drawn by the importer: the box only.

## 4. Recommendations and decisions left to the maintainer

1. **Import settings the program should enforce**: draw the copper as a coverage mask (4 x 4 sub-samples) at 0.1 mm; a pixel at most half the thinnest track found in the file (and a warning when a track is thinner than the pixel); 8-connected labelling for any question of "which piece is which".
2. **Use the NumPy-only reader** (no new dependency, no licence question); keep gerbonara + shapely only as a test reference.
3. **Nets**: X2 net attribute when present, connectivity for the rest, a netlist (`.kicad_pcb` or a netlist file) as the check or the source, and the user assigns a piece otherwise.
4. **Missing for a real import**: the step where the user confirms layers, outline and which holes are vias (a Gerber cannot tell a via from a component pad); the board outline polygon from the profile layer exists as a prototype (README 4.47) and needs that confirmation; the form of the inputs (decided later by the maintainer).
5. **Open decisions**: whether to download the Ucamco example data sets as extra conformance files; whether to support more CAD formats than KiCad for the check of the nets.

## 5. How to reproduce

```
cd research/gerber-import && python -m pytest -q tests                          # 41 tests, 8 s
.venv/bin/python research/gerber-import/scripts/fetch_boards.py                 # the boards and the CAD file into data/ (git-ignored; licences differ)
.venv/bin/python research/gerber-import/scripts/study_kicad_nets.py             # section 4.33, seconds
.venv/bin/python research/gerber-import/scripts/study_reader_conformance.py     # section 4.17, about 5 minutes (needs gerbonara)
.venv/bin/python research/gerber-import/scripts/make_figures.py                 # the picture in figures/
```
