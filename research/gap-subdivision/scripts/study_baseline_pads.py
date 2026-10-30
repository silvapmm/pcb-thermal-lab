#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_baseline_pads.py
@brief Baseline of the program on designed boards with a copper pad (bare laminate around it) against the converged graded 3D solver: pad size, bottom, gap, layers, source, h, copper, cell.
@details Question: which designed boards with partial copper does the program get wrong today, and by how much, against a converged independent 3D answer? The reference is
         lib/graded_pad3d.py (graded grid, three scales, limit fitted; checked against the exact series on a uniform board to 0.01 %, tests/test_graded_pad3d.py); its energy balance
         and the spread between the finest grid and the limit are stored with every row. The references are slow (20 to 60 s per board); they are cached in out/refs_pads.json and
         the finished table is written to baseline/pads.csv (committed), from which `rerun_baseline.py` re-runs only the models.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_baseline_pads.py   (from the repository root; about 10 to 15 minutes with 4 processes the first time).
"""

import csv
import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool

import _bootstrap as BS
import boards as B

BASE = B.Board("pad", layers=2, gap=1.6, copper=35.0, size=30.0, source=3.0, power=1.0, h_top=10.0, h_bottom=10.0, stack="advanced", pad=10.0, pad_layers=(0,))
CELL = 0.5
FIELDS = ["sweep", "tag", "layers", "gap_mm", "copper_um", "size_mm", "source_mm", "pad_mm", "bottom", "h_top", "h_bottom", "stack", "cell_mm", "ref_K", "ref_spread_pct", "ref_order",
          "ref_balance"] + [f"{m}_K" for m in B.MODELS]


def bottom_cfg(bd, kind):
    """!
    @brief Set what the layers below the top one carry.
    @param bd A Board.
    @param kind "full" (full copper), "empty" (no copper on the last layer), "pad" (the pad on every layer).
    @return A new Board.
    """
    last = bd.layers - 1
    if kind == "full":
        return replace(bd, pad_layers=(0,), empty_layers=())
    if kind == "empty":
        return replace(bd, pad_layers=(0,), empty_layers=(last,))
    return replace(bd, pad_layers=tuple(range(bd.layers)), empty_layers=())


def rows():
    """!
    @brief The designed boards of the baseline.
    @return List of (sweep, tag, Board, cell in mm, bottom kind).
    """
    out = []
    for pad in (6.0, 10.0, 14.0, 20.0, 26.0):
        for kind in ("empty", "full", "pad"):
            out.append(("pad_size", f"pad{pad:g}-{kind}", bottom_cfg(replace(BASE, pad=pad), kind), CELL, kind))
    for g in (0.1, 0.2, 0.4, 0.8, 1.6, 3.2):
        for kind in ("empty", "full"):
            out.append(("gap", f"gap{g:g}-{kind}", bottom_cfg(replace(BASE, gap=g), kind), CELL, kind))
    for l in (3, 4, 6, 8):
        for g in (0.2, 1.6):
            out.append(("layers", f"L{l}-gap{g:g}-top-pad", replace(BASE, layers=l, gap=g), CELL, "full"))
        out.append(("layers", f"L{l}-gap0.4-all-pads", bottom_cfg(replace(BASE, layers=l, gap=0.4), "pad"), CELL, "pad"))
    for s in (2.0, 3.0, 6.0, 9.0):
        out.append(("source", f"src{s:g}", bottom_cfg(replace(BASE, source=s), "full"), CELL, "full"))
    for h in (5.0, 25.0, 100.0):
        out.append(("h", f"h{h:g}", bottom_cfg(replace(BASE, h_top=h, h_bottom=h), "full"), CELL, "full"))
    for cu in (17.5, 70.0):
        out.append(("copper", f"cu{cu:g}", bottom_cfg(replace(BASE, copper=cu), "full"), CELL, "full"))
    for c in (1.0, 0.25):
        out.append(("cell", f"cell{c:g}", bottom_cfg(BASE, "full"), c, "full"))
    for stack in ("simple",):
        for l in (4, 6):
            out.append(("stack", f"L{l}-simple-top-pad", replace(BASE, layers=l, gap=0.4, stack=stack), CELL, "full"))
            out.append(("stack", f"L{l}-advanced-top-pad", replace(BASE, layers=l, gap=0.4), CELL, "full"))
    return out


def _ref(args):
    """!
    @brief Worker: the converged reference of one board.
    @param args (tag, Board, cell).
    @return (tag, cell, dict of the reference).
    """
    tag, bd, cell = args
    t = time.time()
    r = B.graded_peak(bd, cell)
    r["seconds"] = time.time() - t
    return tag, cell, r


def main(argv):
    """!
    @brief Compute (or load) the references, run the five models and write baseline/pads.csv.
    @param argv Command line arguments (a number of processes, default 4).
    @return None.
    """
    nproc = int(argv[0]) if argv else 4
    cache_path = BS.OUT / "refs_pads.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    table = rows()
    todo = [(tag, bd, cell) for _, tag, bd, cell, _ in table if f"{tag}|{cell}" not in cache]
    print(f"{len(table)} boards, {len(todo)} references to compute with {nproc} processes", flush=True)
    with Pool(nproc) as pool:
        for tag, cell, r in pool.imap_unordered(_ref, todo):
            cache[f"{tag}|{cell}"] = r
            cache_path.write_text(json.dumps(cache))
            print(f"  ref {tag:28s} {r['peak']:9.3f} K  spread {r['spread']:+.3f} %  p {r['order']:.2f}  bal {r['balance']:.6f}  {r['seconds']:.0f} s", flush=True)
    out = []
    for sweep, tag, bd, cell, kind in table:
        ref = cache[f"{tag}|{cell}"]
        p = B.problem(bd)
        res = B.all_models(bd, cell, p)
        row = {"sweep": sweep, "tag": tag, "layers": bd.layers, "gap_mm": bd.gap, "copper_um": bd.copper, "size_mm": bd.size, "source_mm": bd.source, "pad_mm": bd.pad, "bottom": kind,
               "h_top": bd.h_top, "h_bottom": bd.h_bottom, "stack": bd.stack, "cell_mm": cell, "ref_K": round(ref["peak"], 4), "ref_spread_pct": round(ref["spread"], 4),
               "ref_order": round(ref["order"], 3), "ref_balance": round(ref["balance"], 7)}
        for m in B.MODELS:
            row[f"{m}_K"] = round(res[m][0], 4)
        out.append(row)
    with open(BS.BASELINE / "pads.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(out)
    print(f"{'tag':28s} {'ref K':>8s} " + " ".join(f"{m:>8s}" for m in B.MODELS))
    for r in out:
        print(f"{r['tag']:28s} {r['ref_K']:8.2f} " + " ".join(f"{100 * (r[f'{m}_K'] / r['ref_K'] - 1):+8.2f}" for m in B.MODELS))


if __name__ == "__main__":
    main(sys.argv[1:])
