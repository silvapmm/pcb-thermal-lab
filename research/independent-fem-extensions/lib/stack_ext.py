#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file stack_ext.py
@brief A layered finite-element model with PARTIAL slabs (a copper tab and solder over a polygon, a plate and an interface under the board), built on
       `independent-fem-edge/lib/fem.py` (imported, never edited).
@details `board.Board` extrudes one plan mesh through slabs that all cover the whole plan, so a tab smaller than the board cannot be expressed and its via
         loop would turn every slab into copper. This builder extrudes the plan through a list of slabs (each a list of element thicknesses), keeps in every
         slab only the plan quads whose centroid satisfies the slab's region, and puts a film on every FREE face: the top of an element with no element above it,
         the bottom of one with none below, and a lateral face on the plan boundary or beside a quad that is absent in that slab. Symmetry lines carry no film.
         Per slab: conductivities per quad (`kfun`), films (`h_up`, `h_down`, `h_wall`), an optional volumetric source (total power spread uniformly in the
         slab's elements of a region), and the capacity `rho_c` (J/m3K) used by `transient.py`. SI units; z grows downwards from the top of the first slab.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "independent-fem-edge", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import fem                                                              # noqa: E402


def slab(name, dz, kfun, region=None, h_up=0.0, h_down=0.0, h_wall=0.0, power=0.0, source_region=None, rho_c=0.0):
    """!
    @brief Describe one slab.
    @param name Label ('tab', 'solder', 'cu1', 'gap1', 'interface', 'plate' ...).
    @param dz Element thicknesses of the slab, m (sequence).
    @param kfun Callable(centroids (Q, 2), quad index array) -> (kx (Q,), kz (Q,)) in W/mK, or a tuple (kx, kz) of numbers.
    @param region None (the whole plan) or callable(centroids) -> bool: where the slab exists.
    @param h_up Film on an exposed upward face, W/m2K.
    @param h_down Film on an exposed downward face, W/m2K.
    @param h_wall Film on lateral free faces (plan boundary except the symmetry lines, and beside an absent quad), W/m2K.
    @param power Heat generated in the slab, W (spread uniformly over the slab's elements inside `source_region`).
    @param source_region None (the whole slab) or callable(centroids) -> bool.
    @param rho_c Volumetric heat capacity rho c of the slab, J/m3K.
    @return dict.
    """
    return dict(name=name, dz=np.asarray(dz, float), kfun=kfun, region=region, h_up=h_up, h_down=h_down, h_wall=h_wall, power=power, source_region=source_region, rho_c=rho_c)


class Stack:
    """!
    @brief Plan mesh plus a list of slabs, built into a `fem.Model`.
    """

    def __init__(self, plan, slabs, symmetry=()):
        """!
        @brief Create the description.
        @param plan Quad2D plan mesh (m).
        @param slabs List of `slab` dicts from the top down.
        @param symmetry Lines with no wall film: list of ('x', value) or ('y', value) in m.
        @return None.
        """
        self.plan, self.slabs, self.symmetry = plan, slabs, list(symmetry)

    def build(self):
        """!
        @brief Build the model.
        @return Tuple (fem.Model, info dict: present (nz, Q) bool, sub (nz,) slab index of every sub-layer, zn (nz + 1,), Np, c (centroids), rho_c (E,) per element,
                free_top (list of (F, 4) node arrays of the faces with a film: 'up'), faces dict with 'up', 'down', 'wall' node arrays and their h).
        """
        plan = self.plan
        c = plan.centroids()
        Q, Np = c.shape[0], plan.xy.shape[0]
        dz, sub, regions = [], [], []
        for i, s in enumerate(self.slabs):
            for t in s["dz"]:
                dz.append(t)
                sub.append(i)
            regions.append(np.ones(Q, bool) if s["region"] is None else np.asarray(s["region"](c), bool))
        dz, sub = np.asarray(dz), np.asarray(sub)
        nz = dz.size
        zn = np.concatenate([[0.0], np.cumsum(dz)])
        present = np.array([regions[i] for i in sub])                    # (nz, Q)
        nodes = np.column_stack([np.tile(plan.xy, (nz + 1, 1)), np.repeat(zn, Np)])
        s_idx, q_idx = np.nonzero(present)
        q = plan.quads
        elems = np.concatenate([q[q_idx] + (s_idx * Np)[:, None], q[q_idx] + ((s_idx + 1) * Np)[:, None]], axis=1)
        m = fem.Model(nodes, elems)
        E = elems.shape[0]
        rho_c = np.zeros(E)
        owner = sub[s_idx]
        for i, s in enumerate(self.slabs):
            sel = owner == i
            if not sel.any():
                continue
            kf = s["kfun"]
            kxq, kzq = kf(c, np.arange(Q)) if callable(kf) else (np.full(Q, kf[0]), np.full(Q, kf[1]))
            m.k[sel, 0] = np.asarray(kxq)[q_idx[sel]]
            m.k[sel, 1] = np.asarray(kxq)[q_idx[sel]]
            m.k[sel, 2] = np.asarray(kzq)[q_idx[sel]]
            rho_c[sel] = s["rho_c"]
            if s["power"]:
                src = np.ones(Q, bool) if s["source_region"] is None else np.asarray(s["source_region"](c), bool)
                esel = sel & src[q_idx]
                if not esel.any():
                    raise ValueError(f"slab {s['name']}: the source region holds no element")
                vol = m.element_volumes()
                m.q[esel] += s["power"] / vol[esel].sum()
        # free faces: up (no element above), down (none below) and lateral
        up_nodes, up_h, dn_nodes, dn_h = [], [], [], []
        elem_of = -np.ones((nz, Q), np.int64)
        elem_of[s_idx, q_idx] = np.arange(E)
        for L in range(nz):
            qs = np.nonzero(present[L])[0]
            h_up, h_dn = self.slabs[sub[L]]["h_up"], self.slabs[sub[L]]["h_down"]
            free_up = qs if L == 0 else qs[~present[L - 1, qs]]
            free_dn = qs if L == nz - 1 else qs[~present[L + 1, qs]]
            if h_up > 0 and free_up.size:
                up_nodes.append(q[free_up] + L * Np)
                up_h.append(np.full(free_up.size, h_up))
            if h_dn > 0 and free_dn.size:
                dn_nodes.append(q[free_dn] + (L + 1) * Np)
                dn_h.append(np.full(free_dn.size, h_dn))
        edges = np.stack([q, np.roll(q, -1, axis=1)], axis=2).reshape(-1, 2)
        own = np.repeat(np.arange(Q), 4)
        key = np.sort(edges, axis=1)
        order = np.lexsort((key[:, 1], key[:, 0]))
        ks, es, os_ = key[order], edges[order], own[order]
        same = np.concatenate([[False], (ks[1:] == ks[:-1]).all(axis=1)])
        # an edge shared by two quads: ids (first, second); a boundary edge: only one
        first = ~same
        nxt_same = np.concatenate([same[1:], [False]])
        pair_a = np.nonzero(first & nxt_same)[0]
        nbr = -np.ones(ks.shape[0], np.int64)
        nbr[pair_a] = os_[pair_a + 1]
        nbr[pair_a + 1] = os_[pair_a]
        mid = plan.xy[es].mean(axis=1)
        sym_free = np.ones(ks.shape[0], bool)
        for axis, value in self.symmetry:
            sym_free &= np.abs(mid[:, 0 if axis == "x" else 1] - value) > 1e-9
        wall_nodes, wall_h = [], []
        for L in range(nz):
            h_w = self.slabs[sub[L]]["h_wall"]
            if h_w <= 0:
                continue
            pres_own = present[L, os_]
            pres_nbr = np.where(nbr >= 0, present[L, np.maximum(nbr, 0)], False)
            free = pres_own & ~pres_nbr & (sym_free | (nbr >= 0))        # a symmetry line only exempts the plan boundary, not an interior free face
            idx = np.nonzero(free)[0]
            if idx.size:
                e = es[idx]
                wall_nodes.append(np.column_stack([e[:, 0] + L * Np, e[:, 1] + L * Np, e[:, 1] + (L + 1) * Np, e[:, 0] + (L + 1) * Np]))
                wall_h.append(np.full(idx.size, h_w))
        for nd, hh in zip(up_nodes + dn_nodes + wall_nodes, up_h + dn_h + wall_h):
            m.add_faces(nd, h=hh)
        faces = {"up": np.vstack(up_nodes) if up_nodes else np.zeros((0, 4), np.int64), "down": np.vstack(dn_nodes) if dn_nodes else np.zeros((0, 4), np.int64)}
        info = {"present": present, "sub": sub, "zn": zn, "Np": Np, "c": c, "rho_c": rho_c, "elem_of": elem_of, "faces": faces, "s_idx": s_idx, "q_idx": q_idx,
                "slab_first_level": np.array([int(np.nonzero(sub == i)[0][0]) if (sub == i).any() else -1 for i in range(len(self.slabs))])}
        return m, info

    def solve(self, **kw):
        """!
        @brief Build and solve (steady).
        @param kw Passed to `fem.Model.solve`.
        @return dict from `fem.Model.solve` plus 'model' and 'info'.
        """
        m, info = self.build()
        r = m.solve(**kw)
        r["model"], r["info"] = m, info
        return r

    def level_nodes(self, info, slab_index, quads, bottom=False):
        """!
        @brief Node faces of the top (or bottom) face of a slab over the given quads.
        @param info Info dict of `build`.
        @param slab_index Index of the slab in the list.
        @param quads Boolean mask (Q,) or index array of plan quads.
        @param bottom True for the lower face of the slab.
        @return int array (F, 4).
        """
        sub = info["sub"]
        levels = np.nonzero(sub == slab_index)[0]
        L = levels[-1] + 1 if bottom else levels[0]
        qq = np.nonzero(quads)[0] if np.asarray(quads).dtype == bool else np.asarray(quads)
        return self.plan.quads[qq] + L * info["Np"]
