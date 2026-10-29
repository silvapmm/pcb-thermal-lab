"""!
@file pdn.py
@brief DC current in copper with sources, sinks and links: a research prototype of the electrical side of an electro-thermal run (voltage sources, current sinks per pad, resistors that join pieces of copper).
@details The copper of a layer is a sheet of resistance Rs (ohm per square) on pixels, as in joule.py (`_edges` stencils). Terminals are named sets of pixels (the copper under a pad). The elements are
         ("vsource", terminal, volts) which holds the terminal at a potential, ("isink", terminal, amps) which takes a current out of the terminal, and ("link", terminal_a, terminal_b, ohms) a resistor between two terminals
         (a 0 ohm jumper, a ferrite bead, a shunt, a fuse, the bridge between two pieces of one net). The unknowns are the pixel potentials and one node per terminal; a connected piece that holds no voltage source is
         floating: it carries no current and no heat, whatever its voltage. Returns the potential, the Joule power per pixel and the power of every link; the power of the sources equals the copper, the links and the loads (V at the pad times its current).
         The pad currents are inputs (from a power budget or a netlist), not something the copper can infer.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as cg
import scipy.sparse.linalg as sla

import joule

G_TIE = 1.0e6              # S, conductance tying a terminal node to each of its pixels (large: the pad is an equipotential)


def solve(mask, sheet_ohm, terminals, elements, stencil="4"):
    """!
    @brief Potentials, Joule power and link power of a copper layer with sources, sinks and links.
    @param mask Boolean array (rows, cols) of the copper.
    @param sheet_ohm Sheet resistance (ohm per square, scalar).
    @param terminals Dict name -> boolean array like mask (the pixels of the pad).
    @param elements List of ("vsource", t, volts), ("isink", t, amps) and ("link", t1, t2, ohms).
    @param stencil "4" (axial links, exact for axis-aligned copper, the default) or "9" (isotropic, better for tilted tracks wider than about 8 pixels, 20 % too resistive on a 2-pixel strip: joule._edges).
    @return dict with "V" (potential array, nan on floating copper), "q" (Joule power per pixel, W), "links" (list of (t1, t2, current A, power W)), "p_source" (W delivered by the sources), "p_sinks" (W taken by the loads: V at the pad times its current), "p_copper" and "p_links" (W).
    @throws ValueError If a terminal does not touch the copper, an element names an unknown terminal, or a sink sits on a piece that no voltage source reaches.
    """
    mask = np.asarray(mask, bool)
    names = list(terminals)
    for t in names:
        if not (np.asarray(terminals[t], bool) & mask).any():
            raise ValueError(f"terminal {t!r} does not touch the copper")
    ny, nx = mask.shape
    idx = -np.ones(mask.shape, int)
    idx[mask] = np.arange(mask.sum())
    n = int(mask.sum())
    g = np.full(mask.shape, 1.0 / sheet_ohm)
    rows, cols, vals = [], [], []
    for sl_a, sl_b, wt in joule._edges(stencil):
        both = mask[sl_a] & mask[sl_b]
        gf = wt * g[sl_a][both]
        rows.append(idx[sl_a][both]); cols.append(idx[sl_b][both]); vals.append(gf)
    node = {t: n + k for k, t in enumerate(names)}
    for t in names:                                                      # a node per terminal, tied to every pixel under the pad
        pix = idx[np.asarray(terminals[t], bool) & mask]
        rows.append(np.full(pix.size, node[t])); cols.append(pix); vals.append(np.full(pix.size, G_TIE))
    for el in elements:
        if el[0] == "link":
            if el[1] not in node or el[2] not in node:
                raise ValueError(f"link names an unknown terminal: {el[1:3]}")
            rows.append(np.array([node[el[1]]])); cols.append(np.array([node[el[2]]])); vals.append(np.array([1.0 / el[3]]))
        elif el[0] in ("vsource", "isink") and el[1] not in node:
            raise ValueError(f"{el[0]} names an unknown terminal: {el[1]}")
    m = n + len(names)
    r, c, v = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    adj = sp.coo_matrix((v, (r, c)), shape=(m, m)).tocsr()
    adj = adj + adj.T
    lap = (sp.diags(np.asarray(adj.sum(axis=1)).ravel()) - adj).tocsr()
    inj = np.zeros(m)
    fixed = np.zeros(m, bool)
    val = np.zeros(m)
    for el in elements:
        if el[0] == "isink":
            inj[node[el[1]]] -= el[2]
        elif el[0] == "vsource":
            fixed[node[el[1]]] = True
            val[node[el[1]]] = el[2]
    ncomp, lab = cg.connected_components(adj, directed=False)
    live = np.isin(lab, np.unique(lab[fixed]))                          # components that hold a voltage source; the others float
    for el in elements:
        # A sink on a piece that no source reaches has no current to take: refuse it instead of losing the current silently (found by the review)
        if el[0] == "isink" and el[2] != 0.0 and not live[node[el[1]]]:
            raise ValueError(f"isink on terminal {el[1]!r}: no voltage source is connected to its piece (add a link or a source)")
    free = live & ~fixed
    sol = np.zeros(m)
    sol[fixed] = val[fixed]
    rhs = inj[free] - lap[free][:, fixed] @ val[fixed]
    sol[free] = sla.spsolve(lap[free][:, free].tocsc(), rhs)
    volt = np.full(mask.shape, np.nan)
    volt[mask] = np.where(live[:n], sol[:n], np.nan)
    q = np.zeros(mask.shape)
    vv = np.where(np.isnan(volt), 0.0, volt)
    for sl_a, sl_b, wt in joule._edges(stencil):
        both = mask[sl_a] & mask[sl_b] & ~np.isnan(volt[sl_a]) & ~np.isnan(volt[sl_b])
        gf = wt * g[sl_a]
        p = np.where(both, gf * (vv[sl_a] - vv[sl_b]) ** 2, 0.0)
        q[sl_a] += 0.5 * p
        q[sl_b] += 0.5 * p
    links = []
    for el in elements:
        if el[0] == "link":
            dv = sol[node[el[1]]] - sol[node[el[2]]]
            links.append((el[1], el[2], dv / el[3], dv * dv / el[3]))
    flux = lap @ sol
    p_source = float(sum(sol[node[e[1]]] * flux[node[e[1]]] for e in elements if e[0] == "vsource"))
    p_sinks = float(sum(sol[node[e[1]]] * e[2] for e in elements if e[0] == "isink"))      # what the loads take: V at the pad times the current
    return {"V": volt, "q": q, "links": links, "p_source": p_source, "p_sinks": p_sinks, "p_copper": float(q.sum()), "p_links": float(sum(l[3] for l in links))}
