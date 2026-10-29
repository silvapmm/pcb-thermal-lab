#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plate2d.py
@brief The finite-height plate by the full 2D problem: average Nusselt number at Ra = 1e4 ... 1e7 against the levels, with grid and domain-size checks and the energy balance.

@details Uses `lib/plate2d.py` (independent of the program). For each Rayleigh number and Pr = 0.71 it runs the base grid (90 x 80 cells in the half plane, 3 L wide, 1.5 L below and 3 L above
         the plate), a coarser grid (60 x 50) and a larger domain (6 L wide, 3 L below, 6 L above), prints the mean Nusselt number, the number of pseudo-time steps, the energy
         balance (heat out of the domain / heat out of the plate) and the ratios to each level. Results go to out/plate2d.json. It takes some 20 to 40 minutes: run it in the background.

Usage: .venv/bin/python research/plate-h-level/scripts/study_plate2d.py [quick]     ("quick": Ra 1e4 and 1e5, the coarse grid only)
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                        # noqa: E402
import plate2d as p2                                      # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
PR = 0.71
COARSE = dict(nx=60, ny_plate=50, ny_below=20, ny_above=30)
BASE = dict(nx=90, ny_plate=80, ny_below=30, ny_above=45, dx0=1e-3, dy_end=1.5e-3)
WIDE = dict(nx=90, ny_plate=80, ny_below=30, ny_above=45, dx0=1e-3, dy_end=1.5e-3, width=6.0, below=3.0, above=6.0)


def one(ra, cfg, name):
    """!
    @brief Run one configuration to the steady state.
    @param ra Rayleigh number.
    @param cfg Keyword arguments of Plate2D.
    @param name Label of the configuration.
    @return dict with the results.
    """
    t = time.time()
    m = p2.Plate2D(ra, PR, **cfg)
    # time step: the wall coupling limit 3 dx0^2 and the convective CFL limit with the buoyant velocity scale 0.3 sqrt(Pr Ra) (Ostrach: 0.275 sqrt(Pr Ra y))
    dt = min(3.0 * m.x[1] ** 2, 0.35 * min(m.x[1], m.y[m.j0 + 1] - m.y[m.j0]) / (0.3 * (PR * ra) ** 0.5))
    r = m.run(dt=dt, max_steps=600000, check=5000, tol=2e-5)
    out = {"ra": ra, "config": name, "nu": r["nu"], "steps": r["steps"], "converged": r["converged"], "energy_balance": m.energy_balance(), "seconds": time.time() - t}
    out.update({k: r["nu"] / float(L.nu_level(k, ra, PR)) for k in ("general", "laminar", "bl", "bl_le", "mcadams")})
    print(f"Ra {ra:.0e} {name:6s} Nu {r['nu']:.4f} steps {r['steps']} conv {r['converged']} balance {out['energy_balance']:.3f} | /general {out['general']:.3f} /laminar {out['laminar']:.3f} "
          f"/exactBL {out['bl']:.3f} /BL+0.68 {out['bl_le']:.3f} /0.59 {out['mcadams']:.3f}  ({out['seconds']:.0f} s)", flush=True)
    return out


def main():
    """!
    @brief Run the cases and write out/plate2d.json.
    @return None.
    """
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    rows = []
    cases = [(1e4, "coarse", COARSE), (1e5, "coarse", COARSE)] if quick else [
        (1e4, "coarse", COARSE), (1e4, "base", BASE), (1e4, "wide", WIDE),
        (1e5, "coarse", COARSE), (1e5, "base", BASE), (1e5, "wide", WIDE), (1e6, "coarse", COARSE), (1e6, "base", BASE), (3e6, "base", BASE), (1e7, "coarse", COARSE), (1e7, "base", BASE), (3e7, "base", BASE)]
    # The cases are independent: one process each (4 at a time)
    import multiprocessing as mp
    with mp.Pool(4) as pool:
        rows = pool.starmap(one, [(ra, cfg, name) for ra, name, cfg in cases])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "plate2d.json"), "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
