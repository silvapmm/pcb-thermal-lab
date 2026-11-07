#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_down_laws.py
@brief How far is each published law of the face turned down from the program's 0.27 Ra^(1/4), over Ra 1e2 to 1e9 and over the boards (A/P 5 to 100 mm, dT 5 to 80 K)?
@details No solver: the laws of lib/down_laws.py at Pr 0.71 and the program's air properties. Prints (1) Nu of each law and its ratio to the program over Ra, (2) the spread of
         the published levels, (3) h of the face down for a grid of boards. Writes out/down_laws.json (read by make_figures.py).
Usage: .venv/bin/python research/face-down-convection/scripts/study_down_laws.py   (about a second)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import down_laws as D  # noqa: E402
from pcbthermal import convection  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RA = [1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 1e7, 1e8, 1e9]


def h_down(law, ap_mm, dt, t_amb=25.0):
    """!
    @brief Coefficient of the face turned down for a board of A/P and excess dT with one law.
    @param law Nu(Ra) function.
    @param ap_mm Characteristic length A/P in mm.
    @param dt Excess of the face over the air in K.
    @param t_amb Ambient in degC.
    @return (h in W/m2K, Ra).
    """
    props = convection.air_properties(t_amb + 0.5 * dt)
    ra = convection.rayleigh(dt, ap_mm * 1e-3, props)
    return float(law(ra)) * props["k"] / (ap_mm * 1e-3), ra


def main():
    """!
    @brief Print the tables and write the data of the figures.
    @return None.
    """
    names = list(D.DOWN)
    print("Nu of each law (ratio to the program in brackets)")
    print("Ra".rjust(8) + "".join(n[:22].rjust(26) for n in names))
    data = {"ra": RA, "nu": {n: [] for n in names}}
    for ra in RA:
        base = float(D.DOWN[names[0]](ra))
        cells = []
        for n in names:
            v = float(D.DOWN[n](ra))
            data["nu"][n].append(v)
            cells.append(f"{v:7.3f} ({v / base:4.2f})".rjust(26))
        print(f"{ra:8.0e}" + "".join(cells))
    print("\nBoards: h of the face down in W/m2K, convection only, 25 degC ambient")
    print("A/P mm  dT    Ra       program  Incropera GLmean  VDI    ratio Inc/prog")
    rows = []
    for ap in (5, 10, 15, 22.2, 30.8, 50, 100):
        for dt in (5, 20, 80):
            hp, ra = h_down(D.program_down, ap, dt)
            hi, _ = h_down(D.incropera7, ap, dt)
            hg, _ = h_down(D.gl_mean, ap, dt)
            hv, _ = h_down(D.vdi, ap, dt)
            rows.append({"ap": ap, "dt": dt, "ra": ra, "program": hp, "incropera": hi, "gl": hg, "vdi": hv})
            print(f"{ap:6.1f} {dt:4d} {ra:9.2e} {hp:8.2f} {hi:8.2f} {hg:8.2f} {hv:8.2f}   {hi / hp:5.2f}")
    data["boards"] = rows
    ras = np.array([r["ra"] for r in rows])
    inc = np.array([r["incropera"] / r["program"] for r in rows])
    print(f"\nRa of the boards {ras.min():.1e} to {ras.max():.1e}; Incropera / program {inc.min():.2f} to {inc.max():.2f}")
    # Spread of the 1/5 laws among themselves (the part of the uncertainty that stays whatever is chosen)
    fifth = ["Incropera 0.52 Ra^1/5 (M)", "Goldstein-Lau mean 0.475", "VDI 0.6 (Ra f1)^1/5 (S)"]
    for ra in (1e3, 1e4, 1e5):
        v = [float(D.DOWN[n](ra)) for n in fifth]
        print(f"Ra {ra:.0e}: spread of the three 1/5 laws {100 * (max(v) / min(v) - 1):.1f} %, mean {np.mean(v):.3f}")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "down_laws.json"), "w") as fh:
        json.dump(data, fh, indent=1)


if __name__ == "__main__":
    main()
