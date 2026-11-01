#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_peaceman_nonsquare.py
@brief Does the printed Peaceman radius for non-square cells and anisotropic conductivity hold on the lattice?

Question: Lie (2019) eq. 4.34, after Peaceman (1983), gives the equivalent radius of a well in a block
dx x dy of an anisotropic medium (Kx, Ky),
  r0 = 0.28 sqrt( sqrt(Ky/Kx) dx^2 + sqrt(Kx/Ky) dy^2 ) / ( (Ky/Kx)^(1/4) + (Kx/Ky)^(1/4) ),
and Koch et al. (2019) eq. 5.6 writes the constant as exp(-gamma)/2 = 0.2807.  This script solves the
five-point lattice (the same lattice as the node-centred FDM of the program and the cell-centred FVM on
a uniform grid) with a unit point sink, reads the equivalent radius from the potential difference to
nodes far from the well, and compares it with the printed formula.  No program code is imported.  A second, domain-free
reference (added by the review) is the potential kernel of the infinite five-point lattice, written as a one-dimensional
integral and evaluated by quadrature at 400 and 800 steps from the sink: it shows that the 0.1 to 7 % differences of the
finite rectangle are effects of its boundary, and that the printed formula is exact on the lattice to 1e-5.

Method: link conductances gx = Kx dy/dx and gy = Ky dx/dy (unit thickness), a large rectangle with the
potential fixed on its outer ring, one unit sink in the middle node.  Away from the well the continuum
solution is p = -(q / (2 pi Ke)) ln(rho) with Ke = sqrt(Kx Ky) and the stretched distance
rho^2 = x^2/Kx + y^2/Ky, so r0 = rho_far exp(-2 pi Ke (p0 - p_far) / q) in the stretched plane; the conversion to the physical
well radius is explained in lattice_r0.  Finding: the printed formula equals the exact stretching of the
isotropic non-square lattice (0.14 sqrt(dx'^2 + dy'^2), dx' = dx/sqrt(Kx)) times that conversion (algebraic identity).

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_peaceman_nonsquare.py
"""
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.integrate import quad


def lattice_r0(kx: float, ky: float, dx: float, dy: float, n: int = 401, far: int = 10) -> float:
    """!
    @brief Equivalent well radius of the five-point lattice read at nodes far from the sink.

    @param kx   Conductivity along x, W/(m K) (any consistent unit).
    @param ky   Conductivity along y.
    @param dx   Node spacing along x, m.
    @param dy   Node spacing along y, m.
    @param n    Nodes per side of the (odd) square array of nodes; the outer ring is held at zero.
    @param far  Distance in nodes of the probe nodes from the sink along both axes.

    @return float Equivalent radius r0 in metres in the convention of Peaceman (physical well radius),
            the mean over the four axis probes, converted from the stretched plane (see the comment at the return).
    """
    gx = kx * dy / dx  # conductance of a link along x
    gy = ky * dx / dy  # conductance of a link along y
    m = n - 2  # interior nodes per side
    idx = np.arange(m * m).reshape(m, m)  # row = y index, column = x index
    rows, cols, vals = [], [], []
    diag = np.zeros(m * m)
    # links to the right (x) and up (y); the outer ring is Dirichlet zero, so a missing neighbour only adds to the diagonal
    for axis, g in ((1, gx), (0, gy)):
        a = idx.take(range(m - 1), axis=axis).ravel()
        b = idx.take(range(1, m), axis=axis).ravel()
        rows += [a, b]
        cols += [b, a]
        vals += [-g * np.ones_like(a, dtype=float)] * 2
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)
    # the boundary links of the interior ring nodes
    for sl_idx, g in ((idx[:, 0], gx), (idx[:, -1], gx), (idx[0, :], gy), (idx[-1, :], gy)):
        np.add.at(diag, sl_idx, g)
    mat = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(m * m, m * m))
    mat = (mat + sp.diags(diag)).tocsc()
    c = m // 2
    rhs = np.zeros(m * m)
    rhs[idx[c, c]] = 1.0  # unit sink (sign chosen so that p is positive at the well)
    p = spla.spsolve(mat, rhs).reshape(m, m)
    ke = math.sqrt(kx * ky)
    est = []
    for (di, dj) in ((far, 0), (-far, 0), (0, far), (0, -far)):
        rho = math.sqrt((dj * dx) ** 2 / kx + (di * dy) ** 2 / ky)  # stretched distance of the probe
        est.append(rho * math.exp(-2.0 * math.pi * ke * (p[c, c] - p[c + di, c + dj])))
    # The fit gives the radius of a circular hole in the stretched plane.  A physical circular well of radius rw
    # is an ellipse there (semi-axes rw/sqrt(kx), rw/sqrt(ky)) whose equivalent circle has the mean semi-axis, so the
    # radius that goes with the physical rw is the fit times 2 sqrt(kx ky) / (sqrt(kx) + sqrt(ky)).
    return float(np.mean(est)) * 2.0 * ke / (math.sqrt(kx) + math.sqrt(ky))


def kernel_x(gx: float, gy: float, a: int) -> float:
    """!
    @brief Potential difference G(0, 0) - G(a, 0) of a unit source on the infinite five-point lattice with link conductances gx, gy.

    @param gx Conductance of a link along x (W/K for unit thickness).
    @param gy Conductance of a link along y.
    @param a  Offset of the probe node along x, in nodes.

    @return float Potential difference in K per W.
    @note The Fourier integral (1 / 4 pi^2) double integral of (1 - cos(a t1)) / (2 gx (1 - cos t1) + 2 gy (1 - cos t2)) is
          reduced to one dimension with the closed form of the integral over t2 (2 pi / sqrt(A (A + 4 gy)), A = 2 gx (1 - cos t1)).
    """
    def f(t):
        aa = 2.0 * gx * (1.0 - math.cos(t))
        return (1.0 - math.cos(a * t)) / math.sqrt(aa * (aa + 4.0 * gy)) if t > 0.0 else 0.0
    val, _ = quad(f, 0.0, math.pi, limit=4000)
    return val / math.pi  # (1 / 2 pi) times twice the half-range integral


def infinite_lattice_r0(kx: float, ky: float, dx: float, dy: float, far: int = 800) -> float:
    """!
    @brief Equivalent well radius of the infinite five-point lattice (no outer boundary), physical convention as lattice_r0.

    @param kx  Conductivity along x.
    @param ky  Conductivity along y.
    @param dx  Node spacing along x, m.
    @param dy  Node spacing along y, m.
    @param far Probe offset along x in nodes (the far-field error is of order far^-2).

    @return float Equivalent radius r0 in metres.
    """
    gx, gy = kx * dy / dx, ky * dx / dy
    ke = math.sqrt(kx * ky)
    rho = far * dx / math.sqrt(kx)  # stretched distance of the probe
    r_stretched = rho * math.exp(-2.0 * math.pi * ke * kernel_x(gx, gy, far))
    return r_stretched * 2.0 * ke / (math.sqrt(kx) + math.sqrt(ky))


def peaceman_r0(kx: float, ky: float, dx: float, dy: float) -> float:
    """!
    @brief Printed equivalent radius (Lie 2019 eq. 4.34; constant exp(-gamma)/2 of Koch et al. 2019 eq. 5.6).

    @param kx Conductivity along x.
    @param ky Conductivity along y.
    @param dx Cell size along x, m.
    @param dy Cell size along y, m.

    @return float Equivalent radius in metres.
    """
    c = math.exp(-0.5772156649015329) / 2.0  # 0.28074..., the printed 0.28
    num = math.sqrt(math.sqrt(ky / kx) * dx ** 2 + math.sqrt(kx / ky) * dy ** 2)
    return c * num / ((ky / kx) ** 0.25 + (kx / ky) ** 0.25)


def main() -> None:
    """!
    @brief Print the lattice radius against the printed one for a sweep of aspect ratios and anisotropies.

    @return None
    """
    print("exp(-pi/2) = %.5f (Peaceman 1978 / Lie 4.3.2), exp(-gamma)/2 = %.5f (constant of eq. 4.34)"
          % (math.exp(-math.pi / 2), math.exp(-0.5772156649015329) / 2))
    print("%6s %6s %6s %6s | %10s %10s %10s %10s %10s" % ("kx", "ky", "dx", "dy", "rectangle", "infinite", "printed",
                                                          "rect. %", "inf. %"))
    for kx, ky, dx, dy in ((1, 1, 1, 1), (1, 1, 2, 1), (1, 1, 1, 0.5), (4, 1, 1, 1), (1, 4, 1, 1),
                           (0.1, 1, 1, 1), (4, 1, 2, 1), (1, 9, 0.5, 1), (10, 1, 1, 3), (1, 1, 10, 1)):
        a = lattice_r0(kx, ky, dx, dy)  # finite rectangle, Dirichlet ring, probe 10 nodes away
        c = infinite_lattice_r0(kx, ky, dx, dy)  # infinite lattice, probe 800 nodes away
        b = peaceman_r0(kx, ky, dx, dy)
        print("%6.2f %6.2f %6.2f %6.2f | %10.5f %10.5f %10.5f %10.2f %10.4f"
              % (kx, ky, dx, dy, a, c, b, 100.0 * (a - b) / b, 100.0 * (c - b) / b))


if __name__ == "__main__":
    main()
