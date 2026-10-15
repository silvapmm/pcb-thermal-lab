"""!
@file __init__.py
@brief PCB thermal physics core (no GUI dependencies).

Three models share one problem description (`pcbthermal.model`):
- `fvm`      cell-centred finite-volume solver, steady and transient (reference model)
- `lumped`   small thermal resistor network
- `analytic` closed-form fin solution of a single equivalent sheet
"""

__version__ = "0.1.0"
