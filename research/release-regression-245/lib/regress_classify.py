#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file regress_classify.py
@brief Difference of two result sets and classification of every shift against the table of expected shifts (`reference/expected_shifts.json`).
@details Pure Python, no program and no NumPy: it reads the JSON result sets of `regress_harness.py`. A record is a (board, model, cell, solver) triple; its metrics are flattened by
         `metrics_of` (maximum, mean and minimum temperature, temperature per layer, per part and per block, the heat balance, the unknowns and a checksum of the field).
         Two values are the same only when they are equal as floats (bit identical); every other metric is a shift.

         A shift gets one class:
         * `expected`: a rule of the table matches (board, model, cell, metric), its direction and its size (absolute, in K, or relative to the rise of the old run) are inside the
           documented range;
         * `expected_out_of_range`: a rule matches but the shift is outside the range that the study gave (the item is the cause, the size needs a look);
         * `to_be_explained`: only rules that say "to be explained" match (the item is a plausible cause and its size is not known);
         * `unexplained`: no rule matches;
         * `must_not_move`: the shift is inside the scope of a `must_not_move` entry (the board and model that no item of the release may change); this class is always an alarm
           and wins over every rule.
         A change of warning texts alone is recorded as `warnings_only` and is not a shift. The solve time is information, never a shift.
"""

import fnmatch
import json
from pathlib import Path

CLASSES = ("expected", "expected_out_of_range", "to_be_explained", "unexplained", "must_not_move")
ALARMS = ("unexplained", "must_not_move")
GROUPS = ("temperature", "field", "count", "balance", "status")


def load_set(path):
    """!
    @brief Read a result set.
    @param path JSON file written by regress_harness.run_suite.
    @return dict.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def index(result_set, key="records"):
    """!
    @brief Records of a result set by (board, model, cell, solver).
    @param result_set A result set.
    @param key "records" or "sor".
    @return dict.
    """
    return {(r["board"], r["model"], float(r["cell_mm"]), r.get("solver", "direct")): r for r in result_set.get(key, [])}


def metric_group(name):
    """!
    @brief Group of a flattened metric name.
    @param name Metric name from metrics_of.
    @return One of GROUPS.
    """
    if name == "status":
        return "status"
    if name in ("t_sum", "t_sumsq"):
        return "field"
    if name == "unknowns":
        return "count"
    if name in ("power_in", "balance_error") or name.endswith(":power_top_w") or name.endswith(":power_w") or name.endswith(":w_to_block"):
        return "balance"
    return "temperature"


def metrics_of(rec):
    """!
    @brief Flatten the numbers of a record into {name: value}.
    @param rec A record with status "ok" (a skipped or failed record gives only its unknowns).
    @return dict of floats (and the integer unknowns).
    """
    m = {}
    if rec.get("unknowns") is not None:
        m["unknowns"] = rec["unknowns"]
    if rec.get("status") != "ok":
        return m
    for k in ("t_max", "t_mean", "t_min", "power_in", "balance_error", "t_sum", "t_sumsq"):
        if rec.get(k) is not None:
            m[k] = rec[k]
    for i, v in enumerate(rec.get("layer_mean") or []):
        if v is not None:
            m[f"layer_mean[{i}]"] = v
    for p in rec.get("parts") or []:
        for k in ("t_max", "t_mean", "t_junction", "power_w", "power_top_w"):
            if p.get(k) is not None:
                m[f"part:{p['name']}:{k}"] = p[k]
    for b in rec.get("blocks") or []:
        for k in ("t_mean", "t_max", "w_to_block"):
            if b.get(k) is not None:
                m[f"block:{b['name']}:{b['face']}:{k}"] = b[k]
    return m


def _in(value, allowed):
    """!
    @brief Membership with the wildcard "*".
    @param value The item to find.
    @param allowed "*" or a list of values (strings are matched with fnmatch).
    @return bool.
    """
    if allowed == "*" or allowed is None:
        return True
    if isinstance(value, str):
        return any(fnmatch.fnmatchcase(value, a) for a in allowed)
    return any(abs(float(value) - float(a)) < 1e-9 for a in allowed)


def scope_matches(scope, board, model, cell, metric):
    """!
    @brief True when a rule or a must_not_move entry covers a (board, model, cell, metric).
    @param scope dict with the keys boards, models, cells, metrics ("*" or lists; boards and metrics accept fnmatch patterns, metrics also the group names).
    @param board Board name.
    @param model Model key (the SOR runs use "fvm_sor").
    @param cell Cell size in mm.
    @param metric Flattened metric name.
    @return bool.
    """
    if any(fnmatch.fnmatchcase(metric, pat) for pat in scope.get("exclude", [])):
        return False                                                           # a rule can leave out the metrics that a more exact rule owns
    metrics = scope.get("metrics", "*")
    if metrics != "*":
        group = metric_group(metric)
        if not (group in metrics or _in(metric, metrics)):
            return False
    return _in(board, scope.get("boards", "*")) and _in(model, scope.get("models", "*")) and _in(cell, scope.get("cells", "*"))


def in_range(rule, delta, old, rise):
    """!
    @brief Check a shift against the direction and size bounds of a rule.
    @param rule Rule dict (direction "up", "down" or "any"; abs_k and rel_rise as [low, high] bounds on the size; rel as the bound on a count).
    @param delta New minus old.
    @param old Old value.
    @param rise Rise of the old maximum temperature over the ambient in K (None when unknown).
    @return bool.
    """
    d = rule.get("direction", "any")
    if d == "up" and delta < 0:
        return False
    if d == "down" and delta > 0:
        return False
    size = abs(delta)
    lo_hi = rule.get("abs_k")
    if lo_hi is not None and not (lo_hi[0] <= size <= lo_hi[1]):
        return False
    lo_hi = rule.get("rel_rise")
    if lo_hi is not None and rise:
        if not (lo_hi[0] <= size / rise <= lo_hi[1]):
            return False
    lo_hi = rule.get("rel")
    if lo_hi is not None and old:
        if not (lo_hi[0] <= size / abs(old) <= lo_hi[1]):
            return False
    return True


def classify_shift(table, board, model, cell, metric, old, new, rise):
    """!
    @brief Class of one shifted metric.
    @param table The expected-shifts table (dict).
    @param board Board name.
    @param model Model key.
    @param cell Cell size in mm.
    @param metric Flattened metric name.
    @param old Value in the baseline.
    @param new Value in the revision under test.
    @param rise Rise of the baseline maximum over the ambient in K (for relative bounds).
    @return tuple (class, list of rule ids, note).
    """
    for entry in table.get("must_not_move", []):
        if scope_matches(entry, board, model, cell, metric):
            return "must_not_move", [entry["id"]], entry.get("reason", "")
    delta = new - old
    found = [r for r in table.get("rules", []) if scope_matches(r, board, model, cell, metric)]
    if not found:
        return "unexplained", [], ""
    quantified = [r for r in found if r.get("status") != "to be explained"]
    ok = [r for r in quantified if in_range(r, delta, old, rise)]
    if ok:
        return "expected", [r["id"] for r in ok], "; ".join(r.get("note", "") for r in ok if r.get("note"))
    explained_later = [r for r in found if r.get("status") == "to be explained"]
    if explained_later:
        return "to_be_explained", [r["id"] for r in explained_later], "; ".join(r.get("note", "") for r in explained_later if r.get("note"))
    return "expected_out_of_range", [r["id"] for r in quantified], "; ".join(r.get("note", "") for r in quantified if r.get("note"))


def diff_sets(base, new, table, key="records"):
    """!
    @brief Compare two result sets and classify every shift.
    @param base Result set of the earlier revision (v2.4.4).
    @param new Result set of the revision under test.
    @param table The expected-shifts table.
    @param key "records" (the steady runs) or "sor" (the SOR runs).
    @return dict: summary (counts per class, identical records, status changes), entries (one per record with a difference or a warning change), missing (keys in only one set).
    """
    a, b = index(base, key), index(new, key)
    entries, counts, identical, same_status_skipped = [], {c: 0 for c in CLASSES}, 0, 0
    counts["warnings_only"] = 0
    for k in sorted(set(a) & set(b), key=lambda t: (t[0], t[2], t[1], t[3])):
        ra, rb = a[k], b[k]
        board, model, cell, solver = k
        mname = model if solver == "direct" else f"{model}_{solver}"
        if ra["status"] != "ok" and rb["status"] != "ok" and ra["status"] == rb["status"]:
            same_status_skipped += 1
            continue
        entry = {"board": board, "model": mname, "cell_mm": cell, "status_old": ra["status"], "status_new": rb["status"], "metrics": [],
                 "seconds_old": ra.get("seconds"), "seconds_new": rb.get("seconds"), "warnings_added": [], "warnings_removed": []}
        rise = (ra["t_max"] - ra["ambient"]) if ra.get("t_max") is not None and ra.get("ambient") is not None else None
        if ra["status"] != rb["status"]:
            cls, rules, note = classify_shift(table, board, mname, cell, "status", 0.0, 1.0, rise)
            entry["metrics"].append({"name": "status", "old": ra["status"], "new": rb["status"], "delta": None, "class": cls, "rules": rules, "note": note or f"{ra['status']} -> {rb['status']}"})
            counts[cls] += 1
        ma, mb = metrics_of(ra), metrics_of(rb)
        for name in sorted(set(ma) | set(mb)):
            va, vb = ma.get(name), mb.get(name)
            if va == vb:
                continue
            if va is None or vb is None:
                cls, rules, note = classify_shift(table, board, mname, cell, "status", 0.0, 1.0, rise)
                entry["metrics"].append({"name": name, "old": va, "new": vb, "delta": None, "class": cls if cls != "unexplained" else "unexplained", "rules": rules, "note": "present in one set only"})
                counts[entry["metrics"][-1]["class"]] += 1
                continue
            cls, rules, note = classify_shift(table, board, mname, cell, name, va, vb, rise)
            entry["metrics"].append({"name": name, "old": va, "new": vb, "delta": vb - va, "class": cls, "rules": rules, "note": note})
            counts[cls] += 1
        wa, wb = set(ra.get("warnings") or []), set(rb.get("warnings") or [])
        entry["warnings_added"], entry["warnings_removed"] = sorted(wb - wa), sorted(wa - wb)
        if not entry["metrics"] and (wa != wb):
            counts["warnings_only"] += 1
        if entry["metrics"] or wa != wb:
            entries.append(entry)
        else:
            identical += 1
    return {"summary": {"counts": counts, "identical_records": identical, "skipped_in_both": same_status_skipped,
                        "alarms": sum(counts[c] for c in ALARMS)},
            "entries": entries, "missing": {"only_in_base": sorted(map(list, set(a) - set(b))), "only_in_new": sorted(map(list, set(b) - set(a)))}}


def transient_diff(base, new):
    """!
    @brief Compare the times to 63 % of two result sets.
    @param base Earlier result set.
    @param new Result set under test.
    @return List of dicts: board, model, part, old, new, relative change (None where a run failed or did not reach 63 %).
    """
    ia = {(t["board"], t["model"]): t for t in base.get("transients", [])}
    ib = {(t["board"], t["model"]): t for t in new.get("transients", [])}
    rows = []
    for k in sorted(set(ia) & set(ib)):
        pa = {p["name"]: p for p in ia[k]["parts"]}
        pb = {p["name"]: p for p in ib[k]["parts"]}
        for name in sorted(set(pa) | set(pb)):
            va = (pa.get(name) or {}).get("t63_s")
            vb = (pb.get(name) or {}).get("t63_s")
            rows.append({"board": k[0], "model": k[1], "part": name, "old": va, "new": vb,
                         "change": (vb / va - 1.0) if (va and vb) else None, "identical": va == vb})
    return rows


def classify_transients(rows, table):
    """!
    @brief Class of every change of a time to 63 %, from the `transients` part of the table.
    @param rows Output of transient_diff.
    @param table The expected-shifts table (keys must_not_move and may_move, each a list of dicts with id, boards, models, note).
    @return The same rows with `class` ("identical", "must_not_move", "to_be_explained" or "unexplained") and `rules`.
    """
    t = table.get("transients", {})
    for r in rows:
        if r["identical"]:
            r["class"], r["rules"] = "identical", []
            continue
        if r["change"] is None:
            r["class"], r["rules"] = "unexplained", []                        # a run that failed or never reached 63 % in one set only
            continue
        hit = [e["id"] for e in t.get("must_not_move", []) if scope_matches(e, r["board"], r["model"], 0.0, "t63")]
        if hit:
            r["class"], r["rules"] = "must_not_move", hit
            continue
        hit = [e["id"] for e in t.get("may_move", []) if scope_matches(e, r["board"], r["model"], 0.0, "t63")]
        r["class"], r["rules"] = ("to_be_explained", hit) if hit else ("unexplained", [])
    return rows


def internal_checks(result_set):
    """!
    @brief Invariants that a result set must satisfy by itself, whatever the revision.
    @details (1) the Lumped and Analytic cell is clamped to 0.5 to 1 mm by the API, so their 2 mm and 1 mm runs are the same run; (2) the SOR solution equals the direct solution at
             the same cell within 1e-3 K; (3) the heat balance of the FVM, FDM and 3D solid closes within 1e-3 of the power.
    @param result_set A result set.
    @return List of dicts: check, board, model, value, ok.
    """
    out = []
    rec = index(result_set)
    for (board, model, cell, solver), r in sorted(rec.items()):
        if model in ("lumped", "analytic") and cell == 2.0 and r["status"] == "ok":
            r1 = rec.get((board, model, 1.0, solver))
            if r1 and r1["status"] == "ok":
                d = abs(r["t_max"] - r1["t_max"])
                out.append({"check": "clamp 2 mm == 1 mm", "board": board, "model": model, "value": d, "ok": d < 1e-9})
        if model in ("fvm", "fdm", "solid3d") and r["status"] == "ok" and r.get("balance_error") is not None:
            out.append({"check": "heat balance", "board": f"{board} {cell:g} mm", "model": model, "value": r["balance_error"], "ok": abs(r["balance_error"]) < 1e-3})
    for (board, model, cell, solver), r in sorted(index(result_set, "sor").items()):
        d = rec.get((board, model, cell, "direct"))
        if r["status"] == "ok" and d and d["status"] == "ok":
            out.append({"check": "SOR equals direct", "board": board, "model": "fvm", "value": abs(r["t_max"] - d["t_max"]), "ok": abs(r["t_max"] - d["t_max"]) < 1e-3})
    return out


def sor_table(base, new):
    """!
    @brief Sweeps, omega and fall-back (0 sweeps: the direct solver took over) of the SOR runs in two result sets (information: the sweeps are expected to fall, the temperatures are checked elsewhere).
    @param base Earlier result set.
    @param new Result set under test.
    @return str, Markdown.
    """
    a, b = index(base, "sor"), index(new, "sor")
    lines = [f"| Board | Sweeps {base['label']} | Sweeps {new['label']} | Omega {base['label']} | Omega {new['label']} | Fall-back {base['label']} | Fall-back {new['label']} | Tmax {base['label']} | Tmax {new['label']} |",
             "| :-- | --: | --: | --: | --: | :-- | :-- | --: | --: |"]
    for k in sorted(set(a) | set(b)):
        ea = (a.get(k) or {}).get("extras") or {}
        eb = (b.get(k) or {}).get("extras") or {}
        ta, tb = (a.get(k) or {}).get("t_max"), (b.get(k) or {}).get("t_max")
        lines.append(f"| {k[0]} | {ea.get('iterations', '')} | {eb.get('iterations', '')} | {ea.get('omega', '')} | {eb.get('omega', '')} | "
                     f"{'yes' if ea.get('iterations') == 0 else ''} | {'yes' if eb.get('iterations') == 0 else ''} | {_num(ta)} | {_num(tb)} |")
    return "\n".join(lines) + "\n"


def markdown(diff, base_label, new_label, max_rows=400):
    """!
    @brief The classified shifts as Markdown tables: the counts, the alarms first, then the maximum-temperature shifts of every record.
    @param diff Output of diff_sets.
    @param base_label Label of the earlier set.
    @param new_label Label of the set under test.
    @param max_rows Rows kept in the long table.
    @return str.
    """
    s = diff["summary"]
    lines = [f"## {new_label} against {base_label}", "", f"Records identical in every number: {s['identical_records']}; skipped or failed in both: {s['skipped_in_both']}; alarms (unexplained or must-not-move): **{s['alarms']}**.", "",
             "| Class | Shifted numbers |", "| :-- | --: |"]
    for c in CLASSES + ("warnings_only",):
        lines.append(f"| {c} | {s['counts'].get(c, 0)} |")
    alarms = [(e, m) for e in diff["entries"] for m in e["metrics"] if m["class"] in ALARMS]
    lines += ["", "### Alarms (to be looked at before the release)", ""]
    if not alarms:
        lines.append("None.")
    else:
        lines += ["| Board | Model | Cell [mm] | Metric | Old | New | Shift | Class |", "| :-- | :-- | --: | :-- | --: | --: | --: | :-- |"]
        for e, m in alarms[:max_rows]:
            lines.append(f"| {e['board']} | {e['model']} | {e['cell_mm']:g} | {m['name']} | {_num(m['old'])} | {_num(m['new'])} | {_num(m['delta'], True)} | {m['class']} |")
    lines += ["", "### Shift of the maximum temperature and of the unknowns, every record that moved", "",
              "| Board | Model | Cell [mm] | Tmax old | Tmax new | Shift [K] | Class (Tmax) | Rules | Unknowns old to new |", "| :-- | :-- | --: | --: | --: | --: | :-- | :-- | :-- |"]
    n = 0
    for e in diff["entries"]:
        by = {m["name"]: m for m in e["metrics"]}
        tm, un = by.get("t_max"), by.get("unknowns")
        any_other = [m for m in e["metrics"] if m["name"] not in ("t_max", "unknowns")]
        if tm is None and un is None and not any_other:
            continue
        if n >= max_rows:
            break
        n += 1
        worst = tm or (any_other[0] if any_other else un)
        lines.append(f"| {e['board']} | {e['model']} | {e['cell_mm']:g} | {_num(tm['old']) if tm else ''} | {_num(tm['new']) if tm else ''} | {_num(tm['delta'], True) if tm else '(' + worst['name'] + ')'} | "
                     f"{worst['class']} | {', '.join(worst['rules'])} | {(str(un['old']) + ' to ' + str(un['new'])) if un else ''} |")
    return "\n".join(lines) + "\n"


def _num(x, sign=False):
    """!
    @brief A number for a table cell.
    @param x Number, string or None.
    @param sign True to always show the sign.
    @return str.
    """
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return f"{x:+.4f}" if sign else f"{x:.4f}"
