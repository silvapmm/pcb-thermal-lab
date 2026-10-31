# Literature status for `analytic-partial-copper`

| Source | Used for | Status |
| :-- | :-- | :-- |
| Muzychka, Culham, Yovanovich (2003), Eqs. 16 to 28 | The independent solver reproduces Eq. 27 for a plate (+0.20 % at 0.1 mm), by `research/bare-spot-under-source` (its four solver tests re-run here) | R (by that folder) |
| Carslaw and Jaeger, *Conduction of Heat in Solids* (1959) | The fin equation behind the closed form of a heated strip with a step in the sheet conductance (`lib/strip.py`) | M for the book; the algebra is derived in the docstring and checked by `tests/test_strip.py` (the solver is within 0.33 % at 0.1 mm cells, first order) |
| `research/effective-conductivity` 4.11 | The one-layer 20 mm pad (Analytic -28.8 % quoted, -28.3 % reproduced here) | R (re-run here) |
| `research/gap-subdivision` baseline | 52 pad rows and 44 uniform rows with converged graded 3D references | R (the committed tables; the program's Analytic reproduces its column to 5.7e-7) |
| A published numerical case of a part on a copper pad over bare laminate | None found in the repository; no web search was made in this session | N |
| A published precedent for a heater-weighted copper fill (`K0`) in a Fourier-series board model | Not searched | N |
