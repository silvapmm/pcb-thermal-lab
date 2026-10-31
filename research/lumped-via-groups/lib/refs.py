#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file refs.py
@brief The simple boards of the via-group study, their independent fine-grid references (cached on disk) and the Lumped variants that are compared.
@details A "spec" is a plain dict describing a square board of full copper planes with a square source on the top copper and an n x n via array under it:
         `layers, n, pitch, dia, fill, side, src, power`, optionally `offset` (mm) and `shape` ("array" or "row": a row of `n` vias along x). The reference is the layered fine-grid
         solver `sheets2d` (1/16 mm; the layered model of the program with every barrel drawn at its real size, nothing of the program imported by the solver) read through
         `research/lumped-analytic-vias/lib/harness.py`. For each spec it stores, per layer: the footprint mean, the mean over the core (the square that the vias cover, one pitch
         wider than the outer vias) and over the rest of the footprint, the maximum of the source layer, with and without vias. The cache is `out/refcache/*.json` (git-ignored).
         `VARIANTS` maps a name to a context-manager factory (the Lumped patches of this folder and of `lumped-analytic-vias`).
"""

import contextlib
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FOLDER))
sys.path.insert(0, os.path.join(ROOT, "research", "lumped-analytic-vias", "lib"))
sys.path.insert(0, HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import cases                                                                 # noqa: E402
import harness as hz                                                         # noqa: E402
import lumped_groups as lg                                                   # noqa: E402
import lumped_zones as lz                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402

CACHE = os.path.join(FOLDER, "out", "refcache")

DEFAULT = dict(layers=4, n=3, pitch=1.0, dia=0.3, fill=0.0, side=30.0, src=10.0, power=3.0, offset=(0.0, 0.0), shape="array")


def make_problem(spec):
    """!
    @brief Build the Problem of a spec.
    @param spec dict (see the module header); missing keys take `DEFAULT`. Extra keys: `src_aspect` (the source is `src * aspect` by `src / aspect` mm, same area) and `clusters`
           (a list of (dx_mm, dy_mm, n, pitch_mm): the vias are those n x n arrays centred at the board centre plus the offsets; the key `n` is then ignored).
    @return Problem.
    """
    s = {**DEFAULT, **spec}
    p = cases.array(s["layers"], s["n"], s["pitch"], s["dia"], s["fill"], s["side"], s["src"], s["power"], 1.6, 10.0, 200.0, tuple(s["offset"]))
    if s.get("src_aspect"):
        c = s["side"] / 2 + 0.0
        w, h = s["src"] * s["src_aspect"], s["src"] / s["src_aspect"]
        x0, y0 = c - w / 2 + s["offset"][0], c - h / 2 + s["offset"][1]
        p.heaters[0].polygon = np.array([(x0 * 1e-3, y0 * 1e-3), ((x0 + w) * 1e-3, y0 * 1e-3), ((x0 + w) * 1e-3, (y0 + h) * 1e-3), (x0 * 1e-3, (y0 + h) * 1e-3)])
    if s.get("clusters"):
        p.vias = []
        c = s["side"] / 2
        for dx, dy, n, pitch in s["clusters"]:
            h = (n - 1) / 2
            for i in range(n):
                for j in range(n):
                    p.add_via(c + dx + (i - h) * pitch, c + dy + (j - h) * pitch, s["dia"], fill_k=s["fill"])
    return p


def _key(spec):
    """!
    @brief Cache key of a spec.
    @param spec dict.
    @return str.
    """
    s = {**DEFAULT, **spec}
    s["offset"] = list(s["offset"])
    return hashlib.sha1(json.dumps(s, sort_keys=True).encode()).hexdigest()[:16]


def reference(spec, dx_mm=1.0 / 16):
    """!
    @brief Fine-grid layered reference of a spec (cached).
    @param spec dict.
    @param dx_mm Cell of the reference in mm.
    @return dict with E, t_with, t_without (maxima of the source layer, K) and, per layer, foot / core / ann means with vias, foot_nv without.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, _key(spec) + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    s = {**DEFAULT, **spec}
    pc.load_libraries()
    p = make_problem(spec)
    fields = {}
    for lab, vias in (("with", True), ("without", False)):
        T, dx = hz.reference_field(p, dx_mm, with_vias=vias)
        fields[lab] = T
    T = fields["with"]
    nn = T.shape[1]
    xs = (np.arange(nn) + 0.5) * dx
    px = [q[0] for q in p.heaters[0].polygon]
    py = [q[1] for q in p.heaters[0].polygon]
    inside = (xs[None, :] > min(px)) & (xs[None, :] < max(px)) & (xs[:, None] > min(py)) & (xs[:, None] < max(py))
    # the core: the cells within half a pitch of a via (the union of the squares around the vias), inside the footprint
    core = np.zeros_like(inside)
    half = s["pitch"] / 2 * 1e-3
    if s.get("clusters"):
        half = min(c[3] for c in s["clusters"]) / 2 * 1e-3
    for v in p.vias:
        core |= (np.abs(xs[None, :] - v.x) < half) & (np.abs(xs[:, None] - v.y) < half)
    core &= inside
    ann = inside & ~core
    out = {}
    L = T.shape[0]
    out["t_with"] = float(T[0].max())
    out["t_without"] = float(fields["without"][0].max())
    out["E"] = out["t_without"] - out["t_with"]
    out["foot"] = [float(T[l][inside].mean()) for l in range(L)]
    out["core"] = [float(T[l][core].mean()) for l in range(L)]
    out["ann"] = [float(T[l][ann].mean()) for l in range(L)]
    out["foot_nv"] = [float(fields["without"][l][inside].mean()) for l in range(L)]
    out["core_share"] = float(core.sum() / inside.sum())
    json.dump(out, open(path, "w"))
    return out


def lumped_E(spec, name):
    """!
    @brief Via effect E of one Lumped variant on a spec.
    @param spec dict.
    @param name Key of `VARIANTS`.
    @return float E in K (max rise without vias minus with vias, on the 0.5 mm raster).
    """
    pc.load_libraries()
    p = make_problem(spec)
    q0 = hz.no_vias(p)
    return hz.effect(p, "lumped", VARIANTS[name], 0.5, q0)


def variants_f(f):
    """!
    @brief The patch with the full group term scaled by f.
    @param f Factor on the macro resistance.
    @return Context-manager factory.
    """
    return lambda: lg.patched(macro="all", macro_scale=f)


VARIANTS = {
    "L_prog": lambda: contextlib.nullcontext(),
    "L_ring": lambda: lg.patched(macro="none", micro="ring"),
    "L_nn": lambda: lg.patched(macro="none"),
    "L_grp0": lambda: lg.patched(macro="all"),
    "L_out": lambda: lg.patched(macro="out"),
    "L_loss": lambda: lg.patched(macro="loss"),
    # the ladder of the zone model, one change at a time
    "L_zone0": lambda: lz.patched(geometry="disc", core_int=0.0, micro_peak=False, peak="annulus"),          # Krogh link alone, concentric discs
    "L_zone_c1": lambda: lz.patched(geometry="disc", core_int=1.0, micro_peak=False, peak="annulus"),        # + the core-internal resistance Q / (8 pi S)
    "L_zone_disc": lambda: lz.patched(geometry="disc", core_int=1.0, micro_peak=True, peak="annulus"),       # + the micro peak
    "L_zone_p": lambda: lz.patched(geometry="potential", core_int=0.0, micro_peak=True, peak="annulus"),     # link of the real shapes (logarithmic potentials)
    "L_zone": lambda: lz.patched(geometry="potential", core_int=0.0, micro_peak=True, peak="potential_lossy"),  # + the peak of the real shapes with the K0 kernel: the proposal
    "L_zone_k": lambda: lz.patched(geometry="potential", core_int=0.0, micro_peak=True, peak="potential_lossy", micro_scale=0.0),  # no micro well: the vertical conductivity of the array
}
