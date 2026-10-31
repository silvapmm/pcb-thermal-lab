# For the project documents

Text that would enter `docs/validation.md`, `docs/theory.md`, `docs/models.md` and `docs/versions.md` if S3 and S4 are adopted. The formulas are in `theory-text.md`; the numbers are the ones the
scripts of this folder print (README sections 2 and 3) and are to be re-checked by the reviewer before they enter a project document.

* `docs/theory.md`, solvers: the relaxation factor of the SOR is Young's optimum from an estimate of the Jacobi spectral radius (A.2 to A.4 of `theory-text.md`); the program's earlier formula is the optimum of a plate with fixed edges.
* `docs/validation.md` section 5: the SOR rows with the new omega (sweeps, seconds).
* `docs/theory.md`, Analytic model: the tile rule (B.3), the number of modes of `G`, the cost of the correction.
* `docs/validation.md`, via rows and section 18: the numbers after the correction, with the limits of README 4.
* `docs/versions.md`: remove the items S3 and S4 from 'Planned' when implemented.

Numbers for the text (from the README of this folder): SOR on the example board at 1 mm, 2247 sweeps with the program's omega (1.9391) against 812 with the Rayleigh omega (1.9669) and 781 at Young's exact optimum (1.9671); on the plates 2.8 to 11 times fewer sweeps; the direct solve stays faster. Copper-fill gain of the example board in the Lumped and Analytic models, 6.79 and 6.32 K today, 4.47 and 4.27 K with the proposals (FVM at 0.25 mm: 4.20 K); tile rule `min(1 mm, 0.75 d_nn)` with a floor of 0.25 mm.
