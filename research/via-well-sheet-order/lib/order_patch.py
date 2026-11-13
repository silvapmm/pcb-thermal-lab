#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file order_patch.py
@brief In-memory copy of the via-well order: the wells of the FVM (and FDM) read the sheet conductance AFTER the laminate rule instead of before it (the program is not edited).
@details `fvm.Network.__init__` calls `viawell.build(problem, d, S, ...)` with the sheet of the copper nodes BEFORE `laminate.build` moves the laminate of the interior nodes out of
         them. `after()` wraps `viawell.build` so that the first call is kept (the list of blocks and the array `gz_via` are held by the network by reference) and wraps
         `laminate.build` so that, once the result has the reduced sheet, the real `viawell.build` is called again with that sheet and the two objects are refilled in place. Outside
         `after()` nothing is patched (today's program). A network whose rule does not run keeps the first call.
"""

import contextlib

from pcbthermal import laminate, viawell

LAST = []             # reduced sheet of the last laminate.build call that found no via call waiting (the FDM builds the rule BEFORE the wells)
PENDING = []          # (arguments, blocks, gz_via) of the viawell.build calls that wait for the reduced sheet


@contextlib.contextmanager
def after():
    """!
    @brief Context in which the via wells read the sheet conductance after the laminate rule.
    @return Context manager.
    """
    real_via, real_lam = viawell.build, laminate.build
    PENDING.clear()
    LAST.clear()

    def via_build(problem, d, S, cover, dx, dy, nx, ny, origin, active, *a, **k):
        if LAST:                                    # FDM order: the rule has run already, the wells take its reduced sheet at once
            S = LAST.pop()
            return real_via(problem, d, S, cover, dx, dy, nx, ny, origin, active, *a, **k)
        # FVM order, first call with the sheet before the rule: the result is kept and refilled when the rule has run
        blocks, gz_via = real_via(problem, d, S, cover, dx, dy, nx, ny, origin, active, *a, **k)
        PENDING.append(((problem, d, cover, dx, dy, nx, ny, origin, active, a, k), blocks, gz_via))
        return blocks, gz_via

    def lam_build(board, fill, cell, cover, active, edge, S, *args, **kw):
        res = real_lam(board, fill, cell, cover, active, edge, S, *args, **kw)
        L = board.layers
        if not PENDING:
            LAST[:] = [res.S[:L]]
        while PENDING:
            (problem, d, cov, dx, dy, nx, ny, origin, act, a, k), blocks, gz_via = PENDING.pop()
            nb, ng = real_via(problem, d, res.S[:L], cov, dx, dy, nx, ny, origin, act, *a, **k)
            blocks[:] = nb
            gz_via[...] = ng
        return res

    viawell.build, laminate.build = via_build, lam_build
    try:
        yield
    finally:
        viawell.build, laminate.build = real_via, real_lam
        PENDING.clear()
