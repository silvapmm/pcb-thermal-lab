# Review: vias through imported copper read the masks (ray test of the rim)

Branch: `fix/imported-via-rim-mask` (386129d1 code and tests, 2cb88172 documents; `develop` c266f283 merged in by the reviewer, 7fd2ad1d). Evidence: `research/imported-via-rim` (363c1b08, reviewed separately). Reviewer's verdict: **GO**, with the two fixes below (a live warning and stale texts).

## Verdict in short

* The code does what `docs/theory.md` 2.6 says: on a layer with an imported mask a rim sample counts only when the copper is continuous from the drill circle outward over `max(0.5 mm, 3 pixels)`; heaters still count as contact, zones drawn on an imported layer do not; a drawn board takes the old path, bit for bit (test, and the frozen numbers: 317 passed at 2, 1 and 0.5 mm). The raster lookup uses the same convention as `copper.sample_coverage` (rows from the top, floor of x / pixel); the masks are the cached unpacked arrays of the cell fill, so no copy.
* The FDM uses the same `viawell.build`, so it gets the same rule; it was not measured by the branch and is now (validation 45, Review).
* The claims reproduce: rp2040 +3.3, +0.1, +1.5 % and oswlight +2.4, +4.4, +3.4 % at 1 mm (FVM), the synthetic 2L antipad +1.1 / +1.2 %, the run time unchanged.

## Findings

| # | Kind | Finding | Evidence | Action |
| :-- | :-- | :-- | :-- | :-- |
| 1 | defect in the program (new with the branch) | `checks.uncoupled_vias` now follows the masks, so the live warning 'N vias touch no copper on a layer ...; draw their pads or planes if they are connected' named every signal via in a plane clearance: 925 of 1000 vias (cmm2), 955 of 1008 (isastm), 61 of 126 (oswlight), 123 of 241 (gi-alleg). The clearance is the board as designed and cannot be drawn on an imported layer. | `study_imported_via_rim_review.py real <board>` prints both counts | Fixed: `uncoupled_vias(drawn_only=True)` for the warning; test `test_the_live_warning_does_not_ask_to_draw_on_an_imported_layer`. |
| 2 | wrong document / warning text | The partial-copper warning, its docstring, `docs/theory.md` 2.6 and `docs/validation.md` 34 still said a via just outside an edge of imported copper 'reads 3 to 4 times high (not re-measured)'. Measured against an independent 3D reference with the same masks: islands 0.15 / 0.35 / 0.75 mm from the plane give the via row 2.58 / 1.51 / 0.52 K of a 552 K rise; the full contact read 3.9 / 2.1 / 0.3 K (FVM 1 mm) and up to 13.4 K (FDM 1 mm, 5 times); the ray test uncouples the islands, effect 0, error at most 0.5 % of the rise, safe side. | `... edge` | Texts corrected with the numbers. |
| 3 | unexplained before, now a limit | The executor's range 'hottest part 0 to 4.4 % too cool' is a sample: an Allegro set (gi-alleg, unused inner pads removed) gives +11.1 % FVM / +6.7 % FDM at 1 mm, +3.5 % at 0.5 mm, with a drawn 3 x 3 mm part on its densest via group. | `... real gi-alleg 1.0,0.5` | Stated in validation 45 and CHANGELOG. |
| 4 | limit to record | The reach matters in temperature only beyond about 0.8 mm: 0.3 to 0.8 mm moves the readings by at most 1.1 points; at 1.2 mm real track contacts are dropped (rp2040 C14 +1.5 to +8.2 %). | `... real rp2040 1.0 0.3,0.5,0.8,1.2`, oswlight | Stated; 0.5 mm stays a choice. |
| 5 | limit to record | The shift falls with the cell: rp2040 U3 +3.3 / +1.4 / +0.8 % at 1 / 0.5 / 0.25 mm (FVM), oswlight SW2 +4.4 / +1.9 / +0.8 %; at 0.25 mm the FDM moves +0.0 to +1.4 %. | `... real <board> 0.5,0.25` | Stated. |
| 6 | stale document | The user guide had no word on how vias meet imported copper. | `help/index.html` | One bullet added in the imported-copper section. |

## Other checks (all pass)

* A narrow thermal relief (0.15 mm spokes) on inner layer 2 of the four-layer synthetic board, layer 3 antipad or solid: reference 507.46 / 506.96 K; ray test -0.01 to +0.06 % (FVM), -0.19 to +0.01 % (FDM) at 1, 0.5 and 0.25 mm; rim share 0.167. The reference is the research one adapted to any mask with an iterative solver (0.7 GB; it reproduces the research's 517.123 K of the 2L antipad).
* Coarse pixels 0.05 to 0.2 mm: the antipad stays uncoupled and the part reads the same; at 0.25 mm one ray survives (+0.65 % instead of +1.1 %); the relief within 0.07 % of the reference at every pixel.
* Hostile masks: all copper (share 1), a pixel checkerboard and an empty layer (share 0), solves finite, balance 1e-12; 3000 x 3000 random masks on four layers with 2000 vias: rim test 0.22 s, live check 0.26 s, 0.32 GB.
* The Lumped and Analytic imported-copper warnings still fire (rp2040). The warning texts pass `tests/test_warning_texts_plain.py`. A board resized after the import raised in the live check before the branch too (other checks), so nothing new there.
* Tests after the reviewer's changes: the branch's file and `test_via_barrel_and_rim.py`, `test_via_partial_copper_warning.py`, `test_imported_copper.py`, `test_api.py`, `test_small_251.py`, `test_live_check_speed.py`, `test_help.py`, `test_tooltips.py`, `test_docs.py`, `test_license_header.py`, `test_version.py` passed; frozen numbers 317 passed at 2, 1 and 0.5 mm. The whole battery was not run (the maintainer's, before the merge).

## Reproduce

`.venv/bin/python releases/2.7.0/final-opinion/scripts/study_imported_via_rim_review.py <part>` with `edge`, `relief4`, `pixels`, `hostile`, or `real <board> <cells> [reaches]` (library boards; numbers only). Each part under a few minutes and under 2 GB.

## Not verified

A reference on a real board (the real-board shifts are the ray test against the full contact, not against a truth); the pad island's own contribution, dropped by the rule (0.5 to 1.2 % of the rise on the synthetic boards, safe side); a via joined to an outer layer by a single track (reads the share of the track); a physical board.

## Open decisions for the maintainer

* Whether a check of the vias with a low rim share on imported copper is wanted (research README 6). The reviewer's opinion: no new warning; the clearance is the design and the remaining error is on the safe side.
* Whether the reach should come from the pad size instead of the fixed 0.5 mm (only the 1.2 mm reach moved temperatures by more than a point).
