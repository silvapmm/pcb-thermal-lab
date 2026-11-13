# FDM and a copper edge held inside the board

**Status: closed, reviewed (section 8: go). The correction is implemented in the program** (`fix/fdm-copper-edge-faces`, merged into `develop`, reviewed: go):
`fdm.Network._copper_face_sheets`, switch `face_fill` of `fdm.Network` and `fdm.solve_steady` (default on), `docs/theory.md` 3, `docs/validation.md` 47. The study was
made on a program without it (`develop` 57a28951); since then its 'FDM (program)' column is the program with `face_fill=False` and is labelled **FDM harmonic** below,
and the 'face fill' column is the program as it is now (the prototype of `lib/fdm_variant.py` gives the same field, `tests/test_variant.py`).

## 1. Question

An independent finite-element comparison found that the FDM (harmonic face mean, the FDM default before the face fill) reads a copper edge that stops
INSIDE the outline 2 to 3 times colder than the FVM: -7 / -14 % (20 mm square, copper 1.2 mm in, 200 / 1000 W/m2K, 1 mm cell), -7 / -16 % (disc), -5 / -10 % at 0.5 mm,
the via effect 4 to 16 % low (on the plate with the copper to the wall, so not a copper-edge effect; section 8), and on the 10 mm plate with the copper 0.5 mm in the wall -1.0 % already at 10 W/m2K and -7.6 % at 1000 (FVM -0.1 / -1.1 %).
The earlier FDM review (`docs/validation.md` 41, 41.1) judged the harmonic mean against the FVM at 0.25 mm and the independent 3D solver and found it better everywhere
it looked, and left "the residual -2 to -7 % ... the first-order error of a node-centred scheme with the copper edge between nodes (not fixed here)". This folder finds
which term that is and measures the smallest correction. The program is not touched: every variant is a copy built from the source text of `pcbthermal/fdm.py`
(`lib/fdm_variant.py`); since the adoption the studies run the program itself with `face_fill=False` and `True` (`fdm_variant.harmonic()`).

![A copper edge on a node of the FDM](figures/fig_01_copper_edge_between_nodes.png)
*Figure 1 (`fig_01_copper_edge_between_nodes.png`): section through the strip between the wall and the copper; the control volumes of the nodes, the half-copper sheet that
node 2 reads, and the sheet that the face between two nodes reads with the harmonic mean and with the face fill (made by `scripts/make_diagrams.py`).*

## 2. Method

References: the finite-element limits of an independent finite-element comparison (quoted, not re-run: plate 53.406 / 41.826 / 33.906 K and square 124.551 / 57.201 / 38.972 K at 10 / 200 / 1000
W/m2K), the FVM at 0.0625 mm where no limit exists, and the independent 3D solver `tests/helpers/layered3d.py` at the same cell (as validation 41). Boards: the 10 mm
four-layer plate of `research/strong-edge-laminate` (copper inset 0 to 0.625 mm) and the 20 mm two-layer square, here kept ALIGNED with the grid and run as a plain
rectangle and as the same rectangle with an explicit outline (separating the plain edge from the outline cut-cell treatment). Scripts: `study_cause.py` (tables 3 and 4),
`study_independent_3d.py` (5), `study_harness_shift.py` (6). Cells 0.25 mm or more (FVM reference 0.0625 mm on the 10 mm plate only, 0.125 mm in table E). Memory: under 1 GB
for `study_cause.py` and `study_harness_shift.py`; `study_independent_3d.py` peaks at 4.7 GB (the independent solver on the strips board at 0.25 mm; the earlier 'under 1 GB' was wrong).

## 3. The cause

The FDM (before the face fill) took the copper fill of a node as the covered share of its control volume (`_node_average` of the cell fills) and joined two nodes by the harmonic mean of the two
nodal sheets. A copper edge that falls on a node (or anywhere in the cells around it) leaves that node with a half-copper sheet; the face on the copper side then reads
`2 x 0.5 x 1 / 1.5 = 0.67` of the copper sheet instead of 1 (the cell between the two nodes is entirely copper), and the bare side keeps a node with copper it does not have.
The copper edge is blurred over a cell and the first copper link is weak, so the board spreads the heat less (Figure 1).

### 3.1 Which term (plate, copper 0.5 mm inside, cell 0.25 mm, hottest rise, % of the finite-element limit; `study_cause.py A`)

| h_side | FVM | FDM harmonic | FDM face fill | the same, laminate rule at 1 sub-gap: FVM / FDM / face | at 8 sub-gaps: FVM / FDM / face |
| --: | --: | --: | --: | :-- | :-- |
| 10 | -0.11 | -0.97 | -0.56 | -0.53 / -1.25 / -0.81 | +0.30 / -0.67 / -0.41 |
| 200 | -0.45 | -3.47 | -1.48 | -1.93 / -4.79 / -2.40 | +0.99 / -2.13 / -0.98 |
| 1000 | -1.09 | -7.65 | -2.97 | -4.25 / -10.86 / -4.99 | +1.91 / -4.53 / -1.92 |

At 0.5 mm: FDM harmonic -1.26 / -5.09 / -12.21 %, face fill -0.95 / -2.28 / -4.45 %, FVM +0.35 / +0.54 / +0.69 %.

Controlled experiments (each a copy of `fdm.py` with one term changed; the 'FDM' of this table is the FDM harmonic):

| term | result | verdict |
| :-- | :-- | :-- |
| nodal copper fill and the harmonic mean at the copper edge | faces built from the cell fill (cell between two nodes is uniform along the face) take the aligned inset from -12.2 / -7.65 % to -4.5 / -3.0 % (1000 W/m2K, 0.5 / 0.25 mm) and the 20 mm square (copper 1.2 mm in, edge on a node, 0.6 mm) from -3.1 / -6.1 % to -1.2 / -2.3 % (200 / 1000) | **the cause**: 50 to 77 % of the gap to the FVM |
| film switched off (h_side 0.001, the edge term alone) | FDM -0.55 %, face fill -0.21 %, FVM +0.20 % (against the FVM at 0.0625 mm) | the copper-edge term is there without any film; the film only makes it matter (the gap grows with the film because the heat that cannot spread is lost at the wall) |
| laminate rule (sub-gaps 1, 2, 8) | the FDM-to-FVM gap is 2.9, 3.0, 3.1 points at 200 W/m2K (1, 2, 8 sub-gaps) | not the cause |
| edge film on the laminate nodes, half-volume edge nodes, corner nodes | copper to the wall with ONE sub-gap: FDM = FVM to 0.1 point (-10.34 / -10.28 % at 1000 W/m2K, 0.25 mm); with more sub-gaps the FDM converges from the cool side to the limit (-1.10 % at 8 sub-gaps and 0.125 mm) while the FVM overshoots (+2.01 % at 8 sub-gaps and 0.25 mm: the half-cell film); table E (`study_cause.py E`, added by the review) | not defects of the FDM's copper edge; at the wall with eight sub-gaps the FDM is the better of the two, with the shipped rule it is the cooler (-5.13 against -3.52 % at 1000 W/m2K, 0.25 mm; the wall term of A40) |
| outline cut-cell cover | aligned square as a plain rectangle and as an explicit outline: FDM -3.13 / -3.25 %, face -1.15 / -1.27 % (200 W/m2K, 0.6 mm); -6.10 / -6.28, -2.25 / -2.43 (1000) | not the cause (0.1 to 0.2 point) |
| via edge image | plate with the copper TO THE WALL (the board of the finite-element via comparison), cell 0.25 mm: the image acts only in the FVM, and switching it off there changes the via effect by 0.8 / 0.7 points at 0.16 mm from the wall (200 / 1000 W/m2K; the earlier '0 to 6 points' was not reproduced by any script) and by 0 at 3 mm; the FDM via error (-5.38 / -3.59 / -15.52 / -9.87 % at 0.16 / 3 mm, 200 / 1000) is the same with the face fill (no copper edge on that board); table F (`study_cause.py F`, added by the review) | not the cause of the via numbers; they follow the wall term |

What the face fill does NOT remove, stated: the plate with the copper to the wall (FDM -1.10 % at 200 and -5.13 % at 1000 W/m2K, 0.25 mm, identical with the face fill) is the
wall term (laminate sub-gaps, see the row above) and the via effect on that board at 1000 W/m2K stays 10 to 16 % low at 0.25 mm. The remaining inset gap of the face fill
to the FVM (1 to 2 points) is that same wall term.

### 3.2 The position of the copper edge (cell 0.25 mm, error against the FVM at 0.0625 mm; `study_cause.py D`)

| inset mm | 200: FVM / FDM harmonic / face | 1000: FVM / FDM harmonic / face |
| --: | :-- | :-- |
| 0.300 | +0.43 / -1.97 / -0.37 | +1.02 / -6.97 / -1.08 |
| 0.375 | -2.50 / -4.78 / -3.26 | -6.58 / -13.81 / -8.48 |
| 0.450 | -3.97 / -6.11 / -4.70 | -9.75 / -16.37 / -11.49 |
| 0.500 | +0.49 / -2.56 / -0.55 | +0.88 / -5.81 / -1.03 |
| 0.550 | +0.54 / -2.49 / -0.50 | +0.93 / -5.69 / -0.99 |
| 0.625 | -2.77 / -5.65 / -3.78 | -5.39 / -11.47 / -7.17 |

![error against the position of the copper edge](figures/fig_02_error_against_edge_position.png)
*Figure 2 (`fig_02_error_against_edge_position.png`): the same numbers; the FVM itself scatters by 4 to 11 points with the edge inside a cell (the cut cell mixes copper and bare
by area), the FDM harmonic is 2 to 7 points cooler everywhere, the face fill 0.7 to 2.1 points cooler than the FVM.*

The scatter of the FVM when the edge falls inside a cell is a limit of the cell-centred scheme (validation 40, 43) and is not touched. The face fill stays on the same side
and 1.3 to 5 times closer to the FVM than the FDM harmonic at every position.

### 3.3 The 20 mm square, aligned (heater mean, % of the finite-element limit; `study_cause.py C`)

| h_side, cell | FVM | FDM harmonic | face fill |
| :-- | --: | --: | --: |
| 200, 0.6 | -0.56 | -3.13 | -1.15 |
| 200, 0.4 | -0.97 | -3.40 | -1.86 |
| 1000, 0.6 | -1.05 | -6.10 | -2.25 |
| 1000, 0.4 | -1.76 | -6.17 | -3.23 |
| 200, 0.5 (edge mid-cell) | -2.90 | -5.56 | -4.08 |
| 1000, 0.5 (edge mid-cell) | -5.37 | -10.35 | -7.35 |

Plain rectangle and explicit outline of the same 20 mm box agree to 0.2 point (the table is the plain rectangle). This is NOT the board of the turned squares below: those are
20 mm squares inside a 32 mm box, and the FDM reads the same aligned square 2 to 5 points differently as the whole board or as an outline in a larger box (A40, section 8).

The ten turned and shifted squares of the finite-element comparison (not rebuilt by this folder; the program numbers are those re-run by the review of `fix/fdm-copper-edge-faces`,
`docs/validation.md` 47.1): mean error 1 mm / 0.5 mm, 200 W/m2K: FDM harmonic -6.97 / -4.89, face fill -5.77 / -3.77; 1000: FDM harmonic -14.23 / -9.12, face -11.99 / -6.86 (FVM -3.07 / -2.68
and -5.53 / -4.68). A turned slanted edge inside a cell leaves most of the gap, because the cell fill of a cut cell is the same blur. **The face fill is not a full cure there** (it removes
1.2 and 2.3 of the 4 and 8 points). Where the copper reaches a turned or curved outline the face fill moves the FDM 0.05 to 0.5 point AWAY from the finite elements (square at 1000 W/m2K,
1 mm, -4.36 -> -4.76 %; disc to the rim -4.88 -> -5.33 %; T at 200 W/m2K -0.73 -> -1.20 %): the earlier text called this 'unchanged within -0.4 point' and the INTEGRATION 'none
overshoots'; the review of the fix showed that the weak harmonic link at the cut cells had offset the FDM wall term (two errors no longer cancelling, validation 47.1).

![plate against the finite-element limit](figures/fig_03_inset_plate_against_fem.png)
*Figure 3 (`fig_03_inset_plate_against_fem.png`): table 3.1, shipped laminate rule.*

## 4. The smallest correction

`face_fill` (the prototype: about 25 lines in `fdm.Network.__init__`; adopted as `fdm.Network._copper_face_sheets`; no change of the unknowns, the matrix pattern, the capacities, the sources or the vias):

* keep the nodal fill for everything nodal (capacity, vertical links, top and bottom film, via sheets, laminate rule);
* for the in-plane face of a COPPER layer take the sheet from the copper fill of the CELLS the face runs through: `S_face = (A_face + B x f_face) x (mean cover)`, with `B = (k_cu - k_lam) t_cu`,
  `A` the nodal sheet with no copper (after the rule), `f_face` the average of the two cells flanking the face (one at the board edge);
* faces of the laminate nodes, imported-copper faces and boards with a metal block keep the earlier code (the variant applies only with the laminate rule and drawn copper).
* in the program (not in the prototype) only the faces where a nodal fill differs from the face fill by more than `fdm.FACE_FILL_TOL` (1e-9) are replaced and only with the harmonic
  mean, so uniform and hatched copper are bit-identical and the tiny moves of the prototype on full-copper boards (section 6) do not happen; elsewhere the prototype and the program
  agree to 3e-6 of the rise (the mean of unequal bare sheets at faces whose fills agree).

Properties checked (`tests/test_variant.py`, 11 passed on the current `develop`): the switchless copy of the source is the program bit for bit; the prototype gives the program's field
(plate, square, gap board, within 1e-5 of the rise); uniform copper is bit-identical; the matrix is symmetric to
1e-12, no positive off-diagonal, balance below 1e-9; the copper-to-the-wall plate moves less than 1e-3 K; the plate error against the finite-element limit lies in the measured
band; the gap board stays below the independent solver and closer to it.

## 5. Against the independent 3D solver (validation 41 boards, same cell, hottest rise; `study_independent_3d.py`)

| board | cell mm | FVM % | FDM harmonic % | face fill % |
| :-- | --: | --: | --: | --: |
| plate_pad | 1 / 0.5 | -2.12 / -1.66 | -7.31 / -4.32 | -5.36 / -2.86 |
| one_layer_pad | 1 / 0.5 | -1.73 / -1.48 | -6.75 / -4.07 | -5.20 / -2.75 |
| 3 mm gap (50 x 24 mm) | 1 / 0.5 / 0.25 | -1.48 / -1.18 / -0.97 | -5.49 / -3.17 / -1.96 | -3.52 / -1.92 / -1.20 |
| strips 2 / 2 (40 x 20 mm, own geometry) | 1 / 0.5 / 0.25 | -11.77 / -9.58 / -8.22 | -33.63 / -23.43 / -15.89 | -23.05 / -15.00 / -10.37 |

The first three rows reproduce the numbers of validation 41 for the FVM and the FDM to the digit; the face fill is cooler than the reference in every row (it never overshoots) and closer in
every row. The strips board is this study's own geometry: strips along x every 4 mm, the 4 x 4 mm part at y 8 to 12 mm lies over a strip AND a gap (the earlier text said 'on a strip').
The strips row of validation 41 is another board whose geometry is in no script and which is not reconciled (validation 47.2), so only the face-fill-against-harmonic difference is comparable.

![against the independent 3D solver](figures/fig_04_against_independent_3d.png)
*Figure 4 (`fig_04_against_independent_3d.png`): table 5.*

## 6. What moves (harness boards, FDM, `study_harness_shift.py`)

Hottest rise, shift of the face fill against the FDM harmonic (re-run on the program as adopted), in K at 2 / 1 / 0.5 mm (FDM above 120 000 unknowns not run: `example_board`, `profile_board`, `example_cut_to_T` at 0.5 mm, an unverified
gap):

| board | shift |
| :-- | :-- |
| plate_pad | +8.19 / +6.55 / +4.81 K (+2.7 / +2.1 / +1.5 % of the rise) |
| one_layer_pad | +1.00 / +1.08 / +0.91 K (+1.6 / +1.7 / +1.4 %) |
| two_layer_partial | +0.117 / +0.393 / +0.314 K (+0.09 / +0.29 / +0.23 %) |
| part_top_path | +0.128 / +0.249 / +0.212 K (+0.27 / +0.51 / +0.44 %; the part mean -0.4 to -0.8 %) |
| example_board, profile_board | -0.0095 K at 2 mm, +0.0077 K at 1 mm (about 0.02 %) |
| example_cut_to_T | -0.0104 / +0.0083 K at 2 / 1 mm |
| every other board (`t_outline`, `part_across_outline`, `round_outline`, `plate_vias`, `plate_lone_via`, `reference_board`, `plate_uniform`, `one_layer_full`, `finned_block`, `hatched_copper`) | 0 |

With the program as adopted 18 of the 48 runs made here move by more than the 1e-8 K tolerance of the frozen test; with the three skipped 0.5 mm runs they are the 21 records of the
pending file `fdm-copper-edge-faces`. **Corrected by the review**: the prototype (which replaces every copper face) moved 36 of 48 runs, the six full-copper boards above by 1e-5 to
2.6e-3 K; the adopted code replaces only the faces whose fills differ, so those boards do not move. All four large rows go the same way as the independent comparison (hotter, closer): `plate_pad` -7.31 to -5.36 % at 1 mm.
Balance of every run below 2e-11 (relative to the power). The times to 63 % and the profile curves were not measured here; the 7 times of the pending file move (validation 47).

## 7. Limits

* The face fill removes 50 to 77 % of the FDM-to-FVM gap for a copper edge on or near a node, 1.2 of 7 points (200 W/m2K) on turned slanted edges at 1 mm; after it the plate with the copper inset stays 1.5 / 3.0 % cool at 200 / 1000 W/m2K (0.25 mm; the aligned square 1.2 to 3.2 %) and the via effect (on the plate with the copper to the wall) 10 to 16 % low, set by the wall (laminate sub-gaps) term of the FDM and by the cut-cell mixing of a copper edge inside a cell.
* No FDM change touches the half-volume nodes, the film or the outline cover (shown not to be the cause).
* The finite-element limits are quoted, not re-run here; that comparison reads the hottest POINT and the program the hottest CELL mean (-0.2 to -0.75 % at these cells, the same for
  both FDM columns, so the comparison of the two faces is unaffected).

## 8. Review

Reviewer's verdict: **go for closing.** The cause is confirmed on the current `develop` (with the face fill merged), the ablations hold, the numbers reproduce to the digit,
and the claims that the review of `fix/fdm-copper-edge-faces` found wrong are corrected above. Work of the review, on this branch:

* **Studies re-pointed at the program.** The study ran on `develop` 57a28951, before the face fill was merged; on today's tree `fdm.solve_steady` IS the face fill, so the old
  'FDM (program)' column would silently have become the face fill and three folder tests failed. `lib/fdm_variant.py` now offers `harmonic()` (the program with `face_fill=False`)
  and `load(face_fill=True)` switches the program's own face path off before adding the prototype; the studies run the program with `face_fill=False` / `True`; the tables are
  labelled 'FDM harmonic' and 'face fill'. A test now holds that the prototype gives the program's field (3e-6 of the rise at most; the program replaces only the faces whose fills differ).
* **Re-run on the current tree** (`study_cause.py A B C D`, `study_independent_3d.py`, `study_harness_shift.py`): every number of tables 3.1, 3.2, 3.3 (the aligned square), 5 and the
  large rows of 6 reproduced to the digit; the FVM columns too (the FVM items of 2.7.0 merged after 57a28951 do not reach these boards).
* **Ablations checked again, two added as scripts.** The plain-rectangle against explicit-outline control (table C) holds (0.1 to 0.2 point; identical at 0.4 and 0.5 mm).
  The wall claims were in no script: table E (`study_cause.py E`) now prints them and reproduces them:

  | h_side, cell | one sub-gap: FVM / FDM harm / face | shipped rule | eight sub-gaps |
  | :-- | :-- | :-- | :-- |
  | 200, 0.25 | -2.28 / -2.35 / -2.35 | -0.57 / -1.10 / -1.10 | +0.46 / -0.59 / -0.59 |
  | 200, 0.125 | -2.30 / -2.30 / -2.30 | -0.77 / -0.91 / -0.91 | +0.04 / -0.28 / -0.28 |
  | 1000, 0.25 | -10.28 / -10.34 / -10.34 | -3.52 / -5.13 / -5.13 | +2.01 / -2.31 / -2.31 |
  | 1000, 0.125 | -10.29 / -10.31 / -10.31 | -4.11 / -4.58 / -4.58 | +0.32 / -1.10 / -1.10 |

  (plate with the copper to the wall, hottest rise, % of the finite-element limit). With one sub-gap the FDM and the FVM agree, so the edge film on the laminate nodes, the
  half-volume and the corner nodes are not the copper-edge cause; with the shipped rule the FDM wall term is 0.5 to 1.6 points cooler than the FVM, which is the FDM wall
  item (A40), not this folder's cause. The via image claim (table F) was **wrong in its size**: the image changes the FVM via effect by 0.8 / 0.7 points at 0.16 mm, not '0 to 6'; the
  conclusion (not the cause) stands. The FDM via numbers are those of the board with the copper to the wall, which the face fill does not touch (bit-identical via effect).
* **Corrected claims** (also corrected in `docs/validation.md` 47 by the review of the fix): 'every copper-edge board gets closer and none overshoots' holds for the boards of the
  tables, not where the copper reaches a turned or curved outline (0.05 to 0.5 point further off; section 3.3); the strips board has its part over a strip and a gap, and the
  strips row of validation 41 is not reconciled; the harness shift of the prototype (36 runs) is not that of the adopted code (18 of 48 runs, 21 records with the three skipped 0.5 mm runs); the
  memory of `study_independent_3d.py` is 4.7 GB, not under 1 GB; the 'FDM' of the turned squares is a board inside a 32 mm box, not the same FDM board as the aligned square (A40).
* **Finite-element numbers checked** against the report of the finite-element comparison (read only): the plate limits 53.406 / 41.826 / 33.906 and 51.687 / 36.981 / 24.332 K, the
  square limits 124.551 / 57.201 / 38.972 and 50.635 / 30.114 K, the via effects 1.579 / 2.534 / 0.683 / 1.226 K, and every FDM and FVM percentage this folder quotes from it agree;
  its own review notes the point-against-cell read-out (section 7).
* **Program untouched**: `git diff develop...research/fdm-inset-edge --stat -- pcbthermal tests examples ico` is empty.
* **Open**: A40 (the FDM wall term on the board box against an outline side; the turned squares), A32 (node-centred cut cells), the warning texts that quote the FDM at a
  copper edge (now upper bounds, not re-measured). No decision of the maintainer is left from this folder: the correction was decided and merged.

## 9. What was read and what was not verified

* Read in full: the report of the independent finite-element comparison, section 3 (tables 3(a) to 3(d)) and its review, `pcbthermal/fdm.py`, `docs/validation.md` 41, 41.1, 41.2, `tests/test_fdm_harmonic_face.py`, `viawell.py` (edge image condition), `laminate.py` (`build`, `plan_gaps`).
* Re-run here: every number of tables 3.1 to 6 (scripts above), the report's FDM/FVM numbers for the plate and the square reproduced to the digit; NOT re-run: the finite-element limits (quoted), the full ten-board turned-square set with the variant (the numbers of 3.3 are those re-run by the review of the fix, `docs/validation.md` 47.1), the disc and the T with the variant, the via effect on an inset board (the finite-element via board has the copper to the wall; there the face fill changes nothing, table F).
* Not verified: time to 63 % and profile curves (measured by the fix: validation 47), the harness FDM at 0.5 mm for the three 150 000-unknown boards, imported copper, boards with a metal block (the variant leaves them as they are by construction), several parts, the disc.
* Base: the study on `develop` 57a28951; the review re-ran it on `develop` with the face fill merged (the release-candidate tree of 2.7.0, merged into this branch).
