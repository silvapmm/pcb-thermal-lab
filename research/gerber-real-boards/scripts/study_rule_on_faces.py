#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_rule_on_faces.py
@brief Do the flow-based faces beat the fill fraction when the program runs WITH the laminate rule of 2.4.5, measured against an independent 3D reference, on synthetic boards of known copper and on the real boards?
@details The question of README 9.2 (the review's open item). Variants (lib/rule_study.py): today_on / today_off (the fill fraction, rule on / off), flow_off and lambda_off (the faces of the earlier study, rule off),
         flow_naive (those faces on the network with the rule on), flow_on and lambda_on (faces built on the copper node after the rule moved its laminate, the rule on).
         Reference: lib/ref3d.py on the same binary masks at the 0.1 mm pixel (laminate in 8 sub-slabs per gap on 2 layers, 3 on 4 layers; both converged to 0.1 % in lib tests / README 10.1).
         Windows of 12 mm, heater 4.8 mm at the centre, cells of 0.6 and 1.2 mm (6 and 12 pixels, even as the faces need), h = 10 W/m2K on both faces, adiabatic sides.
         Parts: `synthetic` (6 patterns x stacks 2solid, 2same, 4), `real` (3 windows per board of the boards of data/, top-layer rule of the earlier study), `holes` (real boards again with the plated holes as vias in
         the program and barrels in the reference). Output: out/rule_on_faces_<part>.json (written after every case; a rerun skips the cases done) and the printed tables.
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/study_rule_on_faces.py --part synthetic|real|holes [--boards a,b] [--quick]
         Memory: one reference solve at a time, 1.5 to 3 GB; run one part per process.
         NOT verified: any measurement on a physical board; heaters other than a 4.8 mm square on the top layer; windows larger than 12 mm; copper thickness other than 35 micrometres.
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import time

import numpy as np

import boardrun
import native_gerber as ng
import onesheet
import registry
import rb_paths
import rule_study as rs
import synth

VARIANTS = ["today_off", "today_on", "flow_off", "lambda_off", "flow_naive", "flow_on", "lambda_on"]
CELLS = (0.6, 1.2)
CENTRE, HEATER, WINDOW = (6.0, 6.0), 4.8, 12.0


def n_sub_for(layers):
    """!
    @brief Sub-slabs of every gap in the reference: 8 for two layers (gap 1.53 mm), 3 for four (gap 0.49 mm).
    @param layers Copper layers.
    @return int.
    """
    return 8 if layers == 2 else 3


def load(path):
    """!
    @brief The rows already done in a result file.
    @param path Path of the JSON file.
    @return list of rows (empty when the file does not exist).
    """
    try:
        with open(path) as fh:
            return json.load(fh)["rows"]
    except (OSError, ValueError, KeyError):
        return []


def save(path, rows, meta):
    """!
    @brief Write the rows and the meta data.
    @param path Path of the JSON file.
    @param rows List of rows.
    @param meta Dict stored beside the rows.
    @return None.
    """
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"meta": meta, "rows": rows}, fh, indent=1)


def synthetic(rows, path, meta, quick):
    """!
    @brief Part synthetic: known patterns.
    @param rows Rows already done (extended in place).
    @param path Result file.
    @param meta Meta data for the file.
    @param quick True: three patterns and the 2-layer stacks only.
    @return None.
    """
    done = {(r["name"], r["cell"]) for r in rows}
    pats = synth.PATTERNS[:3] if quick else synth.PATTERNS
    for stack in ("2solid", "2same", "4"):
        if quick and stack == "4":
            continue
        for pat in pats:
            name = f"{pat}/{stack}"
            if all((name, c) in done for c in CELLS):
                continue
            ib0 = synth.synthetic_board(pat, stack, CELLS[0])
            L = len(ib0.layers)
            t = time.time()
            ref = rs.reference(ib0, CENTRE, HEATER, n_sub_for(L))
            for c in CELLS:
                ib = synth.synthetic_board(pat, stack, c)
                r = rs.run_case(ib, CENTRE, HEATER, n_sub_for(L), VARIANTS, ref=ref)
                rows.append({"name": name, "kind": "synthetic", "layers": L, "cell": c, **r})
                print(f"{name} cell {c}: ref {r['ref_mean']:.1f} K; " + ", ".join(f"{k} {v:+.1f}" for k, v in r["error"].items()), flush=True)
            print(f"  ({time.time() - t:.0f} s)", flush=True)
            save(path, rows, meta)


def real(rows, path, meta, boards, holes, quick):
    """!
    @brief Part real (and holes): windows of the downloaded boards.
    @param rows Rows already done (extended in place).
    @param path Result file.
    @param meta Meta data for the file.
    @param boards List of board keys (None: all with two or more copper layers).
    @param holes True: plated holes as vias / barrels.
    @param quick True: one window per board.
    @return None.
    """
    done = {(r["name"], r["cell"]) for r in rows}
    for key in registry.available():
        r0 = registry.roles(key)
        if len(r0["copper"]) < 2 or (boards and key not in boards):
            continue
        box0 = ng.layer_bbox(r0["outline"]) if r0["outline"] else ng.layer_bbox(r0["copper"][0])
        for w in onesheet.cut_windows(r0["copper"][0], box0, per_board=1 if quick else 3, pix=synth.PIX_MM, window=WINDOW, heater=HEATER, seed=11):
            name = f"{key} ({w['x_left']}, {w['y_bottom']})"
            if all((name, c) in done for c in CELLS):
                continue
            box = (w["x_left"], w["y_bottom"], w["x_left"] + WINDOW, w["y_bottom"] + WINDOW)
            t = time.time()
            ibs = {c: boardrun.import_window(key, box, synth.PIX_MM, c) for c in CELLS}
            L = len(ibs[CELLS[0]].layers)
            ref = rs.reference(_strip(ibs[CELLS[0]], holes), CENTRE, HEATER, n_sub_for(L), holes=holes)
            for c in CELLS:
                r = rs.run_case(ibs[c], CENTRE, HEATER, n_sub_for(L), VARIANTS, holes=holes, ref=ref)
                rows.append({"name": name, "kind": "real", "board": key, "layers": L, "cell": c, "holes": len(ibs[c].holes) if holes else 0, **r})
                print(f"{name} L{L} cell {c}: ref {r['ref_mean']:.1f} K; " + ", ".join(f"{k} {v:+.1f}" for k, v in r["error"].items()), flush=True)
            print(f"  ({time.time() - t:.0f} s)", flush=True)
            save(path, rows, meta)


def _strip(ib, holes):
    """!
    @brief The imported board with or without its holes.
    @param ib Imported board.
    @param holes True keeps them.
    @return ImportedBoard (a shallow copy when the holes are removed).
    """
    import copy
    if holes:
        return ib
    c = copy.copy(ib)
    c.holes = []
    return c


def summarise(rows):
    """!
    @brief The summary of the rows: per group (kind, layers, cell) the mean absolute error, the maximum, the bias of every variant, and how often the faces beat the fill fraction.
    @param rows List of rows.
    @return dict group -> {variant -> {n, mean_abs, max_abs, bias}, "wins" -> {pair -> (count, mean points gained)}}.
    """
    out = {}
    keys = sorted({(r["kind"], r["layers"], r["cell"]) for r in rows})
    for k in keys + [(kind, "all", c) for kind in sorted({r["kind"] for r in rows}) for c in CELLS]:
        sel = [r for r in rows if r["kind"] == k[0] and (k[1] == "all" or r["layers"] == k[1]) and r["cell"] == k[2]]
        if not sel:
            continue
        g = {}
        for v in VARIANTS:
            e = np.array([r["error"][v] for r in sel])
            g[v] = {"n": int(e.size), "mean_abs": float(np.abs(e).mean()), "max_abs": float(np.abs(e).max()), "bias": float(e.mean())}
        wins = {}
        for a, b in (("flow_on", "today_on"), ("lambda_on", "today_on"), ("flow_on", "flow_off"), ("flow_on", "lambda_on")):
            d = np.array([abs(r["error"][b]) - abs(r["error"][a]) for r in sel])          # positive: a is closer to the reference than b
            wins[f"{a} vs {b}"] = {"a_better": int((d > 0).sum()), "n": int(d.size), "mean_points": float(d.mean())}
        g["wins"] = wins
        out[f"{k[0]} L{k[1]} cell {k[2]}"] = g
    return out


def print_summary(rows):
    """!
    @brief Print the summary tables.
    @param rows List of rows.
    @return dict from summarise.
    """
    s = summarise(rows)
    for grp, g in s.items():
        print(f"\n{grp}: mean abs / max abs / bias (percent of the heater mean rise)")
        for v in VARIANTS:
            x = g[v]
            print(f"  {v:12s} n={x['n']:3d}  {x['mean_abs']:6.2f} / {x['max_abs']:6.2f} / {x['bias']:+6.2f}")
        for k, w in g["wins"].items():
            print(f"  {k:26s} better in {w['a_better']:2d} of {w['n']:2d}, mean gain {w['mean_points']:+.2f} points")
    return s


def main(argv):
    """!
    @brief Run the part asked for.
    @param argv Command-line words: --part, --boards, --quick.
    @return None.
    """
    part = argv[argv.index("--part") + 1] if "--part" in argv else "synthetic"
    boards = argv[argv.index("--boards") + 1].split(",") if "--boards" in argv else None
    quick = "--quick" in argv
    path = rb_paths.OUT / f"rule_on_faces_{part}{'_quick' if quick else ''}.json"
    meta = {"window_mm": WINDOW, "heater_mm": HEATER, "pixel_mm": synth.PIX_MM, "cells_mm": CELLS, "variants": VARIANTS, "h_face": rs.H_FACE, "n_sub": {"2": 8, "4": 3}}
    rows = load(path)
    if part == "synthetic":
        synthetic(rows, path, meta, quick)
    elif part in ("real", "holes"):
        if not registry.available():
            raise SystemExit("no board in data/: run research/gerber-real-boards/scripts/fetch_boards.py first")
        real(rows, path, meta, boards, part == "holes", quick)
    else:
        raise SystemExit("--part must be synthetic, real or holes")
    save(path, rows, meta)
    print_summary(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
