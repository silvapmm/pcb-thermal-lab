#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file runs.py
@brief One-line runs of the program's models with or without the via treatment of this study, shared by the study scripts.
@details `rise(problem, model, cell_mm, variant)` returns the maximum rise over the ambient of the top layer; `variant` is "program" (develop as it is) or a dict of options of
         `edge_patch.patched_edge` (the recommended treatment with those additions), so a table of variants is a list of such entries. `via_effect` is T_max(no via) - T_max(via).
         For the 3D solid the footprint rule of `solid_patch` ("point" is the program's) is selected with `solid_rule`.
"""

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "point-via-convergence", "lib"))

import edge_patch as ep                                                     # noqa: E402
import program_cases as pc                                                  # noqa: E402
import solid_patch as sp                                                    # noqa: E402

PROGRAM = "program"
MW_PROTOTYPE = {"board_only": False, "fold": False, "image": False}         # the treatment as the point-via-convergence prototype has it
MW_BOARD = {"board_only": True, "fold": False, "image": False}               # + the footprint restricted to the cells on the board
MW_IMAGE = {"board_only": True, "fold": False, "image": True}                # + the image of the edge in the well
MW_FOLD = {"board_only": True, "fold": True, "image": False}                 # + the cut footprint folded back


def rise(problem, model="fvm", cell_mm=1.0, variant=PROGRAM, solid_rule=None):
    """!
    @brief Maximum rise over the ambient of one model.
    @param problem A Problem.
    @param model fvm, fdm, solid3d, lumped or analytic.
    @param cell_mm Cell in mm.
    @param variant "program" or a dict of options of edge_patch.patched_edge (FVM, FDM and, for the Lumped model, gz_via).
    @param solid_rule None (the program's rule) or a name of solid_patch (area, tuned, disc_eta ...) for the 3D solid.
    @return float rise in K.
    """
    def run():
        """!
        @brief The run itself.
        @return float rise in K.
        """
        if model == "solid3d" and solid_rule is not None:
            with sp.patched(solid_rule):
                return pc.max_rise(problem, model, cell_mm)
        return pc.max_rise(problem, model, cell_mm)

    if variant == PROGRAM:
        return run()
    with ep.patched_edge(**variant):
        if model == "lumped":
            with ep.lumped_sees_gz_via():
                return run()
        return run()


def field(problem, cell_mm=1.0, variant=PROGRAM, model="fvm"):
    """!
    @brief Temperature of the top layer (degC) on the grid of a model, for the maps.
    @param problem A Problem.
    @param cell_mm Cell in mm.
    @param variant "program" or a dict of options of edge_patch.patched_edge.
    @param model fvm or fdm.
    @return numpy.ndarray (ny, nx) of the top-layer temperature.
    """
    from pcbthermal import SolverOptions, simulate

    def run():
        """!
        @brief The run itself.
        @return numpy.ndarray top layer.
        """
        return simulate(problem, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model].T[0].copy()

    if variant == PROGRAM:
        return run()
    with ep.patched_edge(**variant):
        return run()


def without_vias(problem):
    """!
    @brief A copy of a problem with no vias.
    @param problem A Problem.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.vias = []
    return q


def via_effect(problem, model="fvm", cell_mm=1.0, variant=PROGRAM, solid_rule=None):
    """!
    @brief E = T_max(no via) - T_max(via) for a model, cell and variant.
    @param problem A Problem with vias.
    @param model Model key.
    @param cell_mm Cell in mm.
    @param variant See `rise`.
    @param solid_rule See `rise`.
    @return float E in K.
    """
    return rise(without_vias(problem), model, cell_mm, PROGRAM, solid_rule) - rise(problem, model, cell_mm, variant, solid_rule)
