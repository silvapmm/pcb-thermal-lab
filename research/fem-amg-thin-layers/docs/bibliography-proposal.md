# Proposed entries for research/theory/BIBLIOGRAPHY.md

Proposal only: `research/theory/BIBLIOGRAPHY.md` and the other project documents stay untouched by this branch (CLAUDE.md 9.5). Status keys: R read in full, S summary, M memory, N not obtained.
**Nothing below was opened for this plan: every status is N or M until the literature step of the investigation is done** (review: still true at the close; the review did not open them either and relied on a dense eigenvalue check, a direct solve and an independent column solve instead, README 10.2; the column preconditioner is block (line) Jacobi, whose textbook source would be Saad, chapter on block preconditioners, status N) (open archives first, then the web; the maintainer's papers library `papers/` is read-only and nothing from it is committed).

## In the local papers library (listed by file name, not opened here)

| Source | Where | Use | Status |
| :-- | :-- | :-- | :-- |
| Y. Saad, *Iterative Methods for Sparse Linear Systems*, 2nd ed. (`papers/pdf/IterMethBook_2ndEd.pdf`; an extract of pp. 140 to 150 is in `papers/md`) | library | CG, preconditioning, SSOR/ILU as the baseline of E10; the multigrid chapter if present | N for this purpose (the extract was converted for another topic) |
| Peng, Appelo, Liu (2022), embedded-boundary AMG (`papers/pdf/PengAppeloLiu2022EmbeddedAMG.pdf`) | library | AMG on a Poisson problem with strongly varying coefficients; possible remarks on anisotropy | N |

## To obtain (open first)

| Source | Why | Where to look | Status |
| :-- | :-- | :-- | :-- |
| pyamg documentation and source (https://pyamg.readthedocs.io, https://github.com/pyamg/pyamg): `smoothed_aggregation_solver`, `ruge_stuben_solver`, `rootnode_solver`, strength measures 'symmetric', 'evolution', 'algebraic_distance', 'affinity', smoothers, `aspreconditioner` | the exact parameter names and defaults of every variant | the installed 5.4.1 docstrings first (`help(...)`), then the site | N (the existing entry reads PyPI metadata only, status R for the metadata) |
| N. Bell, L. Olson, J. Schroder, *PyAMG: Algebraic Multigrid Solvers in Python*, JOSS 2023, doi 10.21105/joss.05495 | the package paper | JOSS is open access | N |
| L. Olson, J. Schroder, R. Tuminaro, *A new perspective on strength measures in algebraic multigrid*, Numer. Linear Algebra Appl. 17 (2010) | the evolution measure (why it sees anisotropy) | author's archive, arXiv or the publisher | N |
| P. Vanek, J. Mandel, M. Brezina, *Algebraic multigrid by smoothed aggregation for second and fourth order elliptic problems*, Computing 56 (1996) | smoothed aggregation and its anisotropy limits | publisher; may be paid | N |
| J. W. Ruge, K. Stueben, *Algebraic multigrid*, in Multigrid Methods (McCormick, ed.), SIAM 1987 | classical AMG, strength theta, semi-coarsening by strength | not open (book chapter) | N |
| U. Trottenberg, C. Oosterlee, A. Schueller, *Multigrid*, Academic Press 2001 | anisotropic problems: semi-coarsening and line/plane relaxation (geometric alternative) | book, not open | N |
| W. L. Briggs, V. E. Henson, S. F. McCormick, *A Multigrid Tutorial*, 2nd ed., SIAM 2000 (already N/S in the bibliography, topic 16) | anisotropy chapter, AMG chapter | book | N (existing status S) |
| Brandt (1977/1986), multi-level adaptive solutions; Stueben (2001) *An introduction to algebraic multigrid* (in Trottenberg et al.) | background | open copies of Stueben's text exist; to search | N |
| Kolev, Vassilevski and related work on AMG for anisotropic diffusion | optional, only if E6 shows the classical route matters | arXiv | N |

## Formulas to write down when read (none is used yet)

The strength-of-connection definitions (symmetric, classical, evolution with its k and epsilon), the Galerkin coarse operator and the smoothed prolongator of smoothed aggregation, the cost model of a V cycle (operator complexity), and the CG residual bound in the preconditioned norm. A published numerical case to reproduce with an independent solver: an anisotropic diffusion model problem (epsilon = 1e-3 to 1e-6 in a 2D grid) solved with the same pyamg calls and, independently, with a direct factorisation (SuperLU) as a check of the variants, before the program's matrices; written into `tests/` and the README when done.
