# Text for the project documents once this folder is merged

Nothing in the project documents is edited on the research branch. When the folder is merged, the maintainer (or the `maintainer` agent on a `docs/` branch) applies this text.

## docs/validation.md, section 46, first sentence

Replace "An independent hexahedral finite-element comparison program (not part of the repository; trilinear Q1 elements ...)" by:

"An independent hexahedral finite-element comparison program (`research/independent-fem-edge`: trilinear Q1 elements with a conforming mesh, films on every wall slice, orthotropic laminate, a solid copper cylinder for a via; scikit-fem and pyamg live only in that folder's own git-ignored scratch environment) solved the boards ..." and keep the rest. Every number of sections 28, 36, 40, 43, 44 and 46 that quotes "the finite elements" is reproducible with the scripts of that folder (`scripts/study_fem_cases.py`, `study_program.py`, `study_fv_refs.py`, `study_report.py`, `study_thin_laminate.py`; README sections 3 and 6).

## Other places that say the reference is outside the repository (to be changed by the maintainer; not edited here)

| file | what it says | change |
| :-- | :-- | :-- |
| `docs/validation.md` 46 | "not part of the repository" | the sentence above |
| `CLAUDE.md` "Where to continue (2.7.0)", open decision (1), and gate item (1) | the finite-element reference rests on a program outside the repository | state that it is the research folder `research/independent-fem-edge`, with its review row; close the decision when the reviewer has re-checked it |
| `CLAUDE.md` Decisions Log, entry "The edge warnings quote the independent finite-element comparison" | "The finite-element program is outside the repository." | "is the research folder `research/independent-fem-edge`" |
| `CLAUDE.md` Project Structure | no line for the folder | none needed (research folders are listed in `research/README.md`) |
| `releases/2.7.0/final-opinion/README.md` (sections 2, 5 and 6) and `fdm-copper-edge-faces.md` | cite `tmp/fem` (git-ignored) and `research/independent-fem-edge` as paused, unmerged | point to the folder after the merge (release work: the reviewer's text, not edited here) |
| `pcbthermal/checks.py` | the warning texts call it "an independent finite-element solution" / "hexahedral"; no comment says it is outside the repository | none (program not edited; the texts are right) |
| `pcbthermal/help/index.html` limits table | "An independent finite-element solution" | none |
| `research/strong-edge-laminate/README.md` 8 | uses the earlier hexahedral numbers | optionally point to this folder |
