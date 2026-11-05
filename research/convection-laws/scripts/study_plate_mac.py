#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plate_mac.py
@brief Nusselt number of the two faces of a thin hot horizontal strip (half width 1 = A/P) with the new primitive-variable solver, in cold closed boxes of increasing size, Ra = 3e2 to 1e4, Pr 0.71.
@details The plate (zero thickness, T = 1, no slip) lies on y = 0 for x <= 1 of the half domain x >= 0 (symmetry line at x = 0); the box walls are cold (T = 0, no slip).
         The box is the unavoidable difference with the open domain of research/horizontal-plate-h (free inflow, outflow at the top): the cold walls add cooling, so the Nu
         read in a box of size s are an UPPER trend that falls towards the open value as s grows; the sweep over s and the comparison with the open-domain numbers of the other
         solver (README of horizontal-plate-h, section 5, strip, both faces hot: Ra 1e3 up 1.412 down 2.296; Ra 1e4 up 2.075 down 3.501; reproduced here only as printed) show
         what can be concluded. Checks per case: heat leaving the plate against heat reaching the cold walls (energy balance), and the resolution (the base grid and a finer one).
         Output: out/plate_mac.json and a printed table.
Usage: .venv/bin/python research/convection-laws/scripts/study_plate_mac.py [--quick|--both|--isolated]   (about an hour in one process; --quick: Ra 1e3 only, base grid; --both and --isolated split the sweep in two processes, the second writes out/plate_mac_isolated.json)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import mac2d  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def build(ra, s=1.0, fine=1.0, w=4.0, hu=6.0, hd=3.0, faces="both"):
    """!
    @brief The half domain of the strip in a cold box of size s times (w, hu, hd).
    @param ra Rayleigh number of the half width.
    @param s Box scale.
    @param fine Resolution factor (1 = base grid).
    @param w Box half width at s = 1 (the plate half width is 1).
    @param hu Box height above the plate at s = 1.
    @param hd Box depth below the plate at s = 1.
    @param faces "both", "up" or "down": the faces that are hot (the other one is insulated).
    @return mac2d.Box.
    """
    n = lambda k: max(4, int(round(k * fine)))
    xf = mac2d.graded([(1.0, n(36), 0.96), (w * s - 1.0, n(20 + 10 * s), 1.08)])
    yf_below = mac2d.graded([(hd * s, n(24 + 10 * s), 0.94)])
    yf_above = mac2d.graded([(hu * s, n(30 + 12 * s), 1.06)])
    yf = np.concatenate([yf_below - hd * s, yf_above[1:]])
    yf[len(yf_below) - 1] = 0.0
    return mac2d.Box(xf, yf, ra, west=("sym", None), east=("wall", 0.0), south=("wall", 0.0), north=("wall", 0.0), plate=(1.0, 1.0), faces=faces)


def run_case(ra, s, fine=1.0, faces="both"):
    """!
    @brief Solve one case.
    @param ra Rayleigh number.
    @param s Box scale.
    @param fine Resolution factor.
    @param faces Hot faces ("both", "up", "down").
    @return dict with Nu_up, Nu_down, the heat balance and the run data.
    """
    box = build(ra, s, fine, faces=faces)
    t0 = time.time()
    steps = box.run(t_end=80.0, tol=1e-6)
    nu_u, nu_d, qu, qd = box.plate_nusselt()
    nu_u, nu_d = (nu_u if faces != "down" else 0.0), (nu_d if faces != "up" else 0.0)
    plate_heat = nu_u + nu_d                                   # per unit half width, both faces
    walls = box.heat_into_walls()
    # the heat into the walls is per unit length along each side, west and the symmetry line carry none
    return {"faces": faces, "ra": ra, "s": s, "fine": fine, "nu_up": nu_u, "nu_down": nu_d, "plate_heat": plate_heat, "wall_heat": sum(walls.values()), "balance": sum(walls.values()) / plate_heat,
            "converged": bool(box.converged), "steps": steps, "t": box.t, "umax": float(np.abs(box.u).max()), "vmax": float(np.abs(box.v).max()), "seconds": time.time() - t0,
            "nx": box.nx, "ny": box.ny, "q_up_centre": float(qu[0]), "q_up_tip": float(qu[-1]), "q_down_centre": float(qd[0]), "q_down_tip": float(qd[-1])}


def main():
    """!
    @brief Run the sweep and print it.
    @return None.
    """
    quick = "--quick" in sys.argv
    # (Ra, box scale, resolution factor): the base grid at s = 1 for the four Ra, a finer grid and a box twice as large at the Ra where the open-domain solver has numbers
    cases = [(1e3, 1.0, 1.0, "both")] if quick else [(3e2, 1.0, 1.0, "both"), (1e3, 1.0, 1.0, "both"), (3e3, 1.0, 1.0, "both"), (1e4, 1.0, 1.0, "both"), (1e3, 1.0, 1.4, "both"), (1e3, 2.0, 1.0, "both"), (1e4, 2.0, 1.0, "both"),
                                                      (1e3, 1.0, 1.0, "up"), (1e3, 1.0, 1.0, "down"), (1e4, 1.0, 1.0, "up"), (1e4, 1.0, 1.0, "down")]
    out_name = "plate_mac.json"
    if "--isolated" in sys.argv:                                    # the four isolated-face cases alone, in a second process, to a file of their own
        cases = [c for c in cases if c[3] != "both"]
        out_name = "plate_mac_isolated.json"
    elif "--both" in sys.argv:                                      # the cases with both faces hot alone
        cases = [c for c in cases if c[3] == "both"]
    rows = []
    print("Ra     s  fine  faces  nx x ny   Nu_up   Nu_down  balance  conv   umax   steps  seconds")
    os.makedirs(OUT, exist_ok=True)
    for ra, s, fine, faces in cases:
        r = run_case(ra, s, fine, faces)
        rows.append(r)
        print(f"{ra:6.0e} {s:3.1f} {fine:4.1f} {faces:5s} {r['nx']:3d}x{r['ny']:3d}  {r['nu_up']:.3f}   {r['nu_down']:.3f}   {r['balance']:.3f}   {r['converged']!s:5} {r['umax']:6.1f} {r['steps']:6d}  {r['seconds']:.0f}", flush=True)
        with open(os.path.join(OUT, out_name), "w") as fh:           # saved after every case: the sweep is long
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
