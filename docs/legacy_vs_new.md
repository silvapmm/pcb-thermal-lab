# Legacy Solvers vs New Models on One Example Board

Generated 2026-10-16 by `examples/legacy_comparison.py` (run `python examples/legacy_comparison.py`;
the legacy solvers are imported with stubs for wxPython/matplotlib, so only their numerics run).

## Example board

100 x 80 mm, 1.6 mm, 4 copper layers of 35 µm, ambient 25 °C, h_top 10, h_bottom 15, h_side 10 W/m²K.

| Element | Description |
| :-- | :-- |
| Heater A | 4 W, 10 x 10 mm at (30..40, 35..45), top layer |
| Heater B | 1.5 W, 6 x 6 mm at (65..71, 38..44), top layer |
| Copper | top layer only over 70 x 50 mm (15..85, 15..65); layers 2 to 4 are full planes |
| Vias | 3 x 3 array, 0.3 mm holes, 3.5 mm pitch under heater A |
| Sink | bottom layer, 20 x 20 mm at (25..45, 30..50), +30 W/m²K |

The same board is given to every model. The legacy solvers get the equivalent editor
`json_config` (canvas pixels, 1 px = 1 mm) with their own default FR-4 and solid-copper via
assumptions. There is no measurement for this board, so the reference is the grid-converged
new FVM (0.5 mm), which conserves energy to 1e-12 and was checked against exact solutions
(see `physics_core.md`). The "dT error" column is the error of the temperature rise above ambient.

## Results

Reference = FVM at 0.5 mm: Tmax 85.87 degC (dT 60.87 K). Requested power 5.50 W, ambient 25 degC.

| Group | Model | Tmax [°C] | dT error vs ref | Tmean [°C] | Power used [W] | Energy balance | Time [s] | Note |
| :-- | :-- | --: | --: | --: | --: | --: | --: | :-- |
| new | FVM, cell 2 mm | 85.34 | -0.9 % | 50.09 | 5.50 | +1e-13 | 0.04 |  |
| new | FVM, cell 1 mm | 85.81 | -0.1 % | 50.09 | 5.50 | -8e-13 | 0.23 |  |
| new | FVM, cell 0.5 mm | 85.87 | +0.0 % | 50.09 | 5.50 | +3e-12 | 1.86 |  |
| new | Lumped (rings) | 100.46 | +24.0 % | 50.33 | 5.50 | +6e-15 | 0.00 |  |
| new | Analytic (modal) | 114.52 | +47.1 % | 51.18 | 5.50 | +3e-15 | 0.03 |  |
| legacy | Analytic, Basic | 603.95 | +851.1 % | 314.48 | 5.50 | not computed | 0.00 |  |
| legacy | Lumped, Basic | 32.24 | -88.1 % | 97.42 | 5.50 | not computed | 0.00 |  |
| legacy | Analytic, Advanced | 34081.12 | +55844.9 % | 17053.06 | 5.50 | not computed | 0.00 |  |
| legacy | Lumped, Advanced | 449.00 | +596.5 % | 4264.97 | 5.50 | not computed | 0.00 |  |
| legacy | FDM, dx 10 mm (app defaults) | 124.93 | +64.2 % | 55.64 | 8.17 | not computed | 1.15 | 152 it, converged=True |
| legacy | FDM, dx 2 mm (defaults tol/omega) | 76.94 | -14.7 % | 45.27 | 5.50 | not computed | 0.06 | 554 it, converged=True |
| legacy | FDM, dx 1 mm (defaults tol/omega) | 66.56 | -31.7 % | 34.59 | 5.50 | not computed | 0.25 | 593 it, converged=True |
| legacy | FDM, dx 1 mm (tight tol, omega 1.9) | 82.50 | -5.5 % | 49.98 | 5.50 | not computed | 0.47 | 1251 it, converged=True |

Notes:
- Legacy **Analytic/Lumped Basic and Advanced** are not usable on this board: errors from -88 % to +55 845 %.
  The legacy Lumped result is also internally inconsistent (Tmean 97.4 °C above Tmax 32.2 °C).
- Legacy **FDM at the app default grid (10 mm)** injects 8.17 W for the requested 5.50 W (+49 %).
- Legacy **FDM with the default tolerance** reports `converged=True` yet is -14.7 % (2 mm) and -31.7 % (1 mm) off:
  the stop test is the step size, and the error gets worse on finer grids. With a tight tolerance and
  omega 1.9 it improves to -5.5 %; the rest is modelling (solid vias, no FR-4 lateral conduction).
- New **FVM** matches itself across grids (-0.9 % at 2 mm, -0.1 % at 1 mm) and conserves power and energy.
- New **Lumped** (+24 %) and **Analytic** (+47 %) are much better than the legacy models but still
  too far off on this non-uniform board. The next section shows why.

## Why the new Lumped and Analytic models miss on this board (ablation)

Features removed one at a time, FVM at 1 mm as reference:

| Case | FVM Tmax [°C] | Lumped Tmax [°C] | Lumped dT error | Analytic Tmax [°C] | Analytic dT error |
| :-- | --: | --: | --: | --: | --: |
| full example | 85.81 | 100.46 | +24.1 % | 114.52 | +47.2 % |
| no sink | 88.91 | 102.67 | +21.5 % | 116.05 | +42.5 % |
| no vias | 94.67 | 116.88 | +31.9 % | 115.22 | +29.5 % |
| no sink, no vias | 97.32 | 118.80 | +29.7 % | 116.74 | +26.9 % |
| top copper over the full board | 85.29 | 95.64 | +17.2 % | 95.29 | +16.6 % |
| no sink/vias, full top copper | 96.68 | 110.46 | +19.2 % | 97.15 | +0.7 % |
| only heater A | 79.97 | 83.13 | +5.8 % | 108.56 | +52.0 % |
| only A, no sink/vias, full copper | 90.30 | 92.54 | +3.4 % | 90.62 | +0.5 % |

Reading:
- **Analytic** is essentially exact (+0.5 % / +0.7 %) when the board is uniform (no vias, no sink, full copper). Its errors come from
  partial copper (+17 %), vias (they act under the heater, but the model smears them over the board) and the sink (also smeared).
- **Lumped** is good for a single heater (+5.8 %), and loses accuracy with two separated heaters (+20 to +30 %), because it merges them
  into one disc; partial copper and the board edges add further error.
