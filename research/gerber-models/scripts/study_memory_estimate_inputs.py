#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_memory_estimate_inputs.py
@brief Why did the memory guard estimate 9.7 GB for the 3D solid fine run of README 4.34/4.35 on one tree and 10.6 GB on another? Print the inputs of `memory.check` for the same problem under different states of the process.
@details `memory.estimate_bytes` is `base + law(unknowns, cells) * safety`, and `base` is the resident size of the calculating process (`memory.resident_bytes()`) plus the imported masks
         (`copper_run_bytes`). The unknown count and the law are fixed by the problem; the base is not. This script builds the rectangle board of 4.35 (two copper layers, 0.1 mm), calls `memory.check`
         for the 3D solid twice in a fresh process (same inputs, same output expected), then again after the process has grown (a ballast array of 0.5 and 1.0 GB touched, then freed) and with the base given
         explicitly, and prints unknowns, base, law part and estimate each time. Nothing is solved. Run: .venv-research/bin/python research/gerber-models/scripts/study_memory_estimate_inputs.py (from the repository root; seconds).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import numpy as np

from pcbthermal import Problem, memory

import conduction as cd
import rect_board as rb


def make(layers):
    """!
    @brief The rectangle board with its zones and heater, as study_models_rect_board.py builds the truth problem.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(width_mm=rb.W, height_mm=rb.H, layers=layers, thickness_mm=cd.T_LAM * 1000.0, copper_um=cd.T_CU * 1e6, h_top=cd.H_FACE, h_bottom=cd.H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=rb.heater(0.0))
    for r in rb.rects(0.0):
        p.add_zone(1, rect=r, fill=1.0)
    return p


def show(label, p, model, base=None):
    """!
    @brief Print the guard's inputs and estimate for one call.
    @param label Text for the line.
    @param p Problem.
    @param model Model key.
    @param base Resident bytes to use (None: the process's own).
    @return float Estimate in GB.
    """
    v = memory.check(p, (model,), 0.1, fraction=0.60, refuse="return", base=base)[0]
    b = (memory.resident_bytes() if base is None else base) + memory.copper_run_bytes(p)
    print(f"{label:46s} {model:8s} unknowns {v.unknowns:8d}  base {b / 1e9:5.2f} GB  law part {(v.estimate - b) / 1e9:5.2f} GB  estimate {v.estimate / 1e9:5.2f} GB  limit {v.limit / 1e9:5.2f} GB  {v.verdict}")
    return v.estimate / 1e9


def main():
    """!
    @brief Run the comparison.
    @return None.
    """
    for layers in (2, 1):
        p = make(layers)
        print(f"\n--- rectangle board, {layers} copper layer(s), 0.1 mm cells ---")
        for model in ("solid3d", "fvm", "fdm"):
            a = show("fresh process, first call", p, model)
            b = show("fresh process, second call (same inputs)", p, model)
            assert abs(a - b) < 0.1, "same inputs must give the same estimate (the process base drifts by some MB between two calls)"
        for gb in (0.5, 1.0):
            ballast = np.ones(int(gb * 1e9 / 8))                       # touched pages count in the resident size
            for model in ("solid3d", "fvm"):
                show(f"process holding a {gb} GB array", p, model)
            del ballast
        show("base given explicitly 0.11 GB", p, "solid3d", base=0.11e9)
        show("base given explicitly 1.00 GB", p, "solid3d", base=1.0e9)


if __name__ == "__main__":
    main()
