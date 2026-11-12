# Integration: strong cooled edge (closes Planned item 21)

The review (README 8) corrected the study: there is no converged residual of the layered idealisation on this board. The error at a strongly cooled wall is (i) the default two sub-gaps
of a 0.4 to 0.8 mm gap and (ii) a defect of the simple stack-up for three or more layers: every layer node stands for T / L, so the outer copper nodes carry the edge film of too much
laminate at the copper temperature. With the physical slabs and eight sub-gaps the plate is +0.4 % at 1000 W/m2K and -0.4 % at 2000 (0.25 mm cell) against the 3D reference.

## Recommendation

1. **Decision for the maintainer: the slabs of the simple stack-up.** Two ways, measured only on the study board and the example board:
   * (A) `Board.slab_thicknesses()` of the simple stack-up returns copper plus half of each adjacent gap (the advanced rule with equal gaps), for every model that reads it. Moves every simple
     board of three or more layers (two layers are equal already): FVM of the example board at 1 mm (h_side 10) 85.376 to 85.465 degC (+0.089 K); the plate of the study at 1000 W/m2K, 0.25 mm,
     default sub-gaps -8.9 to -5.1 %; a refreeze of the FVM, FDM, Lumped and Analytic records of the simple boards of three or more layers (not counted). Branch `fix/simple-stackup-slabs`.
   * (B) Only the edge film uses the physical slabs (the rest of the simple model unchanged): boards without an edge coefficient bit-identical; needs care in `laminate.build`, whose moves of the
     film use the held laminate of the simple slab. Not prototyped.
   * (C) Keep it and warn (done on `fix/edge-laminate-warning-text`): the user can use the advanced stack-up.
   The reviewer's recommendation is (A) in 2.8.0 or later with its own frozen-number pass: the simple model is internally inconsistent (slabs T / L, links from the real gaps) and the fix is one
   function, but it moves many records for a gain that is small in air (0.1 % at 10 W/m2K).
2. **Warning text** (`checks.check_edge_laminate`, `EDGE_LAMINATE_H` stays 200; implemented on `fix/edge-laminate-warning-text`): the existing numbers (two-layer 3.2 mm boards, where
   the simple slabs are physical) stay; a sentence is added with this study's four-layer numbers and the via effect, and, for a simple stack-up of three or more layers, the clause that the
   advanced stack-up removes part of the error. Numbers (0.25 mm cell, against the 3D reference): plate with the default two sub-gaps -1.8 / -4.8 / -8.9 / -14.4 % at 200 / 500 / 1000 /
   2000 W/m2K in the simple stack-up, -0.8 / -2.5 / -5.1 / -8.9 % with the physical slabs, within 0.5 % with physical slabs and eight sub-gaps; via effect (via 0.16 mm from the wall) -8 / -19
   / -34 / -51 % simple default, -2.7 / -4.1 / -7.3 / -13.1 % physical with eight.
3. **More sub-gaps by default near a strong edge** (optional, not recommended now): 8 sub-gaps take the physical-slab plate from -5.1 to +0.4 % at 1000 W/m2K but read +3 to +4 % hot at a
   0.5 mm cell (half-cell film); the user can set `laminate_n_max` / `laminate_s_max_mm`.
4. **Documents**: `docs/validation.md` 28 (the -17 / -23 / -26 % and 'does not converge away with the cell') and the Planned item 21 of `docs/versions.md` are corrected on
   `fix/edge-laminate-warning-text`; validation 36 gets a pointer (its boards are two-layer, unaffected).
5. Open (`research/ROADMAP.md`): a via within one cell of a wall cooled above 500 W/m2K (-7 to -13 % at 0.25 mm, against a reference that is itself 5 % uncertain there); a structurally
   different solver (finite elements) for E.

## Impact

This branch: research folder only; the program and its tests are untouched. The warning text: no number moves. Option (A): moves frozen numbers (see 1).
