#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file what_moved.py
@brief Question: which frozen read-outs moved between 2.7.x and 2.8.0, board by board and model by model, by how much, and which item of 2.8.0 explains each shift?

@details Reads JSON only (no solver is run): the frozen numbers of the last release, `tests/regression/data/v2.7.0.json` (v2.7.1 moved no frozen number), and the pending
         files of 2.8.0 in `tests/regression/data/pending/` (each moved record is held, with its FINAL numbers, by exactly one file; the other items that also moved it are
         named by the key `also_moved_by`; a file with `new_models` or `new_readouts` holds ADDITIONS, not shifts). Run from the repository root:

             .venv/bin/python releases/2.8.0/reproduction/scripts/what_moved.py [--frozen FILE] [--pending DIR]

         It prints Markdown: a summary per model and cell, one table per model with a row per board, the times to 63 % of the transient boards, and the additions.
         A read-out is a temperature of a record (board maximum, mean and minimum, the mean of each layer, the peak, mean and junction of each part, the mean and maximum of a
         metal block); the sums `t_sum` and `t_sumsq`, the balance error and the powers are not read-outs. A read-out counts as moved when it changed by more than the
         round-off bound of the harness, 1e-8 K. Shifts are signed (positive = 2.8.0 reads hotter); the rise is the 2.7.0 board maximum over the ambient of 25 degC
         (every frozen board has that ambient, `tests/regression/regress_boards.py` and the three example files).
"""

import argparse
import glob
import json
import logging
import os
import statistics
import sys
from collections import defaultdict

# Item id of each pending file that holds shifts (the ids of `releases/2.8.0/REFREEZE_PLAN.md` section 2).
ITEMS = {
    "face-film-half-slab": "M1",
    "drawn-copper-faces": "M2",
    "lumped-first-link-edge": "M3",
    "block-exact-cover": "M4",
}
# Round-off bound of the harness (`REFREEZE_PLAN.md` item L8), in K.
ROUND_OFF_K = 1e-8
# Ambient of every frozen board, in degC.
AMBIENT_C = 25.0
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CELLS = ("2", "1", "0.5")


def is_readout(metric):
    """!
    @brief Whether a metric of a frozen record is a temperature read-out.
    @param metric Metric name as stored in the frozen file (for example `t_max`, `part:U1:t_mean`, `layer_mean[2]`).
    @return bool True for a temperature in degC, False for sums, powers, heat flows, counts and the balance error.
    """
    if metric in ("t_max", "t_mean", "t_min") or metric.startswith("layer_mean["):
        return True
    if metric.startswith("part:"):
        return metric.split(":")[-1] in ("t_max", "t_mean", "t_junction")
    if metric.startswith("block:"):
        return metric.split(":")[-1] in ("t_max", "t_mean")
    return False


def load_pending(folder):
    """!
    @brief Read the pending files of the release.
    @param folder Folder that holds `<topic>.json` pending files.
    @return tuple (shifted, credits, transients, additions): shifted maps a record key to (final metrics, item ids); transients maps a transient key to (final t63 by part,
            item ids); additions maps a pending file name to its records (files with `new_models` or `new_readouts`).
    """
    shifted, transients, additions = {}, {}, {}
    files = sorted(glob.glob(os.path.join(folder, "*.json")))
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("new_models") or data.get("new_readouts"):
            # additions never move an old number: kept apart and only counted
            additions[name] = data.get("records", {})
            continue
        own = ITEMS.get(name, name)
        also = data.get("also_moved_by", {})
        for key, rec in data.get("records", {}).items():
            shifted[key] = (rec["metrics"], [own] + [ITEMS.get(n, n) for n in also.get(key, [])])
        for key, rec in data.get("transients", {}).items():
            # the transient keys of `also_moved_by` carry the prefix `t63:`
            transients[key] = (rec["t63"], [own] + [ITEMS.get(n, n) for n in also.get("t63:" + key, [])])
    return shifted, transients, additions


def record_shifts(old, new):
    """!
    @brief Signed shifts of the temperature read-outs of one record.
    @param old Metrics of the 2.7.0 record.
    @param new Metrics of the 2.8.0 record (the pending file's final numbers).
    @return dict metric -> shift in K (2.8.0 minus 2.7.0) for every read-out present in both.
    """
    return {m: new[m] - old[m] for m in old if is_readout(m) and m in new}


def fmt_k(value):
    """!
    @brief Format a shift in K with a precision that keeps small shifts readable.
    @param value Shift in K.
    @return str The number, in fixed or scientific notation.
    """
    if value == 0.0:
        return "0"
    if abs(value) < 1e-3:
        return f"{value:+.1e}"
    return f"{value:+.3f}"


def main():
    """!
    @brief Measure what moved and print the Markdown tables.
    @return int Exit status (0).
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frozen", default="tests/regression/data/v2.7.0.json", help="frozen numbers of the last release")
    ap.add_argument("--pending", default="tests/regression/data/pending", help="folder of the pending files of the release")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    out = logging.getLogger("what_moved").info

    with open(args.frozen, encoding="utf-8") as fh:
        frozen = json.load(fh)
    shifted, transients, additions = load_pending(args.pending)
    records = frozen["records"]
    boards = frozen["boards"]
    out(f"Reference: `{args.frozen}` (version {frozen['version']}); pending files: `{args.pending}` ({len(shifted)} moved records, "
        f"{len(transients)} moved times to 63 %, additions: {', '.join(f'{k} {len(v)}' for k, v in additions.items())}).")
    stray = [k for k in shifted if k not in records]
    out(f"Moved records without a frozen record (should be none): {len(stray)}.")

    # Per record: the shifts and the items; records not in a pending file did not move at all.
    per = {}
    for key, rec in records.items():
        board, model, cell = key.split("|")
        if key in shifted:
            new, items = shifted[key]
            d = record_shifts(rec["metrics"], new)
        else:
            items, d = [], {m: 0.0 for m in rec["metrics"] if is_readout(m)}
        rise = rec["metrics"]["t_max"] - AMBIENT_C
        per[key] = dict(board=board, model=model, cell=cell, d=d, items=items, rise=rise)

    # 1. Summary per model and cell.
    out("\n## Summary per model and cell (frozen boards, temperature read-outs)\n")
    out("| Model | Cell (mm) | Records | Records moved | Read-outs moved / all | Median shift of the moved (K) | Largest shift (K) | Where | Largest board-maximum shift (% of rise) | Items |")
    out("| :-- | --: | --: | --: | --: | --: | --: | :-- | --: | :-- |")
    for model in MODELS:
        for cell in CELLS:
            keys = [k for k, p in per.items() if p["model"] == model and p["cell"] == cell]
            if not keys:
                continue
            moved_vals, n_all, n_moved_rec, items = [], 0, 0, set()
            big, where, big_rel = 0.0, "-", 0.0
            for k in keys:
                p = per[k]
                n_all += len(p["d"])
                mv = {m: v for m, v in p["d"].items() if abs(v) > ROUND_OFF_K}
                if mv:
                    n_moved_rec += 1
                    items.update(p["items"])
                moved_vals += [abs(v) for v in mv.values()]
                for m, v in mv.items():
                    if abs(v) > abs(big):
                        big, where = v, f"{p['board']} `{m}`"
                rel = 100.0 * p["d"].get("t_max", 0.0) / p["rise"]
                if abs(rel) > abs(big_rel):
                    big_rel = rel
            med = statistics.median(moved_vals) if moved_vals else 0.0
            out(f"| {model} | {cell} | {len(keys)} | {n_moved_rec} | {len(moved_vals)} / {n_all} | {fmt_k(med)} | {fmt_k(big)} | {where} | "
                f"{big_rel:+.2f} | {', '.join(sorted(items)) or '-'} |")

    # 2. One table per model, a row per board.
    for model in MODELS:
        out(f"\n## {model}: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)\n")
        out("| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |")
        out("| :-- | --: | --: | --: | :-- | --: | :-- |")
        for board in boards:
            cols, rels, n_mv, n_all, items = [], [], 0, 0, set()
            for cell in CELLS:
                p = per.get(f"{board}|{model}|{cell}")
                if p is None:
                    cols.append("not frozen")
                    rels.append("-")
                    continue
                n_all += len(p["d"])
                mv = {m: v for m, v in p["d"].items() if abs(v) > ROUND_OFF_K}
                n_mv += len(mv)
                items.update(p["items"] if mv else [])
                big = max(mv.values(), key=abs) if mv else 0.0
                cols.append(fmt_k(big))
                rels.append(f"{100.0 * p['d'].get('t_max', 0.0) / p['rise']:+.4f}")
            out(f"| {board} | {' | '.join(cols)} | {' / '.join(rels)} | {n_mv} / {n_all} | {', '.join(sorted(items)) or 'none'} |")

    # 3. Times to 63 % (transient boards, 1 mm).
    out("\n## Times to 63 % (transient boards of the harness, 1 mm)\n")
    out("| Board, model | Part | 2.7.0 (s) | 2.8.0 (s) | Shift (%) | Items |")
    out("| :-- | :-- | --: | --: | --: | :-- |")
    tiny = 0
    for key in sorted(frozen["transients"]):
        old = frozen["transients"][key]["t63"]
        if key not in transients:
            continue
        new, items = transients[key]
        for part in sorted(old):
            if part not in new:
                continue
            rel = 100.0 * (new[part] - old[part]) / old[part]
            if abs(rel) < 1e-3:
                # held in a pending file but below 0.001 %: counted, not listed
                tiny += 1
                continue
            out(f"| {key.replace('|', ', ')} | {part} | {old[part]:.4f} | {new[part]:.4f} | {rel:+.3f} | {', '.join(items)} |")
    out(f"\nParts whose time moved by less than 0.001 % (listed in a pending file, not shown): {tiny}.")
    unchanged_t = [k for k in frozen["transients"] if k not in transients]
    out(f"\nTimes to 63 % not moved: {len(unchanged_t)} of {len(frozen['transients'])} ({', '.join(sorted(set(k.split('|')[1] for k in unchanged_t)))}).")

    # 4. Additions.
    out("\n## Additions (new records or new metrics; no old number moves)\n")
    for name, recs in additions.items():
        by = defaultdict(int)
        for key in recs:
            _b, model, cell = key.split("|")
            by[(model, cell)] += 1
        out(f"* `{name}`: {len(recs)} records; " + ", ".join(f"{m} {c} mm: {n}" for (m, c), n in sorted(by.items())))
        if any(k.split("|")[1] == "fem" for k in recs):
            # the new model against the reference on the same board and cell (2.8.0 numbers of both; column read-out, board maximum)
            out("\n  | Board | Cell (mm) | FEM board maximum (degC) | FVM board maximum (degC) | FEM - FVM, % of the FVM rise |")
            out("  | :-- | --: | --: | --: | --: |")
            for key in sorted(recs, key=lambda k: (k.split("|")[0], -float(k.split("|")[2]))):
                board, _m, cell = key.split("|")
                ref = f"{board}|fvm|{cell}"
                if ref not in records:
                    continue
                fvm_now = shifted.get(ref, (records[ref]["metrics"], []))[0]["t_max"]
                fem = recs[key]["metrics"]["t_max"]
                out(f"  | {board} | {cell} | {fem:.3f} | {fvm_now:.3f} | {100.0 * (fem - fvm_now) / (fvm_now - AMBIENT_C):+.2f} |")
        if name == "surface-records":
            # the surface read-out of a 35 um copper face against the column mean: how far apart can the two be on the frozen boards?
            gaps = []
            for key, rec in recs.items():
                base = records.get(key)
                if base is None:
                    continue
                final = shifted.get(key, (base["metrics"], []))[0]
                for m, v in rec["metrics"].items():
                    if m.endswith(":t_max_surface"):
                        gaps.append((v - final[m.replace("_surface", "")], key, m))
            if gaps:
                g = max(gaps, key=lambda x: abs(x[0]))
                out(f"  part peak, surface minus column mean over {len(gaps)} part read-outs: median {statistics.median(abs(x[0]) for x in gaps):.2e} K, "
                    f"largest {g[0]:+.4f} K ({g[1]} `{g[2]}`)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
