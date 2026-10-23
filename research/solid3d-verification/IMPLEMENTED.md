# 3D solid and verification: what entered the program

Released in **2.3.0** (the 3D solid) and **2.4.0** (the verification and the convergence studies).

| What | Where |
| :-- | :-- |
| The 3D finite-volume solid (real slabs per copper layer and gap, vias as copper rods, blocks, steady state), key `solid3d` | `pcbthermal/solid3d.py` |
| Input checks that warn about a one-sided pad (Lumped and Analytic unreliable) | `pcbthermal/checks.py` |
| Tests | `tests/test_solid3d.py`, `tests/test_solid3d_verification.py`, `tests/test_copper.py` |
| Project documents | `docs/validation.md` sections 3, 3.1 and 16; `docs/models.md` (section on the 3D solid); `docs/theory.md`; `CHANGELOG.md`; `docs/versions.md` |

Not implemented: a time simulation of the 3D solid (steady state only); the FEM solid inside the program (it stays an offline cross-check, scikit-fem is not a dependency).
