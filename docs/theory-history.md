# Theory: history

Passages of `docs/theory.md` that describe an earlier state of the program or a value that was replaced, kept as
the record. They were moved here byte for byte, each under the number of the section it left, and the theory
keeps only what is implemented now. What each version did is in `versions.md`; the current numbers are in
`validation.md`. The list of moves and its check are `releases/2.9.0/simplify/theory_moves.json` and
`releases/2.9.0/simplify/scripts/theory_moves.py`.

## 1.5

**Via target ratio: the figure quoted before the barrel length of 2.6.0 (audit of 2.8.0)**

> ; the -2.1 to +3.9 % quoted before was with the barrel over `d` alone (audit of 2.8.0, the study re-run with both lengths by `releases/2.8.0/audit/scripts/study_via_checks.py target`)

## 2.1.1

**The links before the open-fraction rule (sentence of the paragraph on the cut-cell flux)**

> The earlier links scaled the sheet of a cut cell by `c` and took the harmonic mean, a factor about `c` too weak into a sliver; the edge film sat on the node, behind that weak link. The program now uses

**The distance used by the drawn layers before 2.7.0**

> Before 2.7.0 the drawn layers used the signed distance from the cell centre (negative off the board); the

**The earlier statement about the floor 0.25 (measured with the cell-centre distance of 2.6.0)**

> The earlier statement (it binds in 80 node cells at 2000 W/m²K and moves the peak 0.06 to 0.15 K) was measured with the cell-centre distance of 2.6.0 and no longer holds. 

## 2.2

**The first numbers of the positive entries (program before the rim rule of 2.6.0)**

> *The numbers first written here (832 / 864 and 3104 / 3872 entries, the largest 0.74 and 1.31 times the diagonal, up to 2.2) are those of the program before the rim rule of 2.6.0 (section 2.6), which uncouples the via from the bare third layer of that board: the audit printed 832 / 864, 0.74 / 1.31 on the tag v2.5.2 and 432 / 432, 0.018 / 0.015 on v2.6.0; they are history.* 

**The via effect before the rim rule of 2.6.0, against the smeared-barrel 3D solid**

> **Before the rim rule of 2.6.0** (section 2.6), against the program's own 3D solid at 1/16 to 1/20 mm (which smears the barrel over its disc with no wall), the FVM read the effect 31 to 47 % low for a copper edge through the via, 45 to 68 % low for a track ending on it and 3 to 4 times high for a via just outside a copper edge at 0.5 mm or coarser; those numbers are history (`validation.md` 30.1). 

## 2.5

**The spread of the peak with the earlier cut-cell links**

> ; the earlier links 0.25 to 3.0 K, `validation.md` 32.2

## 2.6

**The first figures of the image limit, withdrawn**

> . The '4 to 10 % at 1 mm' and '19 points at 1 mm' written here before were against a cell-centred 3D reference later found hot, and are withdrawn

**The error of the partial-copper reading before the contact rule**

> ; 31 to 68 % before the rule

**The contact of an imported via before the ray test**

> ; before it the full contact read the effect 1.5 to 5 times high, `validation.md` 45

## 4

**The cut-cell link of the 3D solid before the open-fraction rule**

> A cell cut by the outline (cover `c_b < 1`) used to be joined with the cover-scaled conductivity `k c_b` and the harmonic mean, which makes the link into a sliver of a cell (`c_b` of 0.01 to 0.1) `2c_b/(1 + c_b)` of a full link, and the edge film sat on the sliver node behind the cover-scaled conduction: the heat of the edge column could not reach the sliver and the sliver cell read far too hot (a jump of 15.8 K, 13 % of the rise, between covers 0.01 and 0.02 at 1 mm and `h_side` = 200 W/m²K; +1.6 K at the default 10; four to five times the same defect of the FVM, `research/cut-cell-links` 10.1, `validation.md` 33). Now, for the

## 4a

**Review of the model branch (tree feature/fem-model): the checks of the steady FEM**

> **Review of the model branch** (`releases/2.8.0/fem-model/REVIEW_BRANCH4.md`, tree `feature/fem-model`): (1) the first test of case 2 met the paper to the printed digit by two offsets that cancel (the 1 um laminate film of the one-layer Problem, +0.09 K, and a 2 x 2 mm window that `round()` to even put 0.5 mm off the centroid, -0.07 K); the converged node is 0.02 to 0.05 K below the paper with a conductive film and moves by at most 0.01 K from a 2 mm to a 0.5 mm cell and from the refinement 1 to 4; (2) on a 40 x 30 mm two-layer board (35 um, isotropic laminate 0.3 W/mK, 6 mm part, 1 W) the heater surface mean converges from below in the FEM (55.003 / 55.083 / 55.104 / 55.108 K for the fine element 1 / 0.5 / 0.25 / 0.25 mm at the cell 1, 1, 1, 0.5 mm) and from above in the independent finite volumes of `research/solid3d-verification/lib/layered3d.py` (55.379 / 55.183 / 55.134 K at 1 / 0.5 / 0.25 mm), both to about 55.12 K: the 0.4 to 0.9 % between the FEM and the FVM at the same cell is mostly the discretisation of the finite volumes (the 6 or 12 elements across the gap give the same number to 0.1 mK); (3) a hollow via (0.3 mm drill, 25 µm plating, open) 3 mm from a 3 x 2 mm, 0.5 W part on the 10 x 10 mm four-layer strong-edge board lowers the hottest node by 1.422 / 1.428 / 1.436 K at the cell 1 / 0.5 / 0.25 mm and the heater surface mean by 1.475 / 1.481 / 1.482 K, against 1.431 / 1.434 K and 1.476 / 1.481 K of the research tool (`research/independent-fem-extensions`, fine size 0.2 / 0.1 mm); (4) the face flux of a part on thick outer copper is continuous at the 105 µm switch: 2.4 mK between the face flux and the volumetric source at 110 µm, where the independent 3D (a face flux) puts the surface 2.7 mK above the column; (5) the conjugate gradients against the direct solve: 6e-10 to 1.8e-9 K on four meshes of 12 558 to 80 500 unknowns. 

## 5

**The one-node footprint before the zones of 2.5.0**

> ; the +22 to +221 % of the effect, 8 to 26 % of the rise, of `validation.md` 18.1 is the one-node footprint before the zones of 2.5.0

**The earlier near-side deficit, against the FVM before its laminate band**

> ; the earlier -9 / -15 % were against the FVM before its laminate band

## 6

**The earlier range of the interface balance**

> ; the earlier text gave the first range up to 500

**The Analytic step response of a board with vias before fix/analytic-transient-hot-point**

> (Until `fix/analytic-transient-hot-point` the Analytic read the step response of a board with vias at the hottest point of the board without them: -22 % at 0.3 s and a square-wave swing -11 % against the finite elements on a via cluster; the fix moved no frozen number, `releases/2.8.0/audit/DECISIONS_2.md`, preface and decision 24.)

## 7

**The branch that introduced the half-copper term of the block film**

> since `fix/face-film-half-slab`; 

## 10

**The fast-wave factors on four layers before 2.7.0**

> , 5 to 7 before

**The wording of the Lanczos factor before the audit of 2.8.0**

> ; the text said `sinc(k/N)` until the audit 2.8.0 A5, which is not what the code computes
