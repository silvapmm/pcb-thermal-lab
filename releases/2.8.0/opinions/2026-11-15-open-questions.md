# Open questions of 2.8.0: reviewer's opinion

Scope: the eight questions of the main session on `development` f2064f8e. Read: `docs/versions.md` 'Planned: 2.8.0', `CLAUDE.md` ('Where to continue' and the
latest Decisions Log entries), `research/ROADMAP.md`, `research/REVIEW.md`, `research/independent-fem-extensions` (README 1 to 9, INTEGRATION),
`research/lumped-dense-via-group` (README 0 and 9, INTEGRATION), `research/block-warning-remeasure` (headings and verdict), `releases/2.8.0/reviews/lumped-part-readout.md`,
`releases/2.8.0/opinions/2026-11-14-overnight-plan.md`, and the code of the warnings in `pcbthermal/checks.py`. **Nothing was re-run for this opinion**: every number
below is quoted from a reviewed README (the section is named); the code statements were checked by reading the code at the line given. This file is the only change.

## Verdicts

| # | Question | Verdict |
| --: | :-- | :-- |
| 1 | FDM own via defect | **Declared limit now**, in the text of an existing warning and the documents; a fix only inside one FDM node-centred investigation with A32/A40, not in 2.8.0 unless that study ends early |
| 2 | Analytic via text at a strong edge | **Change the text in two places of `checks.py`**: the edge-laminate warning of the reduced models (it fires for any number of vias) and the one-or-two-vias warning; exact wording below |
| 3 | Resolved tab and solder | **Not a feature**; a stated limit (about 1 % of the part rise, safe side); one cheap check of a top block as a tab, optional |
| 4 | 3D solid next to a wall | **Already in Planned** ('Board-edge image of the via in the FDM and the 3D solid', 'Fixes waiting for a study'), not in the 2.8.0 tables; update its numbers and the warning text; investigation after A30 |
| 5 | A46 | **Now, in wave 2, before A27**; one Lumped fix branch later for both |
| 6 | The rest of the plan | Ordered list below; five to start tomorrow |
| 7 | 'Version of confidence' | Defensible only as 'bounded, measured and warned', not as 'fixed'; one unsafe-side FVM error has no warning (drawn copper, 5a) |
| 8 | Non-neutral wording about G1 | Three places left (file:line below); the rest is generic text |

## 1. FDM own via defect (1 to 9 % at 0.25 mm)

**What the evidence says** (`independent-fem-extensions` README 8.1 and 9.2 item 1, column 'FDM 8' against 'FVM 8', the same eight sub-gaps on both): at 0.25 mm the FDM via
effect is -2.3 / -2.3 / -0.8 % at 200 W/m2K and -8.6 / -4.3 / -4.0 % at 1000 W/m2K (via 0.16 mm from the wall, via 3 mm from the wall, 3 x 3 array), against +0.8 / -0.1 / +1.1 and
+0.2 / +2.0 / +3.1 % for the FVM; at 1 mm -2.0 to -19.7 %. Three facts decide the answer:

* **Sign: safe side.** A via effect read too small means the model removes less heat through the vias, so the part reads hotter than the truth.
* **Size against what the user sees.** With the default two sub-gaps the FVM itself reads the same via effect -8.7 to -12.7 % at 1000 W/m2K (the laminate at the edge,
  A16/A18), more than the FDM's own part; at 200 W/m2K the FDM's own part is 1 to 3 points at 0.25 mm. The via effect is a fraction of the part rise (on study 1, about
  1 K of the rise), so the FDM's own defect is a fraction of a percent of a part temperature on these boards.
* **Evidence board.** The study board is 10 x 10 mm with every wall cooled and a 200 W/m2K bottom; '3 mm from the wall' is still close to a wall on it. The cause
  (the node-centred well: half-volume nodes, the footprint of nodes, the Peaceman radius on a node lattice) was not separated. A fix without a cause is a guess.

**Recommendation.** Keep it as a declared limit of the comparison model in 2.8.0:

* Text, no new trigger (`fix/via-and-edge-warning-texts`, below): in `checks.check_edge_laminate` (the FVM/FDM edge warning, `checks.py` about line 1148 to 1159), after
  'the effect of a via near the edge more', add for the FDM: 'and the FDM reads the via effect low also away from the edge (4 to 9 % at a 0.25 mm cell and 1000 W/m2K, up to
  20 % at 1 mm, safe side)'. At 200 W/m2K the deficit (1 to 3 points) does not need a warning.
* Documents: `docs/theory.md` 3 (FDM limits), `docs/models.md` (FDM), a section of `docs/validation.md` that holds the 'FDM 8' column with the reference
  (`independent-fem-extensions` 8.1), and the row 'FDM via effect far from the wall' of 'Planned: 2.8.0' changed to 'stated limit (2.8.0); fix with the FDM node-centred
  investigation'.
* **If fixed later**: one research branch for the three FDM questions that share the node-centred stencil at a wall (A32 cut cells, A40 box-edge against outline-edge, this
  well), e.g. `research/fdm-node-centred-walls`, size M to L, investigation first (separate well, footprint and edge image on the study-1 board with eight sub-gaps; then the
  outline square of A40). Frozen-number risk if adopted: every FDM record of the via boards of the harness at three cells and their times; it overlaps A30 (FVM and FDM via
  boards), so the two fixes are serial and the second moves its records out of the first pending file.

## 2. The Analytic via text at a strong edge

**Code read.** `checks.py` line 927 to 930: the 'one or two vias ... up to 16 % too small' warning fires only for `len(vs) <= 2`. The study's -17.0 % is the **3 x 3 array**, which
gets no via warning at all; at 1000 W/m2K on the 1.6 mm board the reduced-model edge warning (`check_reduced_edge_laminate`, line 1197 to 1224, trigger `h_side x thickness >= 150`)
fires instead, and its text speaks of the board temperature only. The -17 to -20 % is the laminate at the edge (at 200 W/m2K the same Analytic reads +3.9 / -4.5 / -2.8 %), so
its place is the edge warning; the via warning only needs a pointer. Both are text only (no frozen number).

**Exact wording.**

* `check_reduced_edge_laminate` (line 1218 to 1223): when `"analytic" in models` and the problem has a via on the board, append to the long text, before 'Use the FVM or the
  FDM for such a board.':

  > The Analytic model also reads the effect of the vias too small near such an edge: 17 to 20 % too small next to an edge of 1000 W/m2K (one via 0.16 or 3 mm from the
  > edge, or a 3 x 3 array, on a 1.6 mm four-layer board, against an independent finite-element solution), within 5 % at 200 W/m2K.

  and to the short text: `; Analytic via effect up to 20 % too small next to a 1000 W/m2K edge`.
* The one-or-two-vias warning (line 928 to 930), long text:

  > Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (an effect of 1 to 4 K; the tile is 1 mm and the barrel is read
  > at its scale), and 17 to 20 % too small next to an edge cooled at 1000 W/m2K; use the FVM for the value.

  short text: `Analytic model: one or two vias were measured up to 16 % too small in the via effect (up to 20 % next to a strongly cooled edge); use the FVM.`
* Documents: `docs/validation.md` the table row 'Analytic, via correction' (line 1183) and the 'Limits, measured' sentence (line 747 and 1207): add 'and 17 to 20 % next to an edge
  of 1000 W/m2K (`research/independent-fem-extensions` 8.1)'; `CHANGELOG.md` Unreleased. The user guide does not quote the 16 % (checked). A test: the edge warning with the
  Analytic and a via contains 'effect of the vias', without a via it does not (`tests/test_laminate_edge_band.py`, beside the existing `check_reduced_edge_laminate` asserts).

## 3. The resolved tab and solder (about 1 % of the part rise)

**Evidence** (`independent-fem-extensions` 8.2): the resolved tab (0.2 mm copper on 0.1 mm solder, no film under it) is 0.99 K (0.95 %) cooler at the part mean and 1.37 K
(1.32 %) at the hottest point for the 6 mm part, 0.48 / 0.93 K for 4 mm; the program's idealisation (uniform flux plus a series offset) is on the **safe side**, and it does not
depend on the cluster. One board, one tab thickness, one solder value (synthetic, README 7.4).

**Opinion: not a feature for 2.8.0.** A 1 % safe-side error is below every other error the version is trying to bound; a tab input would add a part body to the input model
(geometry, capacity, a film on its top and sides, the re-import of parts) for a gain inside the reference's own band on most boards. Write it as a stated limit of the part
model (`docs/theory.md`, the section on parts and the heater; `docs/validation.md`, the numbers above) and close the Planned row 'Part over a thermal-via cluster with a copper tab
block' as measured (the program within 0.6 % of variant A in every model; the idealisation about 1 %).

**Cheapest representation today (no code)**, if a user wants it: a metal block (`Heatsink` with `thickness` 0.2 mm, copper 385 W/mK, on layer 1, the polygon of the tab,
`pad_thickness` 0.1 mm and `pad_k` 50 for the solder) over a `Heater` on layer 1. The board face under a block loses nothing and the block's top and sides convect, as variant B;
the difference is that the heat still enters the top copper and reaches the tab through the solder, so the tab acts as a parallel spreader that evens the footprint. What the user
gets: the block temperature (the tab) in the results and a part row (board peak under the footprint) that falls by the spreading of the tab; the Lumped and Analytic take a block
in the steady state only. `base_interface` / `base_pad_*` is NOT a representation of the tab: it is a read-out offset `P t / (k A)` added to the board peak (it does not spread),
correct for the junction column and nothing else. **Not measured**: whether the top-block representation recovers the 0.95 % (one run of the study-2 board, FVM 0.5 mm, against
variant B; size S, executor in `research/independent-fem-extensions`). If it does, one sentence in the user guide; if not, nothing. The wave-3 item 'Heat source inside a block'
is the exact representation and stays after its own investigation, low priority on this evidence.

## 4. The 3D solid next to a wall (+0.6 to +25.8 % at 0.5 mm)

**Already planned**: 'Board-edge image of the via in the FDM and the 3D solid' in 'Fixes waiting for a study' (it says 'about 19 points too large'); it is in none of the
2.8.0 wave tables. The new evidence (`independent-fem-extensions` 8.1 and 9.2 item 3): +9.7 / +25.8 % at 0.5 mm and +3.2 / +9.6 % at 0.25 mm for the via 0.16 mm from the wall
(200 / 1000 W/m2K), +13.8 / +6.7 % for the via 3 mm away at 1000 W/m2K, +0.6 to +1.9 % at 200 W/m2K away from the wall. It falls by about half per halving of the cell, so it is
a discretisation error (footprint or edge), not a constant bias; the cause was not separated and is not claimed.

**Sign: unsafe side** (a via effect read too large makes the part read too cool), but a fraction of a via effect of about 1 K, in a comparison model.

**Order.** (a) In 2.8.0, text only in `fix/via-and-edge-warning-texts`: the edge-via warning of `check_via_limits` (`checks.py` line 1517 to 1520) says 'about 19 points too
large' at 1 mm; add 'up to about 26 % at 0.5 mm next to an edge of 1000 W/m2K, and about 7 to 14 % also 3 mm from such an edge'; the second clause has no trigger today (the
via is not within one cell of the edge): add the 3D solid to the FVM/FDM strong-edge warning text when `solid3d` is selected (same trigger, `check_edge_laminate`). Put the
numbers into the Planned bullet as evidence. (b) The investigation (separate the edge image, the slab rule and the footprint on the study-1 board: a three-way ablation, S to M,
research) after A30, because both touch the via footprint; not a 2.8.0 fix.

## 5. A46: the zones of the Lumped footprint depend on the grid position

**Now, in wave 2, and before A27.** Reasons: (1) the noise is up to 3.5 points on one board and moves the zoned mean from -1.1 % to -2.9 to -3.2 %, on the cool (unsafe)
side (`lumped-dense-via-group` 9.2); (2) A27 (the first link near an edge) has to be measured on boards with vias and zones too, and a placement noise of 3 points would blur that
measurement; (3) the hygiene step the dense-group study names (the core counted on the fine grid, the position mask) is small and research-only, the Lumped runs are cheap, and
the FVM references of the 66-case sweep are cached in that folder; (4) both end in `lumped.py`, so their fixes go into ONE Lumped fix branch.

**Frozen numbers, important**: the pending file `lumped-part-readout.json` already holds **all 51 Lumped records** of the 17 boards at three cells. Any later Lumped fix (A46,
A27) moves records that are in that file; by `test_no_record_or_time_is_in_two_pending_files` the next Lumped fix must take its records out of that file into its own (as the
2.6.0 integration did), or, simpler, regenerate that one file under a combined item. Do not run two Lumped fixes in parallel.

## 6. The rest of the plan

### 6.1 Where wave 2 stands (read, not re-run)

| Item | State |
| :-- | :-- |
| FEM extensions (A43) | done at the cleared levels and reviewed; left for a quiet machine: 1b and study 2 at 0.05 mm, the masks at 45 degrees, the checkerboard check (it checks nothing yet) |
| Transient reference (V2) | partly: the tool is built and checked (`lib/transient.py`), the plate wave and the study-2 plate step are done; left: 3 to 4 boards (the simple-stack-up case that moved 16 %, a partial-copper board, a via board, an outline) |
| Metal block warning study | done (`block-warning-remeasure`); the wave-3 row 'Block warnings of the Lumped and Analytic' is **done** too (the texts were rewritten in `fix/lumped-part-readout`, reviewed): mark both rows done |
| Part over a via cluster with a tab | done (study 2): close the row as measured (section 3) |
| FDM via far from the wall, Analytic via text | sections 1 and 2 |
| A46 | open (section 5) |
| E13, 5a, A18, A27, A30, A32/A40, memory law at 8 to 16 slabs | open |

Stale registers found on the way (documents, for the maintainer agent): `research/ROADMAP.md` A45 is still 'ready' although `fix/lumped-part-readout` is merged; the index row of
`block-warning-remeasure` in `research/README.md` (line 47) still calls the warning text and the Lumped part rows 'proposals'; A43 in the roadmap and the wave-2 row 'FEM
extensions (A43)' still quote 'the FDM via effect 4 to 16 % low', which the review replaced by 1 to 9 % at 0.25 mm; A44 (a research test failing) is open.

### 6.2 Dependencies and overlaps

* **Model fixes are serial** (they touch `fvm.py`, `fdm.py`, `laminate.py`, `viawell.py` or `checks.py`, and their frozen records overlap: the example board has drawn partial
  copper, vias and small parts, so 5a, A30 and A18 all move some of its FVM and FDM records). Order of the fixes: **text branch** (checks.py, no numbers) -> **5a** (widest,
  FVM and FDM on drawn partial copper) -> **A30** (via boards) -> **A18** (small parts on bare laminate) -> FDM node-centred if adopted. Each pending file is written after the
  previous merge, and records already pending are moved out of the older file (one record, one file).
* **Lumped fixes** (A46 then A27) are one branch that regenerates the Lumped pending file; they can run beside the FVM/FDM fixes (different records, different files), but not
  beside each other.
* **B5** (vias with a span, component holes as vias) touches `viawell.py` and the via of every model: after A30. Its study (against the finite-element tool) can run earlier.
* **Blocks** (adiabatic face, emissivity per block, source inside a block) move only boards with blocks (`blocks.py`, `fvm.py`): after A18 in the serial order, or beside the
  Lumped branch; the adiabatic face and emissivity need their 'how far it matters' study first (the Planned row says so).
* **Studies are parallel** (research branches, nothing in the program) within the load rule (at most 3 heavy jobs, each under 2 GB unless declared). **E13 and the memory law
  at 8 to 16 slabs run alone** on a quiet machine.
* **Features without numbers are parallel** with everything: the element-tree filter box (`gui/`), paint and erase of the mask (`gui/`, `document.py`, `copper.py`; the mask is
  an input), heater modes (`gerber/parts.py`, `import_window.py`), the capacity inventory (transient summary), the top-of-case read-out (`analysis.py`, panels), the Cut
  slider (S). Their only conflicts are in the documents (CHANGELOG, user guide, tips, `tests/test_help.py`): merge one at a time.
* **Reviewer first** (before code): every number-moving item (5a, A18, A30, A27, A46, B5, the block options, source inside a block, any FDM fix); and a **researcher first**
  for the two items whose numbers are not sourced: the TO-263 thick-film family (theta element-to-tab) and the solder entry of the via-fill library (conductivity), because a
  number with no source does not enter Preferences.

### 6.3 Ordered list (size; frozen)

1. `fix/via-and-edge-warning-texts`: sections 1, 2 and 4 (Analytic, FDM, 3D solid texts) and the stale registers (S; no).
2. Studies, in parallel by load: V2 remainder (M), A46 (M) then A27 (M), 5a investigation (M), A18 second round (M), A30 sector-well prototype (M to L), B5 study (M).
3. E13 alone on a quiet night (M, memory-heavy); the memory law at 8 to 16 slabs alone (S to M); the A43 finer levels alone.
4. FDM node-centred investigation (A32, A40, the FDM via; M to L): may end as a stated limit; not blocking.
5. Fixes in series: 5a -> A30 -> A18 (M each; one pending file each); the Lumped branch A46 + A27 beside them (M; the Lumped pending file).
6. Features in parallel at any time: element-tree filter (S to M), Cut slider (S), capacity inventory (S to M), top-of-case read-out (S; the TO-263 family only after its
   source), heater modes (M), paint and erase (M), solder via fill (S, after its source), B5 code (M, after A30), block options (S to M, after their study), source inside a
   block (M, last, low priority).
7. Release gate as written.

### 6.4 The five to start tomorrow

| # | Branch | Agent | Brief (three lines) |
| --: | :-- | :-- | :-- |
| 1 | `fix/via-and-edge-warning-texts` | executor, then reviewer | Change the texts of `checks.check_reduced_edge_laminate`, the one-or-two-vias Analytic warning, `check_edge_laminate` (FDM via away from the edge; the 3D solid when selected) and the edge-via text of `check_via_limits` as `releases/2.8.0/opinions/2026-11-15-open-questions.md` 1, 2, 4 say. / Add tests that the clauses appear only with the model and a via; update validation, theory 3 and 4, models, CHANGELOG, and the stale register rows of 6.1. / Text only: the frozen numbers must pass untouched; touches `checks.py`, so it merges before any other branch that touches it. |
| 2 | `research/transient-reference-boards` | researcher with executor | With `research/independent-fem-extensions/lib/transient.py`, run step response and time to 63 % of 3 to 4 boards: the simple-stack-up case that moved 16 %, a partial-copper board, a via board, an outline; one square wave read at a point away from a source edge. / Compare FVM and FDM at 2, 1, 0.5 mm reading the same quantity (hottest node against hottest cell); state the 0.5 to 3.5 % caveat of a footprint mean. / Each solve under 2 GB, one at a time; README with numbered results, no program change. |
| 3 | `research/lumped-zone-placement` (A46) | researcher with executor | Measure the zoned Lumped part peak over the placements of `lumped-dense-via-group` 9.2 with the core counted on the fine grid and the position mask, on a copy (monkeypatch, as `lib/variants.py`). / Report the spread over placements before and after, on the 66 cases and the independent 3D cases, and the zone decisions that flip; peak with peak. / Name the frozen Lumped records it would move and how they leave `lumped-part-readout.json`; no program change. |
| 4 | `research/drawn-copper-faces` (5a) | researcher with executor | On a copy, give drawn zones the exact zone fill (`geometry.exact_coverage`) and the flow-based faces of the imported copper; measure on the stripes, plain-inset and padded boards of validation 40 against the resolved references of `independent-fem-extensions` 8.4 and `imported-copper-edge-film`. / Report FVM and FDM at 1, 0.5, 0.25 mm, the cost, and every harness record that would move. / The program untouched; the frozen-number list goes into INTEGRATION.md. |
| 5 | `feature/element-tree-filter` | executor, then reviewer | Add a filter box to the element tree (Ctrl+F when the tree has the focus; typing in the box never fires a window letter shortcut). / Tooltip, user guide, keyboard list, `tests/test_shortcuts.py`, a stress scenario in `tests/test_gui_stress.py`. / Display only; no number moves; documents merged one at a time with the other feature branches. |

Load: items 2 to 4 are research jobs of under 2 GB each (the ceiling of three heavy jobs applies; 2 and 4 are the heavier); 1 and 5 are light. At most two reviewers at once.

## 7. The risk of calling 2.8.0 'a version of confidence'

**Fixed or changed since 2.7.1 (in `development`)**: the Lumped part read-out (single parts -9 to -15 % of the FVM rise become -0.2 to -5.8 %; 51 Lumped records pending), the
block warning texts re-measured, the housekeeping. **Measured and confirmed with no change needed**: the barrel rule `d + 0.5 t_cu` for hollow barrels (FVM and FDM within 1.6
points between cores), the transient of the FVM and FDM with a plate and a cluster (within 1.1 %), the profile decision's closed-form floor (-0.38 % on the 20 Hz wave), the
program on the via cluster with a plate (within 0.6 %), `MAX_CORE` 0.92.

**Documented limits still open** (side: unsafe = the part reads too cool):

| Limit | Size | Side | Warned |
| :-- | :-- | :-- | :-- |
| Drawn partial copper (5a): stripes, pads, copper held inside the outline | -3 to -8 % (FVM, FDM, 0.25 mm) | unsafe | **no** |
| Laminate at a strong edge (A16/A18/A34), default sub-gaps | FVM up to -6 % on 1.6 mm, -16 % on 3.2 mm; via effect -9 to -13 % at 1000 W/m2K | unsafe | yes |
| Small parts on thick bare laminate (A18) | 16 to 20 % | unsafe | yes |
| Lumped near an edge (A27) | 4 to 15 % | unsafe | yes |
| Lumped zones by grid position (A46) | up to 3.5 points, mean -3 % | unsafe | no (inside the Lumped's general statements) |
| Reduced models on small imported parts (E13) | 25 to 82 %, against an unconverged reference | unsafe | yes |
| Part across an outline in the equivalent rectangle (Lumped, Analytic) | about 28 % | unsafe | the outline warning, not this number |
| 3D solid via effect next to a wall | up to +26 % of the via effect at 0.5 mm | unsafe (small in the rise) | partly (1 mm number) |
| FDM via effect (own) and A40 at a turned outline | 1 to 9 % of the via effect; -7.3 % against -5.0 % | safe; A40 unsafe | partly |
| Analytic via effect at a strong edge | 17 to 20 % | safe | after item 1 |
| Via at a copper corner or a track end (A30) | 15 to 85 % of the via effect low | safe | yes |
| Part idealisation (no tab) | about 1 % | safe | no (a stated limit) |
| Blind and buried vias as through vias | not measured | unsafe | yes |
| No measurement of a physical board; the face-up law | unknown | - | the Results-summary line |

**Risk.** If wave 3 lands only partly, 2.8.0 is 2.7.1 plus one Lumped fix plus documents: then 'confidence' can only mean 'every known error measured against an independent
reference, bounded and stated', not 'fixed'. That is honest and defensible **if** (a) every unsafe-side error of the FVM, the reference model, above about 3 % is either fixed
or warned with its measured number: today only **5a has no warning**, so either 5a lands or a warning for drawn partial copper on the FVM and FDM is added in 2.8.0; (b) the
release notes carry the table above in a short form (the README and `docs/versions.md`), so the word 'confidence' rests on a list and not on a slogan; (c) the refreeze is done
once with one pending file per item and no record in two files (the Lumped file is the trap, section 5). A second risk is time: wave 3 has four serial model fixes of size M
each, each through executor, reviewer and the whole battery (about 45 min per battery); if the release must close, the cut line is after 5a and the Lumped branch.

## 8. Non-neutral wording about the physical measurement

Searched with case-insensitive `git grep` for the words that name a person, an institution or a measured dataset, in `docs/`, `research/`, `releases/`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `.claude/agents/`, `tests/`, `pcbthermal/`. Not edited here.

| File:line | What it holds |
| :-- | :-- |
| `releases/2.7.0/final-opinion/fem-reference-opinion.md:76` | the G1 row names a specific external source of data instead of the neutral 'a physical measurement' (the overnight opinion proposed neutral words; not applied) |
| `releases/2.8.0/opinions/2026-11-14-overnight-plan.md:13` to `:36` | the table and the replacement texts of section 1 quote the old non-neutral wording verbatim, so this record now carries it itself; replace the quotes by file:line pointers |
| `CLAUDE.md:368` | 'The measured board (G1) will happen': the definite article reads as a specific board; neutral: 'A physical measurement (G1) may happen' (minor) |

Everything else that matched is generic and can stay: 'never compared with a measured board' (`pcbthermal/results.py:17`, `pcbthermal/gui/help.py:149`,
`docs/versions.md:12` and `:434`, `tests/test_help.py:96`, `tests/test_model_limit_warnings.py:712`), 'no measured board' in the limits of research READMEs, the
purpose-built board of `research/ROADMAP.md` section 5, and 'laboratory' in the names of cited sources (the Waterloo laboratory, interface measurements) and in the instrument list
of `research/convection-laws/docs/measurement-plan.md`. `.claude/agents/` has no match. Git history keeps the old texts (published history is never rewritten).

## What was not verified

No study or test was run for this opinion; the numbers are those of the reviewed READMEs. The proposed warning texts were not tried in the program (their trigger
conditions were read in `checks.py`); the top-block representation of a tab (section 3) is a proposal with no measurement; the frozen-record overlaps of 6.2 are reasoned
from the harness boards and the pending file, not listed record by record.
