#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief Variants of the first link of the Lumped ring network near a board edge, built by editing a COPY of pcbthermal/lumped.py in memory (the program is never written).
@details Variants: "program" the module as it is; "expo" the link from the footprint to ring 1 (and the zone model's A to ring 1) is divided by the open fraction omega of
         ring 1 (area of ring 1 on the board divided by the area of the same ring on an unbounded plane, both by the distance transform): the heat leaves the footprint only
         through the part of the contour that has board outside it, so the 2 pi of the logarithmic potential becomes 2 pi omega (exact for a part on an insulated side: omega 1/2
         and the half plane); "expo_peak" also divides the micro peak term (the spreading inside the footprint) by omega; "expo_p" with the power OMEGA_POWER (study of the exponent).
         install(name) puts the variant where pcbthermal.api calls the Lumped model.
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree  # noqa: E402,F401

OMEGA_TAIL = '''

# ---- appended by lib/variants.py: the open fraction of ring 1
OMEGA_POWER = 1.0          # exponent of omega on the first link
OMEGA_PEAK = False         # also divide the micro peak term


def _open_fraction(foot, edges, dx, dy):
    """Area of ring 1 on the board over the area of the same ring on an unbounded plane (1 when the board does not clip it)."""
    if len(edges) < 2:
        return 1.0
    r1 = edges[1]
    clipped = float(((~foot) & (ndimage.distance_transform_edt(~foot, sampling=(dy, dx)) <= r1)).sum())
    pad = int(np.ceil(r1 / min(dx, dy))) + 2
    big = np.pad(foot, pad)
    full = float(((~big) & (ndimage.distance_transform_edt(~big, sampling=(dy, dx)) <= r1)).sum())
    return min(max(clipped / full, 0.05), 1.0) if full > 0 else 1.0
'''

REPL = [
    # one-node network: omega after the potentials, the first link and the peak
    ("    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)\n    a_eq = np.sqrt(cnt[0] * cell / np.pi)\n",
     "    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)\n    omega = _open_fraction(foot, edges, net.dx, net.dy) ** OMEGA_POWER\n    a_eq = np.sqrt(cnt[0] * cell / np.pi)\n"),
    ("                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1\n",
     "                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * omega * S[l, 0]) + half_k1\n"),
    ("    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0])\n",
     "    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0] * (omega if OMEGA_PEAK else 1.0))\n"),
    ('            "peak_coef": f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0]),\n',
     '            "peak_coef": f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0] * (omega if OMEGA_PEAK else 1.0)),\n'),
    # zone network: A to ring 1
    ("    r_c = math.sqrt(cnt[1] * cell / math.pi)\n    a_f = math.sqrt((cnt[0] + cnt[1]) * cell / math.pi)\n",
     "    r_c = math.sqrt(cnt[1] * cell / math.pi)\n    a_f = math.sqrt((cnt[0] + cnt[1]) * cell / math.pi)\n    omega = _open_fraction(foot, edges, net.dx, net.dy) ** OMEGA_POWER\n"),
    ("            out.append((0, 2, viaconstriction.annulus_out_resistance(S[l, 0], r_c, a_f) + 0.5 * thick[2] / (S[l, 2] * length[2])))\n",
     "            out.append((0, 2, viaconstriction.annulus_out_resistance(S[l, 0], r_c, a_f) / omega + 0.5 * thick[2] / (S[l, 2] * length[2])))\n"),
]


# ---- the image variants of lumped-near-edge (ported to the current program), with a reflection factor RHO of the edge
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
            phi += RHO ** (abs(mx) + abs(my)) * (np.log(np.maximum(di, 0.447 * np.sqrt(dx * dy))) * w[None, :]).sum(axis=1) / w.sum()
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
                U += RHO ** (abs(mx) + abs(my)) * w[a] * np.log(np.maximum(np.hypot(X - xi[a], Y - yi[a]), floor))
    return U / w.sum()
'''

RHO_TAIL = '''

# ---- appended by lib/variants.py: reflection factor of the board edge for the image potentials
RHO = 1.0
RHO_MODE = "one"


def _set_rho(net):
    """Reflection factor of the edge: 1 (insulated); "robin": (1 - beta) / (1 + beta), beta = (edge conductance per metre) lambda / S, lambda the fin length of the layers together."""
    global RHO
    if RHO_MODE == "one":
        RHO = 1.0
        return
    per = 2.0 * (net.nx * net.dx + net.ny * net.dy)
    ge = float(sum(float(np.sum(g)) for g in net.g_side)) / per
    s_tot = float(sum(float(np.mean(net.S[l])) for l in range(net.nl)))
    g_face = float(sum(float(np.mean(net.g_top[l] + net.g_bottom[l])) for l in range(net.nl))) / (net.dx * net.dy)
    lam = (s_tot / max(g_face, 1e-12)) ** 0.5
    beta = ge * lam / max(s_tot, 1e-12)
    RHO = (1.0 - beta) / (1.0 + beta) if RHO_MODE == "robin" else float(RHO_MODE)
'''

LINK_OLD = '            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])\n            if k == 0:\n                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1\n            return 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1\n'
LINK_NEW = '            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])\n            if k == 0:\n                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + max(U_ring[1] - phi_bnd, 0.1 * half_k1 * 2.0 * np.pi * S[l, 1]) / (2.0 * np.pi * S[l, 1])\n            return max(U_ring[k + 1] - U_ring[k], 1e-3) * 0.5 * (1.0 / S[l, k] + 1.0 / S[l, k + 1]) / (2.0 * np.pi)\n'
POT_ANCHOR = "    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)\n"
RHO_ANCHOR = "    foot = cov > 0\n    # Distance of every cell to the footprint (metres); zero inside it\n"



DELTA_TAIL = '''

# ---- appended by lib/variants.py: the image correction ADDED to the program's first link ("delta")
def _pair_potentials(cov, dx, dy, ny, nx):
    """Footprint potentials (mean, boundary, min) and the total potential field with the images of the edges (RHO) and without them (the real footprint only)."""
    global RHO
    keep = RHO
    out = {}
    for tag, rho in (("img", keep), ("zero", 0.0)):
        RHO = rho
        out[tag] = (_footprint_potentials(cov, dx, dy), _total_potential(cov, dx, dy, ny, nx, images=(tag == "img")))
    RHO = keep
    return out
'''

DELTA_LINK_OLD = "                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1\n"
DELTA_LINK_NEW = "                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1 + (f_r[l] * d_phi / (2.0 * np.pi * S[l, 0]) + d_u / (2.0 * np.pi * S[l, 1]) if DELTA_ON else 0.0)\n"
DELTA_SETUP = (
    "    d_phi, d_u = 0.0, 0.0\n"
    "    if R > 1:\n"
    "        pp = _pair_potentials(cov, net.dx, net.dy, ny, nx)\n"
    "        (pi_, ui), (p0, u0) = pp['img'], pp['zero']\n"
    "        d_phi = (pi_[1] - pi_[0]) - (p0[1] - p0[0])\n"
    "        d_u = (ring_sum(ui)[1] / cnt[1] - pi_[1]) - (ring_sum(u0)[1] / cnt[1] - p0[1])\n"
    "        d_phi, d_u = (max(d_phi, 0.0), max(d_u, 0.0)) if DELTA_CLIP else (d_phi, d_u)\n")


ZONE_ON = False
ZONE_OLD = "            out.append((0, 2, viaconstriction.annulus_out_resistance(S[l, 0], r_c, a_f) + 0.5 * thick[2] / (S[l, 2] * length[2])))\n"
ZONE_NEW = ("            out.append((0, 2, viaconstriction.annulus_out_resistance(S[l, 0], r_c, a_f) + (max(U1z - phi_bz, 0.1 * 0.5 * thick[2] / (S[l, 2] * length[2]) * 2.0 * math.pi * S[l, 2]) / (2.0 * math.pi * S[l, 2]) if U1z is not None else 0.5 * thick[2] / (S[l, 2] * length[2]))))\n")
ZONE_ANCHOR = "    r_c = math.sqrt(cnt[1] * cell / math.pi)\n"
ZONE_SETUP = ("    phi_bz = _footprint_potentials(cov, net.dx, net.dy)[1]\n"
              "    U1z = _ring1_potential(cov, net.dx, net.dy, ny, nx, idx2 == 2) if (R > 2 and int((cov > 0).sum()) <= IMAGE_MAX_CELLS) else None\n")


def zone_patch(text):
    """!
    @brief The same first-link change in the zone model: the half ring of A to ring 1 is replaced by (U1 - phi_boundary) / (2 pi S) with the images.
    @param text Edited source.
    @return Source with the zone link patched.
    @throws RuntimeError When an anchor is missing.
    """
    for old_, new_ in ((ZONE_ANCHOR, ZONE_ANCHOR + ZONE_SETUP), (ZONE_OLD, ZONE_NEW)):
        if text.count(old_) != 1:
            raise RuntimeError("anchor missing: " + old_[:50])
        text = text.replace(old_, new_)
    return text


def image_source(name, text, rho_mode):
    """!
    @brief Text of lumped.py with the image potentials ("img": link of ring 0 and micro peak only; "pot": plus the potential links of ring to ring).
    @param name "img" or "pot".
    @param text Source of pcbthermal/lumped.py.
    @param rho_mode "one" (insulated edge), "robin" (reflection from the edge film) or a number.
    @return Edited source.
    @throws RuntimeError When an anchor is missing.
    """
    zone = rho_mode.endswith("zone")
    rho_mode = rho_mode[:-4].rstrip("+") or "one" if zone else rho_mode
    text = text + IMAGE_TAIL + RHO_TAIL + f"\nRHO_MODE = {rho_mode!r}\n"
    if name in ("delta", "delta_clip"):
        text += POT_TAIL + DELTA_TAIL + f"\nDELTA_ON = True\nDELTA_CLIP = {name == 'delta_clip'}\n"
        if text.count(RHO_ANCHOR) != 1 or text.count(DELTA_LINK_OLD) != 1:
            raise RuntimeError("anchor missing: delta")
        text = text.replace(RHO_ANCHOR, "    _set_rho(net)\n" + RHO_ANCHOR)
        # the setup needs ring_sum, cnt and R, which exist after the ring bookkeeping: put it right before the first call of the potentials
        text = text.replace(POT_ANCHOR, POT_ANCHOR + DELTA_SETUP)
        return text.replace(DELTA_LINK_OLD, DELTA_LINK_NEW)
    if text.count(RHO_ANCHOR) != 1:
        raise RuntimeError("anchor missing: rho")
    text = text.replace(RHO_ANCHOR, "    _set_rho(net)\n" + RHO_ANCHOR)
    if name == "first":
        # the footprint-to-ring-1 link alone, with the ring-1 mean potential computed on ring 1 only (cost of the proposal)
        text += POT_TAIL.split("def _total_potential")[0] + (Path(__file__).with_name("tail_fast.txt").read_text())
        old_link = LINK_OLD.split("\n")
        new_first = ("            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])\n"
                     "            if k == 0:\n"
                     "                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + (max(U1 - phi_bnd, 0.1 * half_k1 * 2.0 * np.pi * S[l, 1]) / (2.0 * np.pi * S[l, 1]) if U1 is not None else half_k1)\n"
                     "            return " + old_link[3].split("return ", 1)[1] + "\n")
        anchor = POT_ANCHOR
        setup = "    U1 = _ring1_potential(cov, net.dx, net.dy, ny, nx, idx == 1) if (R > 1 and int((cov > 0).sum()) <= IMAGE_MAX_CELLS) else None\n"
        for old_, new_ in ((anchor, anchor + setup), (LINK_OLD, new_first)):
            if text.count(old_) != 1:
                raise RuntimeError("anchor missing: " + old_[:50])
            text = text.replace(old_, new_)
        if zone:
            text = zone_patch(text)
        return text
    if name in ("pot", "pot_first", "pot_rings"):
        text += POT_TAIL
        lines = LINK_NEW.split("\n")             # lines 0 to 2: half_k1 and the footprint-to-ring-1 link, line 3: the ring-to-ring link
        old_lines = LINK_OLD.split("\n")
        if name == "pot_first":
            link = "\n".join(lines[:3] + old_lines[3:])
        elif name == "pot_rings":
            link = "\n".join(old_lines[:3] + lines[3:])
        else:
            link = LINK_NEW
        for old_, new_ in ((POT_ANCHOR, POT_ANCHOR + "    U_ring = ring_sum(_total_potential(cov, net.dx, net.dy, ny, nx)) / cnt\n"), (LINK_OLD, link)):
            if text.count(old_) != 1:
                raise RuntimeError("anchor missing: " + old_[:50])
            text = text.replace(old_, new_)
    return text


def source(name, text, power=1.0):
    """!
    @brief The text of lumped.py with the edits of one variant.
    @param name Variant name ("program", "expo", "expo_peak").
    @param text Source of pcbthermal/lumped.py.
    @param power Exponent of omega.
    @return Edited source.
    @throws RuntimeError When an anchor is missing or not unique.
    @throws ValueError Unknown variant.
    """
    if name == "program":
        return text
    if name.startswith(("img", "pot", "delta", "first")):
        base, _, mode = name.partition(":")
        return image_source(base, text, mode or "one")
    if name not in ("expo", "expo_peak"):
        raise ValueError(name)
    for old, new in REPL:
        if text.count(old) != 1:
            raise RuntimeError("anchor missing or repeated: " + old[:60])
        text = text.replace(old, new)
    text += OMEGA_TAIL + f"\nOMEGA_POWER = {power!r}\nOMEGA_PEAK = {name == 'expo_peak'}\n"
    return text


_CACHE = {}


def load(name, power=1.0):
    """!
    @brief The variant as a module of the package pcbthermal.
    @param name Variant name.
    @param power Exponent of omega.
    @return Module.
    """
    key = (name, power)
    if key in _CACHE:
        return _CACHE[key]
    import pcbthermal.lumped as orig
    spec = importlib.util.spec_from_loader(f"pcbthermal.lumped_{name}_{power}", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "pcbthermal"
    mod.__file__ = orig.__file__
    sys.modules[spec.name] = mod
    exec(compile(source(name, Path(orig.__file__).read_text(), power), f"lumped_{name}", "exec"), mod.__dict__)
    _CACHE[key] = mod
    return mod


def install(name, power=1.0):
    """!
    @brief Make pcbthermal.api call the variant for the Lumped model.
    @param name Variant name.
    @param power Exponent of omega.
    @return None.
    """
    import pcbthermal.api as api
    api.lumped = load(name, power)
