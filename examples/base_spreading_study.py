"""!
@file base_spreading_study.py
@brief How much does the base of a heatsink add to its catalogue resistance when the source is a small component? A 3D conduction solve of a plate with a uniform film coefficient.

@details The catalogue gives the sink-to-ambient resistance R0 for its own test source. A small package on the base adds the conduction through the thickness of the base
         under the source and the spreading in the plate. The plate is solved in 3D (finite volumes, uniform film h = 1/(R0 A) on the top face, other faces insulated, a uniform flux on
         a centred square on the bottom face); the extra resistance is (mean temperature rise of the source / power) minus R0.

Usage: python examples/base_spreading_study.py
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def extra_resistance(side_mm=40.0, t_mm=3.0, k=204.0, r0=12.0, src_mm=3.3, n=100, nz=6):
    """!
    @brief Extra resistance of a plate for a small centred square source, in K/W.
    @param side_mm Plate side in mm.
    @param t_mm Plate thickness in mm.
    @param k Conductivity in W/mK.
    @param r0 Catalogue resistance of the heatsink in K/W (film coefficient 1/(R0 A) over the top face).
    @param src_mm Side of the source in mm.
    @param n Cells per side in the plan.
    @param nz Cells across the thickness.
    @return Tuple (extra resistance on the mean temperature of the source, extra resistance on its maximum) in K/W.
    """
    dx = side_mm * 1e-3 / n
    dz = t_mm * 1e-3 / nz
    h = 1.0 / (r0 * (side_mm * 1e-3) ** 2)
    idx = np.arange(n * n * nz).reshape(nz, n, n)
    rows, cols, vals = [], [], []

    def link(a, b, g):
        rows.append(a.ravel())
        cols.append(b.ravel())
        vals.append(np.full(a.size, g))

    link(idx[:, :, :-1], idx[:, :, 1:], k * dx * dz / dx)          # x neighbours: k A / d
    link(idx[:, :-1], idx[:, 1:], k * dx * dz / dx)                # y neighbours
    link(idx[:-1], idx[1:], k * dx * dx / dz)                      # z neighbours
    off = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(idx.size, idx.size))
    off = off + off.T
    diag = np.asarray(off.sum(axis=1)).ravel()
    top = idx[-1].ravel()                                          # Layer nz - 1 carries the film (half cell of conduction in series)
    diag[top] += 1.0 / (1.0 / (h * dx * dx) + dz / 2.0 / (k * dx * dx))
    K = sp.diags(diag) - off
    q = np.zeros(idx.shape)
    lo, hi = int(round((side_mm - src_mm) / 2 / (side_mm / n))), int(round((side_mm + src_mm) / 2 / (side_mm / n)))
    q[0, lo:hi, lo:hi] = 1.0 / ((hi - lo) ** 2)                    # One watt into the bottom layer under the source
    theta = spla.spsolve(K.tocsc(), q.ravel(), permc_spec="MMD_AT_PLUS_A").reshape(idx.shape)
    src = theta[0, lo:hi, lo:hi]
    return float(src.mean() - r0), float(src.max() - r0)


def main():
    """!
    @brief Print the table: extra resistance by metal, thickness and source size, for a 40 x 40 mm base and a 12 K/W catalogue value.
    """
    chain = {3.3: 30.0 + 4.6 + 12.0, 5.0: 27.0 + 2.0 + 12.0}        # theta_JC(top) + default paste + catalogue resistance (MOSFET and LDO of component_study)
    print("Extra resistance of a 40 x 40 mm heatsink base (catalogue 12 K/W) for a small component, K/W (mean over the source); share of the top chain in brackets")
    print("| Base | 3.3 mm source (chain 46.6 K/W) | 5 mm source (chain 41 K/W) |\n| :-- | --: | --: |")
    for metal, k in (("aluminium", 204.0), ("copper", 386.0), ("carbon steel", 54.0)):
        for t in (1.0, 3.0, 6.0):
            a = extra_resistance(t_mm=t, k=k, src_mm=3.3)
            b = extra_resistance(t_mm=t, k=k, src_mm=5.0)
            print(f"| {metal} {t:g} mm | {a[0]:.2f} ({100 * a[0] / chain[3.3]:.1f} %) | {b[0]:.2f} ({100 * b[0] / chain[5.0]:.1f} %) |", flush=True)


if __name__ == "__main__":
    main()
