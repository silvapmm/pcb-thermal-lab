"""!
@file __init__.py
@brief PCB thermal physics core (no GUI dependencies).

Three models share one problem description (`pcbthermal.model`):
- `fvm`      cell-centred finite-volume solver (reference model)
- `lumped`   ring thermal network, one network per heater
- `analytic` closed-form multilayer fin solution with local via/sink corrections

Typical use:

    from pcbthermal import Problem, SolverOptions, simulate
"""

__version__ = "0.2.0"

from .model import Problem, load_problem, reference_problem   # noqa: E402,F401
from .api import SolverOptions, Simulation, simulate           # noqa: E402,F401
from .project import Project, load_project, save_project       # noqa: E402,F401
