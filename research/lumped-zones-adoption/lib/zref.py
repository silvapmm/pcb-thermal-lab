#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file zref.py
@brief Common ground of the studies of this folder: the boards (re-used from `lumped-via-groups`, `lumped-analytic-vias` and `point-via-convergence`), their fine-grid references (cached), the Lumped variants on the 2.4.5 program and the error tables.
@details WRITTEN BUT NOT YET RUN. The boards and the independent references are those of the earlier investigation (`research/lumped-via-groups/lib/refs.py`): a square board of full copper
         planes with a square source and an n x n via array (a "spec"), solved by the fine-grid layered solver `sheets2d` at 1/16 mm, which imports nothing of the program. The variants here are
         the program as it is in 2.4.5 (`P245`: micro well plus the cluster well with the macro cap, Kron reduced) and the zoned network of `zoned_lumped.py` on top of it, in the options
         that answer the questions of the README. The via effect `E = T_max(no vias) - T_max(vias)` is the metric, as before; error = 100 (E_model / E_ref - 1) %, positive when the model is
         cooler than the reference with vias.
         The reference cache is `out/refcache` of THIS folder (git-ignored). Because the references of the earlier folder were made with the program up to 2.4.4, they are recomputed here;
         `use_old_cache()` copies them instead (the numbers of a board without vias come from the program's own network: `program_cases.layer_parameters`; the laminate rule of 2.4.5 does not
         touch the full-copper four-layer boards, which the first run checks by comparing the two caches on three boards).
"""

import contextlib
import json
import math
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
RESEARCH = os.path.dirname(FOLDER)
ROOT = os.path.dirname(RESEARCH)
for sub in ("lumped-via-groups/lib", "lumped-via-groups/scripts", "lumped-analytic-vias/lib", "lumped-analytic-vias/scripts", "point-via-convergence/lib"):
    sys.path.insert(0, os.path.join(RESEARCH, sub))
sys.path.insert(0, HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import refs                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402

OUT = os.path.join(FOLDER, "out")
refs.CACHE = os.path.join(OUT, "refcache")                                   # the references of this folder
OLD_CACHE = os.path.join(RESEARCH, "lumped-via-groups", "out", "refcache")

# The variants. A factory returns a context manager; the program is untouched outside it.
VARIANTS = {
    "P245": contextlib.nullcontext,                                                                       # the program as it is
    "Z_none": lambda: zl.patched(zone_macro="none"),                                                      # zones, micro wells in the zones, no macro term in the zones
    "Z_cap": lambda: zl.patched(zone_macro="cap"),                                                        # zones with the program's cluster well (macro cap 0.75) in the zones
    "Z_none_nomp": lambda: zl.patched(zone_macro="none", micro_peak=False),                               # ablation: no micro peak
    "Z_none_fr": lambda: zl.patched(zone_macro="none", bessel_ring1=True),                                # ablation: Bessel factor on the A-to-ring-1 link
    "Z_cap_nocb": lambda: zl.patched(zone_macro="cap", core_peak=False),                                  # ablation: no bump of a hot core
    "Z_off": lambda: zl.patched(zones=False),                                                             # the zone code present but switched off: must equal P245
    "Z_none_stride": lambda: zl.patched(zone_macro="none", decimation="stride"),                          # the research folder's decimation of the integrals
}


def use_old_cache():
    """!
    @brief Copy the reference cache of `lumped-via-groups` (made with the program up to 2.4.4) into the cache of this folder, for the boards that are not there yet.
    @return int Number of files copied.
    """
    os.makedirs(refs.CACHE, exist_ok=True)
    n = 0
    if os.path.isdir(OLD_CACHE):
        for f in os.listdir(OLD_CACHE):
            if not os.path.exists(os.path.join(refs.CACHE, f)):
                shutil.copy(os.path.join(OLD_CACHE, f), os.path.join(refs.CACHE, f))
                n += 1
    return n


def lumped_E(spec, name, cell_mm=0.5):
    """!
    @brief Via effect E of one Lumped variant on a spec.
    @param spec Spec dict of `refs.make_problem`.
    @param name Key of `VARIANTS`.
    @param cell_mm Raster cell in mm (the program clips the Lumped cell to 0.5 to 1.0 mm).
    @return float E in K.
    """
    pc.load_libraries()
    p = refs.make_problem(spec)
    q0 = hz.no_vias(p)
    with VARIANTS[name]():
        return pc.max_rise(q0, "lumped", cell_mm) - pc.max_rise(p, "lumped", cell_mm)


def lumped_tmax(problem, name, cell_mm=0.5):
    """!
    @brief Maximum rise of a Problem in one Lumped variant (not the via effect).
    @param problem The Problem.
    @param name Key of `VARIANTS`.
    @param cell_mm Raster cell in mm.
    @return float Rise over the ambient in K.
    """
    pc.load_libraries()
    with VARIANTS[name]():
        return pc.max_rise(problem, "lumped", cell_mm)


def error_pct(e_model, e_ref):
    """!
    @brief Error of a via effect in percent of the reference.
    @param e_model Model via effect in K.
    @param e_ref Reference via effect in K.
    @return float.
    """
    return 100.0 * (e_model / e_ref - 1.0)


def summarize(errors, tol=10.0):
    """!
    @brief Mean and maximum of the absolute error, the signed extremes and the count within a tolerance.
    @param errors list of signed errors in percent.
    @param tol Tolerance in percent.
    @return dict with mean, max, lo, hi, within, n.
    """
    a = np.abs(np.asarray(errors, dtype=float))
    return {"mean": float(a.mean()), "max": float(a.max()), "lo": float(min(errors)), "hi": float(max(errors)), "within": int((a <= tol).sum()), "n": len(errors)}


def table(rows, names, title):
    """!
    @brief A Markdown table of mean / max absolute error and the counts within 10 % of each variant over a set of boards.
    @param rows list of dicts {"err": {name: percent}} (one per board).
    @param names Variants in column order.
    @param title Heading text of the table.
    @return str.
    """
    lines = [f"\n{title} ({len(rows)} boards)\n", "| variant | mean | max | within 10 % | signed range |", "| :-- | --: | --: | --: | :-- |"]
    for n in names:
        s = summarize([r["err"][n] for r in rows])
        lines.append(f"| {n} | {s['mean']:.1f} | {s['max']:.1f} | {s['within']} of {s['n']} | {s['lo']:+.1f} to {s['hi']:+.1f} |")
    return "\n".join(lines)


def save_json(name, data):
    """!
    @brief Write a result file into `out/`.
    @param name File name.
    @param data JSON-serialisable object.
    @return str Path written.
    """
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    return path


def disc_polygon(cx, cy, r, n=96):
    """!
    @brief Polygon of a disc.
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param r Radius in m.
    @param n Vertices.
    @return numpy.ndarray (n, 2) in m.
    """
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.column_stack([cx + r * np.cos(t), cy + r * np.sin(t)])
