#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fdm.py
@brief The FDM with the construction (never studied): the program's node-centred FDM against the same FDM with the laminate nodes, against the resolved reference, on the simple boards.
@details Question answered: does the construction of lib/rule.py, applied to the node-centred finite differences (half control volumes on the border of the board, arithmetic mean of the
         nodal conductivities, the closed border of the refined zone of lib/fdmnet.py), remove the shortfall of the FDM over a bare window or a pad as it does for the FVM? The FDM was 3 to 9
         points worse than the FVM over a bare window and -7 to -16 % on pads with a bare bottom (gap-subdivision, bare-spot-under-source). Boards: windows and pads of the simple set on two
         layers (0.8 and 1.6 mm), the typical 4 and 6 layers, one-layer pad and window; grids of 1 and 0.5 mm (the FDM node grid is the cell grid plus one). Printed: the error of the program's FDM,
         of the FDM with the rule, of the FVM with the rule, and the arithmetic-mean leak check (the heat balance of the FDM ladder). Output: out/fdm.json.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_fdm.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import fdmnet as FN
import gapnet as GN
import report as RP
import rule as RU
import runner as RN


def fdm_peak(spec, rule, cell, p):
    """!
    @brief Peak under the part in the FDM with a rule (the program's FDM for the preset "program"), and its heat balance.
    @param spec A boards.Spec.
    @param rule A rule.Rule.
    @param cell Grid spacing in mm.
    @param p The Problem.
    @return tuple (peak with the face term, balance heat out / power).
    """
    net = FN.build(p, cell, rule)
    th, _ = net.solve_steady()
    peak, _ = GN.peak_under_parts(net, th, p, rule)
    out = float(((net.g_amb - net.g_pin) * th).sum())
    return peak, out / net.Q.sum()


def main():
    """!
    @brief Run the boards.
    @return None.
    """
    specs = [s for s in BD.simple_set() if ("window 6" in s.name or "pad 10" in s.name) and "uniform" not in s.name and ("1.6" in s.name or "typical" in s.name or "0.8" in s.name or s.name.startswith("1L"))]
    rows = []
    for cell in (1.0, 0.5):
        for s in specs:
            p = BD.problem(s)
            ref = RN.reference(s)["max"]
            e0, _ = fdm_peak(s, RU.PRESETS["program"], cell, p)
            e1, bal = fdm_peak(s, RU.Rule(), cell, p)
            f1 = RN.fvm_peak(s, RU.Rule(), cell, p)["peak"]
            f0 = RN.fvm_peak(s, RU.PRESETS["program"], cell, p)["peak"]
            rows.append({"board": s.name, "cell": cell, "FDM program": RN.err(e0, ref), "FDM rule": RN.err(e1, ref), "FVM program": RN.err(f0, ref), "FVM rule": RN.err(f1, ref),
                         "FDM balance": (".9f", bal)})
    RP.table(rows, list(rows[0]), title="FDM with the construction: error of the peak against the resolved face value, percent")
    RP.save("fdm", rows)


if __name__ == "__main__":
    main()
