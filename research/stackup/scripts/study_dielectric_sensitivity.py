"""!
@file study_dielectric_sensitivity.py
@brief Does "the dielectric conductivity and thickness move the temperature by about 1 %, the copper by 5 %" hold beyond the 4-layer board with vias, and does an independent solver agree?

@details The sensitivity table of `stackup_outline_study.py` (section 4.2 of the README) is measured on one board: 4 layers, full copper on every layer, nine vias
         under the part. This study repeats the same changes (dielectric conductivity through the thickness -30 / +30 %, every dielectric thickness -10 / +10 %,
         every copper thickness -15 / +15 %) on boards where the heat has to cross the dielectric: one layer with full copper, one layer with a 20 mm pad, two
         layers with full copper and no vias, four layers (the typical template) with full copper and no vias, and the study board with its vias.
         Each case is solved with the FVM of the program and, where the board has no vias, with the independent 3D finite-volume solver
         `research/effective-conductivity/lib/layered3d.py` (real slabs, no layered idealisation, no code of the program).
         Same physics on both sides: 60 x 40 mm, a 6 x 6 mm source of 3 W in the middle of the top face, 12 W/m2K on both faces including under the source,
         insulated edges, FR-4 isotropic (0.3 W/mK through and in the plane, so that the independent solver, isotropic per slab, models the same material),
         copper 385 W/mK, 1 mm cells.

Usage: .venv/bin/python research/stackup/scripts/study_dielectric_sensitivity.py   (from the repository root; about 1 minute)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "effective-conductivity", "lib"))

import numpy as np                                                    # noqa: E402

import layered3d                                                      # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate               # noqa: E402
from pcbthermal.model import Dielectric                               # noqa: E402

W, H, DX = 60e-3, 40e-3, 1e-3                                         # board and cell in m
SOURCE = (27e-3, 17e-3, 33e-3, 23e-3)                                 # the 6 x 6 mm source, edges on cell edges
P, HF, K_CU = 3.0, 12.0, 385.0                                        # W, W/m2K, W/mK
PAD = (20e-3, 10e-3, 40e-3, 30e-3)                                    # the 20 mm copper pad of the one-layer case

# Boards: (name, copper per layer in um, dielectric gaps in um (the laminate under the copper for one layer), full copper?, vias?)
BOARDS = [
    ("1 layer, full copper, 1.6 mm", [35.0], [1565.0], True, False),
    ("1 layer, 20 mm pad, 1.6 mm", [35.0], [1565.0], False, False),
    ("2 layers, full copper, no vias", [35.0, 35.0], [1530.0], True, False),
    ("4 layers (template), full copper, no vias", [35.0, 15.2, 15.2, 35.0], [210.4, 1065.0, 210.4], True, False),
    ("4 layers (template), full copper, 9 vias", [35.0, 15.2, 15.2, 35.0], [210.4, 1065.0, 210.4], True, True),
]
# Changes: (name, factor on k through, factor on dielectric thickness, factor on copper thickness)
CHANGES = [
    ("k -30 %", 0.7, 1.0, 1.0), ("k +30 %", 1.3, 1.0, 1.0),
    ("thickness -10 %", 1.0, 0.9, 1.0), ("thickness +10 %", 1.0, 1.1, 1.0),
    ("copper -15 %", 1.0, 1.0, 0.85), ("copper +15 %", 1.0, 1.0, 1.15),
]
K_FR4 = 0.3


def program(cu, gaps, full, vias, fk, ft, fc):
    """!
    @brief Rise of the hottest point with the FVM of the program.
    @param cu Copper thickness per layer in um.
    @param gaps Dielectric thickness per gap in um (for one layer: the laminate under the copper).
    @param full True for copper over the whole board on every layer, False for the 20 mm pad on layer 1.
    @param vias True for the nine vias of the study board under the source.
    @param fk Factor on the dielectric conductivity (through the thickness; the in-plane value follows, the material is isotropic).
    @param ft Factor on every dielectric thickness.
    @param fc Factor on every copper thickness.
    @return float Rise in K.
    """
    n = len(cu)
    c = [x * fc * 1e-6 for x in cu]
    k = K_FR4 * fk
    p = Problem.new(W * 1e3, H * 1e3, n, thickness_mm=1.6)
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", HF, HF, None
    p.board.materials.k_copper = K_CU
    p.board.materials.k_fr4_through = p.board.materials.k_fr4_inplane = k
    p.board.copper_thickness = c
    if n == 1:
        p.board.thickness = c[0] + gaps[0] * ft * 1e-6                # simple mode: the laminate is the slab minus the copper
    else:
        p.board.dielectrics = [Dielectric(g * ft * 1e-6, "FR-4 (standard)", k, k, 1850.0, 900.0) for g in gaps]
        p.board.thickness = p.board.total_thickness()
    for l in range(1, n + 1):
        p.add_zone(l, rect=(0, 0, W * 1e3, H * 1e3) if full else tuple(v * 1e3 for v in PAD))
        if not full:
            break
    p.add_heater(1, P, rect=tuple(v * 1e3 for v in SOURCE), name="U1")
    if vias:
        for x in (28, 30, 32):
            for y in (18, 20, 22):
                p.add_via(x, y, 0.3)
    return simulate(p, SolverOptions(models=("fvm",), cell_mm=DX * 1e3)).results["fvm"].t_max - p.board.ambient


def independent(cu, gaps, full, fk, ft, fc):
    """!
    @brief Rise of the hottest point of the top face with the independent 3D solver (real slabs).
    @param cu Copper thickness per layer in um.
    @param gaps Dielectric thickness per gap in um.
    @param full True for copper over the whole board, False for the 20 mm pad on the top layer only.
    @param fk Factor on the dielectric conductivity.
    @param ft Factor on every dielectric thickness.
    @param fc Factor on every copper thickness.
    @return float Rise in K.
    """
    nx, ny = int(round(W / DX)), int(round(H / DX))
    xs, ys = (np.arange(nx) + 0.5) * DX, (np.arange(ny) + 0.5) * DX
    pad = (xs[None, :] > PAD[0]) & (xs[None, :] < PAD[2]) & (ys[:, None] > PAD[1]) & (ys[:, None] < PAD[3])
    k_top = K_CU if full else np.where(pad, K_CU, K_FR4 * fk)           # the copper slab of a pad: copper on the pad, laminate elsewhere
    slabs = []
    for i, t in enumerate(cu):
        slabs.append((t * fc * 1e-6, k_top if i == 0 else K_CU, 1))
        if i < len(gaps):
            slabs.append((gaps[i] * ft * 1e-6, K_FR4 * fk, 4 if len(cu) > 1 else 8))
    r = layered3d.solve(DX, nx, ny, slabs, SOURCE, P, HF, HF, film_under_source=True)
    return float(r["T"][0].max())


def main():
    """!
    @brief Print the rise of every board and the change of each stack-up number, program against the independent solver.
    @return None.
    """
    print("Change in the rise of the hottest point [%]: program FVM / independent 3D solver (no independent value for the board with vias)")
    print("| Board | Base rise [K] | " + " | ".join(c[0] for c in CHANGES) + " |")
    print("| :-- | --: | " + " | ".join("--:" for _ in CHANGES) + " |")
    for name, cu, gaps, full, vias in BOARDS:
        b = program(cu, gaps, full, vias, 1, 1, 1)
        bi = None if vias else independent(cu, gaps, full, 1, 1, 1)
        cells = []
        for _, fk, ft, fc in CHANGES:
            r = 100 * (program(cu, gaps, full, vias, fk, ft, fc) / b - 1)
            if bi is None:
                cells.append(f"{r:+.1f}")
            else:
                ri = 100 * (independent(cu, gaps, full, fk, ft, fc) / bi - 1)
                cells.append(f"{r:+.1f} / {ri:+.1f}")
        base = f"{b:.1f}" if bi is None else f"{b:.1f} / {bi:.1f}"
        print(f"| {name} | {base} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
