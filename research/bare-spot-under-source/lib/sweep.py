#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sweep.py
@brief The list of cases of the window sweep and the runner that measures the program's models and the treatments against the resolved reference, with a cache of the reference.
@details Stack-ups: 2 layers 1.6 mm and 0.8 mm (simple), the typical 4 and 6 layer stack-ups of the program. Windows: none, 2, 4, 6, 8, 12, 20 mm squares centred under a 6 mm part,
         on the top copper only; plus windows through every copper layer and a half-bare footprint. The reference (lib/cases.reference at 0.25 mm, 8 sub-slabs per gap) is cached in
         out/ref_cache.json (git-ignored) under the case description.
"""

import json
import os

import cases as C
import layered as LY
import treatments as TR

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "out", "ref_cache.json")

STACKS = {
    "2L 1.6 mm": dict(layers=2, stack="simple", thickness=1.6),
    "2L 0.8 mm": dict(layers=2, stack="simple", thickness=0.8),
    "4L typical": dict(layers=4, stack="template"),
    "6L typical": dict(layers=6, stack="template"),
}
WINDOWS = (0, 2, 4, 6, 8, 12, 20)
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def make_case(stack, w, window_layers=(0,), half=False, **kw):
    """!
    @brief A case of the sweep.
    @param stack Key of STACKS.
    @param w Side of the centred square window in mm (0: full copper).
    @param window_layers 0-based layers that carry the window.
    @param half True: a half-bare footprint (a 10 x 20 mm window whose right edge is the centre line of the part).
    @param kw Other Case fields.
    @return Case.
    """
    c = 15.0
    win = None
    name = f"{stack} w={w}"
    if half:
        win = (c - 10.0, c - 10.0, c, c + 10.0)
        name = f"{stack} half-bare"
    elif w:
        win = C.centred_window(w)
    if window_layers != (0,):
        name += f" layers {','.join(str(i + 1) for i in window_layers)}"
    return C.Case(name, window=win, window_layers=window_layers, **STACKS[stack], **kw)


def key(case, dx, nsub):
    """!
    @brief Cache key of a reference run.
    @param case Case.
    @param dx Fine cell in mm.
    @param nsub Sub-slabs per gap.
    @return str.
    """
    d = dict(vars(case))
    d.pop("notes")
    d.pop("extra")
    return json.dumps([d, dx, nsub], sort_keys=True, default=str)


def cached_reference(case, dx=0.25, nsub=8):
    """!
    @brief The reference peak and mean of a case, from the cache or computed.
    @param case Case.
    @param dx Fine cell in mm.
    @param nsub Sub-slabs per gap.
    @return dict from cases.reference.
    """
    store = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    k = key(case, dx, nsub)
    if k not in store:
        store[k] = C.reference(case, dx, nsub)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(store, open(CACHE, "w"))
    return store[k]


def run_case(case, cells=(1.0, 0.5), models=MODELS, treatments=()):
    """!
    @brief Reference, the program's models and the treatments for one case.
    @param case Case.
    @param cells Cell sizes in mm.
    @param models Model keys of the program.
    @param treatments List of treatment dicts (lib/treatments.py).
    @return dict with ref (max, mean), models {cell: {model: peak}}, treat {cell: {label: {peak, unknowns}}}.
    """
    ref = cached_reference(case)
    p = C.problem(case)
    out = {"name": case.name, "ref": {"max": ref["max"], "mean": ref["mean"]}, "models": {}, "treat": {}}
    for cell in cells:
        out["models"][str(cell)] = {m: C.program_peak(case, m, cell, p) for m in models}
        if treatments:
            net = LY.network(p, cell)
            gaps, kz, kxy = LY.gap_data(p)
            out["treat"][str(cell)] = {label(t): TR.run(p, net, t, gaps, kz, kxy) for t in treatments}
    return out


def label(t):
    """!
    @brief Short text of a treatment.
    @param t Treatment dict.
    @return str.
    """
    if t["kind"] == "none":
        return "program"
    if t["kind"] == "vert":
        return "vert"
    if t["kind"] == "nodes":
        return f"n={t['n']}" + ("+v" if t.get("vert") else "") + (f",m={t['margin']}" if "margin" in t else "")
    return f"skin={t['alpha']}"
