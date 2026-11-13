# Integration of the finite-element comparison program

**What enters the program: nothing.** This folder is our own comparison tool, not a feature. `pcbthermal/`, `tests/`, `examples/`, `ico/` and `requirements.txt` are not touched; `git diff develop...research/independent-fem-edge --stat -- pcbthermal tests examples ico` is empty.

## Recommendation

1. **Merge the folder** into `develop` (the closing review is README 7.0: GO; `research/REVIEW.md`): the evidence of `docs/validation.md` 28, 36, 40, 43, 44 and 46, of the user-guide validation table and of the edge-laminate warning texts is then reproducible from the repository.
2. **The libraries stay out of the project.** scikit-fem (BSD-3-Clause) and pyamg (MIT) are in this folder's `requirements.txt` and the git-ignored `.venv-research`; the solver itself needs numpy and scipy, so the folder's tests run on the project `.venv` and skip only the scikit-fem cross-check. No row is added to the README table of libraries.
3. **Documents**: `docs/validation-text.md` holds the sentence for `docs/validation.md` 46, two corrections of section 46 found by the closing review (its plate rows are against the FEM point maximum while its text says cell mean; its FDM numbers predate section 47) and the list of other places that say the reference is outside the repository.
4. **Open FDM finding** (section 4, item 5; partly cured by the cell-fill faces of 2.7.0, `docs/validation.md` 47): on `develop` e39de188 the FDM with a copper edge inside the outline is still about twice as far from the FEM as the FVM at strong films (square 1.2 mm in, 1 mm cell, 1000 W/m2K: -12.0 % against -5.5 %); the residual is `research/ROADMAP.md` A40. The FDM via effect 4 to 16 % low at 0.25 mm is not in any project document.

## Risks

* The tables are a snapshot of the program at `develop` e39de188 (re-run by the closing review; the first run's label 48ad0380 was wrong); a later model change moves the program columns, not the finite-element ones. `scripts/study_program.py`, `study_thin_laminate.py prog` and the two report scripts regenerate them in under 2 minutes.
* The finest meshes need CG with pyamg (the scratch environment) and up to 3 GB; the largest board (8 layers, pad, 0.05 mm) was not solved.
* A hollow plated barrel, stripes, imported masks, transients and metal blocks are not covered.
