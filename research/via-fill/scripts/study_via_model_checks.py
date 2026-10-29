"""!
@file study_via_model_checks.py
@brief Review checks of the via model behind the via-fill study: closed form of the barrel, every model per fill, the limits, the cell size, an independent solver.

@details Questions answered (README sections 4.4 to 4.8):
         1. Does the program put exactly the closed-form barrel conductance k_Cu A / d into its network (FVM, example board)?
         2. Do the five models agree on the effect of the fill, and how large is it against the two limits (no vias, perfectly conducting vias)?
         3. Does the gain of a copper fill depend on the cell size of the FVM (a via is a point feature in one cell)?
         4. Which cell size is right? A board with a 3 x 3 via array is solved by the program and by the independent finite-volume solver
            `research/solid3d-verification/lib/layered3d.py` with the barrels drawn at their real size (0.1 mm cells, area fractions per cell, quarter domain).
         5. How much of a copper-filled via the 3D solid keeps when its area is larger than one cell (the per-cell fraction is clipped at 1).
         6. What changes if the via diameter is read as the finished hole (plating inside the hole) instead of the drill (plating inside the drill).
         Runs one model at a time; part 4 solves the independent model at 0.1 and 1/12 mm cells (about 180 000 and 250 000 unknowns, up to about 3 GB, 3 to 5 minutes; a cell must
         divide 5.5 and 10.5 mm); `--fine` adds 0.0625 and 0.05 mm cells (about 450 000 and 700 000 unknowns, about 22 minutes in all on a 10-core machine while paging, a peak memory footprint of 22.5 GB on a 16 GB machine: run it alone).

Usage: python research/via-fill/scripts/study_via_model_checks.py [--fine]   (from the repository root; about 8 minutes without --fine)
"""

import argparse
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)                                                                     # the program
sys.path.insert(0, os.path.join(ROOT, "research", "solid3d-verification", "lib"))           # the independent solver

import layered3d                                                         # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate                  # noqa: E402
from pcbthermal import fvm                                               # noqa: E402
from pcbthermal import model as pmodel                                   # noqa: E402
from pcbthermal.examples import example_board                            # noqa: E402
from pcbthermal.geometry import cell_index_of_point                      # noqa: E402
from pcbthermal.model import VIA_FILLS, Materials, Via                   # noqa: E402

K_CU, PLATING = 385.0, 25e-6
# Via-array board of part 4 (mm): four full copper planes, a 10 x 10 mm source over a 3 x 3 array, insulated edges, strong bottom cooling so that the vias matter
W, T_MM, CU_MM, PITCH, D_MM, PL_MM = 21.0, 1.6, 0.035, 3.5, 0.3, 0.025
POWER, H_TOP, H_BOTTOM, K_FR4, K_AIR = 2.0, 10.0, 200.0, 0.3, 0.026
CENTRE = W / 2
VIAS = [(CENTRE + i * PITCH, CENTRE + j * PITCH) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def example_with(fill_k=0.0, no_vias=False, scale=None):
    """!
    @brief The example board with every via given one fill, or without vias, or with the via conductance multiplied.
    @param fill_k Conductivity of the fill in W/mK (0 = open barrel).
    @param no_vias True: remove the vias.
    @param scale Factor on the thermal area of every via (None = unchanged); a large factor gives the limit of perfectly conducting vias.
    @return Problem.
    """
    p = example_board()
    if no_vias:
        p.vias = []
    for v in p.vias:
        v.filled, v.fill_k = False, fill_k
        if scale:
            # Same thermal area times the factor: a copper fill (ratio 1) of a larger equivalent disc, done through the legacy flag
            area = v.thermal_area(p.board.via_plating, p.board.materials.k_copper) * scale
            v.filled, v.fill_k, v.diameter = True, 0.0, 2.0 * math.sqrt(area / math.pi)
    return p


def t_max(problem, models, cell):
    """!
    @brief Maximum temperature of every model.
    @param problem Problem.
    @param models Model keys.
    @param cell Cell size in mm.
    @return dict model -> maximum temperature in degC.
    """
    res = simulate(problem, SolverOptions(models=tuple(models), cell_mm=cell)).results
    return {m: res[m].t_max for m in models}


def part1_closed_form():
    """!
    @brief Compare the via conductance in the FVM network of the example board with k_Cu A / d of every gap.
    @return None.
    """
    print("## 1. Barrel conductance in the FVM network against the closed form (example board, 1 mm cells)\n")
    p = example_with(0.0)
    b = p.board
    nx, ny = int(round(b.width / 1e-3)), int(round(b.height / 1e-3))
    plain = example_with(no_vias=True)
    g_with = fvm.Network(p, nx, ny, assemble=False).gz
    g_without = fvm.Network(plain, nx, ny, assemble=False).gz
    v = p.vias[0]
    i, j = cell_index_of_point(v.x, v.y, nx, ny, b.width / nx, b.height / ny)
    gaps = b.gap_thicknesses()
    n_in_cell = sum(1 for u in p.vias if cell_index_of_point(u.x, u.y, nx, ny, b.width / nx, b.height / ny) == (i, j))
    a = v.thermal_area(b.via_plating, b.materials.k_copper)
    extra = (g_with - g_without)[:, i, j] / n_in_cell
    closed = b.materials.k_copper * a / gaps
    print(f"gaps {', '.join(f'{g * 1e3:.4f}' for g in gaps)} mm; via area {a * 1e6:.4f} mm2")
    print(f"network: {', '.join(f'{x:.5f}' for x in extra)} W/K per gap; closed form: {', '.join(f'{x:.5f}' for x in closed)} W/K")
    print(f"series resistance through the board: network {sum(1 / extra):.1f} K/W, closed form over the gaps {sum(gaps) / (b.materials.k_copper * a):.1f} K/W,"
          f" textbook over the full 1.6 mm {b.thickness / (b.materials.k_copper * a):.1f} K/W (the copper layers are plane copper in the model)\n")


def part2_models():
    """!
    @brief Maximum temperature of the example board for every fill and the two limits, every model, 0.5 mm and 1 mm cells.
    @return None.
    """
    print("## 2. Every model, every fill, and the two limits (example board; change against the open via in K)\n")
    cases = [(name, dict(fill_k=k)) for name, k, _ in VIA_FILLS] + [("no vias", dict(no_vias=True)), ("perfect vias (area x 10^4)", dict(scale=1e4))]
    for cell, models in ((0.5, ("fvm", "fdm", "lumped", "analytic")), (1.0, ("fvm", "fdm", "lumped", "analytic", "solid3d"))):
        print(f"Cells of {cell} mm:\n")
        print("| Case | " + " | ".join(models) + " |")
        print("| :-- |" + " --: |" * len(models))
        base = None
        for name, kw in cases:
            t = t_max(example_with(**kw), models, cell)
            base = base or t
            print(f"| {name} | " + " | ".join(f"{t[m]:.2f} ({t[m] - base[m]:+.2f})" for m in models) + " |", flush=True)
        print()


def part3_cell_sweep():
    """!
    @brief Gain of a copper fill on the example board against the FVM cell size.
    @return None.
    """
    print("## 3. FVM cell size and the gain of a copper fill (example board)\n")
    print("| Cell (mm) | open (°C) | copper fill (°C) | gain (K) | no vias (°C) |")
    print("| --: | --: | --: | --: | --: |")
    for cell in (2.0, 1.0, 0.5, 0.25):
        o = t_max(example_with(0.0), ("fvm",), cell)["fvm"]
        c = t_max(example_with(385.0), ("fvm",), cell)["fvm"]
        n = t_max(example_with(no_vias=True), ("fvm",), cell)["fvm"]
        print(f"| {cell} | {o:.2f} | {c:.2f} | {c - o:+.2f} | {n:.2f} |", flush=True)
    print()


def array_board(cell, fill_k, models=("fvm",)):
    """!
    @brief Temperature rise of the via-array board of part 4 in the program.
    @param cell Cell size in mm.
    @param fill_k Fill conductivity in W/mK.
    @param models Model keys.
    @return dict model -> maximum rise in K.
    """
    p = Problem.new(W, W, 4, T_MM, CU_MM * 1e3, h_top=H_TOP, h_bottom=H_BOTTOM, h_side=None, materials=Materials(k_fr4_inplane=K_FR4))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, W, W))
    p.add_heater(1, POWER, rect=(CENTRE - 5, CENTRE - 5, CENTRE + 5, CENTRE + 5))
    for x, y in VIAS:
        p.add_via(x, y, D_MM, fill_k=fill_k)
    res = simulate(p, SolverOptions(models=tuple(models), cell_mm=cell)).results
    return {m: res[m].t_max - p.board.ambient for m in models}


def array_board_independent(dx_mm, fill_k, sub=20, n_sub=4):
    """!
    @brief Temperature rise of the via-array board by the independent solver, barrels drawn at their real size (quarter domain, area fractions per cell).
    @param dx_mm Cell size in mm (must divide the half width).
    @param fill_k Fill conductivity in W/mK (0 = open bore).
    @param sub Sub-samples per cell side for the area fractions.
    @param n_sub Sub-slabs per dielectric gap.
    @return float Maximum rise of the top layer in K.
    """
    n = int(round(CENTRE / dx_mm))
    f_cu, f_core = np.zeros((n, n)), np.zeros((n, n))
    s = (np.arange(sub) + 0.5) / sub
    xs = ((np.arange(n)[:, None] + s[None, :]) * dx_mm).ravel()
    X, Y = np.meshgrid(xs, xs)
    r_o, r_i = D_MM / 2, D_MM / 2 - PL_MM
    for vx, vy in VIAS:
        if vx > CENTRE + 1e-9 or vy > CENTRE + 1e-9:
            continue                                                       # the quarter [0, C]^2 holds a full, two half and a quarter via
        rr = np.hypot(X - vx, Y - vy)
        ring = ((rr <= r_o) & (rr > r_i)).reshape(n, sub, n, sub).mean(axis=(1, 3))
        core = (rr <= r_i).reshape(n, sub, n, sub).mean(axis=(1, 3))
        share = 1.0 if (vx < CENTRE - 1e-9 and vy < CENTRE - 1e-9) else 0.5 if (vx < CENTRE - 1e-9 or vy < CENTRE - 1e-9) else 0.25
        a = dx_mm ** 2
        ring *= share * math.pi * (r_o ** 2 - r_i ** 2) / (ring.sum() * a)  # exact copper area of the part of the barrel in the quarter
        core *= share * math.pi * r_i ** 2 / (core.sum() * a)
        f_cu += ring
        f_core += core
    k_core = fill_k if fill_k > 0 else K_AIR                                 # an open bore holds air (a zero conductivity would leave isolated cells)
    k_gap = f_cu * K_CU + f_core * k_core + (1 - f_cu - f_core) * K_FR4     # dielectric slab: FR-4 with the barrel and its core
    k_plane = np.full((n, n), K_CU)                                          # copper plane: whole, as in the program (the land and the part's pad cover the bore)
    gap = (T_MM - 4 * CU_MM) / 3 * 1e-3
    slabs = []
    for layer in range(4):
        slabs.append((CU_MM * 1e-3, k_plane, 1))
        if layer < 3:
            slabs.append((gap, k_gap, n_sub))
    c = CENTRE * 1e-3
    res = layered3d.solve(dx_mm * 1e-3, n, n, slabs, (c - 5e-3, c - 5e-3, c, c), POWER / 4, H_TOP, H_BOTTOM, film_under_source=True)
    return float(res["T"][0].max())


def part4_independent(fine):
    """!
    @brief The via-array board: FVM at several cells against the independent solver with resolved barrels.
    @param fine True: add the independent solve at 0.05 mm cells.
    @return None.
    """
    print("## 4. Via-array board (21 x 21 mm, four planes, 3 x 3 vias of 0.3 mm under a 10 mm source, 2 W, h 10 / 200 W/m2K, insulated edges)\n")
    print("| Solver | open (K) | copper fill (K) | gain of the copper fill (K) |")
    print("| :-- | --: | --: | --: |")
    for dx in ((0.1, 1.0 / 12.0, 0.0625, 0.05) if fine else (0.1, 1.0 / 12.0)):
        o, c = array_board_independent(dx, 0.0), array_board_independent(dx, K_CU)
        print(f"| independent, barrels resolved, {dx:.4g} mm | {o:.2f} | {c:.2f} | {c - o:+.2f} |", flush=True)
    names = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "solid3d": "3D solid"}
    for cell in (1.0, 0.5):                                                # every model where all of them run quickly
        o, c = array_board(cell, 0.0, tuple(names)), array_board(cell, K_CU, tuple(names))
        for m in names:
            print(f"| {names[m]} {cell} mm | {o[m]:.2f} | {c[m]:.2f} | {c[m] - o[m]:+.2f} |", flush=True)
    for cell in (0.25, 0.125, 0.0625):                                     # the FVM alone on finer cells
        o, c = array_board(cell, 0.0)["fvm"], array_board(cell, K_CU)["fvm"]
        print(f"| FVM {cell} mm | {o:.2f} | {c:.2f} | {c - o:+.2f} |", flush=True)
    print("\nPeaceman's equivalent radius of a point source in one cell of a five-point stencil is 0.198 dx: it equals the via radius 0.15 mm at dx = 0.76 mm.\n")


def part5_solid3d_clip():
    """!
    @brief Share of the copper-equivalent area of a via kept by the per-cell fraction of the 3D solid (clipped at 1).
    @return None.
    """
    print("## 5. 3D solid: the per-cell via fraction is clipped at 1\n")
    print("| Via (mm) | fill | area (mm2) | cell 0.5 mm kept | cell 0.25 mm kept | largest cell that clips (mm) |")
    print("| --: | :-- | --: | --: | --: | --: |")
    for d in (0.3, 0.5):
        for name, k in (("open", 0.0), ("copper", K_CU)):
            a = Via(0, 0, d * 1e-3, False, "", k).thermal_area(PLATING, K_CU) * 1e6
            kept = [min(a / c ** 2, 1.0) * c ** 2 / a for c in (0.5, 0.25)]
            print(f"| {d} | {name} | {a:.4f} | {100 * kept[0]:.0f} % | {100 * kept[1]:.0f} % | {math.sqrt(a):.3f} |")
    print()


def part6_diameter_convention():
    """!
    @brief Resistance of a 0.3 mm via read as a drill (program) or as a finished hole (tooltip).
    @return None.
    """
    print("## 6. The diameter read as the drill (program) or as the finished hole (plating inside the drill)\n")
    for name, k in (("open", 0.0), ("copper", K_CU)):
        drill = Via(0, 0, 0.3e-3, False, "", k).thermal_area(PLATING, K_CU)
        finished = Via(0, 0, 0.3e-3 + 2 * PLATING, False, "", k).thermal_area(PLATING, K_CU)
        r_d, r_f = 1.6e-3 / (K_CU * drill), 1.6e-3 / (K_CU * finished)
        print(f"{name}: drill 0.3 mm {drill * 1e6:.4f} mm2, {r_d:.1f} K/W; finished hole 0.3 mm (drill 0.35) {finished * 1e6:.4f} mm2, {r_f:.1f} K/W ({100 * (r_f / r_d - 1):+.0f} %)")
    print()


def main():
    """!
    @brief Run the six checks and print their tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--fine", action="store_true", help="add the independent solves at 0.0625 and 0.05 mm (about 10 GB, 20 to 30 minutes)")
    args = ap.parse_args()
    pmodel.reload_libraries()
    part1_closed_form()
    part2_models()
    part3_cell_sweep()
    part4_independent(args.fine)
    part5_solid3d_clip()
    part6_diameter_convention()


if __name__ == "__main__":
    main()
