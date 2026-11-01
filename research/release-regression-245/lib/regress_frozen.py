#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file regress_frozen.py
@brief The frozen reference numbers of a release: how they are made from two result sets and how a later run is compared with them.
@details File format (`reference/v<version>.json`, format 1):

         * `version`, `generated_from` (labels, program versions and environment of the two result sets), `settings` (models, cells, boards, caps);
         * `tolerance_k`: the absolute tolerance on a temperature of a record of class `moved` (1e-6 K by default);
         * `records`: `"board|model|cell"` -> `{"class": "bit" | "moved", "metrics": {name: value}}`, only runs that finished (a skipped or failed run is under `skipped`);
         * `transients`: `"board|model"` -> `{"class": ..., "t63": {part: seconds}}`;
         * `skipped`: `"board|model|cell"` -> reason.

         A record is `bit` when every number of it is equal, as floats, in the baseline (the earlier release) and in the release candidate: nothing in the release may change it, so
         the frozen value is compared for exact equality. Every other record is `moved` and is compared within `tolerance_k` (temperatures), 1e-7 relative (the field checksums and
         the heat split) and exactly (the unknown counts). `compare` returns the list of differences; the pytest module `tests/test_frozen_numbers.py` asserts it is empty.
@note Exact equality assumes the same platform family and library builds as the machine that froze the numbers (the sparse direct solver is deterministic on one machine but a
      BLAS build can change the last digit elsewhere). Measured by the review on the same machine: one thread against the default gives the same bits; NumPy 2.3.5 and
      SciPy 1.16.3 against 2.5.4 and 1.18.1 move 8 of 44 bit records of the 2 mm set by at most 2.8e-11 K (field 7e-13 relative), so exact equality fails after a library
      update and `PCBT_FROZEN_BIT_TOL=1e-9` passes. The environment variable `PCBT_FROZEN_BIT_TOL` (absolute, in K) relaxes the `bit` records when a different machine is used;
      the file records the environment it was made on.
"""

import json
from pathlib import Path

import regress_classify as C

FORMAT = 1
TOLERANCE_K = 1e-6
REL_TOL = 1e-7                 # field checksums and the heat split of a moved record: 1e-6 K per cell at 100 degC is 1e-8 of the sum


def key(board, model, cell):
    """!
    @brief Key of a record in the frozen file.
    @param board Board name.
    @param model Model key.
    @param cell Cell size in mm.
    @return str "board|model|cell".
    """
    return f"{board}|{model}|{cell:g}"


def build(base, new, version, tolerance_k=TOLERANCE_K):
    """!
    @brief Make the frozen file from the baseline and the final release candidate result sets.
    @param base Result set of the earlier release (v2.4.4).
    @param new Result set of the release candidate (the numbers to freeze).
    @param version Version string of the file name and content (for example "2.4.5").
    @param tolerance_k Absolute tolerance in K for the `moved` records.
    @return dict (the content of the frozen file).
    """
    a, b = C.index(base), C.index(new)
    records, skipped = {}, {}
    for k, r in sorted(b.items(), key=lambda t: (t[0][0], t[0][2], t[0][1])):
        board, model, cell, solver = k
        if solver != "direct":
            continue
        if r["status"] != "ok":
            skipped[key(board, model, cell)] = r.get("reason", r["status"])
            continue
        metrics = C.metrics_of(r)
        old = a.get(k)
        same = old is not None and old["status"] == "ok" and C.metrics_of(old) == metrics
        records[key(board, model, cell)] = {"class": "bit" if same else "moved", "metrics": metrics}
    ia = {(t["board"], t["model"]): t for t in base.get("transients", [])}
    trans = {}
    for t in new.get("transients", []):
        if t["status"] != "ok":
            continue
        t63 = {p["name"]: p["t63_s"] for p in t["parts"] if p["t63_s"] is not None}
        old = ia.get((t["board"], t["model"]))
        old63 = {p["name"]: p["t63_s"] for p in old["parts"] if p["t63_s"] is not None} if old and old["status"] == "ok" else None
        trans[f"{t['board']}|{t['model']}"] = {"class": "bit" if old63 == t63 else "moved", "t63": t63}
    return {"format": FORMAT, "version": version, "tolerance_k": tolerance_k,
            "generated_from": {"baseline": {"label": base["label"], "version": base["program"]["version"]}, "frozen": {"label": new["label"], "version": new["program"]["version"]},
                               "environment": new["environment"]},
            "settings": {k: new["settings"][k] for k in ("models", "cells", "max_unknowns", "solid_cap", "transient_cell")}, "boards": sorted(new["boards"]),
            "records": records, "transients": trans, "skipped": skipped}


def load(path):
    """!
    @brief Read a frozen file.
    @param path JSON file.
    @return dict.
    @throws ValueError If the format number is not the one this module reads.
    """
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("format") != FORMAT:
        raise ValueError(f"frozen file format {d.get('format')} is not {FORMAT}")
    return d


def _differs(name, expected, got, cls, tol_k, bit_tol_k):
    """!
    @brief True when a number is outside the tolerance of its class.
    @param name Metric name (decides absolute, relative or exact comparison).
    @param expected Frozen value.
    @param got Value of the run.
    @param cls "bit" or "moved".
    @param tol_k Tolerance in K for a moved temperature.
    @param bit_tol_k Tolerance in K for a bit record (0 = exact).
    @return bool.
    """
    if got is None or expected is None:
        return got != expected
    group = C.metric_group(name)
    if group == "count":
        return got != expected                                                 # unknowns: always exact
    if cls == "bit":
        if bit_tol_k == 0.0:
            return got != expected
        # field checksums: relative to their size; the heat balance: relative to max(|value|, 1 W), because the balance error is round-off (1e-13 W) and a tolerance
        # relative to itself would be 1e-22 W (review: NumPy 2.3.5 / SciPy 1.16.3 against 2.5.4 / 1.18.1 failed 8 bit records on balance_error alone with 1e-9)
        scale = abs(expected) if group == "field" else (max(abs(expected), 1.0) if group == "balance" else 1.0)
        return abs(got - expected) > bit_tol_k * scale
    if group in ("field", "balance"):
        return abs(got - expected) > REL_TOL * max(abs(expected), 1.0)
    return abs(got - expected) > tol_k


def compare(frozen, records, transients=None, bit_tol_k=0.0):
    """!
    @brief Compare run records with the frozen numbers.
    @param frozen Content of the frozen file (load()).
    @param records List of run records of regress_harness.run_one (any subset of the frozen keys).
    @param transients Optional list of regress_harness.t63 results (with a "board" key added).
    @param bit_tol_k Absolute tolerance in K for the `bit` records (0 = exact equality).
    @return List of strings, one per difference (empty when the run agrees with the frozen file).
    """
    out, tol = [], float(frozen.get("tolerance_k", TOLERANCE_K))
    for r in records:
        k = key(r["board"], r["model"], r["cell_mm"])
        if k in frozen["skipped"]:
            if r["status"] == "ok":
                out.append(f"{k}: was skipped when frozen ({frozen['skipped'][k]}) and now ran")
            continue
        exp = frozen["records"].get(k)
        if exp is None:
            out.append(f"{k}: not in the frozen file")
            continue
        if r["status"] != "ok":
            out.append(f"{k}: frozen run finished, this one is {r['status']}: {r.get('reason', '')}")
            continue
        got = C.metrics_of(r)
        for name in sorted(set(exp["metrics"]) | set(got)):
            if _differs(name, exp["metrics"].get(name), got.get(name), exp["class"], tol, bit_tol_k):
                out.append(f"{k} [{exp['class']}] {name}: frozen {exp['metrics'].get(name)!r}, now {got.get(name)!r}")
    for t in transients or []:
        k = f"{t['board']}|{t['model']}"
        exp = frozen["transients"].get(k)
        if exp is None or t["status"] != "ok":
            continue
        got = {p["name"]: p["t63_s"] for p in t["parts"] if p["t63_s"] is not None}
        for name, v in exp["t63"].items():
            g = got.get(name)
            bad = (g != v) if exp["class"] == "bit" and bit_tol_k == 0.0 else (g is None or abs(g - v) > 1e-6 * v)
            if bad:
                out.append(f"{k} [{exp['class']}] t63 of {name}: frozen {v!r}, now {g!r}")
    return out
