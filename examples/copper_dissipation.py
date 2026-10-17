"""!
@file copper_dissipation.py
@brief Does the outer copper dissipate and spread heat like a heatsink? Pad-size sweep and copper versus heatsink, in every model and the 3D solid.

@details Run with `--fem` to add the independent 3D solid (needs scikit-fem). Output: Markdown tables used in docs/validation.md section 3.1.
"""

import sys

import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pcbthermal import Problem, analytic, fdm, fvm, lumped, solid3d

FEM = "--fem" in sys.argv


def board(pad_mm=None, h_extra=0.0, block=False):
    """!
    @brief 100 x 80 mm, 2 layers, 5 W on a 10 x 10 mm heater on top, optional square copper pad on top and a heatsink on the same area.
    @param pad_mm Side of the top copper pad centred on the heater in mm (None for no copper at all).
    @param h_extra Extra coefficient of a heatsink over the pad area in W/m2K (0 for none).
    @param block True to make the heatsink a 3 mm aluminium block (needs a bottom pad, added automatically).
    @return Problem.
    """
    p = Problem.new(100, 80, 2)
    if pad_mm:
        c = (50 - pad_mm / 2, 40 - pad_mm / 2, 50 + pad_mm / 2, 40 + pad_mm / 2)
        p.add_zone(1, rect=c)
    else:
        p.add_zone(1, rect=(45, 35, 55, 45))                     # Just the heater's own pad: every case needs some copper under it
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    if h_extra > 0 and pad_mm:
        p.add_heatsink(1, h_extra, rect=c)
    return p


def run(p, cell=1.0):
    """!
    @brief Maximum temperature in every model.
    @param p Problem.
    @param cell Cell size in mm.
    @return Dict model -> Tmax in degC (plus "fem" when --fem is given).
    """
    out = {"fvm": fvm.solve_steady(p, cell).t_max, "fdm": fdm.solve_steady(p, cell).t_max,
           "solid3d": solid3d.solve_steady(p, cell).t_max, "lumped": lumped.solve_steady(p, cell).t_max,
           "analytic": analytic.solve_steady(p, cell).t_max}
    if FEM:
        sys.path.insert(0, "examples")
        import fem3d_validation as f3
        out["fem"] = f3.solve_fem(p, 1.0)["t_max"]
    return out


def face_split(p, cell=1.0):
    """!
    @brief Heat leaving the top face over the pad area and elsewhere (FVM).
    @param p Problem.
    @param cell Cell size in mm.
    @return (watts over the copper pad, watts over the rest of the top face).
    """
    r = fvm.solve_steady(p, cell)
    b = p.board
    z = p.zones[0]
    x0, y0 = z.polygon.min(axis=0)
    x1, y1 = z.polygon.max(axis=0)
    xs = (np.arange(r.T.shape[2]) + 0.5) * r.dx
    ys = (np.arange(r.T.shape[1]) + 0.5) * r.dy
    inside = (ys[:, None] >= y0) & (ys[:, None] <= y1) & (xs[None, :] >= x0) & (xs[None, :] <= x1)
    h = np.full(r.T[0].shape, b.h_top)
    for hs in p.heatsinks:                                       # A heatsink adds its extra coefficient inside its polygon
        a0, c0 = hs.polygon.min(axis=0)
        a1, c1 = hs.polygon.max(axis=0)
        h += hs.h_extra * ((ys[:, None] >= c0) & (ys[:, None] <= c1) & (xs[None, :] >= a0) & (xs[None, :] <= a1))
    q = h * (r.T[0] - b.ambient) * r.dx * r.dy
    return float(q[inside].sum()), float(q[~inside].sum())


if __name__ == "__main__":
    print("| Top pad | " + " | ".join(["FVM", "FDM", "3D solid (FV)", "Lumped", "Analytic"] + (["3D FEM"] if FEM else [])) + " |")
    print("| :-- |" + " --: |" * (5 + FEM))
    for pad in (None, 20, 30, 40, 60, 80):
        res = run(board(pad))
        print(f"| {'heater pad only (10 mm)' if pad is None else f'{pad} mm square'} | " + " | ".join(f"{v:.1f}" for v in res.values()) + " |", flush=True)
    print()
    print("| Case | " + " | ".join(["FVM", "FDM", "3D solid (FV)"] + (["3D FEM"] if FEM else [])) + " | Heat over the pad [W] | Heat elsewhere [W] |")
    print("| :-- |" + " --: |" * (5 + FEM))
    bare = board(None)
    bare.add_heatsink(1, 30.0, rect=(30, 20, 70, 60))            # A heatsink on bare laminate: the extra coefficient only, no copper to spread in
    for name, p in (("40 mm copper pad", board(40)), ("40 mm pad + heatsink 30 W/m2K", board(40, 30.0)),
                    ("40 mm pad + heatsink 100 W/m2K", board(40, 100.0)), ("heater pad only + heatsink 30 W/m2K (40 mm)", bare)):
        res = {k: v for k, v in run(p).items() if k in ("fvm", "fdm", "solid3d", "fem")}
        w_pad, w_rest = face_split(p)
        print(f"| {name} | " + " | ".join(f"{v:.1f}" for v in res.values()) + f" | {w_pad:.2f} | {w_rest:.2f} |", flush=True)
