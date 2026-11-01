#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_rule_network_split.py
@brief Review of README 10: how much of the error of each mapping against the 3D reference is the mapping and how much is the program's layered network itself, and how big the errors are next to the part of the rise that the copper decides.
@details The 3D reference of study_rule_on_faces.py measures the mapping and the network together. This study runs the program's own network on the 0.1 mm pixel (fill 0 or 1 per pixel, rule on and off;
         `rule_study.pixel_network`), the best any mapping can do on that network, and splits the error of every variant:
         * network error = pixel network (rule on) against the 3D reference;
         * mapping error = variant against the pixel network (rule on).
         It also prints the errors as a share of the spreading excess (heater mean minus the board mean rise P / (2 h A), which the energy balance fixes at 347.2 K on a 12 mm window with
         h = 10 W/m2K on both faces and adiabatic sides), since the percentages of the full rise are diluted by that fixed term. With --nsweep it reruns the pixel network of three windows with
         4 and 8 sub-gaps (and 16 with --n16) (the rule's N_MAX replaced for the call, never edited) to test that the network error is the rule's number of sub-gaps.
         Input: out/rule_on_faces_real.json and out/rule_on_faces_synthetic.json (run study_rule_on_faces.py first). Output: out/rule_network_split.json and the printed tables.
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/study_rule_network_split.py [--nsweep [--n16]]
         Memory: about 2.4 GB peak for the windows; the sweep with 16 sub-gaps on a two-layer window reached 4.5 GB.
         NOT verified: the holes part (the pixel network with vias was not run); windows other than those of study_rule_on_faces.py.
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import re
import sys

import numpy as np

import boardrun
import rb_paths
import rule_study as rs
import synth

CENTRE, HEATER, WINDOW = (6.0, 6.0), 4.8, 12.0
BASE = 1.0 / (rs.H_FACE * 2.0 * (WINDOW * 1e-3) ** 2)       # K: the board mean rise fixed by the energy balance (1 W, both faces, adiabatic sides)
VARIANTS = ("today_on", "flow_naive", "flow_on", "lambda_on")
SWEEP = ("islands/2same", "stripes/2solid", "stickhub (142.29, -106.02)")


def window_board(name):
    """!
    @brief The imported board of a window named as in the result files (holes removed, as in the primary run).
    @param name "pattern/stack" for a synthetic board or "key (x, y)" for a real window.
    @return faces.ImportedBoard at the cell 0.6 mm (the pixel network only uses the pixel).
    """
    m = re.match(r"(\w+) \(([-\d.]+), ([-\d.]+)\)", name)
    if m is None:
        pat, stack = name.split("/")
        return synth.synthetic_board(pat, stack, 0.6)
    key, x, y = m.group(1), float(m.group(2)), float(m.group(3))
    ib = boardrun.import_window(key, (x, y, x + WINDOW, y + WINDOW), synth.PIX_MM, 0.6)
    ib.holes = []
    return ib


def heater_mean(ib, rule=True, n_max=None, s_max=None):
    """!
    @brief Heater mean rise of the pixel network of one window.
    @param ib Imported board.
    @param rule Laminate rule on or off.
    @param n_max Optional most sub-gaps.
    @param s_max Optional longest sub-gap in m.
    @return float, K.
    """
    p = boardrun.make_problem(ib, CENTRE, HEATER, 1.0, h_face=rs.H_FACE)
    return boardrun.heater_stats(rs.pixel_network(ib, p, rule, n_max, s_max), synth.PIX_MM, CENTRE, HEATER)[0]


def table(rows, pixel):
    """!
    @brief Print and return the split per group (kind, layers, cell).
    @param rows Rows of the result files.
    @param pixel Dict name -> {"on", "off"} heater means of the pixel network.
    @return dict group -> numbers.
    """
    out = {}
    for kind in ("real", "synthetic"):
        for layers in (2, 4):
            for cell in (0.6, 1.2):
                sel = [r for r in rows if r["kind"] == kind and r["layers"] == layers and r["cell"] == cell]
                if not sel:
                    continue
                net = np.array([100 * (pixel[r["name"]]["on"] / r["ref_mean"] - 1) for r in sel])
                g = {"n": len(sel), "network_on": [float(np.abs(net).mean()), float(np.abs(net).max()), float(net.mean())],
                     "network_off_bias": float(np.mean([100 * (pixel[r["name"]]["off"] / r["ref_mean"] - 1) for r in sel])),
                     "excess_K": [float(min(r["ref_mean"] - BASE for r in sel)), float(max(r["ref_mean"] - BASE for r in sel))]}
                line = f"{kind} L{layers} cell {cell} (n={len(sel)}): network {g['network_on'][0]:.2f}/{g['network_on'][1]:.2f}/{g['network_on'][2]:+.2f} (rule off bias {g['network_off_bias']:+.2f})"
                err = {}
                for v in VARIANTS:
                    e = np.array([100 * (r["mean"][v] / pixel[r["name"]]["on"] - 1) for r in sel])     # mapping alone
                    x = np.array([100 * (r["mean"][v] - r["ref_mean"]) / (r["ref_mean"] - BASE) for r in sel])   # share of the spreading excess
                    err[v] = np.abs(e)
                    g[v] = {"mapping": [float(np.abs(e).mean()), float(np.abs(e).max()), float(e.mean())], "excess_share": [float(np.abs(x).mean()), float(np.abs(x).max())]}
                    line += f"\n    {v:10s} mapping {np.abs(e).mean():5.2f}/{np.abs(e).max():5.2f}/{e.mean():+5.2f}   against 3D as a share of the excess {np.abs(x).mean():4.0f}/{np.abs(x).max():4.0f} %"
                g["flow_closer_than_lambda"] = int((err["flow_on"] < err["lambda_on"]).sum())
                g["flow_closer_than_fill"] = int((err["flow_on"] < err["today_on"]).sum())
                line += f"\n    mapping alone: flow closer than lambda in {g['flow_closer_than_lambda']} of {len(sel)}, than the fill in {g['flow_closer_than_fill']} of {len(sel)}; spreading excess {g['excess_K'][0]:.1f} to {g['excess_K'][1]:.1f} K"
                print(line, flush=True)
                out[f"{kind} L{layers} cell {cell}"] = g
    return out


def main(argv):
    """!
    @brief Run the pixel networks, print the split, optionally the sweep in the sub-gaps.
    @param argv Command-line words (--nsweep, --n16).
    @return None.
    """
    rows = []
    for part in ("real", "synthetic"):
        p = rb_paths.OUT / f"rule_on_faces_{part}.json"
        if not p.exists():
            raise SystemExit(f"{p} is missing: run study_rule_on_faces.py --part {part} first")
        rows += json.loads(p.read_text())["rows"]
    path = rb_paths.OUT / "rule_network_split.json"
    try:
        pixel = json.loads(path.read_text())["pixel"]
    except (OSError, ValueError, KeyError):
        pixel = {}
    for name in sorted({r["name"] for r in rows}):
        if name not in pixel:
            ib = window_board(name)
            pixel[name] = {"on": heater_mean(ib, True), "off": heater_mean(ib, False)}
            print(f"{name}: pixel network rule on {pixel[name]['on']:.3f} K, off {pixel[name]['off']:.3f} K", flush=True)
            path.write_text(json.dumps({"pixel": pixel}, indent=1))
    res = {"pixel": pixel, "groups": table(rows, pixel)}
    if "--nsweep" in argv:
        ref = {r["name"]: r["ref_mean"] for r in rows}
        res["nsweep"] = {}
        for name in SWEEP:
            ib = window_board(name)
            gap = (rs.THICKNESS - len(ib.layers) * rs.T_CU) / (len(ib.layers) - 1)
            res["nsweep"][name] = {}
            for n in ((4, 8, 16) if "--n16" in argv else (4, 8)):
                v = heater_mean(ib, True, n_max=n, s_max=gap / n * 1.0001)        # s_max just above d / n so that the gap gets exactly n sub-gaps
                res["nsweep"][name][str(n)] = 100 * (v / ref[name] - 1)
            print(f"{name}: network error with " + " / ".join(res["nsweep"][name]) + " sub-gaps " + " / ".join(f"{x:+.2f}" for x in res["nsweep"][name].values()) + " %", flush=True)
    path.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
