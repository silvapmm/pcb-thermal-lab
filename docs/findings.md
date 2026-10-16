# Findings Log: Everything Discovered So Far

2026-10-16. A consolidated record of what was found while reviewing the original program and building the new one, each item with its evidence and
what was done about it. Detail and numbers live in the linked documents; this file is the map.

## A. Problems found in the original program

| # | Finding | Evidence | Outcome |
| :-: | :-- | :-- | :-- |
| A1 | FDM `converged` could be a false positive: the stop rule was the largest change in one sweep (0.01 K), not the residual | weak-cooling case reported converged with 15 % of the power dissipated, 7 K error; on the example board the error is -15 % at 2 mm and **-32 % at 1 mm** (grows when the mesh is refined) | residual criterion; direct solve by default |
| A2 | FDM heater power depended on the grid | 1.4 W injected instead of 5 W at 10 mm cells, 0 W if no node fell inside; **8.17 W for 5.50 W** on the app default grid | power distributed exactly by coverage fraction |
| A3 | FDM module did not import without Numba (`float64[:,:,:]` annotations evaluated at definition) | `NameError`; the "pure Python fallback" was unreachable | removed with the old code |
| A4 | Analytic conduction term was dimensionally wrong (`L / (k A t)`, unit K/(W m)) | 1002 °C on a board of about 90 °C | replaced by the multilayer fin solution |
| A5 | Analytic and Lumped "Advanced" used the heater footprint as the convective area | 24 466 °C and 1342 °C on the reference board | heat spreading is now computed, not assumed |
| A6 | Lumped network was not a valid series/parallel network (divided by 1 + vias, via resistance computed and unused, one FR-4 layer for any layer count, Tmean above Tmax) | Tmean 97.4 °C above Tmax 32.2 °C on the example | rebuilt as a real network |
| A7 | FDM had no lateral conduction in the FR-4, solid-copper vias (plating thickness config unused), sinks on inner layers ignored, full-cell borders | no zone ⇒ 548 °C; solid vs hollow via conductance 3× | anisotropic FR-4, hollow barrels, cell-centred volumes |
| A8 | The "time evolution" GIF animated SOR iterations, not time | no heat capacity anywhere in the code | real transient (matrices) with validated time stepping |
| A9 | Solvers mixed numerics, `print()` and wxPython dialogs | could not be tested without stubbing the GUI | physics package without GUI imports |

## B. Physics findings

| # | Finding | Evidence | Where used |
| :-: | :-- | :-- | :-- |
| B1 | Layers are not thermally merged: under a heater the FR-4 is a resistor (about 13 K/W for a 20 × 20 mm heater) | a single merged sheet gave 79 °C against 90 °C; equal to the FVM (79.09 vs 79.12) only with perfect vertical coupling | Analytic is multilayer |
| B2 | A heater layer spreads heat over about 5 mm (`sqrt(S / (h + n g))`), not over the 34 mm of the whole stack | weighting copper with the stack length gave +9 to +16 % with partial copper; with the layer length -2 % | Analytic copper weighting |
| B3 | The uniform-disc relations (mean-to-edge `1/(8πS)`, peak-to-mean) fail when the layer loses heat vertically under the footprint | no copper under the heater: +24 % until the exact disc solution with losses (Bessel I0, I1) was used | Lumped interior factors |
| B4 | Equivalent-disc spreading fails for non-compact heaters | long thin 40 × 4 mm heater +35 % with rings by distance to the centroid, +9.5 % with rings by distance to the footprint | Lumped offset contours |
| B5 | Vias converge with the mesh to about 0.2 % from 1 mm cells | 82.996 / 85.342 / 85.814 / 85.874 / 85.955 °C for 4 / 2 / 1 / 0.5 / 0.25 mm | no extra via model needed |
| B6 | FR-4 is anisotropic: 0.3 W/mK through, 0.8 to 1.06 in-plane | literature | defaults 0.3 and 0.9 |
| B7 | A copper edge crossing a heater defeats both simplified models (about -25 %) | stress cases | warning from `check_problem` |
| B8 | Transient time scales: the hottest point reaches 63 % in about 19 s, the board mean needs minutes (global constant about 106 s) | example board | default animation duration = 5 global constants |
| B10 | A fast wave is harmless but a slow one is not: at 100 Hz and 30 % duty the oscillation at the hottest point is 0.4 °C (average is enough), at a 20 s period it is 85 °C | example board, `roadmap.md` 1.1 | decision by oscillation in °C |
| B11 | Averaging the fast heater changes the peak by less than its oscillation and cuts the steps by a factor of 40 or more | `tests/test_profiles.py` | mixed regimes in one run |
| B12 | A constant typed `h` is only right near one operating point: on the example board it is within 0.1 °C at 5.5 W but 23 °C too hot at 22 W; the bottom face (facing down) cools worse than the top and radiation is 40 to 60 % of the coefficient | `roadmap.md` section 2 table | computed `h` option |
| B13 | A smeared via array under a heater has almost no effect on the analytic transient (10 °C too hot); scaling the via conductance globally fixes the heater above the vias but cools the distant one by 18 %; one calibrated system per heater fixes both | `physics_core.md` 3.4 | analytic `_ModalSet` |
| B9 | A heater partly outside the board has its full power applied to the part inside | 5 W on half the area: 148 °C | warning from `check_problem` |

## C. Numerical findings

| # | Finding | Evidence |
| :-: | :-- | :-- |
| C1 | SOR and the matrix methods give the same temperatures when SOR stops on the residual | difference ≤ 2e-8 K on five boards; the direct solver is 3 to 30 times faster |
| C2 | The original stop rule on the new FVM reproduces the old failure | 2.7 to 16 K error with a violated heat balance |
| C3 | Implicit Euler is first order and Crank-Nicolson second order in time | error table in `new_approach.md`; stored + lost heat equals injected within 0.2 % |
| C4 | Transient cost is dominated by matrix factorisations; doubling the time step in ten stages needs ten instead of one per frame | 60 frames: 13.6 s → 2.5 s at 1 mm |
| C5 | Direct sparse LU handles 320 000 cells in 4.6 s, CG in 3.3 s | benchmark |

## D. Corrections made along the way (what turned out wrong)

- An early statement that vias made the FVM drift by about 1 % with the cell size was wrong: the drift came from comparing two different via layouts (3.33 mm and 3.5 mm pitch).
  With one layout the convergence is monotonic and within 0.2 % from 1 mm. Fixed in the documents.
- The first Lumped (circular rings) and Analytic (global copper average) versions had +24 % and +47 % errors on the example board; the stress and ablation studies pointed to the causes (B2, B3, B4).
- The first transient used one factorisation per frame; replaced by stage-wise time steps (C4).
- Test infrastructure: a modal question box at window close hung the first GUI test run; GUI tests now use a temporary `QSettings` so they never change the user's preferences.

## E. Decisions

1. The sparse direct solver is the default; SOR is optional and kept for comparison.
2. The FVM is the reference model; Lumped and Analytic are fast estimators with documented accuracy and warnings.
3. Physics is separated from the GUI; the GUI is PySide 6 and talks to `simulate`.
4. All code is documented in Doxygen style and a test enforces it (`tests/test_docs.py`).
5. Transients are available (command line and GUI animation).
6. Power profiles are square waves; each heater is averaged or simulated in time from its oscillation in °C (default 1 °C); thermal resistance is shown in K/W, temperatures and differences in °C.
7. Planned: a single Component element with a type (Source = today's heater, Package 2R, passive areas) and computed `h`; multigrid and a 3D FEM validation script are future options.

## F. Open items

- Per-cell or enclosure-aware radiation, Component element (2R package, passive areas), power shapes beyond the square wave, trace Joule heating, reduced-order models (see `candidate_methods.md`).
- A copper edge crossing the heater, and corner heaters, for the Lumped and Analytic models.
- Interactive validation of the GUI on a real display; measurements of a physical board to validate the absolute numbers.
