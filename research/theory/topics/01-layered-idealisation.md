# 01. The layered idealisation: one temperature per copper layer

![The layered idealisation](../figures/fig_01_layered_idealisation.png)

*Figure 1 (`figures/fig_01_layered_idealisation.png`): a section of the board as the models see it. Each copper layer is one node (one temperature per plan position) with a sheet conductance; the dielectric gap between two layers is a one-dimensional resistance `d/k_th`; the outer layers exchange heat with the air through `h_top` and `h_bottom`.*

## 1. What it is

A printed circuit board is a stack of very thin, very good conductors (copper, 35 um is typical) separated by a poor conductor (FR-4). Solving the heat equation in three dimensions on that stack would need cells thinner than the copper. The **layered idealisation** keeps one temperature per layer and per plan position, `theta_l(x, y)`, and replaces the stack by a chain of 2D sheets joined by vertical conductances. Four of the five models (FVM, FDM, Lumped, Analytic) are built on it; the fifth, the 3D solid (topic 04), is the check of it.

## 2. Why it is allowed

* The Biot number across the copper, `h t_cu / k_cu`, is about 1e-7: the copper is isothermal across its thickness.
* The conduction resistance of the copper, `t_cu / k_cu`, is about 1e-7 m2K/W, four orders of magnitude below that of a dielectric gap, `d / k_th`, about 5e-4 m2K/W. The heat crosses the copper without any visible drop and spends its resistance in the dielectric.

## 3. Symbols

| Symbol | Meaning | Unit |
| :-- | :-- | :-- |
| `theta_l(x,y)` | temperature rise of layer `l` above the ambient | K |
| `S_l` | sheet (in-plane) conductance of layer `l`: the conductance of a square | W/K |
| `f` | copper fill: the area fraction of a cell covered by copper | - |
| `k_cu, k_ip, k_th` | conductivity of copper, of FR-4 in the plane and through the thickness (385, 0.9, 0.3 W/mK by default) | W/mK |
| `slab` | thickness represented by one layer node, `t_pcb / L` | m |
| `d` | thickness of one dielectric gap | m |
| `g` | vertical conductance per area between adjacent layers, `k_th / d` | W/m2K |
| `G_via` | conductance of a via crossing a gap | W/K |
| `h_l` | heat transfer coefficient of an outer face (zero for inner layers) | W/m2K |

## 4. The equations

In-plane conduction of layer `l` is carried by the copper and by the FR-4 of the same slab, in parallel:

    S_l(x,y) = f k_cu t_cu,l + k_ip (slab - f t_cu,l)                       [W/K]

Vertical conduction through a gap is a 1D resistance, and a via adds its barrel in parallel (a via connects **all** layers):

    g = k_th / d            G_via = k_cu A_via / d

with `A_via` the copper area of the barrel (open barrel: `pi[(D/2)^2 - (D/2 - t_plating)^2]`; with a fill, the fill's conductivity times the hole area is added; electroplated copper fills the whole circle; topic 21).

Putting the pieces together gives the **multilayer fin equation** (steady state):

    div(S_l grad theta_l) - h_l theta_l - sum over n = l +- 1 of g (theta_l - theta_n) = - q_l          (1)

`q_l` is the heater power density on its layer. In time, `c_l d theta_l / dt` is added on the left, with `c_l = f rho_c,cu t_cu + (slab - f t_cu) rho_c,fr4`.

**Energy balance.** Integrating (1) over the board makes every internal exchange cancel, and what is left is `sum h_l integral theta_l dA + integral of the edge losses = sum P`: the heat that leaves by every path equals the power injected. Every result reports this balance (10^-12 to 10^-9 on all the test boards).

## 4b. The whole board as one conductivity (a check of the sheet formulas)

Seen from outside, a board of several layers has an in-plane and a through-plane conductivity. For layers in parallel and in series:

    k_in-plane      = sum(k_i t_i) / sum(t_i)           k_through-plane = sum(t_i) / sum(t_i / k_i)           trace layer: k_i = f_i k_Cu

(`f_i` the copper coverage of layer `i`). The Electronics Cooling article of 1998 works the example of a 1.59 mm board with four 35 um copper layers (70 um in total, `k_Cu` 390, `k_FR4` 0.25 W/mK) and finds about 17.4 W/mK in plane and 0.26 W/mK through the thickness; the formulas give **17.41 and 0.2615** (`scripts/check_correlations.py`). The in-plane value is the program's `S_l` summed over the layers divided by the thickness; the through-plane value is the series of the vertical conductances of the chain. The article's message agrees with topic 17: once a continuous copper path exists in the heat-flow direction it dominates, and an effective conductivity of the whole board hides it; the program keeps one node per layer instead.

## 5. What it assumes and where it is wrong

* No gradient across a copper layer, none across the thin dielectric laterally: the gap is a 1D resistance, so there is no spreading **inside** the gap. This costs 0.4 to 2 % against the 3D solid.
* The top and bottom coefficients act directly on the outer layer node (the half slab in series is neglected, 1e-4 of the film resistance).
* One temperature per layer under a footprint (no gradient across a heater).
* The 2D copper is a cell average: it hides how the copper is connected (topic 17), the error that matters most on real boards.

## 6. How the program does it

`pcbthermal/model.py` (board, layers, vias), `fvm.py` (the reference discretisation of equation (1), topic 02), `docs/theory.md` section 1.2 for the text, `docs/models.md` section 1 for the choice of model.

## 7. Where it is tested

* Against the 3D solid and an independent finite-element solid: 0.4 to 2.2 % (FVM), `docs/validation.md` section 3; folder `research/solid3d-verification/` (figures 4 and 5 draw the layered models against the 3D solid).
* The exact 1D series circuit of an advanced stack-up (test in `tests/`), `docs/validation.md` section 12; folder `research/stackup/`.
* The pictures of the five models side by side: `research/models-comparison/figures/fig_04_the_five_models_schematic.png`.

## 8. Related topics

02 (the discretisation), 04 (the check), 17 (copper to cells), 21 (vias), 22 (stack-up).

## 9. Sources

* Equation (1), the fin equation and the sheet conductance: [IncroperaDeWitt] (fin and sheet equations), [CarslawJaeger].
* The same architecture (a Fourier series for the insulating layers with a lateral finite-volume discretisation of the metal layers) found against COMSOL and measurements: [PMC11410250].
* The series and parallel conductivities of the whole board, with a worked example reproduced here: [EC1998Conduction].
* The numbers (0.4 to 2.2 %, 1e-4, 1e-7) come from the repository's own validation: [L-validation], [L-solid3d].

*What was read and what was not verified:* the formulas are copied from `docs/theory.md` section 1.2 (read in full); the textbooks are from the project documents, not opened here.
