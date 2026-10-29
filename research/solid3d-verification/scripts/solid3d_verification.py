#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file solid3d_verification.py
@brief Verification of the 3D solid against an analytical benchmark and a grid-convergence study.

@details Two checks that do not use another solver of this project:
         (1) **Spreading resistance of a circular source on a flux tube** (Yovanovich, J. Electronic Packaging 125 (2003) 169-177, Table 3): an isoflux circular source of
             radius a on one end of a long cylinder of radius b, insulated sides, cooled at the other end. The dimensionless resistance psi = 4 a k Rs depends only on
             eps = a/b (0.9401, 0.8009, 0.6649, 0.5337 for eps = 0.1 ... 0.4; 1.0808 at eps = 0). The program's board is square, so the tube is the square of the same
             area (b = W / sqrt(pi)); the source temperature is the mean over the source and the one-dimensional resistances t/(kA) and 1/(hA) are subtracted.
         (2) **Grid convergence** (Richardson extrapolation and the grid convergence index of Roache, ASME V&V 20): a square source aligned with the cells, so that every mesh
             represents it exactly, solved with the cell size halved twice; the observed order, the extrapolated value and the GCI of the fine mesh are printed.
         Two closed forms are printed beside the table (added by the review): the Bessel series of the circular tube, which reproduces Table 3,
         psi = (16 / (pi eps)) sum_n J1(d_n eps)^2 / (d_n^3 J0(d_n)^2) over the roots d_n of J1, and the double cosine series of the same circular source on the
         square tube of the same area that the 3D solid solves, psi = 4 a sum_{m,n even, not both 0} (2 pi a J1(l a) / l)^2 / ((pi a^2)^2 N_mn l) with
         l = pi sqrt(m^2 + n^2) / W and N_mn = W^2 / 4 (W^2 / 2 when m or n is 0); their difference is the share of the square tube in the gap to the table.

Usage: python research/solid3d-verification/scripts/solid3d_verification.py
"""

import math
import os
import sys

import numpy as np
from scipy.special import j0, j1, jn_zeros

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem, solid3d                                # noqa: E402
from pcbthermal.geometry import coverage_fraction                       # noqa: E402
from pcbthermal.model import Dielectric                                 # noqa: E402

PSI_ISOFLUX = {0.1: 0.9401, 0.2: 0.8009, 0.3: 0.6649, 0.4: 0.5337}      # Yovanovich 2003, Table 3, column m = 0 (isoflux), semi-infinite tube


def psi_circular_series(eps, terms=20000):
    """!
    @brief Exact dimensionless spreading resistance of an isoflux circular source on a semi-infinite circular flux tube (the closed form behind Table 3).
    @param eps Ratio a/b of the source radius to the tube radius.
    @param terms Number of roots of J1 summed.
    @return psi = 4 a k Rs.
    """
    d = jn_zeros(1, terms)
    return float(16.0 / (math.pi * eps) * np.sum(j1(d * eps) ** 2 / (d ** 3 * j0(d) ** 2)))


def psi_square_series(eps, terms=2000):
    """!
    @brief Exact dimensionless spreading resistance of an isoflux circular source at the centre of a semi-infinite square flux tube of the same area (side W = b sqrt(pi)).
    @details The mean source temperature is the double cosine series of the channel; only even orders survive the centred source, whose Fourier
             integral over the disc is 2 pi a J1(l a) / l (up to a sign that squares away).
    @param eps Ratio a/b, b = W / sqrt(pi) the equivalent radius.
    @param terms Highest order m, n of the series (even orders only are summed).
    @return psi = 4 a k Rs with the same a and b as the circular case.
    """
    w = 1.0
    a = eps * w / math.sqrt(math.pi)
    m = np.arange(0, terms, 2) * math.pi / w
    al, be = np.meshgrid(m, m, indexing="ij")
    lam = np.hypot(al, be)
    norm = np.where((al == 0) | (be == 0), w * w / 2.0, w * w / 4.0)
    lam[0, 0] = 1.0                                                      # The uniform mode is the one-dimensional resistance: left out below
    term = (2.0 * math.pi * a * j1(lam * a) / lam) ** 2 / ((math.pi * a * a) ** 2 * norm * lam)
    term[0, 0] = 0.0
    return float(4.0 * a * term.sum())


def tube_problem(width_mm, thickness_m, k, source, h_bottom=1.0e4):
    """!
    @brief A homogeneous isotropic square block, heated on the top face by one source and cooled on the bottom face, insulated elsewhere.
    @param width_mm Side of the square block in mm.
    @param thickness_m Thickness of the block in m.
    @param k Conductivity in W/mK (isotropic).
    @param source Polygon [[x, y], ...] of the 1 W source in mm.
    @param h_bottom Heat transfer coefficient of the cooled face in W/m2K.
    @return Problem.
    """
    p = Problem.new(width_mm=width_mm, height_mm=width_mm, layers=2)
    b = p.board
    b.h_top, b.h_bottom, b.h_side = 1e-6, h_bottom, None
    b.copper_thickness = [5e-6, 5e-6]                                    # No zones: the copper slabs are laminate
    b.dielectrics = [Dielectric(thickness_m, "isotropic block", k, k, 1850.0, 900.0)]
    b.thickness = b.total_thickness()
    b.materials.k_fr4_through = b.materials.k_fr4_inplane = k
    p.zones = []
    p.add_heater(1, 1.0, polygon=source)
    return p


def source_resistance(p, cell_mm, n_diel):
    """!
    @brief Mean temperature rise of the source per watt, from the 3D solid.
    @param p Problem from tube_problem().
    @param cell_mm Cell size in mm.
    @param n_diel Slabs across the thickness.
    @return Rise in K/W.
    """
    r = solid3d.solve_steady(p, cell_mm=cell_mm, n_diel=n_diel)
    cov = coverage_fraction(p.heaters[0].polygon, r.T.shape[2], r.T.shape[1], r.dx, r.dy)
    return float((r.T[0] * cov).sum() / cov.sum() - p.board.ambient)


def circular_psi(eps, t_over_b=1.5, cell_mm=1.0, n_diel=40, width_mm=50.0, k=1.0, h=1.0e4):
    """!
    @brief Dimensionless spreading resistance 4 a k Rs of a circular isoflux source, computed with the 3D solid.
    @param eps Ratio a/b of the source radius to the equivalent radius of the square block.
    @param t_over_b Thickness over the equivalent radius (1.5 is enough for a semi-infinite tube).
    @param cell_mm Cell size in mm.
    @param n_diel Slabs across the thickness.
    @param width_mm Side of the block in mm.
    @param k Conductivity in W/mK.
    @param h Heat transfer coefficient of the cooled face in W/m2K.
    @return psi.
    """
    b = width_mm / 1000.0 / math.sqrt(math.pi)
    a, t = eps * b, t_over_b * b
    th = np.linspace(0.0, 2.0 * math.pi, 96, endpoint=False)
    c = width_mm / 2.0
    src = np.c_[c + a * 1000.0 * np.cos(th), c + a * 1000.0 * np.sin(th)].tolist()
    p = tube_problem(width_mm, t, k, src, h)
    area = (width_mm / 1000.0) ** 2
    rs = source_resistance(p, cell_mm, n_diel) - t / (k * area) - 1.0 / (h * area)      # Remove the one-dimensional resistances
    return 4.0 * a * k * rs


def grid_convergence(cells=(4.0, 2.0, 1.0), side_mm=8.0, width_mm=48.0, t_mm=40.0, k=1.0, n_diel=16):
    """!
    @brief Richardson extrapolation and grid convergence index of the source temperature, with a square source aligned with every mesh.
    @param cells Three cell sizes in mm, each half of the previous (coarse, medium, fine).
    @param side_mm Side of the square source in mm (a multiple of every cell size).
    @param width_mm Side of the block in mm.
    @param t_mm Thickness in mm.
    @param k Conductivity in W/mK.
    @param n_diel Slabs across the thickness (the same on every mesh, so only the plan mesh changes).
    @return Dict with the three values, the observed order p, the extrapolated value and the GCI of the fine mesh (fraction).
    """
    c = width_mm / 2.0
    src = [[c - side_mm / 2, c - side_mm / 2], [c + side_mm / 2, c - side_mm / 2], [c + side_mm / 2, c + side_mm / 2], [c - side_mm / 2, c + side_mm / 2]]
    f = [source_resistance(tube_problem(width_mm, t_mm / 1000.0, k, src), cell, n_diel) for cell in cells]
    f3, f2, f1 = f
    r = cells[0] / cells[1]
    order = math.log(abs((f3 - f2) / (f2 - f1))) / math.log(r)
    extrapolated = f1 + (f1 - f2) / (r ** order - 1.0)
    gci = 1.25 * abs((f1 - f2) / f1) / (r ** order - 1.0)                # Safety factor 1.25 for three grids
    return {"values": f, "order": order, "extrapolated": extrapolated, "gci": gci,
            "monotone": (f3 - f2) * (f2 - f1) > 0.0}


def main():
    """!
    @brief Print both verification tables.
    """
    print("| eps = a/b | Yovanovich Table 3 (isoflux) | series, circular tube | series, square tube | 3D solid, cell 1 mm | 3D solid against the table | against the square tube |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for eps in (0.2, 0.3):
        psi, circ, square = circular_psi(eps), psi_circular_series(eps), psi_square_series(eps)
        print(f"| {eps} | {PSI_ISOFLUX[eps]:.4f} | {circ:.4f} | {square:.4f} | {psi:.4f} | {100 * (psi / PSI_ISOFLUX[eps] - 1):+.1f} % | {100 * (psi / square - 1):+.1f} % |",
              flush=True)
    g = grid_convergence()
    print(f"\nSquare source, cells 4, 2, 1 mm: Tmean rise per watt {g['values'][0]:.4f}, {g['values'][1]:.4f}, {g['values'][2]:.4f} K/W "
          f"(monotone: {g['monotone']}); observed order {g['order']:.2f}, extrapolated {g['extrapolated']:.4f} K/W, GCI of the fine mesh {100 * g['gci']:.2f} %")


if __name__ == "__main__":
    main()
