# Reviewer opinion on the open decisions of 2.5.0 (second note)

Opinion only: no study was re-run for this note; every number is quoted from the file named next to it, read on `develop` (merge of `feature/imported-copper`, `47416ba`).

## 1. Default mapping of imported copper: `faces` on the reduced sheet

**Go**, with three corrections of wording and one of the Auto cell (below).

Evidence: `docs/validation.md` 27.1 (mapping alone against the program's pixel network, 12 mm windows: faces 0.15 to 0.85 % mean absolute at 0.5 to 1 mm, fill 4.2 to 5.6 %, faces closer than the fill in every window), 27.2 (against the independent 3D solver: faces 1.2 to 1.5 %, fill 3.2 to 5.0 %), README 10.5 (faces better than the fill in 21 of 21 real windows, in 41 of 42 window-cells on the mapping alone). The fill is 4 to 9 % too cool everywhere; the faces are the only mapping whose error falls with the cell.

What does not block it:

* The +7.2 to +9.6 % at a 2 mm cell (27.3) is on the hot side (conservative) and falls to +1.7 to +4.3 % at 1 mm and -0.05 to +1.7 % at 0.5 mm; the fill is 15 % cool at 2 mm on the same windows.
* The naive order "cooler on 2 layers" at 2 mm (4.86 against 8.16 %) is a cancellation (double-counted laminate against the overshoot), it is 10 % cool at 0.5 mm; it is not a candidate.
* Unaligned cells: sampling (27.4) keeps them within 1.4 to 3.9 % where averaging was worse; held by a test.
* Coarse pixel: warned below 8 pixels per cell.

Corrections needed before the release (wording, no physics):

* `copper.COARSE_CELL_WARNING` says "4 to 10 % too hot at a 2 mm cell": 27.3 measures 7.2 to 9.6 % at 2 mm (4.3 % is the largest at 1 mm). It also says "about half of it the grid error"; 27.3 says that split was not measured. `FILL_NOTE` repeats "about half". Proposed text:
  > "imported copper at a cell above 1 mm: on 24 mm windows of real two-layer boards the face conductances read up to 4 % too hot at a 1 mm cell and 7 to 10 % too hot at a 2 mm cell for a 4 mm part (on the safe side; how much is the grid error of a part two cells wide and how much the copper inside the cell was not separated); use a cell of 1 mm or less for the result"
* `docs/validation.md` 27.3 says the program's grid error "is the part that is measured in section 23": section 23 is the part across the outline, not a grid study. Drop the pointer or replace it by a run.
* `api.suggest_cell_mm` ignores imported copper: a board without parts gets `hi` = 2 mm and a part of 8 mm or more gets 2 mm, so Auto proposes exactly the cell the program then warns about. Cap Auto at 1 mm when the problem has imported copper (unless the memory guard forces a larger cell, and then say so).
* A cheap run that would settle the split: the same 24 mm windows with full copper on every layer (where the faces are exact) at 2 mm against 0.25 mm gives the grid error of the part alone.

## 2. Cells above 1 mm with imported copper: warn, not refuse

Keep the warning at 1 mm (`COARSE_CELL_MM`). Reasons: the error is on the safe side (too hot); the largest errors measured at 1 mm are 4.3 % (27.3) and 1.6 % (27.1); a refusal would make large boards unrunnable on a 16 GB machine where the memory guard already pushes the cell above 1 mm (CO60, 285 x 95 mm, two layers: 5.5 GB peak at 1 mm, 27.5); and the guard, not the accuracy, is the program's rule for refusing. Make the warning stronger above 1.5 mm (say "the result is a screening estimate") rather than add a second threshold that refuses. Together with the Auto cap of section 1.

## 3. The private names in the unpushed history of `research/gerber-cad-profiles`

Found with `git log -S`: `LEN-ADI-PC:Len` (in `INTEGRATION.md`, commit `b954794`) and `DESKTOP:alexis` with the path `Z:\LASMO\PCB\PCB\PCB.pcb` (two test strings of `tests/test_cadprofiles.py`, commit `488394c`); both removed by the review commit `e73820b`; no commit message holds them; the tip tree is clean; the branch has no remote copy (`git ls-remote` empty).

* **Allowed**: CLAUDE.md forbids rewriting *published* history; this branch was never pushed.
* **Necessary?** Not strictly: the strings are operator banners in third-party board files published under an attribution licence (the MinnowBoard design files, CC-BY-SA 3.0, and another public set), so they are already public and harmless. But the program's own design treats banner text as private (INTEGRATION 2.3), work branches are kept forever, and once pushed the strings can never be taken out. The scrub is cheap and possible only now: **recommended**, but not a blocker.
* **Procedure** (in the worktree that has the branch checked out, with a clean status):
  1. `git update-ref refs/backup/gerber-cad-profiles-pre-scrub e73820b` (a local ref, not a branch; `git push` of the branch does not send it).
  2. A small Perl script outside the repository (scratchpad) that replaces `LEN-ADI-PC:Len` by `<computer>:<user>`, `DESKTOP:alexis` by `HOST:user` and the path by `C:\\path\\to\\PCB.pcb` (the strings the review already used).
  3. `FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --tree-filter 'perl -pi <script> $(git ls-files research/gerber-cad-profiles/INTEGRATION.md research/gerber-cad-profiles/tests/test_cadprofiles.py 2>/dev/null)' -- c76479e..research/gerber-cad-profiles` (`c76479e` is the merge base with `develop`; seven linear commits, no merge commit).
  4. Checks: `git diff refs/backup/gerber-cad-profiles-pre-scrub research/gerber-cad-profiles` is empty (the tip was already clean, so the tree must be byte-identical); `git log -S'alexis' -S... c76479e..research/gerber-cad-profiles` prints nothing for each of the three strings; the seven subjects, authors and dates are unchanged; the folder's tests pass.
  5. Push only the branch (`git push -u origin research/gerber-cad-profiles`); then delete `refs/original/` and the backup ref (`git update-ref -d`), never push them.
  6. One new commit that corrects INTEGRATION item 6 ("scrubbed before the first push").
  No new branch is needed (a cherry-pick sequence would conflict at the review commit).

## 4. Asking users and vendors for sample files

Yes: the evidence lacks any real Zuken (CR-8000, CR-5000, CADSTAR), PADS Professional, Allegro X, a current Xpedition and the Altium placement file (cad-profiles README, "Not verified"). Ask in the user guide and README, and write once to the vendors' support or university programmes (Siemens EDA, Zuken, Cadence) asking for public demonstration output, not customer data. Draft:

> **Help us test your CAD tool.** PCB Thermal Lab reads Gerber, Excellon and placement files with its own reader, and it has been tested on files from KiCad, Altium, EAGLE, Xpedition and several others. If you use a tool or a version we have not seen (Zuken CR-8000 or CR-5000, CADSTAR, PADS Professional, Allegro X, OrCAD X, a recent Xpedition, ...), a sample helps more than anything else.
>
> *What to send*: one complete fabrication output (Gerber, drill and placement files, and the output settings if you can) of a board you are free to share, such as a demonstration or open-hardware board. If you cannot share a board, the first 30 lines of one copper Gerber and one drill file are already useful. Remove or replace anything private before sending (file headers may hold a user name, a computer name or a folder path).
>
> *How*: open an issue on the project's GitHub page and attach the files, or say there how you would rather send them. The program never uploads anything: no file leaves your computer unless you send it.
>
> *What we do with it*: we only read which program wrote the files and how it writes them (the header lines, the units and formats, the names of the layers) and check that the reader understands them. We do not commit your files to the repository or publish them; we keep only the counts and the conventions we learned, and we credit you if you wish. Tell us the licence under which we may keep the files for testing.

## 5. JEDEC documents to fetch (the maintainer's browser) and Churchill

In order of use (all are free after registration on jedec.org, per [JESD51family]):

1. **JESD51-2A**, Integrated Circuits Thermal Test Method Environmental Conditions - Natural Convection (Still Air): the enclosure, the board position, where the ambient is read. Unlocks the boundary conditions of the planned virtual JEDEC test (calculator).
2. **JESD51-3**, Low Effective Thermal Conductivity Test Board for Leaded Surface Mount Packages (1s): board size, thickness, trace copper and layout. The 1s board of the virtual test.
3. **JESD51-7**, High Effective Thermal Conductivity Test Board for Leaded Surface Mount Packages (2s2p): plane and signal copper, the gaps. Unlocks the correction of the 2s2p bottom layer named in 'Planned' and the +3 % QFN case of `docs/calculators.md`.
4. **JESD51-5**, Extension of Thermal Test Board Standards for Packages with Direct Thermal Attachment Mechanisms: the thermal pad and its via array. The exposed-pad QFN check.
5. **JESD51-12.01**, Guidelines for Reporting and Using Electronic Package Thermal Information: the meaning and allowed use of theta and psi. Moves [JESD51family] from N to R for the definitions the calculator and theory 9 rely on.
6. **JESD51-8**, Junction-to-Board: the ring cold plate and where the board temperature is read. The `T_ring` / `psi_JB` convention of theory 9.
7. Next, if time: **JESD51-6** (forced convection, the computed forced h), **JESD51-9** (area-array boards), **JESD51-13** (glossary). Later (Foster chain, junction-to-case): **JESD51-14**, **JESD15-4** (DELPHI), and the official copy of **JESD15-3** (read today through a mirror). **JESD51-1** (K-factor measurement) only if a measurement is compared.

Churchill: **S. W. Churchill, "A comprehensive correlating equation for laminar, assisting, forced and free convection", AIChE Journal 23 (1) (1977) 10-16** (Wiley, paid). Unlocks [ChurchillBlend] (N): whether the program's `(h_n^3 + h_f^3)^(1/3)` with the plus sign only is the paper's rule and for which geometry. Worth fetching with it: **S. W. Churchill and H. H. S. Chu, "Correlating equations for laminar and turbulent free convection from a vertical plate", Int. J. Heat Mass Transfer 18 (1975) 1323-1329** (the `general` and `laminar` forms of `natural_form`, today from memory).

## 6. The 2.5.0 / 2.6.0 line for the three edge topics

* **Board-edge image of the via** - can enter 2.5.0. The prototype exists and passed a decision rule written before the run (`research/via-real-board` 3: +14.5 % at 1 mm, 0.16 mm from the edge, down to +0.7 %; +0.5 to +1.8 % for every position along the edge; nothing changes beyond 1 mm from the edge). Scope: box edges of a rectangular board; an outline keeps the warning. It edits `viawell.py`, so it goes after the partial-copper cold-spot fix, not in parallel. Acceptance: the S1 table reproduced by the program (error of the via effect under 3 % at 1 mm for d <= 1 mm, `h_side` 0 and 10, four positions along the edge, against `lib/edge_reference.py` at 1/16 mm); bit-identical for every via farther than the image range (example board, frozen numbers; any moved record written to a pending file and explained); mirror symmetry; under 1 ms per via.
* **Cut cells (P1)** - investigate now on `research/rotated-square-3d`, implement in 2.6.0. It touches `geometry.py`, `fvm.py`, `fdm.py` and `solid3d.py`, moves every outline number, and its own review recommended P2 (document) for the 3D solid; 0.5 to 0.7 K (about 1 %) is not worth delaying the Gerber release. Acceptance for 2.6.0: edge-shift scatter of the small T at 1 mm well below today's 1.47 K (FVM, reference 1/24 mm) and the +1.4 K mean bias removed; the 80 mm disc time constant still within 0.1 % of the closed form; the turned square within 0.1 K of the aligned one; `test_shift_invariance_is_restored_by_the_cut_cells` and the disc test copied into `tests/`; every moved outline record explained.
* **Spatial edge correction of the Analytic** - 2.6.0. The prototype is good on 100 x 80 mm boards (-0.2 to -2.8 %) but leaves -1 to -11 % on 30 x 20 mm boards, and the Analytic is a fast comparison model that already warns. Acceptance: on the boards of `study_analytic_edge_transfer.py` at `h_side` 10, 100 and 200 W/m2K, every board including 30 x 20 mm within 3 % of the FVM (and of the 3D solid on two of them); bit-identical with `h_side` 0; the 4800-unknown guard respected.

## 7. Order of the remaining 2.5.0 work

Heavy jobs in series by the load rule; writing in parallel; branches that share `fvm.py`, `viawell.py`, `memory.py` one after another.

1. Running, let finish: reviewer on `fix/gerber-reader-tolerances` -> merge (the reader under everything else).
2. Scrub and push `research/gerber-cad-profiles`, then the **eCAD profile minimal subset** (the Xpedition drill files that the reader refuses today are a reader defect, and the dialog shows the profile): before the dialog's last step.
3. **Wording of the imported-copper warnings and the Auto cap** (section 1; on `feature/imported-copper`, reopened): small, before the user guide quotes the texts.
4. `feature/import-dialog` steps 2 and 3 (running) -> reviewer -> merge, after 2 and 3.
5. **Memory law with vias** (`memory.py`): imports bring thousands of plated holes and the law ignores them (27.5); before the release.
6. **Vias with partial copper (cold spots)**: investigation, then fix in `viawell.py`; imported planes with antipads make it common, so it belongs to 2.5.0. Then the **board-edge image** on the same files, if the cold-spot fix is merged in time.
7. `feature/ocr-tool` (running) -> reviewer -> merge -> the after-OCR documents branch.
8. Figure 8: redraw with our own reader (drops the GPL-3.0 render question); on `research/gerber-real-boards`, writing only.
9. User guide branch last among the content branches (after 2 to 7, which it documents).
10. Non-blocking research, on a quiet machine: the heavy runs of `research/paper-case-studies`, the convection-law study (any change of a default it suggests goes to 2.6.0).
11. Version comparison: regenerate on the final tree; give it a home in a research folder (`research/release-regression-*`) linked from `docs/versions.md` rather than a new `docs/` file (the few-documents rule); delete `tmp/version-comparison`.
12. Release gate in the order of CLAUDE.md (reproduction pass, reviewer's final opinion, whole battery, version bump, refreeze folding the pending files).
