# Integration of the finite-element comparison program

**What enters the program: nothing.** This folder is our own comparison tool, not a feature. `pcbthermal/`, `tests/`, `examples/`, `ico/` and `requirements.txt` are not touched; `git diff develop...research/independent-fem-edge --stat -- pcbthermal tests examples ico` is empty.

## Recommendation

1. **Merge the folder** into `develop` (after the reviewer re-checks it, `research/REVIEW.md`): the evidence of `docs/validation.md` 28, 36, 40, 43, 44 and 46, of the user-guide validation table and of the edge-laminate warning texts is then reproducible from the repository.
2. **The libraries stay out of the project.** scikit-fem (BSD-3-Clause) and pyamg (MIT) are in this folder's `requirements.txt` and the git-ignored `.venv-research`; the solver itself needs numpy and scipy, so the folder's tests run on the project `.venv` and skip only the scikit-fem cross-check. No row is added to the README table of libraries.
3. **Documents**: `docs/validation-text.md` holds the sentence for `docs/validation.md` 46 and the list of other places that say the reference is outside the repository.
4. **Open FDM finding** (section 4, item 5; partly cured by the face fill of 2.7.0, `docs/validation.md` 47): the FDM with a copper edge inside the outline is 2 to 3 times cooler than the FVM at strong films; the cause was not traced; it is a `fix/` investigation (`research/ROADMAP.md` A40).

## Risks

* The tables are a snapshot of the program at the tip they were run on (`develop` at 48ad0380 for sections 3 and 4); a later model change moves the program columns, not the finite-element ones. `scripts/study_program.py` and `study_report.py` regenerate them.
* The finest meshes need CG with pyamg (the scratch environment) and up to 3 GB; the largest board (8 layers, pad, 0.05 mm) was not solved.
* A hollow plated barrel, stripes, imported masks, transients and metal blocks are not covered.
