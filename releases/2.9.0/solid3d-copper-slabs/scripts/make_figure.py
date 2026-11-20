#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figure.py
@brief Draws `docs/images/fig_04b_solid3d_copper_slabs.png`: the slabs through a copper layer of the 3D solid by its thickness, and the profile through a uniformly heated 3 mm plate.
@details Left: the number of slabs of a copper layer against its thickness (the rule `solid3d.copper_slab_count`, the same as the FEM's). Right: the temperature of the copper slabs of a one-layer
         12 mm board heated over its whole area (a 1D problem, closed form T(z) = q (1/h + t_lam/k_lam + (t - z)/k_cu)), solved by the 3D solid, with the closed form as a line and the
         column (the mean of the slabs). Run from the repository root:

             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/make_figure.py
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from pcbthermal import Problem, solid3d  # noqa: E402


def profile():
    """!
    @brief Solve the heated plate with the 3D solid.
    @return Tuple (z of the slab centres in m, rise of the slabs in K, closed form at those z in K, column in K, thickness in m).
    """
    t_cu, w, P, h = 3.0e-3, 12.0e-3, 6.0, 250.0
    p = Problem.new(w * 1e3, w * 1e3, layers=1, thickness_mm=3.2, copper_um=t_cu * 1e6, ambient=20.0, h_top=1e-6, h_bottom=h, h_side=None)
    p.add_full_copper(layers=None)
    p.add_heater(1, P, rect=(0.0, 0.0, w * 1e3, w * 1e3), name="U")
    net = solid3d.Solid(p, 2.0)
    theta, _ = net.solve()
    m = p.board.materials
    n = len(net.copper_slabs[0])
    z = (np.arange(n) + 0.5) * t_cu / n
    q = P / w ** 2
    t_lam = float(p.board.slab_thicknesses()[0] - t_cu)
    exact = q * (1.0 / h + t_lam / m.k_fr4_through + (t_cu - z) / m.k_copper)
    got = theta[net.copper_slabs[0]][:, 2, 2]
    return z, got, exact, float(got.mean()), t_cu


def main():
    """!
    @brief Draw and save the figure.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    t = np.linspace(10, 1000, 400)
    a.step(t, [solid3d.copper_slab_count(x * 1e-6) for x in t], where="post", color="#1f77b4")
    a.axvline(105, color="grey", ls=":")
    a.text(112, 7.2, "105 um: one slab up to here", fontsize=8)
    a.set_xlabel("copper thickness (um)")
    a.set_ylabel("slabs through the layer")
    a.set_title("Slabs of a copper layer: 1 up to 105 um, ceil(t / 70 um) above, at most 8")
    a.title.set_fontsize(9)
    z, got, exact, col, t_cu = profile()
    b.plot(exact, z * 1e3, "-", color="#555555", label="closed form (1D)")
    b.plot(got, z * 1e3, "o", color="#d62728", label="3D solid, 8 slabs")
    b.axvline(col, color="#2ca02c", ls="--", label="column (mean of the slabs)")
    b.invert_yaxis()
    b.set_xlabel("rise over the ambient (K)")
    b.set_ylabel("depth from the face of the part (mm)")
    b.set_title("3 mm copper plate heated on its face, 6 W over 12 x 12 mm", fontsize=9)
    b.legend(fontsize=8)
    out = ROOT / "docs" / "images" / "fig_04b_solid3d_copper_slabs.png"
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()
