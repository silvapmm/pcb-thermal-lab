#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_baseline.py
@brief Baseline: the five models of the program on simple boards with a copper pad of growing size (one layer; two layers with a bare or a full second layer) against the independent resolved 3D solver.
@details Question: how far is the Analytic model (and the others) from a resolved 3D solution on a pad board, and is the error always a shortfall? Boards: 60 x 60 mm, 1.6 mm, copper 35 um,
         a 6 x 6 mm part of 1 W in the centre, FR-4 0.3 through and 0.9 in the plane (the program's), films 10 and 15 W/m2K, no edge loss; pads of 6 to 40 mm and the board with full copper.
         The reference (lib/pads.py, resolved3d, quadrant, 0.25 mm cells, 8 sub-slabs through the laminate) is read as the program's 0.5 mm cell would read it; its cell convergence (0.5, 0.25, 0.125 mm)
         is stored too. Writes data/baseline.csv (git-ignored, regenerated) and caches the results in out/.
         Usage: .venv/bin/python research/analytic-partial-copper/scripts/study_baseline.py   (from the repository root; several minutes).
"""

import csv

import _bootstrap as BS
import pads as P

SIZES = (6.0, 10.0, 14.0, 20.0, 30.0, 40.0, None)
KINDS = (("1 layer", 1, "full"), ("2 layers, bare second", 2, "empty"), ("2 layers, full second", 2, "full"))
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def board(layers, second, pad):
    """!
    @brief The designed board.
    @param layers Copper layers (1 or 2).
    @param second What the second layer carries ("full" or "empty").
    @param pad Pad side in mm (None: full copper).
    @return A Pad.
    """
    return P.Pad(name=f"L{layers}-{second}", layers=layers, second=second, pad=pad)


def compute():
    """!
    @brief Run the references and the models on every board.
    @return list of dict rows.
    """
    rows = []
    for label, layers, second in KINDS:
        for pad in SIZES:
            if layers == 2 and second == "empty" and pad is None:
                continue
            bd = board(layers, second, pad)
            p = P.problem(bd)
            ref = P.reference(bd, 0.5, 0.25, p=p)
            row = {"kind": label, "layers": layers, "second": second, "pad_mm": pad if pad else 0.0, "ref_K": ref["peak"], "ref_balance": ref["balance"]}
            for m in MODELS:
                try:
                    row[f"{m}_K"] = P.program_rise(bd, m, 0.5, p)
                except ValueError:
                    row[f"{m}_K"] = float("nan")             # the 3D solid refuses a board above its size limit
            print(label, pad, round(ref["peak"], 2), {m: round(row[f"{m}_K"], 1) for m in MODELS}, flush=True)
            rows.append(row)
    return rows


def convergence():
    """!
    @brief Cell convergence of the reference on the one-layer 10 and 20 mm pads (0.5, 0.25, 0.125 mm), read at the 0.5 mm cell.
    @return list of dict rows.
    """
    rows = []
    for pad in (10.0, 20.0):
        bd = board(1, "full", pad)
        p = P.problem(bd)
        vals = {dx: P.reference(bd, 0.5, dx, p=p)["peak"] for dx in (0.5, 0.25, 0.125)}
        rows.append({"pad_mm": pad, **{f"dx_{dx}": v for dx, v in vals.items()}})
        print("convergence", rows[-1], flush=True)
    return rows


def main():
    """!
    @brief Run the baseline and write data/baseline.csv.
    @return None.
    """
    rows = BS.cached("baseline", compute)
    conv = BS.cached("baseline_convergence", convergence)
    with open(BS.DATA / "baseline.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\nerror against the reference (%):")
    for r in rows:
        print(f"{r['kind']:24s} pad {r['pad_mm']:5.1f}  ref {r['ref_K']:7.2f}  " + "  ".join(f"{m} {100 * (r[m + '_K'] / r['ref_K'] - 1):+6.1f}" for m in MODELS))
    print("\nreference convergence:", conv)


if __name__ == "__main__":
    main()
