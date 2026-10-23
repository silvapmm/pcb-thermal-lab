"""!
@file __init__.py
@brief PCB thermal physics core (no GUI dependencies).

Three models share one problem description (`pcbthermal.model`):
- `fvm`      cell-centred finite-volume solver (reference model)
- `lumped`   offset-contour thermal network, one network per heater
- `analytic` closed-form multilayer fin solution with local via/heatsink corrections

Typical use:

    from pcbthermal import Problem, SolverOptions, simulate
"""

__version__ = "2.4.1"
__author__ = "Pedro Silva (PMS Labs)"
__project_url__ = "https://github.com/silvapmm/pcb-thermal-lab"

from .model import Problem, SquareWave, TableProfile, load_problem, reference_problem   # noqa: E402,F401
from .profile_io import ProfileFileError, read_profile_csv, write_profile_csv   # noqa: E402,F401
from .api import SolverOptions, Simulation, simulate, suggest_cell_mm   # noqa: E402,F401
from .checks import check_problem                                       # noqa: E402,F401
from .project import Project, load_project, save_project       # noqa: E402,F401
