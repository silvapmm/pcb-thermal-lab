# Log: the five models against each other

| Date | What |
| :-- | :-- |
| 2026-10-16 | The legacy program was reviewed (false convergence of its SOR rule, heater power depending on the grid, no lateral conduction in the FR-4, solid vias, dimensionally wrong analytic term, an invalid lumped network, an iterations GIF instead of time); the new FVM, Lumped and Analytic models written; the SOR experiment of section 4.4 and the FDM of `fdm.py` added (the FDM agrees with the FVM within about 1 % and jumps ±0.5 °C with the grid). |
| 2026-10-17 | The 3D solid and the FEM cross-check (see `../solid3d-verification/`). |
| 2026-10-23 | Folder created: the four scripts moved from `examples/`; all four were run again and reproduce the numbers of `docs/validation.md` sections 2 and 5 (19 scenarios, 5 solver boards). Small differences against the text of section 5: CG appears with 3.3e-12 K against 1.8e-12 K in the old table (a solver detail), and the timings are those of this machine. Sections 4.5 to 4.7 are copied from `docs/validation.md` and were **not** re-run here (legacy code removed; time results come from tests). |

Not verified: no measurement of a physical board.
