#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_lumped.py
@brief S4 for the Lumped model: the Krogh well per plane, and what can be fixed cheaply of its two known limits (a lone via or a row outside the footprint, dense arrays of open barrels).
@details Known limits of `research/lumped-analytic-vias`: a lone via and a row outside the footprint are 9 to 31 % off in a small effect and depend on the ring count; dense arrays of open
         barrels are 8 to 24 % under. The model is a ring network around the footprint: a ring carries one mean temperature, the via sits at one radius, so a via outside the
         footprint draws heat from a ring that is not where its gradient is.
         Part 1 (lone via): distance from the source centre 2 to 10 mm, rings 6, 10, 16, 24: error of the via effect of the program, the micro well (`L_ring`, `L_nn`), the cluster
                 proposal (`L_grp0`) and with caps of the cell radius (`lone_cap` 1, 2, 3 fin lengths); and the size of the effect against the rise of the source, which says when the
                 error matters.
         Part 2 (row): 1 to 9 vias away from a source, pitch 1.0 and 1.5 mm, the same variants.
         Part 3 (dense open barrels): 3 x 3 and 5 x 5 arrays at 1.2 to 0.8 mm, open and copper, the variants and the factors `macro_scale` 0.5, 1, 1.5 and `scale`.
         Part 4 (a warning criterion): the error of `L_grp0` against the distance of the via from the footprint edge in units of the ring width, to place a threshold for a warning.
         Every error is 100 (E_model / E_ref - 1) against the fine-grid layered reference.
Usage: python research/young-omega-tiles/scripts/study_s4_lumped.py [--quick]   (from the repository root; minutes). Results go to out/s4_lumped.json.
"""

import contextlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-via-groups", "lib"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import harness as hz                                                        # noqa: E402
import lumped_patch as lp                                                   # noqa: E402
import lumped_zones as lz                                                   # noqa: E402
import cases                                                                # noqa: E402

QUICK = "--quick" in sys.argv
RES = {}

VARIANTS = {
    "program": lambda: contextlib.nullcontext(),
    "micro ring": lambda: lp.patched("krogh", cell="ring"),
    "micro nn": lambda: lp.patched("krogh", cell="nn"),
    "cluster (L_grp0)": lambda: lp.patched("krogh", cell="nn", cluster=True),
    "cluster, macro cap 0.75": lambda: lp.patched("krogh", cell="nn", cluster=True, macro_cap=0.75),
    "cluster, lone cap 1": lambda: lp.patched("krogh", cell="nn", cluster=True, lone_cap=1.0),
    "cluster, lone cap 2": lambda: lp.patched("krogh", cell="nn", cluster=True, lone_cap=2.0),
    "cluster, lone cap 3": lambda: lp.patched("krogh", cell="nn", cluster=True, lone_cap=3.0),
    "zones (lumped-via-groups)": lambda: lz.patched(geometry="potential", core_int=0.0, micro_peak=True, peak="potential_lossy"),
}


def errors(prob, e_ref, names, rings=10):
    """!
    @brief Errors of the Lumped variants on one board.
    @param prob Problem with vias.
    @param e_ref Reference effect in K.
    @param names Variant names.
    @param rings Rings of the Lumped model.
    @return dict name -> percent.
    """
    q0 = hz.no_vias(prob)
    out = {}
    for n in names:
        with VARIANTS[n]():
            out[n] = 100.0 * (sc.effect(prob, "lumped", 0.5, 300, rings, q0) / e_ref - 1.0)
    return out


def part1():
    """!
    @brief Lone via: distance and rings.
    @return None.
    """
    print("## 1. Lone via (copper fill, 2 layers, 3 mm source on a 30 mm board): error of the via effect against the distance and the number of rings (percent)\n")
    names = ["program", "micro ring", "micro nn", "cluster (L_grp0)", "cluster, lone cap 1", "cluster, lone cap 2", "cluster, lone cap 3", "zones (lumped-via-groups)"]
    dists = (2.0, 4.0, 8.0) if QUICK else (2.0, 3.0, 4.0, 6.0, 8.0, 10.0)
    rings = (10,) if QUICK else (6, 10, 16, 24)
    rows, out = [], []
    for d in dists:
        prob = cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, d)
        e_ref = sc.reference_e(prob, 1.0 / 16, f"lone{d}")
        q0 = hz.no_vias(prob)
        t_src = sc.rise(q0, "lumped", 0.5, 300, 10)
        for r in rings:
            er = errors(prob, e_ref, names, r)
            rows.append([d, r, f"{e_ref:.3f}", f"{100 * e_ref / t_src:.1f} %"] + [f"{er[n]:+.1f}" for n in names])
            out.append({"distance": d, "rings": r, "e_ref": e_ref, "e_over_rise_pct": 100 * e_ref / t_src, "err": er})
    outio.table(["distance mm", "rings", "E_ref K", "E / source rise"] + names, rows)
    RES["lone"] = out


def part2():
    """!
    @brief Rows.
    @return None.
    """
    print("## 2. Row of n vias beside a 3 mm source (copper fill, 2 layers, 16 mm board, gap 1 mm): error against n and pitch (percent)\n")
    names = ["program", "micro nn", "cluster (L_grp0)", "cluster, macro cap 0.75", "cluster, lone cap 2", "zones (lumped-via-groups)"]
    rows, out = [], []
    for pitch in (1.0, 1.5):
        for n in ((1, 5) if QUICK else (1, 2, 3, 5, 7, 9)):
            side = max(16.0, 2.0 * math.ceil(2.5 + (n - 1) * pitch + 2.0))          # the row runs from the source edge to the right: keep 2 mm of copper beyond the last via
            prob = cases.row(n, pitch, 0.3, 385.0, side, 2, 3.0, 1.0)
            e_ref = sc.reference_e(prob, 1.0 / 16, f"row{n}-{pitch}")
            er = errors(prob, e_ref, names)
            rows.append([pitch, n, f"{e_ref:.3f}"] + [f"{er[k]:+.1f}" for k in names])
            out.append({"pitch": pitch, "n": n, "e_ref": e_ref, "err": er})
    outio.table(["pitch mm", "vias", "E_ref K"] + names, rows)
    RES["row"] = out


def part3():
    """!
    @brief Dense arrays of open barrels.
    @return None.
    """
    print("## 3. Dense arrays under a source, open and copper-filled barrels: error of the via effect (percent)\n")
    names = ["program", "micro ring", "cluster (L_grp0)", "cluster, macro cap 0.75", "zones (lumped-via-groups)"]
    rows, out = [], []
    boards = [("3 x 3 pitch 3.5", lambda f: cases.array(4, 3, 3.5, 0.3, f)), ("3 x 3 pitch 1.0", lambda f: cases.array(4, 3, 1.0, 0.3, f)),
              ("5 x 5 pitch 1.2 pad", lambda f: cases.pad(4, 5, 1.2, 0.3, f)), ("5 x 5 pitch 0.8 pad", lambda f: cases.pad(4, 5, 0.8, 0.3, f, 20.0, 6.0))]
    for label, build in boards:
        for fill, fl in ((0.0, "open"), (385.0, "Cu")):
            prob = build(fill)
            e_ref = sc.reference_e(prob, 1.0 / 16, f"{label}-{fl}")
            er = errors(prob, e_ref, names)
            # Knobs that scale the constrictions: do they close the gap on open barrels without breaking the filled ones?
            knobs = {}
            for ms in (0.5, 1.5):
                with lp.patched("krogh", cell="nn", cluster=True, macro_scale=ms):
                    knobs[f"macro x{ms}"] = 100.0 * (sc.effect(prob, "lumped", 0.5, 300, 10) / e_ref - 1.0)
            for s in (0.8, 1.2):
                with lp.patched("krogh", cell="nn", cluster=True, scale=s):
                    knobs[f"all x{s}"] = 100.0 * (sc.effect(prob, "lumped", 0.5, 300, 10) / e_ref - 1.0)
            rows.append([label, fl, f"{e_ref:.2f}"] + [f"{er[n]:+.1f}" for n in names] + [f"{v:+.1f}" for v in knobs.values()])
            out.append({"board": label, "fill": fl, "e_ref": e_ref, "err": er, "knobs": knobs})
    outio.table(["board", "fill", "E_ref K"] + names + ["macro x0.5", "macro x1.5", "all x0.8", "all x1.2"], rows)
    RES["dense"] = out


def part4():
    """!
    @brief Where a warning belongs: the error of the cluster variant against the distance of the via from the footprint edge in ring widths.
    @return None.
    """
    print("## 4. Error of the Lumped proposal against the distance from the footprint edge (lone via, 3 mm source, rings 10)\n")
    rows, out = [], []
    for d in (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
        prob = cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, d)
        e_ref = sc.reference_e(prob, 1.0 / 16, f"lone{d}")
        er = errors(prob, e_ref, ["cluster (L_grp0)"])["cluster (L_grp0)"]
        edge = d - 1.5
        rows.append([d, f"{edge:.1f}", f"{e_ref:.3f}", f"{er:+.1f}"])
        out.append({"distance": d, "edge_mm": edge, "e_ref": e_ref, "err": er})
    outio.table(["via from source centre mm", "from footprint edge mm", "E_ref K", "error of L_grp0 %"], rows)
    RES["edge"] = out


def main():
    """!
    @brief Run the parts and save.
    @return None.
    """
    sc.load_libraries()
    for part in (part1, part2, part3, part4):
        part()
    print("saved", outio.save("s4_lumped", RES))


if __name__ == "__main__":
    main()
