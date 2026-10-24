# 18. Spreading resistance: heat leaving a small source into a larger body

![Spreading resistance](../../solid3d-verification/figures/fig_06_spreading_resistance_explained.png)

*Figure 6 of `research/solid3d-verification` (`research/solid3d-verification/figures/fig_06_spreading_resistance_explained.png`): left, the temperature (colour, logarithmic) and the heat flow (white lines) of a circular source on a flux tube at epsilon = 0.3; middle, the dimensionless resistance against epsilon from the axisymmetric solver, Yovanovich's table and the program's 3D solid; right, the error of the axisymmetric solver as the cell is refined (order one).*

Also: `research/solid3d-verification/figures/fig_01_spreading_resistance_vs_yovanovich.png`, `fig_02_grid_convergence.png`, `fig_05_heat_spreading_layered_and_3d.png` (heat spreading under a small heater in the layered models and in the 3D solid). Investigation: `research/solid3d-verification/README.md` 4.1 and 4.3. **Status: implemented as a verification; the physics is what every model has to reproduce.**

## 1. What it is

Heat from a small source (a footprint) into a larger body (the board) first has to spread out; the extra temperature rise this costs is the **spreading (constriction) resistance** `R_s` (K/W). The dimensionless form is

    psi = 4 a k R_s            (a source radius, k conductivity)

For an isoflux circular source of radius `a` on a flux tube of radius `b` (insulated side, cooled far end), `psi` depends on `epsilon = a / b`: it falls from about 0.94 at `epsilon = 0.1` to about 0.53 at 0.4 (Yovanovich's Table 3: 0.9401, 0.8009, 0.6649, 0.5337 for 0.1 to 0.4). The smaller the source against the body, the longer the path of the heat and the larger `psi`.

## 2. Why it matters here

Every heater of a board is a small source on a large body: the sheet conductance of the layered models (topic 01), the rings of the Lumped model (topic 05, whose interior resistance `1 / (8 pi S)` is the disc spreading in a sheet), the Green functions of the Analytic model (topic 06), and the plate model of a block (topic 11, +4.5 % against a published spreading resistance) all have to reproduce it.

## 3. How it is checked

* The program's 3D solid (square tube of the same area, staircase circle) gives +0.8 % at `epsilon = 0.2` and +0.7 % at 0.3 against Table 3; 2 % at 0.1, where the source is only three cells across.
* A **third, independent solver** (axisymmetric finite volumes, written for this study) gives -1.6, -1.0, -0.8 and -0.7 % at 0.1, 0.2, 0.3 and 0.4 at 400 cells per radius. It converges at first order (the flux changes by a step at the source edge): 0.7716, 0.7857, 0.7932 at 100, 200, 400 cells per radius for `epsilon = 0.2`, extrapolating to **0.8006 against 0.8009**. The table lies between the two solvers, which approach it from opposite sides.
* Grid convergence of the 3D solid on a square source aligned with every mesh: observed order 1.68, GCI of the fine mesh 1.14 %.

* **Seri Lee's plate** (aluminium 100 x 100 x 1.3 mm, source 25 x 25 mm, 1 K/W film): an independent 3D solver gives 0.668, 1.284 and 2.275 K/W for the source at the centre, the edge midpoint and the corner against the article's 0.66, 1.29 and 2.38 (+1.2, -0.4 and -4.4 %); the thin plate of conductance `k t` gives the same (`research/effective-conductivity/` 4.4, [EC1998Spreading]).
* **The cases of Muzychka, Culham and Yovanovich** (a cross of five sources, 80.62 against 80.61 C and a mean of 78.90 against 78.87; two sources on a 300 mm plate within 1 % of the rise): [Muzychka2003], `research/effective-conductivity/` 4.6. For an edge source the resistance is twice, and for a corner source four times, that of the mirrored centred system (method of images).

## 4. Limits

The flux tube of the table is circular and the 3D solid's is square; the extrapolation assumes first order; only the isoflux source is checked. The layered models add the 0.4 to 2.2 % of the layered idealisation on top.

## 5. Related topics

04 (the 3D solid), 05, 06, 11.

## 6. Sources

* Table 3 of [Yovanovich2003]; the review literature on spreading resistance: [Lee1995], [EC1998Spreading], [YovanovichMuzychkaEllison] (summarised in `research/component-heatsink/NOTES.md`; `R = R_0 + R_c` accurate to about 5 % for aspect ratio below 2.5).
* Grid convergence: [Roache].
* Own computation: [L-solid3d].

*What was read and what was not verified:* only Table 3 of Yovanovich was taken from the paper (as recorded in the script); the paper itself was not re-read; [Lee1995] was not used beyond the comparison quoted.
