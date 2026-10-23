"""!
@file study_spreading_axisymmetric.py
@brief Yovanovich's spreading resistance of an isoflux circular source on a flux tube from a third, independent solver: an axisymmetric finite-volume model in cylindrical coordinates (no square tube, no staircase circle), compared with the published table and with the program's 3D solid (README 4.2).
@details The source of radius a is on the top face of a cylinder of radius b and length L (insulated sides, T = 0 at the far end, k = 1 W/mK). The dimensionless resistance is psi = 4 a k Rs, with Rs = (mean source temperature) / Q - L / (k pi b^2), the one-dimensional resistance taken out; the table (Yovanovich 2003, Table 3, quoted in solid3d_verification.py) gives psi against eps = a / b. The grid is square (dr = dz = b / 400), the source covers a whole number of cells of the top row, and the length is 2 b (the one-dimensional resistance is subtracted; a longer tube changes psi by less than the quoted digits, checked here for eps = 0.2). Writes out/spreading.json and out/spreading_field.npz (the temperature field for eps = 0.3) read by make_figures.py.
         Run: .venv/bin/python research/solid3d-verification/scripts/study_spreading_axisymmetric.py (from the repository root; about 20 seconds).
"""

import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

OUT = Path(__file__).resolve().parents[1] / "out"
TABLE = {0.1: 0.9401, 0.2: 0.8009, 0.3: 0.6649, 0.4: 0.5337}                  # Yovanovich (2003), Table 3, isoflux source


def solve(eps, length_in_b=2.0, nr=400):
    """!
    @brief The temperature field of an isoflux circular source on a flux tube and the dimensionless spreading resistance.
    @param eps Ratio a / b of the source radius to the tube radius (a multiple of 1 / nr).
    @param length_in_b Length of the tube in radii b.
    @param nr Cells across the radius b (the cells are square).
    @return tuple (psi, temperature field T[z, r] for unit heat flow and k = 1 with b = 1, cells per radius).
    """
    b = 1.0
    dr = b / nr
    nz = int(round(length_in_b * nr))
    r_in = np.arange(nr + 1) * dr                      # radial faces
    r_mid = 0.5 * (r_in[:-1] + r_in[1:])
    area_ring = np.pi * (r_in[1:] ** 2 - r_in[:-1] ** 2)           # area of the annulus of a cell (m2)
    idx = np.arange(nz * nr).reshape(nz, nr)
    rows, cols, vals = [], [], []
    # radial links between cell i and i + 1: k 2 pi r_face dz / dr
    g_r = 2 * np.pi * r_in[1:-1] * dr / dr
    a, c = idx[:, :-1].ravel(), idx[:, 1:].ravel()
    g = np.tile(g_r, nz)
    # axial links: k area / dz
    g_z = (area_ring / dr)
    a2, c2 = idx[:-1, :].ravel(), idx[1:, :].ravel()
    g2 = np.tile(g_z, nz - 1)
    for p, q, w in ((a, c, g), (a2, c2, g2)):
        rows += [p, q, p, q]
        cols += [p, q, q, p]
        vals += [w, w, -w, -w]
    ground = np.zeros(nz * nr)
    ground[idx[-1, :]] = area_ring / (0.5 * dr)                        # T = 0 at the far face, through half a cell
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * nr, nz * nr)) + sp.diags(ground)
    ns = int(round(eps * nr))
    a_src = ns * dr
    q = np.zeros(nz * nr)
    q[idx[0, :ns]] = area_ring[:ns] / (np.pi * a_src ** 2)           # unit heat flow spread over the source
    T = spla.spsolve(K.tocsc(), q).reshape(nz, nr)
    mean_src = np.sum(T[0, :ns] * area_ring[:ns]) / np.sum(area_ring[:ns])
    rs = mean_src - length_in_b * b / (np.pi * b * b)                 # Q = 1, k = 1: spreading part of the resistance
    return 4 * a_src * rs, T


def main():
    """!
    @brief Solve the table's four ratios, the curve between them, the longer tube check and write the results.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for eps in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5):
        psi, _ = solve(eps)
        rows.append({"eps": eps, "psi": psi, "table": TABLE.get(eps)})
        print(f"eps {eps:4.2f}: psi {psi:.4f}" + (f"   Table 3 {TABLE[eps]:.4f}   ({100 * (psi / TABLE[eps] - 1):+.2f} %)" if eps in TABLE else ""))
    longer, _ = solve(0.2, length_in_b=4.0)
    print(f"eps 0.20 with a tube of 4 b instead of 2 b: psi {longer:.4f}")
    sweep = []
    for nr in (100, 200, 400):
        psi_n, _ = solve(0.2, nr=nr)
        sweep.append({"cells_per_radius": nr, "psi": psi_n})
        print(f"eps 0.20 with {nr} cells per radius: psi {psi_n:.4f} ({100 * (psi_n / TABLE[0.2] - 1):+.2f} % of the table)")
    # the error halves with every halving of the cell (the step of the flux at the edge of the source limits the order to one): extrapolate with order one
    extrapolated = 2 * sweep[2]["psi"] - sweep[1]["psi"]
    print(f"extrapolated with order one from 200 and 400: {extrapolated:.4f} against Table 3 {TABLE[0.2]:.4f}")
    psi, T = solve(0.3)
    np.savez_compressed(OUT / "spreading_field.npz", T=T.astype(np.float32))
    (OUT / "spreading.json").write_text(json.dumps({"rows": rows, "psi_eps02_tube_4b": longer, "sweep_eps02": sweep, "extrapolated_eps02": extrapolated}, indent=1))


if __name__ == "__main__":
    main()
