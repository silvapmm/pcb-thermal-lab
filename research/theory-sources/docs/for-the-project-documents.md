# Text for the project documents

Each block names the file and the place where it goes when the maintainer adopts it. Nothing here has been applied. The review corrected the blocks on the horizontal plate, the mixed convection, the Hollands exponent and the validation rows (README 6); its recommendation of which blocks to apply in 2.4.5 is in `INTEGRATION.md` 4.

## `pcbthermal/convection.py`, docstring of `h_natural_vertical`

Replace "Churchill and Chu (1975) itself has not been opened." by:

"The two forms are printed in Lienhard, A Heat Transfer Textbook (6th edition, open), equations 8.13a (laminar, Ra up to 1e9) and 8.13b (all Ra), pages 419 and 420, and reproduce its Example 8.1 (page 421, Nu 47.33). The 1975 paper (Int. J. Heat Mass Transfer 18, 1323) was not obtained."

## `pcbthermal/convection.py`, docstring of `h_natural_horizontal`

Add: "For comparison, Raithby and Hollands (Lienhard equations 8.35, 8.37a and 8.37b, pages 435 and 436) give an up-face coefficient 7 to 26 percent lower than this one for boards of 100 mm and more (3 to 11 percent of the total h with radiation); the down face has no comparable source in its range (Fujii and Imura, equation 8.38, is for a two-dimensional plate on its width). This function keeps the McAdams form (research/theory-sources 3.4)."

## `docs/theory.md`, heat transfer coefficients (natural convection of a vertical plate and mixed convection)

"Vertical plate (equations 8.13a and 8.13b of Lienhard, A Heat Transfer Textbook, pages 433 and 434; Churchill and Chu 1975). The blend of natural and forced convection `h = (h_n^3 + h_f^3)^(1/3)` is the l_p norm with p = 3; Jaffer and Jaffer (arXiv 2401.09469, Table 4, fitted on rough plates) find p between sqrt(3) and 3 for a vertical plate in an aiding or opposing flow, p = 2 for a level flow along a vertical plate or over an upward-facing plate and p = 5 under a downward-facing plate; for a horizontal board the exponent 3 gives a convective coefficient 7 to 11 percent lower on the top face and up to 8 percent higher on the bottom face. Churchill (1977), the usual citation of the rule, was not obtained."

## `docs/research.md` R3 and any text that quotes the Hollands (1984) equation

"The exponent inside the logarithm is the cube root: `Nu = 1 + [1 - 1708/Ra]* [k1 + 2 (Ra^(1/3)/k2)^(1 - ln(Ra^(1/3)/k2))] + [(Ra/5803)^(1/3) - 1]*`, `k1 = 1.44/(1 + 0.018/Pr + 0.00136/Pr^2)`, `k2 = 75 exp(1.5/sqrt(Pr))`. The documentation of the `ht` library writes the fifth root; the code uses the cube root, and the ISO 15099 form (Rohsenow et al. 1985, equation 9 of ASHRAE preprint OR-05-4-3: `k1 = 1.40`, `k2 = Ra^(1/3)/450.5`) confirms the cube root (within 0.3 percent of the code for Ra 2e3 to 1e7 at Pr 0.71; the documented fifth root inside the logarithm is 3 percent low at 1e7). The paper of Hollands (1984) was not obtained."

## `docs/theory.md` and the Gerber folders' text, effective medium (topic 17)

"Hashin-Shtrikman bounds for d = 2 or 3 (Milton, The Theory of Composites, equation 7.10, page 116; phases labelled s1 > s2): `s1 + d f2 s1 (s2 - s1)/(d s1 + f1 (s2 - s1)) >= s* >= s2 + d f1 s2 (s1 - s2)/(d s2 + f2 (s1 - s2))`. Bruggeman: for spheres equations 10.31 and 10.32 (pages 195 and 196); for disks `f1 (s1 - s*)/(s1 + s*) + f2 (s2 - s*)/(s2 + s*) = 0`, obtained by the step of Milton's section 10.5 from the dilute limit of equation 7.9 (not printed there). Keller phase interchange, equation 3.9; for an isotropic medium invariant under the interchange `s* = sqrt(s1 s2)` (3.11, Figure 3.1), pages 47 to 50."

## `docs/validation.md`, new rows (independent 3D solver and models)

"Muzychka, Culham and Yovanovich (2003), case 1 (b) (a 2 mm layer of k 350 on the 10 mm plate of k 10): centroids 56.55 and 59.94 C in the paper, 56.56 and 59.97 by the independent solver, 56.52 and 59.91 FVM, 56.49 and 59.88 FDM, 56.53 and 59.92 3D solid, 56.52 and 59.91 Analytic. Case 2 (heat-sink base 50 x 50 x 10 mm, k 150, h 400, four sources): centroids 97.40, 103.82, 101.28, 99.94 in the paper, 97.41, 103.85, 101.31, 99.95 by the solver (extrapolated mean of the second source 102.373 K against 102.33 K), FVM 94.46, 98.30, 96.62, 96.13 (2.9 to 5.6 K low in the FVM, FDM and Analytic, 67 to 89 percent of the bound q'' t/(2k) of the through-thickness gradient). Lemczyk, Mack, Culham and Yovanovich (1992), Table 1: 16 heat flows within 0.5 percent (one at 1.15 percent) by an independent 2D solver; Tables 2 and 3 typically within 0.1 to 2 percent, at most 4.1 (case a), 9.1 (b), 9.8 (c) and 8.2 percent (d); the case c column at Bi 0.01 matches within 0.9 percent if its bottom film is Bi1 = 0.001."

## `docs/calculators.md` and `docs/validation.md`, Lee (1998) and Yovanovich (2003)

"Lee, Electronics Cooling, January 1998, equation 1: `Rc = (sqrt(Ap) - sqrt(As))/(k sqrt(pi Ap As)) (lam k Ap R0 + tanh(lam t))/(1 + lam k Ap R0 tanh(lam t))`, equation 2: `lam = pi^(3/2)/sqrt(Ap) + 1/sqrt(As)`; worked example 0.66 K/W (reproduced 0.657). Yovanovich, J. Electronic Packaging 125 (2003) 169-177, Table 3 (page 174): `4 a k Rs` of an isoflux circular source (m = 0) 0.9401, 0.8009, 0.6649, 0.5337, 0.4092 for e = 0.1 to 0.5, reproduced by the Bessel series to 1e-4."

## `docs/versions.md`, chapter "Planned", acceptance checks to add to the Foster, Gerber import and multigrid items

* Foster chain: the Cauer ladder of the Nexperia AN11261 (BUK7S1R0-40H) must sum to 0.4000 K/W, give Zth(4 ms) = 0.26 K/W and equal its Foster equivalent (`research/theory-sources/lib/rc_ladder.py`).
* Gerber import: the three examples of the Ucamco specification 2026.05 (two square boxes 0.39996 mm2, region with hole 68 mm2, two disjunct areas 132 mm2).
* Multigrid: a V(2,1) cycle with red-black Gauss-Seidel must reduce the residual by the same factor (about 0.07) from 15 to 255 points per side (`research/theory-sources/lib/mg2d.py`).
