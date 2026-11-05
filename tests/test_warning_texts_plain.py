#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_warning_texts_plain.py
@brief The warnings that reach the screen (live list, Results summary, tooltips) never name an internal branch or study folder: a user does not have them.
@details A board with parts, scattered vias, a heatsink and imported copper runs through every check and every model; the texts of check_input, check_model_limits,
         check_via_limits, check_via_partial_copper, the problem warnings and the warnings of the run are scanned for `research/`, `fix/` and `feature/`.
"""

import re

import numpy as np

from pcbthermal import Problem, SolverOptions, checks, copper, simulate

BAD = re.compile(r"research/|fix/|feature/")


def _board():
    """!
    @brief A 30 mm two-layer board with a part, a heatsink, a lone via far from the part, a via array under the part and imported copper stripes on both layers.
    @return Problem.
    """
    p = Problem.new(30, 30, 2)
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18), name="U")
    p.add_heatsink(1, 50.0, rect=(5, 5, 9, 9))
    p.add_via(3, 27)
    for x in (13.5, 15.0, 16.5):
        for y in (13.5, 15.0, 16.5):
            p.add_via(x, y)
    n = 300
    stripes = np.zeros((n, n), np.uint8)
    stripes[:, ::20] = 255
    stripes[:, 1::20] = 255
    p.imported = copper.imported_from_rasters([stripes, stripes], 0.1, "faces")
    return p


def test_no_internal_branch_or_study_name_in_user_warnings():
    """!
    @brief Scan every warning text (full and one-line forms) of the checks and of a run of all the models.
    @return None.
    """
    p = _board()
    models = ("fvm", "fdm", "lumped", "analytic")
    texts = []
    for cell in (0.5, 1.0):
        for w in checks.check_input(p, models, cell):
            texts += [str(w), checks.line(w)]
    sim = simulate(p, SolverOptions(models=models, cell_mm=1.0))
    texts += [str(w) for w in sim.warnings]
    assert len(texts) > 4                                        # the board really raises warnings
    assert any("Lumped" in t and "via" in t for t in texts)      # including the long via text that used to quote the branches
    bad = [t for t in texts if BAD.search(t)]
    assert not bad, bad[0]
