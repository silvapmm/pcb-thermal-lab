# PCB Thermal Lab

Thermal simulation of printed circuit boards: draw copper zones, heaters, vias and sinks on a board, run three
models and inspect temperatures, gradients, hotspots and component junction temperatures.

| Model | Idea | Use it for |
| :-- | :-- | :-- |
| **FVM** | cell-centred finite volumes on a multi-layer grid, exact sparse solve (reference) | any geometry, final answers |
| **Lumped** | one ring thermal network per heater aggregated from the real geometry | fast estimates, a few percent from the FVM |
| **Analytic** | multilayer cosine-series solution with local via and sink corrections | instant results on boards with uniform copper |

All three share one problem description, conserve energy (reported in every result) and are cross-checked by the test suite.
SOR is available as an optional FVM solver to compare with the original method.

## Install

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # numpy, scipy, matplotlib, PySide6, pytest
```

## Use

```sh
.venv/bin/python -m pcbthermal gui                                   # graphical application
.venv/bin/python -m pcbthermal run examples/example_board.pcbt.json  # command line: models, report, plots
.venv/bin/python -m pcbthermal solvers examples/example_board.pcbt.json   # direct vs CG vs SOR
.venv/bin/python -m pytest -q tests
```

```python
from pcbthermal import Problem, SolverOptions, simulate

p = Problem.new(width_mm=100, height_mm=80, layers=4)
p.add_full_copper().add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)
sim = simulate(p, SolverOptions(cell_mm=1.0))
print(sim.to_markdown())
```

Documentation: [`docs/new_approach.md`](docs/new_approach.md) (old vs new, SOR vs matrices, animation),
[`docs/physics_core.md`](docs/physics_core.md) (models, formulas, API, GUI, verification),
[`docs/candidate_methods.md`](docs/candidate_methods.md) (methods found in the literature),
[`docs/thermal_models.md`](docs/thermal_models.md) and [`docs/legacy_vs_new.md`](docs/legacy_vs_new.md) (review of the original solvers).

## Project

Author: Pedro Silva, PMS Labs. License: (C) 2025 Pedro Silva. All rights reserved (see `LICENSE`).
