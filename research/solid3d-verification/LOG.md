# Log: 3D solid and verification

| Date | What |
| :-- | :-- |
| 2026-10-16 | The independent 3D finite-element script (`fem3d_validation.py`, scikit-fem) was written to check the layered models; a singular-matrix bug in the block case was fixed (nodes that belong to no element are pinned). |
| 2026-10-17 | The program's own 3D solid (`solid3d.py`) was chosen over adding scikit-fem as a dependency. `copper_dissipation.py` studied whether the outer copper dissipates like a heatsink. |
| 2026-10-22 | The maintainer asked how to validate the 3D model: `solid3d_verification.py` added (Yovanovich Table 3, grid convergence index). |
| 2026-10-23 | Folder created: the three scripts moved from `examples/`; figures added. Reproduced on this date: the Yovanovich table (0.8 %, 0.7 %), the GCI (1.14 %, order 1.68), and the copper pad tables with the FEM column (all match `docs/validation.md`). |

Read: Yovanovich's Table 3 values were taken from the published table as recorded in the script (the paper itself was not re-read on 2026-10-23). Not verified: no measurement of a physical board.
