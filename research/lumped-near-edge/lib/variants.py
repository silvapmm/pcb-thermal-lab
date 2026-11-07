#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief Variants of the Lumped ring construction, built by editing a COPY of pcbthermal/lumped.py in memory (the program is never written).
@details Variants (names): "program" the tree as it is; "image" the logarithmic potentials of the footprint (link of ring 0, micro peak) include the 8 mirror images of the footprint in the
         board edges (insulated edge, method of images). The ring geometry is NOT changed: a cell is always nearer to the real footprint than to its image, so the distance contours
         and the clipped ring areas are the program's (section 3 of the README).
         Use install(name) to put a variant in pcbthermal.api in place of the module lumped.
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree  # noqa: E402,F401

IMAGE_TAIL = '''

# ---- appended by lib/variants.py: potentials of the footprint including its mirror images in the board edges
_footprint_potentials_plain = _footprint_potentials
IMAGE_MAX_CELLS = 3600        # review: cell-resolved image potentials up to 3600 footprint cells (a 30 mm part at 0.5 mm; about 0.5 GB of distance matrices)


def _footprint_potentials(cov, dx, dy):
    """Log potentials of the footprint plus the 8 mirror images (insulated edges, one tiling): T = -(P / 2 pi S) (phi_real + phi_images)."""
    idx = np.argwhere(cov > 0)
    # Review: the first version fell back to the program's block potentials (no images) above _MAX_POTENTIAL_CELLS (900 cells, a 15 mm part at 0.5 mm). Those block
    # potentials are not on the same footing as the cell-resolved ring means U of the potential links, and that mismatch, not the 64-source sample, made a centred 20 mm
    # part 2 to 3 points cooler and a 20 mm part in a corner -31 % (program -24 %). Cell-resolved potentials with images up to IMAGE_MAX_CELLS.
    if len(idx) > IMAGE_MAX_CELLS:
        return _footprint_potentials_plain(cov, dx, dy)
    w = cov[cov > 0]
    ny, nx = cov.shape
    boundary = np.zeros(len(idx), dtype=bool)
    for k, (i, j) in enumerate(idx):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < ny and 0 <= b < nx and cov[a, b] == 0:
                boundary[k] = True
                break
    x = (idx[:, 1] + 0.5) * dx
    y = (idx[:, 0] + 0.5) * dy
    d = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    np.fill_diagonal(d, 0.447 * np.sqrt(dx * dy))
    phi = (np.log(d) * w[None, :]).sum(axis=1) / w.sum()
    xw, yw = nx * dx, ny * dy
    for mx in (-1, 0, 1):
        for my in (-1, 0, 1):
            if mx == 0 and my == 0:
                continue
            xi = x if mx == 0 else (-x if mx < 0 else 2 * xw - x)
            yi = y if my == 0 else (-y if my < 0 else 2 * yw - y)
            di = np.hypot(x[:, None] - xi[None, :], y[:, None] - yi[None, :])
            phi += (np.log(np.maximum(di, 0.447 * np.sqrt(dx * dy))) * w[None, :]).sum(axis=1) / w.sum()
    phi_mean = float((phi * w).sum() / w.sum())
    phi_bnd = float(phi[boundary].mean()) if boundary.any() else phi_mean
    return phi_mean, phi_bnd, float(phi.min())
'''


POT_TAIL = '''

# ---- appended by lib/variants.py: the total log potential of the footprint and its images at every cell
def _total_potential(cov, dx, dy, ny, nx, images=True, max_src=None):
    """U(x) = mean over the footprint cells (and the 8 images) of ln |x - source|, at every cell centre (m units, floor 0.447 cell). max_src None: every cell (the review's default; 64 was the first version)."""
    idx = np.argwhere(cov > 0)
    w = cov[cov > 0].astype(float)
    if max_src is not None and len(idx) > max_src:
        sel = np.linspace(0, len(idx) - 1, max_src).astype(int)
        w = np.add.reduceat(w, sel) if False else w[sel] * (w.sum() / w[sel].sum())
        idx = idx[sel]
    sx = (idx[:, 1] + 0.5) * dx
    sy = (idx[:, 0] + 0.5) * dy
    gx = (np.arange(nx) + 0.5) * dx
    gy = (np.arange(ny) + 0.5) * dy
    X, Y = np.meshgrid(gx, gy)
    floor = 0.447 * np.sqrt(dx * dy)
    U = np.zeros((ny, nx))
    rng = (-1, 0, 1) if images else (0,)
    for mx in rng:
        for my in rng:
            xi = sx if mx == 0 else (-sx if mx < 0 else 2 * nx * dx - sx)
            yi = sy if my == 0 else (-sy if my < 0 else 2 * ny * dy - sy)
            for a in range(len(xi)):
                U += w[a] * np.log(np.maximum(np.hypot(X - xi[a], Y - yi[a]), floor))
    return U / w.sum()
'''

LINK_OLD = """            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])
            if k == 0:
                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1
            return 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1
"""
LINK_NEW = """            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])
            if k == 0:
                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + max(U_ring[1] - phi_bnd, 0.1 * half_k1 * 2.0 * np.pi * S[l, 1]) / (2.0 * np.pi * S[l, 1])
            return max(U_ring[k + 1] - U_ring[k], 1e-3) * 0.5 * (1.0 / S[l, k] + 1.0 / S[l, k + 1]) / (2.0 * np.pi)
"""
PEAK_OLD = "    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0])\n"
PEAK_NEW = PEAK_OLD + (
    "    a_true = float(cov.sum()) * cell\n"
    "    if SUBCELL_ON and a_true < 0.999 * A_foot:                 # the power is spread over every cell the part touches: add the spreading inside the cell\n"
    "        peak_extra += max(lat, 0.0) * f_p[layer] * 0.5 * np.log(A_foot / a_true) / (2.0 * np.pi * S[layer, 0])\n")

POT_ANCHOR = "    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)\n"


def source(name, text):
    """!
    @brief The text of lumped.py with the edits of one variant.
    @param name Variant name.
    @param text Source of pcbthermal/lumped.py.
    @return Edited source.
    @throws RuntimeError When an anchor is missing.
    """
    if name == "program":
        return text
    if name == "image":
        return text + IMAGE_TAIL
    if name in ("subcell", "potlinks_subcell"):
        if text.count(PEAK_OLD) != 1:
            raise RuntimeError("anchor missing: peak")
        text = text.replace(PEAK_OLD, PEAK_NEW) + "\nSUBCELL_ON = True\n"
        return text if name == "subcell" else source("potlinks", text)
    if name == "potlinks":
        text = text + IMAGE_TAIL + POT_TAIL
        for old, new in ((POT_ANCHOR, POT_ANCHOR + "    U_ring = ring_sum(_total_potential(cov, net.dx, net.dy, ny, nx)) / cnt\n"), (LINK_OLD, LINK_NEW)):
            if text.count(old) != 1:
                raise RuntimeError("anchor missing: " + old[:50])
            text = text.replace(old, new)
        return text
    raise ValueError(name)


_CACHE = {}


def load(name):
    """!
    @brief The variant as a module of the package pcbthermal.
    @param name Variant name.
    @return Module.
    """
    if name in _CACHE:
        return _CACHE[name]
    import pcbthermal.lumped as orig
    spec = importlib.util.spec_from_loader(f"pcbthermal.lumped_{name}", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "pcbthermal"
    mod.__file__ = orig.__file__
    sys.modules[spec.name] = mod
    exec(compile(source(name, Path(orig.__file__).read_text()), f"lumped_{name}", "exec"), mod.__dict__)
    _CACHE[name] = mod
    return mod


def install(name):
    """!
    @brief Make pcbthermal.api call the variant for the Lumped model.
    @param name Variant name.
    @return None.
    """
    import pcbthermal.api as api
    api.lumped = load(name)
