# Validation: the same scenarios in every model

Every table here is produced by a script in `examples/` and can be regenerated. Models: **FVM** (finite volumes, reference), **FDM** (node-centred finite differences, comparison),
**Lumped** (thermal network), **Analytic** (Fourier series); described in [`models.md`](models.md). Errors are on the **temperature rise** above ambient. Default board:
100 × 80 mm, 4 layers, 25 °C ambient, `h_top` = 10, `h_bottom` = 15, `h_side` = 10 W/m²K, FR-4 0.3/0.9 W/mK (through/in plane), copper 35 µm, 1 mm cells.

**What is and is not validated.** The models are compared with each other, with an independent 3D solid solved by finite elements (section 3), with exact solutions where they exist and with the literature (section 8).
**No model has been compared with a measurement of a physical board**: a good compact model typically lands within about 4 to 5 % of a real board (section 8), and that is the next step to build confidence in absolute values.

## 1. One scenario, every model: the example board

`example_board()`: 100 × 80 mm, 4 layers, top copper only over 15 to 85 × 15 to 65 mm, planes on layers 2 to 4, heaters U1 (4 W, 10 × 10 mm) and U2 (1.5 W, 6 × 6 mm), a 3 × 3 array of 0.3 mm vias under U1,
a 30 W/m²K heatsink on the bottom. Maximum temperature [°C]:

| Model | Tmax | Error on the rise | Time |
| :-- | --: | --: | --: |
| FVM (0.5 mm) | 85.87 | reference | 0.9 s |
| FDM (0.5 mm) | 85.22 | −1.1 % | 0.8 s |
| Analytic | 84.69 | −1.9 % | 0.05 s |
| Lumped | 84.66 (1 mm) | −1.9 % | 0.01 s |
| 3D solid (finite elements, 0.5 mm, vias as copper rods) | 85.59 | −0.5 % (FVM +0.5 %) | |

Every model closes the energy balance below 1e-11 (heat out equals power in).

## 2. Many scenarios, every model (1 mm cells; error against the FVM)

`python examples/validation_study.py`

| Scenario | FVM [°C] | FDM | 3D solid | Lumped | Analytic | Input check |
| :-- | --: | --: | --: | --: | --: | :-: |
| reference board (centred 20 mm heater) | 90.13 | 90.13 (+0.0 %) | 90.27 (+0.2 %) | 89.70 (−0.7 %) | 90.35 (+0.3 %) | - |
| example board (full) | 85.81 | 84.38 (−2.4 %) | 85.98 (+0.3 %) | 84.66 (−1.9 %) | 84.65 (−1.9 %) | - |
| example, no heatsink | 88.91 | 87.47 (−2.3 %) | 89.08 (+0.3 %) | 87.60 (−2.1 %) | 87.78 (−1.8 %) | - |
| example, no vias | 94.67 | 94.58 (−0.1 %) | 94.91 (+0.3 %) | 96.51 (+2.6 %) | 94.56 (−0.2 %) | - |
| example, top copper over the full board | 85.29 | 83.94 (−2.2 %) | 85.42 (+0.2 %) | 84.14 (−1.9 %) | 84.62 (−1.1 %) | - |
| example, uniform (no heatsink, no vias, full copper) | 96.68 | 96.66 (−0.0 %) | 96.88 (+0.3 %) | 98.34 (+2.3 %) | 97.15 (+0.7 %) | - |
| example, only heater U1 | 79.97 | 78.54 (−2.6 %) | 80.12 (+0.3 %) | 77.82 (−3.9 %) | 78.71 (−2.3 %) | - |
| example, only U1, uniform | 90.30 | 90.27 (−0.1 %) | 90.51 (+0.3 %) | 91.10 (+1.2 %) | 90.62 (+0.5 %) | - |
| reference board, heater in the corner | 109.40 | 109.39 (−0.0 %) | 109.54 (+0.2 %) | 102.09 (−8.7 %) | 110.42 (+1.2 %) | - |
| reference board, small 5 mm heater | 103.06 | 103.06 (+0.0 %) | 103.73 (+0.9 %) | 102.87 (−0.2 %) | 103.44 (+0.5 %) | - |
| reference board, 8 layers | 65.70 | 65.70 (+0.0 %) | 65.72 (+0.1 %) | 66.17 (+1.1 %) | 66.11 (+1.0 %) | - |
| heater 5 mm inside the top-copper edge | 94.45 | 94.04 (−0.6 %) | 94.78 (+0.5 %) | 91.45 (−4.3 %) | 93.83 (−0.9 %) | - |
| heater straddling the top-copper edge | 143.89 | 139.77 (−3.5 %) | 149.27 (+4.5 %) | 111.52 (−27.2 %) | 114.54 (−24.7 %) | warns |
| no copper on the heater layer | 150.16 | 150.14 (−0.0 %) | 153.19 (+2.4 %) | 150.12 (−0.0 %) | 150.44 (+0.2 %) | warns |
| 30 x 30 mm copper island around the heater | 92.38 | 91.96 (−0.6 %) | 92.78 (+0.6 %) | 91.66 (−1.1 %) | 89.49 (−4.3 %) | - |
| hatched copper (fill 0.5) on the top layer | 105.78 | 105.78 (+0.0 %) | 106.23 (+0.6 %) | 105.72 (−0.1 %) | 106.00 (+0.3 %) | warns |
| heater on the bottom layer | 88.37 | 88.37 (+0.0 %) | 88.58 (+0.3 %) | 87.97 (−0.6 %) | 88.65 (+0.4 %) | - |
| long thin heater, 40 x 4 mm | 67.84 | 67.84 (+0.0 %) | 67.92 (+0.2 %) | 71.90 (+9.5 %) | 68.12 (+0.7 %) | - |
| heater in the corner (10 mm from two edges) | 105.34 | 104.92 (−0.5 %) | 105.54 (+0.3 %) | 98.51 (−8.5 %) | 106.06 (+0.9 %) | - |
| two heaters 60 mm apart (4 W + 2 W) | 100.41 | 100.33 (−0.1 %) | 100.62 (+0.3 %) | 99.10 (−1.7 %) | 101.07 (+0.9 %) | - |

Reading:

* **FDM and FVM agree to about 0.1 % wherever there are no vias** (and exactly where the geometry lies on the grid). With the via array the FDM is 2 to 3 % low at 1 mm, because it puts a point feature on the nearest grid point; the gap closes with the grid (section 2.1).
  It is 3.5 % low when a copper edge crosses the heater.
* **Analytic** is exact on uniform boards and within 2.3 % with partial copper, vias, heatsinks, corners, thin heaters and several heaters; it fails (−25 %) when a copper edge crosses the heater, and the input check warns.
* **Lumped** stays within about 4 % in most cases, 9 % at worst (corners, thin heaters), and also fails when a copper edge crosses the heater.

### 2.1 Against the grid (example board)

| Spacing [mm] | FVM | FDM (area sampling) | FDM (point sampling, classic) | 3D solid |
| --: | --: | --: | --: | --: |
| 4 | 83.00 | 82.29 | 85.36 | 83.10 |
| 2 | 85.34 | 84.66 | 86.18 | 85.48 |
| 1 | 85.81 | 84.38 | 85.15 | 85.98 |
| 0.5 | 85.87 | 85.22 | 85.58 | 85.56 |
| 0.25 | 85.95 | 85.67 | 85.80 | - |

The FVM rises monotonically to its limit (within 0.2 % from 1 mm; the via array is a point feature that keeps adding a little constriction as the mesh is refined). The classic point-sampled FDM jumps around it
(±0.5 °C) because it samples the copper edge, the heater footprint and the vias at points; area sampling removes the jumps on geometry that is not aligned with the grid. A board whose heater is not on the grid
(reference board, 4 W, 10.4 × 10.7 mm heater at 30.3 mm; 1 mm cells; reference 103.63 °C at 0.2 mm): FVM 103.59, FDM area 103.18, FDM point 105.69.

## 3. Against an independent 3D solid

`python examples/validation_study.py --fem` (scikit-fem, offline, not in `requirements.txt`).

**The 3D model** (`examples/fem3d_validation.py`): a tensor mesh of trilinear hexahedral elements; copper slabs with their true thickness (one element across), FR-4 gaps with four elements across,
copper where a zone exists and FR-4 where it does not; anisotropic FR-4 (0.3 through, 0.9 in plane); convection on the top, bottom and edge facets; the heater as a heat flux on its footprint on the top face;
a heatsink as an extra coefficient on the bottom facets inside its polygon; **a via as a copper rod with the copper area of the plated barrel** (0.147 mm square for a 0.3 mm via with a 25 µm wall, since the wall itself is far below
the mesh), through the whole thickness, with mesh lines refined around every rod. It does not use the "one node per copper layer" idea of the four models, so it measures the error of that idea. Element size 1 mm in the board plane
(halving it moved the 4-layer full-copper case by 0.06 °C; 2 elements instead of 4 across the gaps by 0.02 °C).

Maximum temperature of the top face [°C] and error of every model on the rise (FVM and FDM at 0.5 mm; Lumped and Analytic with their default settings):

| Board | 3D FEM [°C] | FVM | FDM | 3D solid (FV) | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| 4 layers, full copper | 90.6 | 90.3 (−0.4 %) | 90.3 (−0.5 %) | 90.5 (−0.1 %) | 91.1 (+0.7 %) | 90.6 (−0.0 %) |
| 2 layers, 40 mm top pad | 112.2 | 111.5 (−0.8 %) | 111.2 (−1.2 %) | 112.4 (+0.2 %) | 112.1 (−0.1 %) | 106.8 (−6.2 %) |
| 2 layers, 20 mm top pad | 136.2 | 133.7 (−2.2 %) | 131.7 (−4.0 %) | 138.0 (+1.6 %) | 131.1 (−4.5 %) | 109.6 (−23.9 %) |
| example board (partial copper, 9 vias, bottom heatsink) | 85.6 | 85.9 (+0.5 %) | 85.2 (−0.6 %) | 85.6 (−0.0 %) | 84.7 (−1.5 %) | 84.7 (−1.5 %) |

**Metal block** (a heatsink with a thickness; `examples/fem3d_validation.py` models it as a gap-pad slab of conductivity 1 W/mK and thickness `R''` plus the block slab below the board, with its side faces losing heat too; 100 × 80 mm, 2 layers, 5 W, 30 × 30 mm copper pad on the bottom, block 60 × 60 mm unless stated; FVM and FDM at 1 mm; error on the rise):

| Case | 3D FEM [°C] | FVM | FDM |
| :-- | --: | --: | --: |
| no block (bottom pad only) | 134.2 | 133.2 (−0.9 %) | 132.6 (−1.5 %) |
| Al 3 mm, gap pad 5 K cm²/W | 115.5 | 115.0 (−0.5 %) | 114.9 (−0.6 %) |
| same, finned (extra h 60 W/m²K) | 99.7 | 99.0 (−1.0 %) | 99.0 (−1.0 %) |
| same, worse interface (20 K cm²/W) | 118.8 | 118.4 (−0.4 %) | 118.3 (−0.5 %) |
| Al 1 mm | 117.3 | 116.8 (−0.5 %) | 116.7 (−0.6 %) |
| Cu 3 mm | 115.3 | 114.8 (−0.5 %) | 114.8 (−0.6 %) |
| Al 3 mm 40 × 40 over a 50 × 50 mm pad | 120.4 | 119.4 (−1.0 %) | 119.0 (−1.4 %) |
| Al 3 mm 30 × 30 exactly over the pad | 129.3 | 128.1 (−1.1 %) | 127.4 (−1.8 %) |

The block is always within 1.8 % of the solid. (An earlier version of this script left unused nodes in the matrix of the solid and gave wrong numbers for blocks; fixed by pinning exactly the nodes that belong to no element.)

### 3.1 Does the outer copper dissipate and spread heat (against a heatsink)?

`python examples/copper_dissipation.py [--fem]`. Board 100 × 80 mm, 2 layers, 5 W on a 10 × 10 mm heater on top, copper only on the top layer (a square pad centred on the heater), no vias, `h_top` 10 and `h_bottom` 15 W/m²K.
Maximum temperature [°C] against the 3D finite-element solid (error on the rise; the 3D FV column is the program's own `solid3d`):

| Top copper pad | 3D FEM | FVM | FDM | 3D solid (FV) | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| heater pad only (10 mm) | 495.3 | 472.4 (−4.9 %) | 420.9 (−15.8 %) | 533.1 (+8.0 %) | 652.7 (+33.5 %) | 201.1 (−62.6 %) |
| 20 mm square | 273.0 | 266.7 (−2.5 %) | 252.1 (−8.4 %) | 282.0 (+3.6 %) | 517.4 (+98.5 %) | 150.3 (−49.5 %) |
| 30 mm square | 202.6 | 199.7 (−1.6 %) | 193.8 (−5.0 %) | 205.9 (+1.9 %) | 392.9 (+107.2 %) | 145.9 (−31.9 %) |
| 40 mm square | 172.5 | 171.0 (−1.0 %) | 168.2 (−2.9 %) | 174.0 (+1.0 %) | 302.7 (+88.3 %) | 144.9 (−18.7 %) |
| 60 mm square | 150.3 | 149.6 (−0.6 %) | 148.8 (−1.2 %) | 150.6 (+0.2 %) | 200.1 (+39.7 %) | 144.2 (−4.9 %) |
| 80 mm square | 144.6 | 144.1 (−0.4 %) | 144.0 (−0.5 %) | 144.5 (−0.1 %) | 151.1 (+5.4 %) | 143.6 (−0.8 %) |

Copper against heatsink on the same board (40 mm area), FVM heat leaving the top face inside / outside the pad polygon:

| Case | 3D FEM | FVM | FDM | 3D solid (FV) | Heat over the area [W] | Elsewhere on the top face [W] |
| :-- | --: | --: | --: | --: | --: | --: |
| 40 mm copper pad | 172.5 | 171.0 (−1.0 %) | 168.2 (−2.9 %) | 174.0 (+1.0 %) | 1.30 | 0.78 |
| pad + heatsink, extra h 30 W/m²K | 131.5 | 130.9 (−0.6 %) | 130.1 (−1.3 %) | 131.8 (+0.3 %) | 2.99 | 0.40 |
| pad + heatsink, extra h 100 W/m²K | 100.7 | 100.4 (−0.4 %) | 100.3 (−0.5 %) | 100.6 (−0.1 %) | 4.10 | 0.16 |
| heater pad only + heatsink 30 W/m²K on bare laminate | 340.7 | 324.6 (−5.1 %) | 285.6 (−17.5 %) | 369.6 (+9.2 %) | 1.16 | 2.48 |

What it shows:
* **The outer copper dissipates and spreads by itself**: the temperature falls monotonically as the pad grows (495 → 145 °C) and saturates (80 mm gains 6 °C over 60 mm), and the whole top face loses heat, pad and bare laminate alike (the heat found outside the 40 mm pad, 0.78 W, is heat that the copper carried to the laminate).
  The FVM follows the 3D FEM within 1 to 2.5 % for pads of 20 mm and more; the 3D FV solid is within 2 % there, and both 3D models bracket the converged value on the heater-sized pad (section 3).
* **A heatsink works through the copper under it**: the same 30 W/m²K heatsink gives 131 °C on the pad and 325 °C on bare laminate, because on the laminate there is no sheet to spread the heat in. The heatsink adds convection area; the copper provides the path to it.
* **Where the models fail**: with a pad hardly larger than the heater (an edge of copper across the footprint) the FDM loses 8 to 16 % (the grid sees the pad as a few nodes), and the **Lumped and Analytic models are unreliable** for a one-sided pad without vias or bottom copper (Lumped up to +107 %, Analytic up to −63 %); they assume copper around the heater on both faces or a uniform sheet. The input checks already warn about a copper edge crossing a heater; use the FVM for such boards.

The 3D value of the example board is converged: 85.55 °C with 1 mm elements and 85.59 °C with 0.5 mm (2 elements across each gap).

The new **3D solid (FV)** column is the program's own 3D model (`solid3d.py`, section 2.7 of `models.md`; slabs of real thickness, 4 per gap, 1 mm cells here, 0.5 mm in the FEM script's column header): it lands within 0.2 % of the FEM on three boards and 1.6 % high on the 20 mm pad. Its numbers are also the closest to the FVM in section 2 (within 0.3 % on the ordinary scenarios, +4.5 % with a copper edge across the heater, +2.4 % with no copper under it).
**Convergence on a small pad**, where the two 3D models differ most (maximum temperature of the heater-sized copper pad, `copper_dissipation.py`; both rise or fall towards the same limit): 3D FV at 1 mm and 0.5 mm with 4 slabs per gap 533 and 523 °C, with 8 slabs 530 and 519 °C; FEM at 1 mm 495, at 0.5 mm 500 (4 elements per gap) and 502 (8): the limit is about 510 °C, so at 1 mm the FV is 4 % high and the FEM 3 % low on this extreme case (20 mm pad: FV 282, 280, 281, 279; FEM 273, 274, 275; limit about 277 °C).
Reading: on a uniform board the four layered models land on the 3D answer within 0.7 % (FVM, FDM and Analytic within 0.5 %). **With vias and a heatsink (the example board) all four are within 1.5 %**, and the FVM, with each via in one cell, is within 0.5 % of the 3D rods.
With a small copper pad the FVM follows the 3D solid within 2.2 %, the FDM and the Lumped within 4.5 %, and the Analytic loses accuracy exactly where its uniform-sheet assumption breaks (6 % with a 40 mm pad, 24 % with a 20 mm pad). The remaining 0.4 to 2 % of the FVM comes from
representing each copper layer by one node and the dielectric between two layers as a one-dimensional vertical resistance (no lateral spreading inside the gap).

## 4. Why the FVM and the Analytic model give about the same numbers

1. **They solve the same model.** Both treat every layer as a thin conducting sheet, the dielectric as a vertical resistance, one constant `h` per face, the same material properties. The Analytic is the **exact** solution of that model on a
   uniform sheet; the FVM is its **numerical** solution; two correct solutions of one model agree, within the FVM's mesh error (0.2 to 1 %).
2. **The real board is not that model, and that error is shared** (section 3: 0.4 to 3 % from the 3D solid). Neither can be better than the layered model; "FVM = more precise" does not hold in general. What the FVM has is **freedom of geometry**.
3. **Part of the agreement was engineered**: the Lumped and Analytic models were tuned against the FVM (copper weighted with the heater influence, fin lengths, Bessel factors), so tables 1 and 2 measure agreement with the FVM; the 3D solid does not depend on that tuning.
4. **They diverge where the geometry is not uniform near the heater** (section 2: pads, copper edges, corners).

## 5. Linear solvers: direct, conjugate gradients, SOR

`python examples/solver_equivalence.py`. Same boards, same physics, different ways of solving `K θ = Q`:

| Board | Solver | Tmax [°C] | max diff to direct [K] | Residual | Sweeps | Time [s] |
| :-- | :-- | --: | --: | --: | --: | --: |
| reference, 2 layers | direct (sparse LU) | 90.0657 | 0 | 3e-14 | - | 0.01 |
| reference, 2 layers | CG (Jacobi) | 90.0657 | 1.8e-12 | 9e-13 | - | 0.01 |
| reference, 2 layers | SOR, residual 1e-9, automatic ω | 90.0657 | 7.6e-09 | 1e-09 | 656 | 0.05 |
| reference, 2 layers | SOR, step 0.01 K, ω = 1.5 (original rule) | 87.3447 | 2.7 | 6e-02 | 369 | 0.03 |
| reference, 8 layers | direct (sparse LU) | 65.6612 | 0 | 1e-13 | - | 0.23 |
| reference, 8 layers | SOR, residual 1e-9, automatic ω | 65.6612 | 1.7e-08 | 1e-09 | 3247 | 0.69 |
| reference, 8 layers | SOR, step 0.01 K, ω = 1.5 (original rule) | 53.1158 | 13 | 1e-01 | 384 | 0.08 |
| example board | direct (sparse LU) | 85.8143 | 0 | 1e-13 | - | 0.23 |
| example board | SOR, residual 1e-9, automatic ω | 85.8143 | 1.1e-08 | 1e-09 | 2247 | 0.76 |
| example board | SOR, step 0.01 K, ω = 1.5 (original rule) | 69.6449 | 16 | 1e-01 | 562 | 0.18 |
| weak cooling (h = 2 W/m²K, 200 mm) | direct / SOR (residual) | 44.2990 | 2.6e-09 | 1e-09 | 2237 | 0.07 / 0.48 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, step 0.01 K, ω = 1.5 (original rule) | 37.5624 | 6.7 | 3e-01 | 162 | 0.04 |

Direct, CG and SOR with the residual criterion agree to **1e-8 K** or better on all five boards; the original program's stopping rule stops 2.7 to 16 K from the solution with a violated heat balance. The direct solver is the default
(3 to 30 times faster than a correct SOR); SOR stays available as an independent check. (After this table was made the direct solver got a symmetric ordering that makes it about 40 % faster.)

## 6. The removed wxPython program against the current one

Same example board (reference 85.81 °C). Old numbers were obtained by running the original code (git tag `legacy-wxpython-1.0.0`, commit `641da87` with the comparison script).

| Program | Model | Tmax [°C] | Error on the rise | Power used [W] | Note |
| :-- | :-- | --: | --: | --: | :-- |
| old | Analytic, basic | 603.95 | +851 % | 5.50 | dimensionally wrong conduction term |
| old | Lumped, basic | 32.24 | −88 % | 5.50 | not a valid network |
| old | Analytic, advanced | 34081 | +55 845 % | 5.50 | |
| old | Lumped, advanced | 449.00 | +597 % | 5.50 | |
| old | FDM, 10 mm (defaults) | 124.93 | +64 % | **8.17** | injected 8.17 W for 5.50 W |
| old | FDM, 2 mm (defaults) | 76.94 | −15 % | 5.50 | "converged" |
| old | FDM, 1 mm (defaults) | 66.56 | **−32 %** | 5.50 | error grows when the mesh is refined (step-size stopping rule) |
| old | FDM, 1 mm (tight tolerance, ω = 1.9) | 82.50 | −5.5 % | 5.50 | the rest is modelling |
| new | FVM, 1 mm | 85.81 | 0 | 5.50 | energy balance −7e-13 |
| new | FDM (area sampling), 1 mm | 84.38 | −2.4 % | 5.50 | same physics, point features at nodes |
| new | Lumped | 84.66 | −1.9 % | 5.50 | |
| new | Analytic | 84.65 | −1.9 % | 5.50 | |

What went wrong in the old FDM was not the finite-difference idea: a stopping rule on the step size (false convergence), a heater power that depended on the grid, no lateral conduction in FR-4, solid vias, heatsinks on inner layers ignored,
boundary nodes with a full cell. All were fixed (conservative cell balance, exact power, anisotropic FR-4, hollow vias). A correct FDM (section 2) lands within about 1 % of the FVM.

## 7. Time-dependent results

* **Step response, exact check** (`tests/test_fvm.py`): one layer, a heater over the whole board, insulated edges (`C dθ/dt = P − Gθ`, time constant 109.1 s, steady rise 40 K); maximum error in K over three time constants:
  implicit Euler 3.06 / 1.67 / 0.87 / 0.45 for Δt, Δt/2, Δt/4, Δt/8 (first order); Crank-Nicolson 0.315 / 0.077 / 0.019 / 0.005 (second order); stored plus lost heat equals the injected heat within 0.2 %.
* **Step animation, FVM against FDM** (example board, 2 mm; hottest point [°C] at t = 0, 0.12, 0.82, 3.6, 15, 60, 120 s): FVM 25.0, 30.4, 43.6, 53.3, 61.3, 70.7, 76.6; FDM 25.0, 30.3, 43.1, 52.7, 60.6, 70.0, 75.9: within 0.7 °C at every output time (steady maxima 85.3 and 84.7 °C). Power-profile time simulation of the profile example: peak 134.2 °C (FVM) against 129.6 °C (FDM) at 2 mm, where the 6 mm heater is only three cells wide.
* **Step animation, FVM against Analytic** (example board, 4 W + 1.5 W, 1 mm; hottest point [°C] at t = 0, 0.12, 0.35, 0.82, 1.8, 3.6, 7.4, 15, 30, 60, 120 s): FVM 25.0, 30.5, 37.4, 44.0, 49.3, 53.7, 57.7, 61.7, 66.1, 71.2, 77.1; Analytic 25.0, 30.6, 37.4, 43.4, 48.0, 52.0, 55.8, 59.8, 64.1, 69.4, 76.0:
  within 2 °C at every time, after calibrating the vias per heater (without it the Analytic was up to 10 °C off). The hottest point reaches 63 % of its final rise in about 19 s; the whole board needs minutes.
* **Power profiles** (`tests/test_profiles.py`): the exact mean power per step reproduces the energy exactly for any step; against the exact periodic solution of a uniform board (an RC circuit) the decision's peak is within 0.3 % and Crank-Nicolson time stepping within 0.4 %;
  averaging a fast heater changes the peak by less than the oscillation that was neglected, with 40 times fewer steps; a table equals the equivalent square wave to round-off.
  Example (`example_profile_board`: U1 100 Hz, 30 % duty, 13.3 W on → oscillation 0.4 °C, averaged; U2 20 s period, 25 % duty, 6 W on → oscillation 84.8 °C, resolved): peak of the hottest point FVM 135.3 °C, Analytic 134.7, Lumped 131.8;
  steady with the average power 85.8 / 84.8 / 84.7 °C; bound with the on-state powers 231.6 °C (FVM).
* **CSV example** (`examples/csv_profiles`): U1 a repeating 30 s cycle (12 W, 5 W, 0.5 W), U2 a one-shot start-up: peak FVM 119.5 °C, Lumped 116.1, Analytic 115.1 (within 4 %); steady with the average powers 66.5 °C; bound 201.6 °C.

## 8. Computed heat transfer coefficients

Example board, FVM, Tmax [°C], typed `h` (10 top / 15 bottom) against computed (horizontal board, emissivity 0.9):

| Power [W] | Typed | Computed | Difference | Computed h top / bottom [W/m²K] | Vertical | 2 m/s air | Convection ×0.8 |
| --: | --: | --: | --: | :-: | --: | --: | --: |
| 0.55 | 31.1 | 31.9 | +0.8 | 10.4 / 7.9 | 32.0 | 29.9 | 32.1 |
| 1.4 | 40.2 | 41.4 | +1.2 | 11.6 / 8.6 | 41.7 | 37.2 | 42.0 |
| 5.5 | 85.8 | 85.8 | 0.0 | 14.2 / 10.1 | 86.7 | 73.5 | 88.1 |
| 11 | 146.6 | 141.2 | −5.4 | 16.1 / 11.3 | 142.7 | 121.5 | 145.3 |
| 22 | 268.3 | 245.3 | −23.0 | 18.6 / 13.1 | 247.8 | 215.6 | 252.0 |

A constant `h` is right near one operating point and over-estimates the rise by 10 % at 22 W (the typed pair happens to be right near 5.5 W). Radiation is 43 % of the computed top coefficient and 60 % of the bottom one; the bottom face (facing down) cools worse than the top.
Air properties agree with textbook values within 1 to 3 %; the three models agree on the coefficients within 0.1 W/m²K.

## 9. Parts: the junction temperature

`python examples/component_study.py`, `examples/block_contact_study.py` (power coefficient) and `tests/test_component.py`. Five parts of the datasheets read on 2026-10-17 (`docs/models.md` section 6) on a 60 × 60 mm, 2-layer board with a copper pad under the part on both faces (vias under footprints of 3 mm and more), computed natural convection, FVM at 0.5 mm. Level 0 is the plain source (the hottest board point under the part); level 1 adds θ.

| Part | P [W] | θ [K/W] | Pad | Board under part | Tj | P·θ | Share of the rise |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 2 | 4.5 | 8 mm | 227.4 °C | 236.4 °C | 9.0 K | 4 % |
| MOSFET CSD17308Q3 | 2 | 4.5 | 25 mm | 98.6 °C | 107.6 °C | 9.0 K | 11 % |
| LDO TPS7A47 | 1.5 | 1.7 | 8 mm | 176.7 °C | 179.2 °C | 2.5 K | 2 % |
| LDO TPS7A47 | 1.5 | 1.7 | 25 mm | 84.8 °C | 87.3 °C | 2.5 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 8 mm | 109.9 °C | 113.3 °C | 3.4 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 25 mm | 59.3 °C | 62.8 °C | 3.4 K | 9 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 8 mm | 85.6 °C | 95.6 °C | 10.0 K | 14 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 25 mm | 50.9 °C | 60.9 °C | 10.0 K | 28 % |
| Resistor 0603 | 0.1 | 1000 (derived) | 8 mm | 38.9 °C | 138.9 °C | 100 K | 88 % |
| Resistor 0603 | 0.1 | 1000 (derived) | 25 mm | 31.6 °C | 131.6 °C | 100 K | 94 % |

* **Sensitivity** (pad 25 mm): θ ±30 % moves `Tj` by ±0.8 K (LDO), ±1.0 K (buck), ±2.7 K (MOSFET), ±3.0 K (diode) and ±30 K (resistor, where the derived number is the whole answer).
* **The number chosen matters more than its accuracy**: `θJB` instead of `θJC(bot)` gives 102.6 against 87.3 °C (LDO) and 70.2 against 62.8 °C (buck).
* **`ψJB` route** (`Tj = T_ring + ψJB·P`, ring 0.5 to 1.5 mm outside the body, pad 25 mm): LDO 93.7 °C and buck 65.1 °C against 87.4 and 62.8 °C with `θJC(bot)`; with `θJB` as θ 102.7 and 70.2 °C.
* **Datasheet check** (CSD17308Q3, 1 W on its own board of 1 in² of 2 oz copper, computed natural convection): `RθJA` 46.7 K/W against the datasheet's typical 46 and maximum 58; on a minimum pad of 5 mm (assumed size) 164 against the maximum 165 K/W.
* **Power temperature coefficient** against the closed form `ΔT = P0 R/(1 − tc P0 R)` on a linear board (the FVM, Lumped and Analytic models, `tests/test_component.py`): agreement to 0.05 K; for the MOSFET 2 W at 25 °C (107.6 °C without feedback) the junction reaches 138.6, 165.8 and 210 °C for 0.33, 0.5 and 0.67 %/K, with the power rising to 2.75, 3.41 and 4.48 W; a coefficient of 3 %/K has no stable point and the program says so.
* **Top path** (`python examples/top_path_study.py`, `tests/test_component.py`; θJC(top) of the part, 0.5 K·cm²/W paste, 12 K/W clip-on heatsink, pad 25 mm): the heatsink takes 41 to 51 % of the heat and lowers `Tj` of the chips by 15 to 38 K. Against the junction-node prototype of `examples/package_prototype.py` (uniform conductance under the footprint) the program is 0.4 to 0.8 K higher and the top share differs by one point.

| Part | Tj without top path | Tj program | Top share | Tj node prototype | Top share |
| :-- | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 107.6 | 69.8 | 48 % | 69.0 | 47 % |
| LDO TPS7A47 | 87.4 | 56.6 | 51 % | 55.8 | 50 % |
| Buck LMR36510 | 62.8 | 47.8 | 41 % | 47.1 | 40 % |
| Schottky SS12 (SMA) | 60.9 | 43.7 | 49 % | 43.3 | 48 % |

  The series-parallel closure is exact (`Tj − T_amb = R_top·P_top`, `P_top + P_board = P`, test to 1e-4) and the FVM, FDM, Lumped and Analytic models agree on `Tj` within 10 % of its rise.
* **Limits of the approach**: worst case without `theta_sa` (no heat through the top of the package); `θ` is a single number for the whole junction; the junction is the hottest board point under the footprint plus `P·θ` (about 3 K above a junction node with a uniform conductance, which is the conservative side).

## 10. Literature

* Finite volume methods are built from a balance on every cell, so the discrete solution conserves the energy locally and globally; finite differences work on point values (Eymard, Gallouët, Herbin, *Finite Volume Methods*, https://raphaeleh.github.io/PUBLI/bookevol.pdf;
  *Finite Volume Method in Heat Conduction*, https://link.springer.com/rwe/10.1007/978-94-007-2739-7_896; Khouider, https://www.pims.math.ca/files/Khouider_1.pdf). Electronics-cooling tools (Ansys Icepak, Siemens Flotherm, Cadence Celsius) use the finite volume method.
* *A modeling method for thermal steady-state simulation of the four-layer printed circuit board* (https://pmc.ncbi.nlm.nih.gov/articles/PMC11410250/, text read): Fourier-series solutions for the insulating layers combined with a lateral-only finite volume discretisation of the metal layers
  (the architecture of our FVM and Analytic pair); about 1.8 to 2.5 % against COMSOL at the hot region and 4 to 5 % against measurements on a real board; solver under 9 minutes against about 50 for COMSOL.
* Fourier-series multilayer analytical models against finite elements: 1 to 4 % in the studies found by a search (https://researchonline.jcu.edu.au/86884/ and others); figures taken from search summaries, not from the full texts.
* A comparison of finite differences and finite volumes on 1D steady conduction (https://link.springer.com/chapter/10.1007/978-981-97-0037-0_9) is behind a login and was not read.

## 11. Reproduce

```sh
.venv/bin/python -m pytest -q tests                          # all tests (GUI offscreen, documentation gate)
.venv/bin/python examples/validation_study.py [--fem]        # sections 2 and 3
.venv/bin/python examples/solver_equivalence.py              # section 5
.venv/bin/python examples/fem3d_validation.py                # the 3D solid on its own cases
.venv/bin/python examples/copper_dissipation.py [--fem]      # section 3.1, outer copper against heatsink
.venv/bin/python examples/component_study.py                 # section 9, parts and junction temperature
.venv/bin/python examples/csv_profiles/run_example.py        # section 7, CSV example
git archive 641da87 | tar -x -C <empty folder>               # the removed program, section 6
```

## 12. Stack-up, outline, power calculator and process (2026-10-21)

`python examples/stackup_outline_study.py` prints the two tables; `tests/test_stackup.py`, `tests/test_outline.py`, `tests/test_inverse.py` and `tests/test_compute.py` hold the checks.
Board of the study: 60 × 40 mm, 4 layers with full copper, nine vias under a 6 × 6 mm heater of 3 W, typed 12 W/m²K on both faces, FVM at 1 mm.

**Exact checks.**
* A uniform board (heater and copper over the whole board, insulated edges) is one-dimensional: a chain of layer nodes joined by `k/d` of every gap. The FVM and the FDM reproduce the exact series circuit of a stack with three different gaps (0.12 mm at 0.4 W/mK, 0.9 mm at 2 W/mK, 0.25 mm at 0.3 W/mK) to 1e-6 K on every layer.
* The advanced stack-up with equal gaps against the simple one: 0.1 K apart (80.8 against 80.7 K rise); the small difference is how the laminate of the layer nodes is shared (copper plus half of each gap against thickness/N).
* An outline that is the whole rectangle gives the same result as no outline (1e-9 K), and an outline that cuts the board to a smaller rectangle gives the same result as the smaller board (0.05 K) in the FVM, the FDM and the 3D solid.
* The energy balance closes to 1e-9 on every outline in all three models, and a part drawn off the board still delivers its whole power.

**A. Advanced stack-up.** Rise of the hottest point in K (FVM) and the other models as a difference from it:

| Stack | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: |
| simple, equal FR-4 gaps | 80.7 | -4.1 % | -1.5 % | -2.1 % | +7.7 % |
| advanced, the same gaps | 80.8 | -4.1 % | -1.7 % | -2.2 % | +7.7 % |
| thin prepreg 0.1 mm top and bottom, 0.7 mm core | 76.9 | -3.6 % | -1.5 % | -2.4 % | +4.8 % |
| prepreg 0.1 mm, metal-core dielectric 1 mm (2 W/mK) | 75.1 | -3.4 % | -1.5 % | -2.5 % | +4.5 % |
| polyimide flex 0.1 mm gaps (0.15 W/mK) | 77.4 | -5.3 % | -2.1 % | -5.6 % | +2.5 % |
| alumina core 0.6 mm (24 W/mK) | 71.2 | -3.6 % | -2.1 % | -4.3 % | +3.6 % |
| copper 70 / 35 / 35 / 70 µm | 69.8 | -2.2 % | -0.6 % | -0.0 % | +6.4 % |
| copper 17.5 µm on every layer | 102.5 | -6.0 % | -2.6 % | -4.4 % | +7.8 % |

* The stack-up matters: the same board goes from 102.5 K (half-ounce copper) to 69.8 K (heavy outer copper) and from 80.7 to 71.2 K with a ceramic core; the models follow it in the same direction (every row of `test_stackup.py` checks the trend in all five models).
* The spread between models is the same as on the plain board (FDM about 4 % low because a via is sampled at the nearest node, the 3D solid within 2.6 %, the Lumped within 6 %, the Analytic 2.5 to 8 % high): the advanced stack-up does not add a model error.

**B. Board outline.** Rise of the hottest point in K (FVM) and the FDM and the 3D solid as a difference from it:

| Shape | Board area | FVM | FDM | 3D solid |
| :-- | --: | --: | --: | --: |
| rectangle (no outline) | 2400 mm² | 80.7 | -4.1 % | -1.5 % |
| L shape | 1800 mm² | 109.0 | -5.6 % | -1.3 % |
| T shape | 1600 mm² | 105.8 | -3.7 % | -1.1 % |
| ellipse | 1880 mm² | 93.1 | -3.6 % | -1.3 % |
| chamfered corners (6 mm) | 2328 mm² | 82.2 | -4.0 % | -1.5 % |

* Less board makes the heater hotter (the L shape has 25 % less board and the rise grows 35 %), the FVM and the independent 3D solid agree within 1.5 % on every shape, as they do on the rectangle.
* Limits: cell-cover treatment of the boundary (a cell on the edge conducts with its covered fraction), so a neck narrower than two or three cells is poorly resolved; the lumped and analytic models need a rectangle and are not run.

**C. Sensitivity to the stack-up numbers** (`python examples/stackup_outline_study.py`; the typical 4-layer stack-up of `stackups.json`, base rise 84.5 K):

| Change | Rise [K] | Change in the rise |
| :-- | --: | --: |
| dielectric k through -30 % (0.21 W/mK) | 85.4 | +1.0 % |
| dielectric k through +30 % (0.39 W/mK) | 83.8 | -0.8 % |
| all dielectric thicknesses -10 % (fabricator tolerance) | 84.2 | -0.4 % |
| all dielectric thicknesses +10 % | 84.8 | +0.4 % |
| prepreg 0.25 and core 0.35 W/mK | 84.6 | +0.1 % |
| finished copper 15 % thinner (etch and plating spread) | 89.3 | +5.7 % |
| finished copper 15 % thicker | 80.8 | -4.4 % |

Without the vias under the part (base rise 93.4 K) the same ±30 % in the dielectric conductivity gives +3.3 / -2.3 %. The prepreg and the core matter little; the copper and the vias matter more.

**D. Finned metal block** (60 × 40 mm two-layer board, 3 W part, aluminium block 40 × 30 mm on the bottom face, 5e-5 m²K/W interface, typed 10 W/m²K; rise of the hottest point in K):

| Block | Fin ratio at 10 W/m²K | FVM | FDM | 3D solid | Lumped | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| plain plate 3 mm | 1.0 | 88.3 | 88.2 | 88.9 | 100.3 | 99.8 |
| fins 15 × 1.5 mm, pitch 8 mm | 4.7 | 61.2 | 61.2 | 61.7 | 72.1 | 69.4 |
| fins 15 × 1.5 mm, pitch 12 mm | 3.5 | 66.4 | 66.3 | 66.8 | 77.8 | 75.5 |
| fins 30 × 1.5 mm, pitch 8 mm | 8.4 | 53.2 | 53.2 | 53.6 | 62.4 | 59.3 |

The FVM, the FDM and the 3D solid agree within 1 % on a finned block (the same fin ratio in all three); the lumped and analytic models are 10 to 13 % high on a board with a block, as they are on a plain block (they replace it by an equivalent coefficient).

**E. The interface sheet.** The interface between a heatsink and the board or the package is one dielectric sheet (thickness / conductivity): a sheet equal to the typed resistance gives the same temperatures to 1e-9 K (FVM), and a 1.5 mm sheet instead of 0.5 mm of the same material raises the hottest point by more than 0.3 K in the FVM, FDM and 3D solid (`tests/test_heatsink_part.py`); in the lumped and analytic models a plain block is replaced by an equivalent coefficient that cannot beat the bare face, so the sheet only shows there with fins or an extra h.

**Power from a measured temperature.** The forward model reproduces the measurement: the power recovered from the model's own board temperature at the mean-under-part and the 1 mm ring points is exact to 1e-3 (affine, two model runs plus a check), the hottest point and the junction need a few more because the hottest point can move with the power, and with computed convection (not linear) the iteration converges to 2e-3 (`tests/test_inverse.py`). The accuracy against a real measurement is the accuracy of the drawn board and of the probe: no measurement of a real board has been made in this project yet.

**Calculation process.** A cancelled run stops at once (the process is terminated, the next job starts a fresh one), jobs run one at a time, and closing the program leaves no process (`tests/test_compute.py`, `test_gui_stress.py`). Results travel by pickle (22 MB for a four-model run with a profile, 0.04 s).
