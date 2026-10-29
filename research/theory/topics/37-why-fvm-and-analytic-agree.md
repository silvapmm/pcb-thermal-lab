# 37. Why the FVM and the Analytic model give about the same numbers

![Why they agree](../figures/fig_30_why_fvm_analytic_agree.png)

*Figure 30 (`figures/fig_30_why_fvm_analytic_agree.png`): the FVM and the Analytic model solve the same layered model (numerically and exactly), the real board differs from that model by an error they share, and part of their agreement was tuned; the 3D solid and the finite-element solid are the independent check.*

![Analytic modes and edges](../figures/fig_32_analytic_modes_and_edges.png)

*Figure 32 (`figures/fig_32_analytic_modes_and_edges.png`): left, the rise of the hottest point of the example board in the Analytic model against the FVM at 0.5 mm cells (60.87 K) as the number of cosine modes grows: -7.85 % with 10 modes, -0.42 % with 20, then -1.94 % at 30 modes and from 75 to 300 (-2.04 % at 50); the curve is flat from 75 modes on, so the remaining -1.9 % is not truncation of the series; its cause on this board (vias, heatsink, partial copper) and why 20 modes is closer were not traced. Right, the four uniform scenarios of `docs/validation.md` 2: the Analytic against the FVM at 0.25 mm is +0.30 to +0.96 % with the board's `h_side` and -0.07 to -0.29 % with insulated edges in both (the study of topic 37). Computed by `scripts/make_figures.py`.*

**Status: explanation** (`docs/validation.md` section 4).

## 1. Four reasons

1. **They solve the same model.** Both treat every layer as a thin conducting sheet, the dielectric as a vertical resistance, one constant `h` per face, the same material properties. The Analytic model is the **exact** solution of that model on a uniform sheet; the FVM is its **numerical** solution; two correct solutions of one model agree. *(This file and `docs/validation.md` 4 said "within the FVM's mesh error (0.2 to 1 %)"; measured, that is wrong: on the uniform scenarios the FVM moves by 0.03 to 0.08 points from 1 to 0.25 mm, while the Analytic stays +0.3 to +1.0 % above it because its cosine series has insulated edges and the boards lose heat through `h_side` = 10 W/m2K; with insulated edges in the FVM too the gap is -0.04 to -0.29 %, `scripts/study_fvm_analytic_edges.py`.)*
2. **The real board is not that model, and that error is shared** (0.4 to 3 % against the 3D solid). Neither can be better than the layered model; "FVM = more precise" does not hold in general. What the FVM has is **freedom of geometry**.
3. **Part of the agreement was engineered**: the Lumped and Analytic models were tuned against the FVM (copper weighted with the heater influence, fin lengths, Bessel factors), so the comparison tables measure agreement with the FVM; the 3D solid does not depend on that tuning.
4. **They diverge where the geometry is not uniform near the heater**: pads, copper edges, corners (24 % low with a 20 mm pad, 25 % with an edge across the footprint, topic 06).

## 2. What follows

* On a uniform board the Analytic is the exact solution only of the board with insulated edges; the gap to the FVM there measures the edge loss, not either model's discretisation.
* A table of "error against the FVM" is **agreement with a reference model**, not accuracy; the accuracy of the layered idealisation is measured against the 3D solid (topic 29).
* The vias and the fins are not tested independently by the 3D and finite-element solids, which share the choice of the via as a rod of the barrel's copper area (topic 29).

## 3. Related topics

01, 02, 06, 29.

## 4. Sources

Own computation: [L-validation], [L-solid3d], `scripts/study_fvm_analytic_edges.py` (this folder). The FVM-plus-Fourier architecture also appears in the literature ([PMC11410250]).

*What was read and what was not verified:* from `docs/validation.md` section 4 (read in full).
