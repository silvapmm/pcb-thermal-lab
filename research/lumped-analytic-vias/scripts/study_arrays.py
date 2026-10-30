#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_arrays.py
@brief Simple boards 2 to 4: a lone via and a row beside a source, a via array under a source (pitch 3.5 to 1 mm, 2/4/6 layers) and a thermal pad; open and copper-filled barrels.
@details Each board adds ONE thing to the unit cell of `study_unit_cell.py`:
         * `lone`   a via 2 to 8 mm from a 3 mm source: the lateral gradient and the ring (Lumped) or tile (Analytic) structure, one via, no neighbour;
         * `row`    five vias in a row away from the source: neighbours, and a non-axisymmetric sink (the rings of the Lumped model are isotherms around the footprint);
         * `array`  3 x 3 vias under a 10 mm source at 3.5, 2, 1.5, 1 mm pitch (2, 4, 6 layers, drill 0.3 and 0.6): the vias inside the footprint, the dense limit;
         * `pad`    5 x 5 and 3 x 3 at 1.2 and 0.8 mm under a 6 mm source on a 20 mm board (the usual thermal pad).
         Metric: the via effect E (open and copper fill) and the copper-fill gain G = E_Cu - E_open against the fine-grid layered reference (`sheets2d`, 1/16 mm).
Usage: python research/lumped-analytic-vias/scripts/study_arrays.py [--quick] [--procs N]   (from the repository root; writes out/arrays.json)
"""

import argparse
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import cases                                                                 # noqa: E402
import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402

NAMES = ["FVM", "FVM_fix", "L_prog", "L_ring", "L_grp0", "L_grp", "A_prog", "A_on", "A_bil", "A_fin"]


def build(kind, params, fill):
    """!
    @brief Build a board of the study.
    @param kind "lone", "row", "array" or "pad".
    @param params Tuple of parameters of the kind.
    @param fill Fill conductivity in W/mK.
    @return Problem.
    """
    if kind == "lone":
        layers, dia, dist = params
        return cases.lone_via(30.0, dia, fill, layers, 3.0, dist)
    if kind == "row":
        layers, dia = params
        return cases.row(5, 1.0, dia, fill, 16.0, layers, 3.0, 1.0)
    if kind == "array":
        layers, dia, pitch = params
        return cases.array(layers, 3, pitch, dia, fill)
    if kind == "pad":
        layers, n, pitch = params
        return cases.pad(layers, n, pitch, 0.3, fill, 20.0, 6.0)
    raise ValueError(kind)


def run_case(task):
    """!
    @brief One configuration: reference and errors for the open and the copper-filled barrel, and the error of the copper-fill gain.
    @param task (kind, params).
    @return dict.
    """
    kind, params = task
    pc.load_libraries()
    out = {"task": [kind, list(params)], "E_ref": {}, "err": {}, "E": {}}
    for fill in (0.0, 385.0):
        prob = build(kind, params, fill)
        e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
        q0 = hz.no_vias(prob)
        e = {n: hz.effect(prob, hz.VARIANTS[n][0], hz.VARIANTS[n][1], 0.5, q0) for n in NAMES}
        out["E_ref"][str(fill)] = e_ref
        out["E"][str(fill)] = e
        out["err"][str(fill)] = {n: 100.0 * (e[n] / e_ref - 1.0) for n in NAMES}
    g_ref = out["E_ref"]["385.0"] - out["E_ref"]["0.0"]
    out["G_ref"] = g_ref
    out["gain_err"] = {n: 100.0 * ((out["E"]["385.0"][n] - out["E"]["0.0"][n]) / g_ref - 1.0) for n in NAMES}
    return out


def main():
    """!
    @brief Run the cases and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=5)
    args = ap.parse_args()
    tasks = []
    for layers in ([2] if args.quick else [2, 4]):
        for dia in (0.3, 0.6):
            for dist in (2.0, 4.0, 8.0):
                tasks.append(("lone", (layers, dia, dist)))
            tasks.append(("row", (layers, dia)))
    for layers in ([4] if args.quick else [2, 4, 6]):
        for dia in ((0.3,) if args.quick else (0.3, 0.6)):
            for pitch in (3.5, 2.0, 1.5, 1.0):
                tasks.append(("array", (layers, dia, pitch)))
    for n, pitch in ((3, 1.2), (5, 1.2), (5, 0.8)):
        tasks.append(("pad", (4, n, pitch)))
    with mp.Pool(args.procs) as pool:
        rows = pool.map(run_case, tasks, chunksize=1)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", "arrays.json"), "w"), indent=1)
    print("## Error of the via effect against the fine-grid layered reference (percent of E); Cu = copper fill\n")
    print("| board | layers | params | fill | E_ref K | " + " | ".join(NAMES) + " |")
    print("| :-- | --: | :-- | :-- | --: |" + " --: |" * len(NAMES))
    for r in rows:
        kind, params = r["task"]
        for fill, lab in (("0.0", "open"), ("385.0", "Cu")):
            print(f"| {kind} | {params[0]} | {params[1:]} | {lab} | {r['E_ref'][fill]:.3f} | " + " | ".join(f"{r['err'][fill][n]:+.1f}" for n in NAMES) + " |")
    print("\n## Error of the copper-fill gain (the symptom of the roadmap item A6), percent\n")
    print("| board | layers | params | G_ref K | " + " | ".join(NAMES) + " |")
    print("| :-- | --: | :-- | --: |" + " --: |" * len(NAMES))
    for r in rows:
        kind, params = r["task"]
        print(f"| {kind} | {params[0]} | {params[1:]} | {r['G_ref']:.3f} | " + " | ".join(f"{r['gain_err'][n]:+.1f}" for n in NAMES) + " |")
    print("\n## Summary: mean and maximum absolute error of E (both fills) and of the gain, by board kind\n")
    for kind in ("lone", "row", "array", "pad"):
        sel = [r for r in rows if r["task"][0] == kind]
        if not sel:
            continue
        print(f"\n{kind}\n\n| variant | E mean | E max | gain mean | gain max |\n| :-- | --: | --: | --: | --: |")
        for n in NAMES:
            ev = [abs(r["err"][f][n]) for r in sel for f in ("0.0", "385.0")]
            gv = [abs(r["gain_err"][n]) for r in sel]
            print(f"| {n} | {sum(ev) / len(ev):.1f} | {max(ev):.1f} | {sum(gv) / len(gv):.1f} | {max(gv):.1f} |")


if __name__ == "__main__":
    main()
