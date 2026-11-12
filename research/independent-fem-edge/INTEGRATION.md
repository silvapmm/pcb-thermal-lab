# Integration: what the finite-element check means for the recorded validation numbers

Nothing in the program changes. The investigation adds a structurally different reference (conforming trilinear finite elements, `lib/hexfem.py`) and uses it to confirm or correct numbers already
in `docs/validation.md` and in the research folders. Results: README 2 to 5.

## 1. Recommendation

1. **Confirm** (no number to change): validation 40 (the centroid film on drawn layers, the squares, the T and its +1.19 % hot excess), validation 36 at 10 and 200 W/m2K, the simple stack-up slab defect
   (3.9 points at 0.25 mm and 1000 W/m2K), the dominance of the default two sub-gaps over a converged residual, and the finding that there is no via-model defect near the wall.
2. **Correct the size** of the numbers measured against `ref3d` at 1/8 mm at 500 W/m2K and above: that reference is 1.6 % hot on the plate and 6.1 % hot on the via effect at 1000 W/m2K (first-order
   convergence of the cell-centred half-cell film). Against the finite elements the plate at 0.25 mm and 1000 W/m2K is -7.5 % (simple, default), -3.6 % (physical, default), +1.9 % (physical, 8 sub-gaps),
   and the via effect at 0.16 mm is -30.0 / -14.3 / -1.7 % (columns: simple default / physical default / physical 8 sub-gaps). Where an older table quotes the 1/8 mm values, add the FEM column.
3. **Note the uncertainty of the stored truths**: they sit 0.0 to 0.4 % above the finite elements (largest at 1000 W/m2K), so the stated 0.2 % is a little low for strong films.
4. **Do not use the finite elements as the only reference for a via** (E is mesh-noisy at +- 2 % through the disc-share mixing) and do not treat this check as a test of the via model (the representation
   is shared). A conforming via (tetrahedra, or a refined mesh with the barrel as faces) is the next step if the via near a wall matters again.
5. No change to the program, no new frozen numbers, no new dependency. The solver is 250 lines of NumPy and SciPy and can serve later checks (`research/independent-fem-edge/lib`); the cost of the finest
   mesh (190 000 unknowns, 3.6 to 4.1 GB) makes it a research tool and not a test of the battery; the coarse meshes (< 3 s) that give the balance and the closed-form checks are in `tests/test_hexfem.py`.

## 2. Sentences for `docs/validation.md`

(Adopt in the validation sections 36, 38 to 40 and in `research/strong-edge-laminate`; no dates.)

* "The independent references of this section are cell-centred finite volumes. A conforming trilinear finite-element solver (`research/independent-fem-edge`) on the same boards agrees with them within 0.3 % at
  10 and 200 W/m2K and within 0.4 % with the extrapolated truths of the squares and the T; the 1/8 mm cell-centred plate is 1.6 % above it and its via effect at 0.16 mm from the wall 6.1 % above it at 1000 W/m2K
  (the film acts on a cell centre and the error falls with the cell)."
* "Against the finite-element value the FVM at 0.25 mm and `h_side` 1000 W/m2K reads the plate -7.5 % with the simple stack-up and the default two sub-gaps, -3.6 % with the physical slabs and +1.9 % with the
  physical slabs and eight sub-gaps; the earlier -8.9 / -5.1 / +0.4 % were against a reference that is 1.6 % hot."
* "A via 0.16 mm from a wall cooled at 1000 W/m2K has an effect -1.7 % from the finite-element value with the physical slabs and eight sub-gaps (the cell-centred reference gave -7.3 %): the program has no via
  defect at the wall; the 10 to 19 % low effect with the default two sub-gaps is the sub-gap count."
* "The T outline with copper to the wall reads +1.14 % (mean of ten turned boards, 1 mm) against the finite elements and +0.19 % at 0.5 mm."

## 3. Risks and limits

Described in README 5 and 6: one board per case, aligned boards only for the outline cases (the turn is covered by the invariance of the physics), the via representation shared with the finite-volume
references, memory of the finest runs, an unverified Q1 formulation from memory (checked by closed forms, not by a published case).
