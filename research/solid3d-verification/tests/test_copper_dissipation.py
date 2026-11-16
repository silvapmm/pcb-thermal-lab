#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_copper_dissipation.py
@brief Regression test of the study copper_dissipation.py: its Lumped column is the program's network (10 rings, the cell by keyword), not a one-ring network.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.append(os.path.join(HERE, "..", "..", ".."))

import copper_dissipation as cd                                   # noqa: E402
from pcbthermal import lumped                                     # noqa: E402
from pcbthermal.api import SolverOptions, simulate                # noqa: E402


def test_lumped_column_uses_the_program_rings(monkeypatch):
    """!
    @brief run() calls the Lumped with 10 rings and the cell as cell_mm, and its value equals the Lumped that the program runs (simulate, default options).
    @param monkeypatch pytest fixture; the other models are replaced by a constant so that the test stays light.
    """
    seen = {}
    real = lumped.solve_steady

    def spy(problem, *args, **kwargs):
        """!
        @brief Record the arguments of the Lumped call and run the real solver.
        @param problem The Problem.
        @param args Positional arguments of the call.
        @param kwargs Keyword arguments of the call.
        @return The SteadyResult of the real solver.
        """
        seen["args"], seen["kwargs"] = args, kwargs
        return real(problem, *args, **kwargs)

    class Stub:
        """!
        @brief A result with a constant t_max for the models this test does not look at.
        """
        t_max = 0.0

    for mod in (cd.fvm, cd.fdm, cd.solid3d, cd.analytic):
        monkeypatch.setattr(mod, "solve_steady", lambda *a, **k: Stub())
    monkeypatch.setattr(cd.lumped, "solve_steady", spy)
    p = cd.board(None)
    got = cd.run(p, 1.0)["lumped"]
    assert seen["args"] == () and seen["kwargs"] == {"rings": 10, "cell_mm": 1.0}
    monkeypatch.setattr(cd.lumped, "solve_steady", real)
    ref = simulate(cd.board(None), SolverOptions(models=("lumped",), cell_mm=1.0)).results["lumped"].t_max
    assert abs(got - ref) < 1e-9
