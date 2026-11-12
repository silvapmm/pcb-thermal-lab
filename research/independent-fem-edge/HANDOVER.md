# Handover: independent finite-element reference of the cooled-wall boards

Stopped at a clean point by decision of the maintainer: the finite-element reference will be rebuilt by another agent in `tmp/` as a comparison program. Nothing is running.

## Built (all in this folder, the program is untouched)

* `lib/hexfem.py`: conforming trilinear hexahedral FEM (NumPy/SciPy only), graded tensor grid, exact brick stiffness, Robin film by the consistent face mass, bricks switched off for an outline, symmetric SuperLU.
* `lib/boards.py`: the four canonical boards (strong-edge plate and via, 20 mm square quarter, T half and whole), `lib/conv.py`: cached solves (`out/fem_cache.jsonl`), Richardson and GCI.
* `scripts/study_fem_cases.py fem`, `study_references.py fv|prog`, `study_report.py` (tables), `make_figures.py`, `make_diagrams.py`; `tests/test_hexfem.py` (5 passed: series stack, 1D fin with source, balance, grid, half T = whole T).
* `README.md` (numbered results 1 to 7), `INTEGRATION.md` (recommendation and sentences for `docs/validation.md`), figures 1 to 5. `out/` is git-ignored (the 53 solves, `fv.json`, `prog.json`, `report.txt`); rerunning the scripts regenerates it (about 25 min FEM on a quiet machine).

## Measured (details in README 2 to 5)

53 FEM solves, balance 1 to 2.7e-11, observed order 1.5 to 2.1, GCI 0.01 to 0.14 %. FEM plate at 1000 W/m2K 24.351 K: the cell-centred reference ref3d is +3.9 % (1/4 mm) and +1.6 % (1/8 mm) above it, its via effect at 0.16 mm +6.1 %. Program FVM 0.25 mm, 1000 W/m2K: plate -7.5 / -3.6 / +1.9 % (simple default / physical default / physical 8 sub-gaps), via effect at 0.16 mm -30.0 / -14.3 / -1.7 %. Squares and T within 0.4 % of the stored truths; T with copper to the wall +1.14 % (1 mm) confirmed. Via effect from the FEM is mesh-noisy (+-2 %, disc-share mixing).

## Paused / not done

Conforming via (tetrahedra), disc and L outlines, FEM cross-check with scikit-fem (not installed, no licence question), a published case reproduced by the FEM itself, the FDM harmonic default on its own, reviewer pass. The review has NOT been run: this folder is not closed.

## Memory limits

Finest plate meshes (191 400 unknowns) peaked at 3.6 to 4.1 GB resident (above the 3 GB goal; the process was also swapped when paused). Via sequences were capped at 0.07 mm (130 500 unknowns, 2.5 GB); everything else under 2.5 GB. `conv.MAX_NODES` (160 000 x 1.3 grid nodes) refuses larger solves.

## Defect found in my own code (fixed, regression test)

The half-domain T board left the stem wall y = 0 insulated (+2.3 % hot against the stored truth); fixed and held by `test_half_domain_t_equals_the_full_t`.
