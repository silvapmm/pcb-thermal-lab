#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plate_h2d.py
@brief The horizontal plate by the full 2D (strip) and axisymmetric (disc) problem: Nu of the upper and the lower face at Ra = 1e2 ... 1e5 of L = A/P, with the face heated alone and with both faces hot, grid and domain checks, energy balance.

@details Uses `lib/plate_h2d.py` (independent of the program). Each case is marched to the steady state (Pr = 0.71) in a half domain (flow symmetric about the axis; the plume of
         the upper face is unstable in reality at the higher Ra, see the README). Cases:

         * strip (planar, L = a = half width = A/P of a long board): Ra = 1e3, 1e4, 1e5; "both" (the thin free board with both faces at Tw), "up" (the lower face insulated: the
           isolated upper face of the measurements), "down" (the upper face insulated: the isolated lower face of Schulenberg's theory);
         * disc (axisymmetric, radius R, L = A/P = R/2): Ra_L = 1e2, 1e3, 1e4 (Ra_R = 8 Ra_L), the same three configurations;
         * grid and domain checks of the strip at Ra = 1e4 (finer grid, wider and taller domain).

         Prints the table and writes out/plate_h2d.json (numbers) and out/fields_*.npz (the fields of selected runs, read by make_figures.py).
         Nu is always reported for L = A/P: strip Nu = Nu_a, disc Nu_L = Nu_R / 2.

Usage: .venv/bin/python research/horizontal-plate-h/scripts/study_plate_h2d.py [quick|full]   ("quick": Ra 1e3 and 1e4 on the strip, 3 minutes; "full": about an hour, run it in the background)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import plate_h2d as ph                                    # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
PR = 0.71
BASE = dict(n_in=48, n_out=32, n_up=60, n_dn=44, dy0=5e-3, dx_tip=1e-2)
FINE = dict(n_in=70, n_out=48, n_up=90, n_dn=64, dy0=3e-3, dx_tip=6e-3)
WIDE = dict(n_in=48, n_out=32, n_up=60, n_dn=44, dy0=5e-3, dx_tip=1e-2, width=10.0, up=14.0, down=7.0)
FACES = {"both": dict(), "up": dict(hot_down=False), "down": dict(hot_up=False)}


def dt_for(ra):
    """!
    @brief Pseudo-time step from the Rayleigh number (the explicit convection limits it as the buoyant velocity grows).
    @param ra Rayleigh number of the unit length of the solver.
    @return float.
    """
    return float(min(5e-4, 3e-4 * np.sqrt(1e4 / ra)))


def one(geometry, ra_l, faces, grid, name, save=False):
    """!
    @brief Run one case to the steady state.
    @param geometry "strip" or "disc".
    @param ra_l Rayleigh number of L = A/P.
    @param faces Key of FACES.
    @param grid Keyword arguments of the grid (BASE, FINE or WIDE).
    @param name Label of the grid.
    @param save Write the fields to out/.
    @return dict with Nu of the two faces for L = A/P, convergence, balance and the local Nusselt numbers.
    """
    disc = geometry == "disc"
    ra_solver = 8.0 * ra_l if disc else ra_l                # the solver's unit length is R (disc) or a (strip)
    t = time.time()
    dt = dt_for(ra_solver)
    if ra_solver >= 5e4 and grid is BASE:                    # the central convection of the base grid is not stable at the highest Ra (blow-up at any step); a finer first cell was
        grid = dict(grid, dy0=4e-3)                          # (the label stays "base"; the first cell is recorded in the result)
    for attempt in range(3):                              # an explicit-convection blow-up is retried with half the step
        m = ph.HorizontalStrip(ra_solver, PR, axisym=disc, **grid, **FACES[faces])
        m.relax = 0.15
        r = m.run(max_steps=(400000 if ra_solver < 5e4 else 120000), check=2500, tol=2e-5, dt=dt)       # the highest Ra drift slowly: a fixed march of about 11 time units, averaged over the last window
        if np.isfinite(r["nu_up"]) and np.isfinite(r["nu_down"]):
            break
        print(f"   blow-up at dt = {dt:.1e}, retrying with half", flush=True)
        dt *= 0.5
    scale = 0.5 if disc else 1.0                            # Nu_L = Nu_R / 2 for the disc
    out = {"dy0": grid["dy0"], "dt": dt, "geometry": geometry, "ra_l": ra_l, "faces": faces, "grid": name, "nu_up": scale * r["nu_up"], "nu_down": scale * r["nu_down"], "converged": bool(r["converged"]),
           "steps": r["steps"], "amp_up": r["amp_up"], "amp_down": r["amp_down"], "balance": m.energy_balance(), "seconds": time.time() - t}
    x, nu_u, nu_d = m.nusselt_local()
    out["x"], out["local_up"], out["local_down"] = x.tolist(), (scale * nu_u).tolist(), (scale * nu_d).tolist()
    print(f"{geometry:5s} Ra_L {ra_l:8.0e} {faces:5s} {name:5s} Nu up {out['nu_up']:7.3f} down {out['nu_down']:7.3f} conv {out['converged']} steps {r['steps']} "
          f"balance {out['balance']:.3f} amp {r['amp_up']:.1e} {r['amp_down']:.1e}", flush=True)
    if save:
        os.makedirs(OUT, exist_ok=True)
        np.savez(os.path.join(OUT, f"fields_{geometry}_{ra_l:.0e}_{faces}.npz"), x=m.x, y=m.y, T=m.T, psi=m.psi, om=m.om, ip=m.ip, j0=m.j0, axisym=disc)
    return out


def main(mode="full"):
    """!
    @brief Run the cases and write out/plate_h2d.json.
    @param mode "quick" or "full".
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "plate_h2d.json")
    results = []
    if os.path.exists(path) and mode == "full":              # resume: the finished cases are kept
        with open(path) as f:
            results = [r for r in json.load(f) if np.isfinite(r["nu_up"]) and np.isfinite(r["nu_down"])]
    done = lambda g, ra, fc, gr: any(r["geometry"] == g and r["ra_l"] == ra and r["faces"] == fc and r["grid"] == gr for r in results)
    ras = (1e3, 1e4) if mode == "quick" else (1e3, 1e4, 1e5)
    for geometry in ("strip", "disc"):
        if mode == "quick" and geometry == "disc":
            continue
        for ra in (ras if geometry == "strip" else tuple(r / 10.0 for r in ras)):
            for faces in ("both", "up", "down"):
                if done(geometry, ra, faces, "base"):
                    continue
                results.append(one(geometry, ra, faces, BASE, "base", save=(faces == "both")))
                with open(os.path.join(OUT, "plate_h2d.json"), "w") as f:
                    json.dump(results, f)
    if mode == "full":
        for name, grid in (("fine", FINE), ("wide", WIDE)):
            for faces in ("both", "down"):
                if not done("strip", 1e4, faces, name):
                    results.append(one("strip", 1e4, faces, grid, name))
            with open(os.path.join(OUT, "plate_h2d.json"), "w") as f:
                json.dump(results, f)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
