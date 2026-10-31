#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient.py
@brief The thermal capacity of the extra nodes: the step response of the FVM (and the FDM) with the construction against the program and against a resolved 3D step response.
@details Question answered: the extra nodes hold the laminate that the copper nodes gave up (rho c times the thickness they hold, lib/gapnet.py). Is the step response right? Checks: (1) the total
         heat capacity of the network is the program's (identity, printed as a ratio); (2) the step response of the hottest point at the times of the program's transient grid against the resolved
         3D step response (ref3d.transient_spec, Crank-Nicolson, 4 sub-steps per interval) for a two-layer 1.6 mm board with a 10 mm pad on a bare bottom, a one-layer board with a 10 mm pad and a
         four-layer typical board with a 6 mm window; the program, the FVM with the rule and the FDM with the rule; (3) the time to 63 % of the steady peak of every curve and its error. The 3D
         transient uses the top-slab centre node, the layered ones their top copper node (both without the face term, which is the steady offset of the step response). The response is that of a
         step of the power at t = 0 from the board at rest; the profile runner uses the same matrices (fvm.transient_from_network), so it is covered by the same numbers.
         Output: out/transient.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_transient.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np

import boards as BD
import fdmnet as FN
import gapnet as GN
import ref3d as R3
import report as RP
import rule as RU
from pcbthermal import fvm


def t63(times, y):
    """!
    @brief Time at which a rising curve first reaches 63.2 % of its final value (linear interpolation).
    @param times Increasing times in s.
    @param y Curve.
    @return float in s.
    """
    y = np.asarray(y, dtype=float)
    return float(np.interp(0.632 * y[-1], y, times))


def main():
    """!
    @brief Run the three boards.
    @return None.
    """
    specs = [BD.Spec("2L 1.6 pad 10 bare bottom", layers=2, shapes=[("pad", 10), ("none",)]), BD.Spec("1L pad 10", layers=1, shapes=[("pad", 10)]),
             BD.Spec("4L typical window 6", layers=4, stack="template", shapes=[("window", 6)] + [("full",)] * 3)]
    rows, curves = [], {}
    for s in specs:
        p = BD.problem(s)
        amb = p.board.ambient
        prog_net = GN.build(p, 0.5, RU.PRESETS["program"])
        rule = RU.Rule()
        net = GN.build(p, 0.5, rule)
        prog = fvm.transient_from_network(prog_net, 0.0, 600.0, n_out=30, theta_scheme=0.5)
        new = fvm.transient_from_network(net, 0.0, 600.0, n_out=30, theta_scheme=0.5)
        times = prog.times[1:]
        pick = np.linspace(0, len(times) - 1, 12).astype(int)
        ref = R3.transient_spec(s, p, 0.25, 8, [float(times[i]) for i in pick])
        fd = FN.build(p, 0.5, rule)
        fd_tr = fvm.transient_from_network(fd, 0.0, 600.0, n_out=30, theta_scheme=0.5, grid="nodes")
        sel = lambda r: np.array([r.t_max[1:][i] for i in pick])                               # noqa: E731
        ct = {"program": sel(prog), "fvm rule": sel(new), "fdm rule": sel(fd_tr), "ref3d": np.array(ref["peak"])}
        cap_ratio = float(net.C.sum() / prog_net.C.sum())
        row = {"board": s.name, "capacity ratio": (".6f", cap_ratio)}
        for k in ("program", "fvm rule", "fdm rule"):
            row[k + " max |e| %"] = float(np.max(100 * np.abs(ct[k] / ct["ref3d"] - 1)))
            row[k + " t63 %"] = 100 * (t63(times[pick], ct[k]) / t63(times[pick], ct["ref3d"]) - 1)
        row["steady ratio fvm rule / ref3d (late)"] = (".4f", float(ct["fvm rule"][-1] / ct["ref3d"][-1]))
        rows.append(row)
        curves[s.name] = {"t": [float(times[i]) for i in pick], **{k: v.tolist() for k, v in ct.items()}}
        del amb
    RP.table(rows, list(rows[0]), title="Step response against the resolved 3D transient (percent; capacity ratio of the network to the program's)")
    RP.save("transient", {"rows": rows, "curves": curves})


if __name__ == "__main__":
    main()
