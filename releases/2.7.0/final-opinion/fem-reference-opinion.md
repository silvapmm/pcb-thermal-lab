# Reviewer's opinion: finite elements, the open decisions of 2.7.0 and 'Planned: 2.8.0'

Read only, nothing run or edited in the repository. Sources: `research/independent-fem-edge/lib/*.py`, `research/independent-fem-edge/tests/test_mesh_and_crosscheck.py`,
`research/independent-fem-edge/REPORT.md`, `fem-worth-it.md`, `releases/2.7.0/final-opinion/README.md` 6 and `small-branches.md`,
`docs/versions.md` 'Planned: 2.8.0', `docs/validation.md` 40 and 44, `pcbthermal/checks.py`.

## 1. Does the finite-element program need scikit-fem?

**No.** The solver is ours and uses only NumPy and SciPy:

* `research/independent-fem-edge/lib/fem.py` imports `numpy`, `scipy.sparse`, `scipy.sparse.linalg` (own trilinear Q1 assembly, 2x2x2 Gauss, Robin film
  as a face integral, symmetric SuperLU). `mesh2d.py`, `board.py`, `cases.py`, `exact.py`, `refine.py`: NumPy only.
* scikit-fem appears in **a single test**, `tests/test_mesh_and_crosscheck.py:82` (`pytest.importorskip("skfem")`): it assembles the same problem
  on the same mesh and confirms the nodal temperatures to 1e-10. With the project's `.venv` that test is skipped (8 passed, 1 skipped).
* The other optional dependency is **pyamg** (MIT), in `fem.py:223`, only above 60 000 unknowns (preconditioned conjugate gradient).
  In practice it is pyamg, not scikit-fem, that is needed for the larger meshes (without it SuperLU reached 5.2 GB at 138 000 unknowns).

**What makes the test independent** is not scikit-fem: it is the method (continuous nodal Galerkin, mesh conforming to the boundary, film on the real face,
no coverage fraction) and the checks against our own closed forms (1D series, Robin fin, order-2.0 2D Robin series,
order-2 manufactured solutions on the box and the disc, balance 1e-9, rotation invariance) and published cases (Seri Lee, Culham-Yovanovich
coupon). scikit-fem only proves that our assembly equals that of another library on the same mesh; it is a good seal, but it is not
necessary for the conclusion.

**Recommendation**: when moving to `research/independent-fem-edge`, **keep the cross-check test as optional** (`importorskip`), with scikit-fem
(BSD-3) and pyamg (MIT) listed in a `requirements.txt` of the folder (like `research/gerber-import/requirements.txt`), installed in a separate
environment (`.venv-research`), never in the program's `requirements.txt`. Cost of keeping it: zero in the program, one test that is skipped in the battery, one
licence line in the folder. Cost of removing it: the only comparison with a third-party assembly is lost; nothing is gained. Run the cross-check test once
in the review at closing and record the result (1e-10) in the README of the folder.

## 2. Finite elements as a sixth model of the application?

**Not for 2.8.0; probably never in the current form.** Reasons:

* **It duplicates the 3D solid** in its role: both are 3D, steady state only, and serve as a check. What the FEM has in addition (conforming boundary,
  via as a cylinder) depends on a **mesh conforming to the outline and to the copper**, and the program's copper comes from Gerbers as a **raster**. The FEM of
  `research/independent-fem-edge` uses mapped structured meshes (turned square, disc, via in an O-grid), made by hand for each case; there is no mesh generator for
  an arbitrary outline with arbitrary copper. The free generators (Triangle: non-commercial; Gmsh: GPL) are a licence trap;
  writing our own is weeks of work plus a tail of robustness issues with hostile copper (`fem-worth-it.md` 3: 5 to 8 weeks in total).
  A hexahedral FEM on the program's Cartesian grid would have the same problem as the cut cells: it would be a third member of the FVM/FDM family.
* **Cost**: the Q1 stencil has 27 points against 7; SuperLU reached 5.2 GB at 138 000 unknowns (REPORT 2), more than the 3D solid
  at the same size; it would need pyamg (a new dependency), a memory law of its own in the guard, an entry in the frozen-numbers harness,
  theory with a figure, guide, hints, stress tests, and a sixth model that the user would not know when to choose.
* **What it would give has already been obtained as a reference**: the study showed that the 2.7.0 FVM is at -0.4 / -1.4 / -3.2 / -6.0 % (200 to 2000 W/m2K) and
  that the Cartesian reference was +0.9 to +6.4 % hot (validation 46). The gain is knowing where the FVM is wrong, and that is done with the FEM outside the program.
* **When to reconsider**: only if there is a permissive and robust mesh generator and a product request for "accuracy on arbitrary outlines",
  and even then first correct the FVM scheme (cheaper), as the decision rule of `fem-worth-it.md` 6 says.

**Recommendation**: the FEM stays as an **independent research reference** (`research/independent-fem-edge`, reviewed, with its row in
`research/REVIEW.md`), which closes gate item 2 of the final opinion. It is not a sixth model.

## 3. Open decisions of the 2.7.0 gate

| decision | opinion | reason |
| :-- | :-- | :-- |
| Keyboard search in the element tree | **postpone (2.8.0)**, record as a limit | It never worked for letters (the tool keys are window shortcuts; `small-branches.md` 46). It is not a regression; restoring it requires changing the shortcut precedence with focus on the tree, which touches many shortcut tests. Not worth the risk days before the close. |
| First-order hot error of the centroid film where the drawn copper reaches the outline (+1 to +2 % at 1 mm) | **accept** | Safe side (hot), falls with the cell (T: +1.06 % at 1 mm, +0.12 % at 0.5 mm against the FEM, REPORT 3(d)); the alternative was tested and was not better. |
| FDM: box edge against outline edge (A40) | **accept as a known limit**, already written | A previous defect, of the FDM (comparison model); the cut-cell attempt in the FDM made it worse (A32). Fixing it requires a nodal scheme of its own: investigation. |
| Lone via: better on average, not on every layout | **accept** | It is the Lumped; the mean error goes down; the worst cases are inside the Lumped's already warned limits with vias. |
| Reach of the via rim mask (reach from the pad size) | **accept the fixed reach of 0.5 mm; do not adopt** | The raster does not give the pad; the measured deviations are all on the hot side. |
| -2 % from four laminate sub-gaps | **accept** | Against the FEM the idealisation is about -0.8 % on the T and L with copper to the wall (validation 40) and -0.4 % at 200 W/m2K on the 4-layer board; 8 sub-gaps at 0.25 mm read HOT (+2 %, REPORT 3(a)), so raising the default is not an improvement. |
| Default of the cut overlay on the command line ('board + map') | **accept** | Visual only, no number changes; same as the GUI. |
| `check_edge_laminate`, first clause (3.2 mm boards, -2.4 / -5.5 / -16 %, against the hot Cartesian reference) | **fix the text now** (one sentence) or say "against a finite-volume reference 1 to 6 % hot" | Text only, no number changes; leaving a number we know is exaggerated is worse than saying where it comes from. Re-measuring at 3.2 mm with the FEM is for later. |
| `_edge_laminate_uncut` says '3D solver at the same cell' (`checks.py:1151`) | **fix now** | The quoted numbers are the FEM's (validation 46); the sentence is wrong. Text only. |

The two texts are a small `fix/` branch (text, `tests/test_warning_texts_plain.py` and the message tests), with no refreeze.

## 4. Why 'Planned: 2.8.0' does not enter 2.7.0

| item | nature | cheap to include in 2.7.0? |
| :-- | :-- | :-- |
| E13: converged reference for small imported parts | investigation not closed (the FVM itself moves 15 to 30 % between 0.5 and 0.25 mm on a 0402); may give local refinement = feature | No. One can only, without risk, add to the warning "the reference is not converged". |
| Component holes and vias with a span as vias (B5) | feature (import option + blind-via model) | No: new model, touches vias, frozen numbers. |
| Local laminate rule (A18) | investigation with a second round pending (4-cell gate, transition); moves numbers | No. The `check_small_part_laminate` warning covers it. |
| Lumped first link near the edge (A27/A23) | investigation; the candidate was rejected because of error compensation | No. The warning already exists. |
| Drawn copper colder than imported (5a) | investigation; moves numbers | No. |
| Physical measurement (G1) | external data (the colleague's board) | No, it does not depend on us. |
| FDM cut cells (A32/A40) | investigation; the prototype made it worse | No; limit written. |
| Electrothermal (Joule) | large new feature | No. |

**None is a small defect that should be fixed now**: all of them move frozen numbers or need a study, and 2.7.0 already has the refreeze still to do.
What can enter without risk: text only (the two warnings of point 3 and, if wanted, the note on the unconverged reference in the E13 warning).

**What is missing before calling the program 'final'** (opinion): (1) **a physical measurement** (G1) — without it no model has been compared with a real
board, and the sentence "never compared with a measured copper board" stays in the Summary; it is the biggest gap; (2) the FEM as an independent reference
**inside the repository** and reviewed (gate 2), so that validation does not depend on a program outside it; (3) the converged reference for
small imported parts (E13), because the numbers of the reduced-models warning rest on a reference that moves 15 to 30 %; (4) the investigation
of drawn against imported zones (5a), because the same copper reads differently depending on its origin. The rest (A18, A27, A32/A40, B5,
electrothermal) are known and warned limits or features, compatible with a "stable" version.
