#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_impact.py
@brief Question 3, impact: what the floor max(program, E3) would change in the decisions of the test boards of the program (test_profiles) and of the example profile board, and the peak above the mean from E3 against the reference.

@details The floor is applied to the oscillation the program reports (profiles.decide, budget 1 K, FVM 4 mm cell as in the tests), for every heater of a full-copper
layer-1 source with a square wave. Run from the repository root with QT_QPA_PLATFORM=offscreen.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
import impedance as I                                                # noqa: E402
from pcbthermal import profiles                                      # noqa: E402
from pcbthermal.model import Problem, SquareWave, load_problem       # noqa: E402,F401


def stack_of(problem):
    """!
    @brief The stack of a problem as the independent solver's Stack (simple or equal-gap stack-up, copper thickness of layer 1).
    @param problem Problem.
    @return Stack.
    """
    b = problem.board
    m = b.materials
    return A.Stack(t_cu=float(np.asarray(b.copper_thickness)[0]), layers=b.layers, thickness=b.thickness, k_cu=m.k_copper, rho_cp_cu=m.rho_copper * m.cp_copper,
                   kz=m.k_fr4_through, kr=m.k_fr4_inplane, rho_cp_lam=m.rho_fr4 * m.cp_fr4)


def report(label, problem, cell):
    """!
    @brief Print program and floor oscillations of every heater with a repeating square wave.
    @param label Name of the case.
    @param problem Problem.
    @param cell Cell in mm.
    @return None.
    """
    resp = profiles.step_response_fvm(problem, cell)
    dec = profiles.decide(problem, resp, 1.0)
    st = stack_of(problem)
    for i, h in enumerate(problem.heaters):
        w = h.profile
        if not isinstance(w, SquareWave) or h.layer != 0:
            continue
        a = float(np.sqrt(h.area() / np.pi))
        sw = w.p_on - w.p_off
        e3 = sw * I.square_swing(st, w.period, w.duty, a, problem.board.h_top, problem.board.h_bottom)
        print(f"{label:28s} {h.name or i:8s} f={1 / w.period:8.2f} Hz duty={w.duty:.2f} swing {sw:6.2f} W: program {dec[i].oscillation:8.3f} K ({dec[i].regime}), E3 {e3:8.3f} K "
              f"-> floor {max(dec[i].oscillation, e3):8.3f} K")


def main():
    """!
    @brief Run the cases.
    @return None.
    """
    import test_profiles as tp
    for hz in (100.0, 1000.0):
        report(f"example_with_profiles {hz:g} Hz", tp.example_with_profiles(hz), 2.0)
    p = Problem.new(60, 50, 2).add_full_copper()
    p.add_heater(1, 3.0, rect=(10, 20, 20, 30), name="fast", profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    p.add_heater(1, 1.0, rect=(35, 20, 45, 30), name="slow", profile=SquareWave(p_on=4.0, period=2.0, duty=0.25))
    report("mixed regimes (test)", p, 4.0)
    q = load_problem(os.path.join(ROOT, "examples", "profile_board.pcbt.json"))
    report("examples/profile_board", q, 2.0)
    # Peak above the mean from the harmonic sum against the reference, 10 mm part, 20 Hz, 30 %
    st = A.Stack(layers=2)
    a = A.part_radius(10e-3)
    ref = A.Reference(st, a, A.rectangle_radius(60e-3, 40e-3), 10, 10)
    mx, mn = ref.square_wave(1 / 20.0, 0.3, "center")
    mean = 0.3 * ref.rth["center"]
    print(f"20 Hz, 30 %: reference peak above the mean {mx - mean:.4f} K/W, valley {mn - mean:.4f}; swing {mx - mn:.4f}")


if __name__ == "__main__":
    main()
