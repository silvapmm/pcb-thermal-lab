#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file program_patch.py
@brief In-memory copies of the via handling of the FVM and FDM networks with the treatments of `viakernel`; the files of the program are never edited.
@details The `__init__` of `fvm.Network` and `fdm.Network` are read with `inspect.getsource`, the loop that adds the barrel conductance to one
         cell is replaced by a call to `via_hook`, the functions are compiled again inside
         the module of the program. `patched(name)` installs the copies and restores the originals on exit; `name = "point"` does exactly what the program does (tested bit by bit).
         Two families of treatment:
         * independent links ("indep": point, area, ring, peaceman, tuned): the barrel conductance of every gap is divided among the cells of a footprint and added to the
           vertical conductance of each cell, as the 3D solid does (each cell has its own link; with Peaceman wells the star is reduced to links between the sheet nodes of one cell);
         * mean-potential coupling ("mean": mw_point, mw_ring, mw_area, mw_tuned): the via is one conductor; the sheet of layer l reaches it through the weighted mean
           temperature of its footprint (a prescribed flux distribution w), with a Peaceman well of conductance 2 pi S / ln(r_eff / r_via) between that mean and the barrel when the
           effective radius r_eff of the footprint exceeds the via radius. The barrel and the wells are reduced (Kron) to couplings G[l, m] (e_l (x) w - e_m (x) w)(...)^T added to
           the matrix; no extra unknown.
@note The patch changes the steady state and the transient networks alike (they share the constructors), not the Lumped and Analytic models.
@note Updated after `fix/point-via` (the program now holds the mean-potential vias of `viawell.py` itself): the copies replace the program's call to
      `viawell.build` (FVM `__init__`, FDM `__init__`) by `via_hook`, which builds the treatment of this study; the program's own `_assemble` then writes the
      matrix entries of `net.via_blocks`, so `_assemble` is no longer copied. `name = "point"` is the point via of the program up to `f2d5c03` (the barrel conductance
      of every gap added to the cell of the via centre), no longer the program's current treatment; the identity test compares it with values frozen from that commit.
"""

import contextlib
import inspect
import math
import re
import textwrap

import numpy as np

import lattice
import viakernel as vk

# Current treatment; set by `patched`. c0: equivalent-radius constant of the point sink (times the cell); sub: samples per cell side for the area weights
STATE = {"name": "point", "c0": lattice.R_EQ_EXACT, "sub": 16, "eta": 1.0}

# (mode, footprint rule) of every treatment
TREATMENTS = {
    "point": ("indep", "point"), "area": ("indep", "area"), "ring": ("indep", "ring"), "peaceman": ("indep", "peaceman"), "tuned": ("indep", "tuned"),
    "mw_point": ("mean", "point"), "mw_disc": ("mean", "disc"), "mw_area": ("mean", "area"), "mw_ring": ("mean", "ring"), "mw_tuned": ("mean", "tuned"),
}


def _footprint(rule, v, rv, dx, origin, r0, sub, r_target=None):
    """!
    @brief Footprint weights of a via for a rule.
    @param rule point, area, ring, peaceman (a point while r0 > rv, else the area weights) or tuned.
    @param v The Via.
    @param rv Via radius in m.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param r0 Equivalent radius of a point sink on this grid in m.
    @param sub Samples per cell side.
    @param r_target Effective radius wanted by the tuned rule in m (default the via radius).
    @return dict {(i, j): w}.
    """
    r_target = rv if r_target is None else r_target
    if rule == "point":
        return vk.disc_weights(v.x, v.y, 0.0, dx, origin)
    if rule == "area":
        return vk.disc_weights(v.x, v.y, rv, dx, origin, sub, "area")
    if rule == "ring":
        return vk.disc_weights(v.x, v.y, rv, dx, origin, sub, "ring")
    if rule == "peaceman":
        return vk.disc_weights(v.x, v.y, 0.0, dx, origin) if r0 > rv else vk.disc_weights(v.x, v.y, rv, dx, origin, sub, "area")
    if rule == "disc":
        return vk.disc_target_weights(v.x, v.y, rv, r_target, dx, origin)
    if rule == "tuned":
        w = vk.tuned_weights(v.x, v.y, r_target, dx, origin, r_point=r0)
        return w if w is not None else vk.disc_weights(v.x, v.y, 0.0, dx, origin)
    raise ValueError(rule)


def via_hook(net, problem, gz, d, S, dx, dy, nx, ny, origin):
    """!
    @brief Handle every via with the current treatment: independent links go into `gz` now; mean-potential couplings are returned as blocks for the program's assembly.
    @param net The network being built (its `extra_links` list receives the links between non-adjacent layers made by the wells of the independent mode).
    @param problem The Problem.
    @param gz Array (L-1, ny, nx) of vertical conductances of the dielectric, modified in place.
    @param d Gap thicknesses in m, shape (L-1,).
    @param S Sheet conductances in W/K, shape (L', ny, nx); the first L layers are the board layers.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m (equal to dx in the studies).
    @param nx Cells (or nodes) along x.
    @param ny Cells (or nodes) along y.
    @param origin Lower edge of the first cell (0 for the FVM, -dx/2 for the FDM nodes) in m.
    @return list of (rows, cols, w, G) blocks in the format of `viawell.build` (empty unless the treatment is a mean-potential one); the same blocks are kept in the
            old format (cells, w, G) in `net._via_blocks` for the SOR studies.
    """
    b = problem.board
    m = b.materials
    L = gz.shape[0] + 1
    name, c0, sub = STATE["name"], STATE["c0"], STATE["sub"]
    mode, rule = TREATMENTS[name]
    net._via_blocks = []
    blocks = []
    extra = {}
    for v in problem.vias:
        area = v.thermal_area(b.via_plating, m.k_copper)
        gv = m.k_copper * area / d                                   # Barrel conductance of every gap (W/K)
        rv = v.diameter / 2.0
        r0 = c0 * dx                                                 # Equivalent radius of a point sink on this grid
        rt = STATE["eta"] * rv if mode == "mean" else rv                # radius that the mean-potential model must reproduce
        w = _footprint(rule, v, rv, dx, origin, r0, sub, rt)
        w = {k: x for k, x in w.items() if 0 <= k[0] < ny and 0 <= k[1] < nx}
        tot = sum(w.values())
        w = {k: x / tot for k, x in w.items()}
        r_f = vk.effective_radius(w, dx) if (mode == "mean" or rule == "peaceman") else r0
        if mode == "mean":
            # One conductor: the wells (if the footprint is smaller than the via cannot be undone: infinite) and the barrel are reduced to couplings between the layer means
            ic, jc = max(w, key=w.get)
            g_well = [vk.well_conductance(float(S[l, ic, jc]), r_f, rt) if S[l, ic, jc] > 0 else 0.0 for l in range(L)]
            G = vk.kron_barrel(gv, g_well)
            net._via_blocks.append((list(w.keys()), np.array(list(w.values())), G))
            blocks.append((np.array([k[0] for k in w]), np.array([k[1] for k in w]), np.array(list(w.values())), G))
            continue
        wells = rule in ("peaceman", "tuned") and r0 > rv
        for (i, j), x in w.items():
            if not wells:
                gz[:, i, j] += gv * x
            else:
                # Peaceman wells: the barrel joins every sheet through 2 pi S / ln(r_eq / r_via); the star is reduced to links between the sheet nodes of the cell
                g_well = [vk.well_conductance(float(S[l, i, j]), r0, rv) if S[l, i, j] > 0 else 0.0 for l in range(L)]
                G = vk.kron_barrel(gv, g_well)
                for l in range(L - 1):
                    gz[l, i, j] += G[l, l + 1]
                for l in range(L):
                    for k in range(l + 2, L):
                        if G[l, k] > 0:
                            arr = extra.setdefault((l, k), np.zeros((ny, nx)))
                            arr[i, j] += G[l, k]
    for (l, k), arr in extra.items():
        net.extra_links.append((l, k, arr))
    return blocks


# The statements of the program that build the vias (viawell.build): the FVM keeps the blocks on the network, the FDM in a local variable
_LOOP_FVM = re.compile(r"(?P<ind>[ ]+)self\.via_blocks, self\.gz_via = viawell\.build\(.*\n")
_LOOP_FDM = re.compile(r"(?P<ind>[ ]+)via_blocks, _gz_via = viawell\.build\(.*\n")


def _compile(module, func, edits, label):
    """!
    @brief Compile a copy of a function of the program with text edits.
    @param module The module of the program (fvm or fdm).
    @param func The original function.
    @param edits List of (regex or literal, replacement builder) applied in order; a literal is matched once.
    @param label Name for the compiler.
    @return The new function.
    @throws RuntimeError If an edit finds no match (the program changed).
    """
    src = textwrap.dedent(inspect.getsource(func))
    for pattern, builder in edits:
        if isinstance(pattern, str):
            k = src.find(pattern)
            if k < 0:
                raise RuntimeError(f"{pattern!r} not found in {label}")
            ind = re.match(r"[ ]*", src[src.rfind("\n", 0, k) + 1:]).group(0)
            src = src[:k] + builder(ind) + src[k:]
        else:
            m = pattern.search(src)
            if m is None:
                raise RuntimeError(f"via loop not found in {label}")
            src = src[:m.start()] + builder(m.group("ind")) + src[m.end():]
    ns = {}
    exec(compile(src, f"<patched {label}>", "exec"), module.__dict__, ns)
    return ns[func.__name__]


@contextlib.contextmanager
def patched(name="point", c0=lattice.R_EQ_EXACT, sub=16, eta=1.0):
    """!
    @brief Install the copies of the FVM and FDM network code with a via treatment; restore the originals on exit.
    @param name Treatment, a key of TREATMENTS.
    @param c0 Equivalent-radius constant of a point sink (0.1985 exact; 0.2 or 0.2079 for the variants in the literature).
    @param sub Samples per cell side for the area weights.
    @param eta Ratio of the radius the mean-potential model reproduces to the drill radius (1 = an equipotential circle; exp(-1/4) = 0.7788, the uniform sink density of the
               layered idealisation over the disc of the via); used by the "mw_*" treatments only.
    @return Context manager.
    """
    from pcbthermal import fdm, fvm
    if name not in TREATMENTS:
        raise ValueError(name)
    old = (fvm.Network.__init__, fdm.Network.__init__)
    old_state = dict(STATE)
    STATE.update(name=name, c0=c0, sub=sub, eta=eta)
    fvm._via_hook = fdm._via_hook = via_hook                                   # reachable from the compiled copies
    try:
        # The program's own _assemble writes the entries of net.via_blocks, so only the two constructors are copied
        fvm.Network.__init__ = _compile(fvm, old[0], [(_LOOP_FVM, lambda ind: ind + "self.via_blocks = _via_hook(self, problem, self.gz, d, self.S, dx, dy, nx, ny, 0.0)\n"
                                                        + ind + "self.gz_via = np.zeros_like(self.gz)\n")], "fvm.__init__")
        fdm.Network.__init__ = _compile(fdm, old[1], [(_LOOP_FDM, lambda ind: ind + "via_blocks = _via_hook(self, problem, gz, d, S, dx, dy, nx, ny, -0.5 * dx)\n")],
                                        "fdm.__init__")
        yield
    finally:
        fvm.Network.__init__, fdm.Network.__init__ = old
        STATE.clear()
        STATE.update(old_state)
        for mod in (fvm, fdm):
            if hasattr(mod, "_via_hook"):
                delattr(mod, "_via_hook")
