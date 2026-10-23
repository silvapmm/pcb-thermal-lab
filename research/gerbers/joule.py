"""!
@file joule.py
@brief Current in a copper net and the heat it makes: the Laplace equation on the pixels of a net mask (research prototype for "how much does the 5 V net heat up").
@details A net is a set of copper pixels (a mask drawn from the objects that carry the same X2 net attribute, see native_gerber.Layer.net_names). Copper is a thin sheet of sheet
         resistance Rs = rho / t (ohm per square), so the voltage V satisfies div(grad V / Rs) = 0 on the mask. Two terminal sets are given (where the current enters and leaves)
         and the total current I. The result is the resistance R = V / I between them, the potential, and the Joule power of every pixel, q = sum over its faces of (dV)^2 / (2 Rs),
         whose sum is exactly I^2 R. The map can be summed into the cells of the thermal grid and used as a heat source. Temperature dependence of the resistivity
         is handled by `resistivity` (a fixed-point loop is the job of the caller). One layer; vias between layers are not modelled here.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as cg
import scipy.sparse.linalg as sla

RHO_CU_20C = 1.68e-8           # ohm m, annealed copper at 20 C
ALPHA_CU = 0.00393             # 1/K, temperature coefficient of the resistivity of copper


def resistivity(temperature_c, rho20=RHO_CU_20C, alpha=ALPHA_CU):
    """!
    @brief Resistivity of copper at a temperature.
    @param temperature_c Temperature (degrees Celsius).
    @param rho20 Resistivity at 20 C (ohm m).
    @param alpha Temperature coefficient (1/K).
    @return Resistivity (ohm m).
    """
    return rho20 * (1.0 + alpha * (temperature_c - 20.0))


def _edges(stencil):
    """!
    @brief The pixel pairs that are linked, with their weight.
    @details "4": the four axial neighbours, weight 1 (the classical five-point stencil, exact for the axes and too resistive for a thin track at an angle: the current has to follow a staircase).
             "9": the isotropic nine-point stencil: axial neighbours 2/3 and diagonal neighbours 1/6 (they add up to the same conductance across a straight cut, and the Laplacian is
             isotropic to a higher order, so a tilted wide track conducts like a straight one). Weights are positive, so it is still a valid conductance network.
    @param stencil "4" or "9".
    @return List of (slice of the first pixel, slice of the second pixel, weight).
    @throws ValueError For another stencil.
    """
    allr, c1, c2 = slice(None), slice(0, -1), slice(1, None)
    if stencil == "4":
        return [((allr, c1), (allr, c2), 1.0), ((c1, allr), (c2, allr), 1.0)]
    if stencil == "9":
        return [((allr, c1), (allr, c2), 2.0 / 3.0), ((c1, allr), (c2, allr), 2.0 / 3.0), ((c1, c1), (c2, c2), 1.0 / 6.0), ((c1, c2), (c2, c1), 1.0 / 6.0)]
    raise ValueError("stencil must be '4' or '9'")


def solve_net(mask, sheet_ohm, source, sink, current, stencil="4"):
    """!
    @brief Potential, resistance and Joule power of a net between two terminals.
    @details Pixels are 4-connected; the face between two pixels conducts 1 / sheet_ohm for square pixels. The terminals are held at a potential (source at 1, sink at 0) and the
             solution is scaled to the wanted current. Only the part of the mask connected to the terminals is solved; a terminal that is not connected to the other raises ValueError.
    @param mask Boolean array (rows, cols) of the net's copper.
    @param sheet_ohm Sheet resistance in ohm per square (scalar, or an array like mask for a spatially varying value).
    @param source Boolean array like mask: where the current enters.
    @param sink Boolean array like mask: where the current leaves.
    @param current Total current (A).
    @param stencil "4" (axial links) or "9" (isotropic nine-point links, see `_edges`).
    @return Tuple (R, V, q): resistance between the terminals (ohm), potential array (V, nan outside the solved part), Joule power per pixel (W, zero outside).
    @throws ValueError If the terminals are empty or not connected through the mask.
    """
    mask = np.asarray(mask, bool)
    source, sink = np.asarray(source, bool) & mask, np.asarray(sink, bool) & mask
    if not source.any() or not sink.any():
        raise ValueError("a terminal does not touch the copper of the net")
    if (source & sink).any():
        raise ValueError("the two terminals overlap")
    rs = np.broadcast_to(np.asarray(sheet_ohm, float), mask.shape)
    ny, nx = mask.shape
    idx = -np.ones(mask.shape, int)
    idx[mask] = np.arange(mask.sum())
    g = 1.0 / rs
    rows, cols, vals = [], [], []
    # Horizontal and vertical faces between two copper pixels; the face conductance is the series of the two half pixels (harmonic mean of the pixel conductances)
    for sl_a, sl_b, wt in _edges(stencil):
        both = mask[sl_a] & mask[sl_b]
        ga, gb = g[sl_a][both], g[sl_b][both]
        gf = wt * 2.0 * ga * gb / (ga + gb)
        rows.append(idx[sl_a][both]); cols.append(idx[sl_b][both]); vals.append(gf)
    r, c, v = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    n = int(mask.sum())
    adj = sp.coo_matrix((v, (r, c)), shape=(n, n)).tocsr()
    adj = adj + adj.T
    # Keep the connected component(s) that hold the terminals
    ncomp, lab = cg.connected_components(adj, directed=False)
    s_lab = set(lab[idx[source]]); k_lab = set(lab[idx[sink]])
    if not (s_lab & k_lab):
        raise ValueError("the terminals are not connected through the copper of the net")
    keep = np.isin(lab, list(s_lab & k_lab))
    lap = (sp.diags(np.asarray(adj.sum(axis=1)).ravel()) - adj).tocsr()
    fixed = np.zeros(n, bool)
    val = np.zeros(n)
    fixed[idx[source]] = True; val[idx[source]] = 1.0
    fixed[idx[sink]] = True; val[idx[sink]] = 0.0
    free = keep & ~fixed
    rhs = -lap[free][:, fixed] @ val[fixed]
    sol = np.zeros(n)
    sol[fixed] = val[fixed]
    sol[free] = sla.spsolve(lap[free][:, free].tocsc(), rhs)
    flux = lap @ sol                                                       # net current leaving each node at 1 V
    i_unit = float(flux[idx[source]].sum())
    if i_unit <= 0.0:
        raise ValueError("no current flows between the terminals")
    scale = current / i_unit
    resistance = 1.0 / i_unit                                              # ohm: 1 V over the current it drives
    volt = np.full(mask.shape, np.nan)
    volt[mask] = np.where(keep, sol * scale, np.nan)
    # Joule power: half of every face's (dV)^2 g to each of its two pixels
    q = np.zeros(mask.shape)
    vv = np.where(np.isnan(volt), 0.0, volt)
    for sl_a, sl_b, wt in _edges(stencil):
        both = mask[sl_a] & mask[sl_b] & ~np.isnan(volt[sl_a]) & ~np.isnan(volt[sl_b])
        ga, gb = g[sl_a], g[sl_b]
        gf = wt * 2.0 * ga * gb / (ga + gb)
        p = np.where(both, gf * (vv[sl_a] - vv[sl_b]) ** 2, 0.0)
        q[sl_a] += 0.5 * p
        q[sl_b] += 0.5 * p
    return resistance, volt, q


def to_cells(q, n):
    """!
    @brief Sum a Joule-power map into coarse cells of n x n pixels (the heat source of the thermal grid); the total is conserved.
    @param q Power per pixel (W).
    @param n Pixels per cell side.
    @return Array (rows // n, cols // n) of power per cell (W).
    """
    ny, nx = (q.shape[0] // n) * n, (q.shape[1] // n) * n
    return q[:ny, :nx].reshape(ny // n, n, nx // n, n).sum(axis=(1, 3))
