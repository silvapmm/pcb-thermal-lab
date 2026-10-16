# PCB Thermal Lab

[![version](https://img.shields.io/badge/version-2.1.0-blue)](CHANGELOG.md) [![tests](https://img.shields.io/badge/tests-138%20passing-brightgreen)](tests)

Thermal simulation of printed circuit boards. Draw copper zones, heaters, vias and sinks on a multi-layer board, run the models and inspect temperatures,
gradients, hotspots, component junction temperatures and the heat evolution in time.

![Editor](docs/images/editor.png)

## Features

- **Four models on one board description** (finite volumes, finite differences, thermal network, analytical series), cross-checked against each other and against an independent 3D solid, each reporting an exact energy balance.
- **Interactive editor** (PySide 6): rectangles and polygons, vias, sinks, undo/redo, background photo, dark and light themes.
- **Results**: temperature maps per layer, gradients, profiles, hotspot list, heater and junction temperatures, zone statistics, model comparison, temperature painted on the board.
- **Power tables from CSV files** (any piecewise-constant profile, repeating or one-shot) with import and export buttons; documented example in [`examples/csv_profiles`](examples/csv_profiles).
- **Computed heat transfer coefficients**: convection (natural or forced, any orientation) plus radiation from the board temperature, with an optional calibration multiplier, instead of typed numbers.
- **Power profiles**: square-wave power per heater (period or frequency, duty); each heater is averaged or simulated in time automatically, in all three models.
- **Animation of the heat evolution** in real time (power step), with GIF export.
- **Input checks** that warn when a model is doubtful (heater outside the board, no copper under a heater, a copper edge crossing a heater, ...).
- **Command line and Python API** for scripts and parameter sweeps; project files in plain JSON.

![Temperature](docs/images/results_temperature.png)

## Which model should I use?

| Model | Advantage | Apply it to | Error on the rise vs a 3D solid | Time (example board) |
| :-- | :-- | :-- | :-- | :-- |
| **FVM** (finite volumes) | reference, any geometry, full field, transient and animation | final answers, any board with a warning, via arrays, heat-up behaviour | 0.4 to 2.2 % | 0.13 s (1 mm) |
| **FDM** (finite differences) | the same equations on grid points, independent check of the FVM | comparing discretisations (steady state only) | 0.5 to 4 % | 0.12 s |
| **Lumped** (thermal network) | fastest, built from the real footprint and outline, several heaters heat each other | design exploration, parameter sweeps, ranking layouts | 0.1 to 4.5 % | about 10 ms |
| **Analytic** (cosine series) | exact on uniform boards, independent of the FVM, shows the physics | quick estimates with solid planes, checking the FVM, teaching | 0 to 1.5 % on uniform boards and with vias, 24 % with a small copper pad | about 50 ms |

Rule of thumb: run them all (`--model compare`); if they agree within about 5 % and there are no warnings the numbers are consistent; if not, trust the FVM.
**No model has been compared with a measurement of a physical board yet**; see the limits in [`docs/validation.md`](docs/validation.md).

## Install

```sh
git clone https://github.com/silvapmm/pcb-thermal-lab.git
cd pcb-thermal-lab
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # numpy, scipy, matplotlib, PySide6, pytest
```

## Use

```sh
.venv/bin/python -m pcbthermal gui                                         # application
.venv/bin/python -m pcbthermal run examples/example_board.pcbt.json        # command line: all models, report, plots (--model compare adds the FDM)
.venv/bin/python -m pcbthermal run --duration cycles --cycles 4 examples/profile_board.pcbt.json
.venv/bin/python -m pcbthermal transient examples/example_board.pcbt.json --gif   # animation
.venv/bin/python -m pcbthermal solvers examples/example_board.pcbt.json    # direct matrices vs CG vs SOR
.venv/bin/python -m pcbthermal --version
.venv/bin/python -m pytest -q tests
```

```python
from pcbthermal import Problem, SolverOptions, simulate

p = Problem.new(width_mm=100, height_mm=80, layers=4)
p.add_full_copper().add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)
sim = simulate(p, SolverOptions(cell_mm=1.0))
print(sim.to_markdown())          # models, errors against the reference, warnings
sim.save("results")               # report, JSON, CSV fields, figures
```

![Summary](docs/images/results_summary.png)

![Power profile](docs/images/power_profile.png)

![Time simulation](docs/images/results_power_profile.png)

## Documentation

Three documents: [`docs/models.md`](docs/models.md) (what the models are, how they work, power profiles, computed heat transfer coefficients, which one to use),
[`docs/validation.md`](docs/validation.md) (the same scenarios in every model, against a 3D solid, the old program, solvers, time-dependent checks) and
[`docs/roadmap.md`](docs/roadmap.md) (planned work and its evidence). A documented example with power profiles from CSV files: [`examples/csv_profiles`](examples/csv_profiles).
Release notes: [`CHANGELOG.md`](CHANGELOG.md).

## Versions and branches

- Version **2.1.0** (2026-10-16): power profiles (square wave) and computed heat transfer coefficients.
- Version **2.0.0** (2026-10-16): first release of the rebuilt program. The original wxPython program was 1.0.0 (git tag `legacy-wxpython-1.0.0`).
- `main`: released versions, tagged `vMAJOR.MINOR.PATCH`. `develop`: integration branch for the next version. Work happens on `feature/*` branches.
- Semantic versioning; the version is defined in `pcbthermal/__init__.py` and shown in the application (title bar, status bar, About) and in every report.

## Author and license

Pedro Silva, PMS Labs. (C) 2025 Pedro Silva. All rights reserved (see `LICENSE`).
