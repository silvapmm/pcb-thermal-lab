"""!
@file study_disc_reference.py
@brief Are the FVM reference and the same-area rectangle right on a round board, checked against a reference that does not use the program's grid?

@details A round two-layer board (80 mm across, full copper on both layers) with a round part of 2 W at its centre is axisymmetric, so the layered
         model of the program (two copper sheets coupled through the dielectric, films on the faces, edge film on the rim) reduces to two coupled
         ordinary differential equations in the radius. This script solves them with its own radial finite volumes (thousands of rings, checked by
         halving the ring width), which share neither the program's square grid nor its cover fractions nor its edge-length rule. Against that
         reference it prints the maximum and the mean rise of the program's FVM and FDM on the real outline, of the 3D solid (real slabs, an
         independent geometry of the thickness) and of the Lumped and Analytic models, which run on the rectangle of the same area
         (`Problem.equivalent_rectangle`). It also prints the board time constant C/G in closed form against the program's, and the board mean of a power step\n         (radial implicit Euler with a fixed small step) against the program's transient.

Usage: .venv/bin/python research/outline/scripts/study_disc_reference.py (from the repository root; about a minute)
"""

import math
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from pcbthermal import Problem, SolverOptions, fvm, simulate          # noqa: E402

D_MM = 80.0          # Board diameter (mm)
A_MM = 4.0           # Radius of the part (mm)
POWER = 2.0          # Power of the part (W)
N_SIDES = 128        # Sides of the polygons that stand for the circles in the program
BOX_MM = 82.0        # Box of the board (mm): a little larger than the disc, whose equal-area polygon pokes out of an 80 mm box


def circle(cx, cy, r, n=N_SIDES):
    """!
    @brief A regular polygon of the same area as a circle (the program's outline and footprint are polygons).
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param r Radius of the circle in mm.
    @param n Number of sides.
    @return List of [x, y] in mm.
    """
    # Circumradius that gives the polygon the area of the circle: n/2 R^2 sin(2 pi/n) = pi r^2
    rc = r * math.sqrt(2.0 * math.pi / (n * math.sin(2.0 * math.pi / n)))
    return [[cx + rc * math.cos(a), cy + rc * math.sin(a)] for a in np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)]


def board():
    """!
    @brief The round test board: 80 mm across inside an 82 x 82 mm box, two layers of full copper, a round part of 2 W on the top layer.
    @return Problem.
    """
    p = Problem.new(BOX_MM, BOX_MM, 2).add_full_copper()
    p.add_heater(1, POWER, polygon=circle(BOX_MM / 2, BOX_MM / 2, A_MM), name="U")
    p.set_outline(circle(BOX_MM / 2, BOX_MM / 2, D_MM / 2))
    return p


def radial_network(p, n_rings):
    """!
    @brief Conductance matrix, heat capacities and source of the axisymmetric layered model, with radial finite volumes.
    @details Unknowns: the rise of every ring on each of the two copper layers. Ring k spans [k dr, (k+1) dr]; the radial conductance between rings is
             2 pi r_face S / dr with S the sheet conductance of the layer (copper plus the dielectric share of the slab, as `docs/theory.md`
             defines the layer node); the vertical conductance is k_through / gap per unit area; the faces lose h per unit area and the rim
             h_side * slab * 2 pi R. The heat capacity of a ring is that of its copper and its share of the laminate. The source is spread uniformly
             over r < a on the top layer.
    @param p The round Problem (its board gives the materials, films and thicknesses).
    @param n_rings Number of rings from the centre to the rim.
    @return Tuple (K sparse in W/K, C in J/K, q in W, ring areas in m2).
    """
    b = p.board
    m = b.materials
    big_r = D_MM / 2000.0
    a = A_MM / 1000.0
    dr = big_r / n_rings
    r_in = np.arange(n_rings) * dr
    r_out = r_in + dr
    area = math.pi * (r_out ** 2 - r_in ** 2)                     # Ring areas (m2)
    slab = b.slab_thicknesses()
    t_cu = np.asarray(b.copper_thickness)
    k_lam, rho_cp_lam = b.layer_laminate()
    sheet = m.k_copper * t_cu + k_lam * (slab - t_cu)             # Sheet conductance of every layer (W/K), full copper
    c_area = m.rho_copper * m.cp_copper * t_cu + rho_cp_lam * (slab - t_cu)   # Heat capacity per area of every layer (J/m2K)
    g_z = b.gap_properties()[0][0] / b.gap_thicknesses()[0]       # Vertical conductance per area (W/m2K)
    h = [b.h_top, b.h_bottom]
    n = 2 * n_rings
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    cap = np.zeros(n)
    for layer in range(2):
        base = layer * n_rings
        g_r = 2.0 * math.pi * r_out[:-1] * sheet[layer] / dr        # Between ring k and k + 1
        i = base + np.arange(n_rings - 1)
        rows += list(i) + list(i + 1)
        cols += list(i + 1) + list(i)
        vals += list(-g_r) * 2
        diag[i] += g_r
        diag[i + 1] += g_r
        diag[base:base + n_rings] += h[layer] * area + g_z * area
        diag[base + n_rings - 1] += b.h_side * slab[layer] * 2.0 * math.pi * big_r
        cap[base:base + n_rings] = c_area[layer] * area
    idx = np.arange(n_rings)
    rows += list(idx) + list(idx + n_rings)
    cols += list(idx + n_rings) + list(idx)
    vals += list(-g_z * area) * 2
    k_mat = (sp.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(diag)).tocsc()
    covered = math.pi * (np.clip(r_out, 0, a) ** 2 - np.clip(r_in, 0, a) ** 2)   # Overlap of every ring with the source disc
    q = np.zeros(n)
    q[:n_rings] = POWER * covered / (math.pi * a * a)
    return k_mat, cap, q, area


def board_mean(theta, area):
    """!
    @brief Mean rise over the board area and the two layers, as the program's t_mean.
    @param theta Rises of the rings, top layer first (K).
    @param area Ring areas (m2).
    @return Mean rise in K.
    """
    n = len(area)
    return float(np.sum((theta[:n] + theta[n:]) * area) / (2.0 * np.sum(area)))


def radial_reference(p, n_rings):
    """!
    @brief Steady temperature rise of the axisymmetric layered model.
    @param p The round Problem.
    @param n_rings Number of rings from the centre to the rim.
    @return Tuple (maximum rise in K, area-mean rise of the two layers in K).
    """
    k_mat, _, q, area = radial_network(p, n_rings)
    theta = spla.spsolve(k_mat, q)
    return float(theta.max()), board_mean(theta, area)


def radial_transient_mean(p, n_rings, times, dt):
    """!
    @brief Board mean rise after a power step from ambient, implicit Euler with a fixed small step on the radial network.
    @param p The round Problem.
    @param n_rings Number of rings.
    @param times Output times in s (multiples of dt).
    @param dt Time step in s.
    @return List of mean rises in K at the output times.
    """
    k_mat, cap, q, area = radial_network(p, n_rings)
    lu = spla.splu((sp.diags(cap / dt) + k_mat).tocsc())
    theta = np.zeros_like(q)
    out, t = [], 0.0
    for t_out in times:
        while t < t_out - 1e-9:
            theta = lu.solve(cap / dt * theta + q)
            t += dt
        out.append(board_mean(theta, area))
    return out


def closed_time_constant(p):
    """!
    @brief C/G of the round board in closed form: heat capacity of copper and laminate over the face and rim films.
    @param p The round Problem.
    @return Time constant in seconds.
    """
    b = p.board
    m = b.materials
    big_r = D_MM / 2000.0
    t_cu = float(np.sum(b.copper_thickness))
    rho_cp = float(np.mean(b.layer_laminate()[1]))
    c_area = m.rho_copper * m.cp_copper * t_cu + (b.thickness - t_cu) * rho_cp
    area, perim = math.pi * big_r ** 2, 2.0 * math.pi * big_r
    return c_area * area / ((b.h_top + b.h_bottom) * area + b.h_side * b.thickness * perim)


def main():
    """!
    @brief Print the radial reference (with its ring check) and the program's models against it.
    @return None.
    """
    p = board()
    amb = p.board.ambient
    ref = {}
    print("| radial reference, rings | max rise (K) | mean rise (K) |")
    print("| --: | --: | --: |")
    for n in (2000, 4000, 8000):
        ref = radial_reference(p, n)
        print(f"| {n} | {ref[0]:.4f} | {ref[1]:.4f} |")
    t_ref, m_ref = ref
    print("\n| model | cell (mm) | max rise (K) | error of max | mean rise (K) | error of mean |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for model, cells in (("fvm", (1.0, 0.5)), ("fdm", (1.0, 0.5)), ("solid3d", (1.0,)), ("lumped", (1.0,)), ("analytic", (1.0,))):
        for c in cells:
            r = simulate(p, SolverOptions(models=(model,), cell_mm=c)).results[model]
            mean = r.t_mean - amb                                 # Board-area mean over the layers
            print(f"| {model} | {c:g} | {r.t_max - amb:.3f} | {(r.t_max - amb - t_ref) / t_ref * 100:+.2f} % | {mean:.3f} | "
                  f"{(mean - m_ref) / m_ref * 100:+.2f} % |", flush=True)
    print("\n| time constant | s |")
    print("| :-- | --: |")
    print(f"| closed form C/G | {closed_time_constant(p):.2f} |")
    for c in (2.0, 1.0):
        print(f"| program FVM, {c:g} mm cells | {fvm.estimate_time_constant(p, cell_mm=c):.2f} |")
    times = [100.0, 300.0, 600.0]
    ref_t = radial_transient_mean(p, 1000, times, 0.05)
    log = fvm.solve_transient(p, 600.0, n_out=10, cell_mm=1.0)
    lin = fvm.solve_transient(p, 600.0, n_out=60, cell_mm=1.0, substeps=10, log_times=False)
    print("\n| board mean rise at 600 s after the step | K |")
    print("| :-- | --: |")
    print(f"| radial reference (1000 rings, implicit Euler, 0.05 s) | {ref_t[-1]:.3f} |")
    print(f"| program FVM, 1 mm, doubling step, 10 frames (as study_outline_time_constant.py) | {log.t_mean[-1] - amb:.3f} |")
    print(f"| program FVM, 1 mm, constant step of 1 s | {lin.t_mean[-1] - amb:.3f} |")
    print("\nRadial reference mean rise at " + ", ".join(f"{t:g} s: {v:.3f} K" for t, v in zip(times, ref_t)))


if __name__ == "__main__":
    main()
