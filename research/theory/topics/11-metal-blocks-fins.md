# 11. Metal blocks and fins: a plate on the board, and a plate fin

![Metal block](../figures/fig_11_metal_block.png)

*Figure 11 (`figures/fig_11_metal_block.png`): left, a block on the board through an interface sheet (the heat enters the block where it overlaps copper; over bare laminate it must also cross the FR-4); middle, a plate fin whose heat to the air falls along the fin, `eta = tanh(mL) / (mL)`; right, the two equivalents of the Lumped and Analytic models, which keep the block's lateral conduction.*

Real sections of the block, the interface and the fins: `research/block-and-fins/figures/fig_05_block_section.png`; the convection scenarios of a heatsink: `research/component-heatsink/figures/fig_03_heatsink_convection_scenarios.png` and `fig_04_block_metal_and_interface.png`.

## 1. What it is

A heatsink with `thickness > 0` is a **plate of metal** (conductivity `k`, heat capacity `rho c`, thickness `t`) pressed on the top or bottom face through an interface of resistance per area `R''`. It is a heat spreader, not a lumped coefficient.

## 2. In the layered models: one extra layer of nodes

One node per cell on that face, with the coverage `c` of the cell by the block:

    lateral sheet conductance   S = k t c                              (joined by the harmonic mean, as the board)
    heat capacity               C = rho c t dx dy c
    contact to the board layer  G = c dx dy [ f / R'' + (1 - f) / (R'' + d_h / k_th) ]
    exposed surface             G = h_exp dx dy c,          h_exp = h_face r_fin + h_extra
    sides of the plate          G = h_wall t L_edge,         h_wall = h_face + h_extra
    board face under the block  its coefficient is multiplied by (1 - c)

`f` is the copper fill of the board layer there and `d_h` half a layer slab: the heat enters the block mostly **where it overlaps copper** (the intersection of the planes) through `R''`; over bare laminate it must also cross the FR-4 (a much larger resistance). The block is an isotropic plate without gradient across the thickness (valid while `h t / k` is small: aluminium or copper of 1 to 10 mm are within 0.6 % of the 3D solid); cells with no block have 1e-9 W/K to the ambient. Heat escapes through the exposed surface (with the fins) and the side walls of the plate (without them; `L_edge` the block outline inside the cell, `t` the plate thickness). *(This file had one coefficient for both; until a review found it, the program also gave the side walls the fin ratio and a finned block ran 5.5 to 6.4 % too cool, `research/block-and-fins/` and `docs/validation.md` 12 D.)*

## 3. Fins

Plate fins on the block (height `H`, thickness `t_f`, pitch `p`): efficiency `eta = tanh(m H_c) / (m H_c)`, `m = sqrt(2 h_face / (k t_f))`, of a straight fin with a convecting tip taken as adiabatic at the corrected height `H_c = H + t_f / 2`; per unit of base area the fin ratio is `r_fin = (1 - t_f/p) + 2 H_c eta / p`, and only the exposed face carries it (`h_exp = h_face r_fin + h_extra`). The model has **no channel choking** between fins (the input checks warn when the gap is smaller than still air allows). Not modelled: the end faces of the fins, their heat capacity (a time simulation of a finned block responds too fast) and the conduction along the fins beyond the efficiency. Fins are validated against a 2D fin (24 cases within 0.08 %); the effect of the spacing on natural convection is not modelled (topic 13).

## 4. In the Lumped and Analytic models (steady state)

An equivalent coefficient `h_eq = 1 / (R'' + 1 / (h_face + h_extra))` (isothermal block, even with the contact area and an annular fin) was 8 to 31 % off, because the block spreads the heat of the pad centre to the whole pad, which a uniform coefficient cannot do. What works is to keep the lateral conduction:

* **Lumped**: the block layer of the FVM network is summed over the rings like the board layers: one more layer of unknowns per ring, lateral links between rings with the same contour formulas (infinite where the block does not reach), a vertical link summed per ring to the heater's layer.
* **Analytic**: on the tile grid the block layer is built with `blocks.extra_layers`; the block temperatures `phi` obey `(K_b + D_amb + D_link) phi = D_link y_b`, so the heat they take from the board is `f = D_link (y_b - phi) = B y_b` with the **Schur complement**

      B = D_link - D_link (K_b + D_amb + D_link)^(-1) D_link

  a dense matrix that couples the tiles of the block among themselves. `B` is added to the local conductance matrix `C` of topic 06, together with the negative conductance `-h_face A cov` for the face that the block hides. This is exact for the tile model.

Both are steady state only; the time simulations still refuse a block, and SOR does not support blocks. Errors against the FVM over 74 cases: Lumped 1.9 % mean, 4.7 % maximum (2.0 and 4.8 % before the minimum ring width of topic 05); Analytic 1.1 % mean, 4.3 % maximum (`research/block-and-fins/README.md` 4.2).

## 5. How the program does it

`pcbthermal/blocks.py` (`extra_layers`, used by `fvm.py`, `fdm.py`, `solid3d.py`, `lumped.py`, `analytic.py`), `docs/theory.md` section 7, `docs/models.md` sections 2.6 and 15.

## 6. Where it is tested

`docs/validation.md` sections 15 (fins against a 2D fin), 17 (block in Lumped and Analytic), 16 (3D solid); `research/block-and-fins/`; the plate model against the published spreading resistance of a small source on a plate, +0.6 % at the centre (-0.8 % at the edge midpoint, -4.6 % at the corner; `research/effective-conductivity/` 4.8 A; the +4.5 % quoted before was a 24 mm source).

## 7. Related topics

06, 05 (the equivalents), 09 (a block as the heatsink of a part), 13, 18.

## 8. Sources

* Fin efficiency and corrected length: [IncroperaDeWitt]. Spreading resistance of a small source on a plate (the plate model's comparison, the worked example of Seri Lee's article): [EC1998Spreading], topic 18; [Lee1995] was cited for it earlier and has not been located.
* Static condensation (Schur complement) of finite-element codes and Kron reduction: [MFEMStaticCond], [Kron2022].
* Channel effect between fins (not modelled): [ElenbaasBCR]. Heatsink catalogues: [HeatsinkCatalogues]. Interface measurement standard: [ASTMD5470].
* Own computation: [L-block].

*What was read and what was not verified:* equations from `docs/theory.md` section 7 (read in full); the plate check is against [EC1998Spreading] (its worked example, read); [Lee1995] could not be found; the channel correlation is not used.
