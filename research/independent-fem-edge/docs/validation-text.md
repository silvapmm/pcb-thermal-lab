# Text for the project documents once this folder is merged

Nothing in the project documents is edited on the research branch. When the folder is merged, the maintainer (or the `maintainer` agent on a `docs/` branch) applies this text.
The numbers are those of the closing review (README section 7.0), the program of `develop` e39de188.

## 1. docs/validation.md, section 46, first sentence (the location of the reference)

Replace "An independent hexahedral finite-element comparison program (not part of the repository; trilinear Q1 elements ...)" by:

"An independent hexahedral finite-element comparison program (`research/independent-fem-edge`: trilinear Q1 elements with a conforming mesh, films on every wall slice, orthotropic laminate, a solid copper cylinder for a via; scikit-fem and pyamg live only in that folder's own git-ignored scratch environment) solved the boards ..." and keep the rest. Every number of sections 28, 36, 40, 43, 44, 46 and 47 that quotes "the finite elements" is reproducible with the scripts of that folder (`scripts/study_fem_cases.py`, `study_program.py`, `study_fv_refs.py`, `study_report.py`, `study_thin_laminate.py`; README sections 3 and 6).

## 2. docs/validation.md, section 46: two corrections found by the closing review

1. **Point maximum against cell mean.** The paragraph says the FEM hottest value "is read as the hottest cell mean like the program's", but the plate rows of its table are against the FEM **point** extrapolation (README 3(a)). Either keep the rows and write "the plate rows are against the point maximum of the finite elements, which lies 0.13 % (200 W/m2K) and 0.20 % (1000) above the hottest 0.25 mm cell (0.52 / 0.75 % above the 0.5 mm cell)", or replace the plate rows by the cell-mean values: FVM 0.25 mm default -0.44 / -3.32 %, eight sub-gaps +0.59 / +2.21 %, FDM 0.25 mm -0.97 / -4.94 % (200 / 1000 W/m2K). The thin-laminate numbers of sections 44 and 46 and of the warnings are cell means already. No conclusion moves (0.1 to 0.2 point).
2. **The FDM sentence is stale since section 47.** Replace "The FDM at its harmonic default reads a drawn copper edge inside the outline 2 to 3 times cooler than the FVM (the square with copper 1.2 mm in: -7.0 / -14.2 % at 1 mm, 200 / 1000 W/m2K) and, on thin-gap boards with pads on the outer layers, 2 to 5 points colder than the FVM" by "The FDM with the cell-fill faces of section 47 reads a drawn copper edge inside the outline about twice as far from the finite elements as the FVM (the square with copper 1.2 mm in: -5.8 / -12.0 % at 1 mm, 200 / 1000 W/m2K, against the FVM's -3.1 / -5.5 %; with the harmonic faces of section 41 it was -7.0 / -14.2 %) and, on boards with pads on the outer layers, 1.7 to 3.7 points colder than the FVM (2 to 5 with the harmonic faces)". The FDM via effect (4 to 16 % low at 0.25 mm) is unchanged. The same "2 to 5 points colder" sentence is in section 44 ("The FDM equals the FVM on full copper to 0.1 point and reads 2 to 5 points colder ...").

## 3. The thickness term of the thin-laminate study (sections 43.2, 44, 46, the user guide and the warning texts)

The closing review found a defect in `scripts/study_thin_laminate.py` (report): the through-thickness correction added to the plan extrapolation at 1000 and 2000 W/m2K was (v12 - v6) / 3, the distance from the 12-element value to the limit, instead of 4 (v12 - v6) / 3, the distance from the 6-element value that the plan sequence uses. The finite-element limits at 1000 and 2000 W/m2K were therefore low by v12 - v6 (0.005 to 0.09 K, at most 0.33 %), and the program errors there move by 0 to -0.35 point. The strong-edge plate of section 3(a), with its own 3 / 6 / 12 / 24 sequence, gives 24.332 K; the corrected thin-board value of the same board is 24.338 K (the uncorrected one was 24.300).

| quoted now (first run) | corrected (closing review) | where |
| :-- | :-- | :-- |
| four layers 1.6 mm, default sub-gaps, 0.25 mm: -0.4 / -1.4 / -3.2 / -6.0 % | -0.4 / -1.4 / **-3.4 / -6.2** % | validation 43.2, 44, 46; help limits table; `checks.py` (the edge-laminate text near line 1100); CLAUDE.md Decisions Log |
| the same, eight sub-gaps: +0.6 / +1.6 / +2.3 / +2.8 % | +0.6 / +1.6 / **+2.2 / +2.6** % | validation 43.2; `checks.py` near line 1101 |
| the reference at 0.25 mm hot: +0.9 / +2.5 / +4.3 / +6.4 %; at 0.125 mm +0.3 / +1.0 / +1.8 / +3.0 % | +0.9 / +2.5 / **+4.1 / +6.2**; +0.3 / +1.0 / **+1.7 / +2.8** % | validation 43.2 (line 'the first four columns'), 44, 46; CLAUDE.md Decisions Log ('+0.9 to +6.4 % hot') |
| thin-gap boards, default: -0.1 to -1.1 / -0.9 to -3.2 / -2.2 to -5.9 / -4.0 to -9.6 % | -0.1 to -1.1 / -0.9 to -3.2 / -2.2 to **-6.0** / **-4.1 to -9.7** % | validation 44 (table), 46; help limits table; `checks.py` near line 1140; CLAUDE.md Decisions Log |
| pads on the outer layers: up to -1.3 / -2.4 / -3.7 / -5.1 % | up to -1.3 / -2.4 / **-3.8 / -5.2** % | validation 44; `checks.py` near line 1140 |
| eight sub-gaps at 0.25 mm, thin: +3.6 to +5.0 (1000), +5.0 to +7.3 (2000) | **+3.5** to +5.0, **+4.9** to +7.3 | validation 44 table |
| eight sub-gaps at 0.125 mm: +1.1 to +1.8 (1000), +1.6 to +2.7 (2000), pads +0.5 to +1.6 | +1.0 to +1.8, +1.5 to +2.7, pads +0.5 to +1.5 | validation 44 table |
| cut gaps, default: ... / -2.6 to -3.8 / -5.1 to -7.5 % | ... / **-2.8 to -4.1** / **-5.2 to -7.9** % | validation 44 |

These are corrections of at most 0.35 point inside ranges that the warnings quote as samples; whether the warning texts of `checks.py` and the user guide are re-worded for them (a `fix/` branch, text only) is the maintainer's decision.

## 4. Places that say the reference is outside the repository (to be changed by the maintainer; not edited here)

| file | what it says | change |
| :-- | :-- | :-- |
| `docs/validation.md` 46 | "not part of the repository" | the sentence of item 1 |
| `CLAUDE.md` "Where to continue (2.7.0)", open decision (1) | "validation 46 and the edge warnings rest on a program OUTSIDE the repository, so either it enters the repository as a research folder with its review row, or ..." | it is the research folder `research/independent-fem-edge`, reviewed (README 7.0, `research/REVIEW.md`); close the decision |
| `CLAUDE.md` "Where to continue (2.7.0)", 'What is left for the release gate', item (1) | "the finite-element decision above (a gate item)" | closed by the merge of the folder |
| `CLAUDE.md` Decisions Log, entry "The edge warnings quote the independent finite-element comparison" | "The finite-element program is outside the repository." | "is the research folder `research/independent-fem-edge`" (and the numbers of item 3 if adopted) |
| `CLAUDE.md` Project Structure | no line for the folder | none needed (research folders are listed in `research/README.md`) |
| `releases/2.7.0/final-opinion/README.md` section 2 (the finite-element reference cited in a git-ignored scratch folder, with this folder "paused, unmerged"), the 'Read:' line after it, and section 6 item 2 | cite a git-ignored folder and the folder as paused and unmerged | point to `research/independent-fem-edge` after the merge (release work: the reviewer's text, not edited here) |
| `releases/2.7.0/final-opinion/fdm-copper-edge-faces.md` (first finding and 'What was not verified') | the finite-element limits cited from a report in the git-ignored scratch folder | the same limits are README 3(a) of this folder |
| `pcbthermal/checks.py` | the warning texts call it "an independent finite-element solution"; no comment says where it is | none for the location (program not edited); the numbers of item 3 if adopted |
| `pcbthermal/help/index.html` limits table | "An independent finite-element solution" | none for the location; the numbers of item 3 if adopted |
| `research/strong-edge-laminate/README.md` 8 | uses the earlier hexahedral numbers | optionally point to this folder |
