#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_bom_roles.py
@brief How well do the designator prefix, the footprint name and the value tell the thermal role of a part, on the placement files and the BOM of the local boards library?
@details Question answered (README 3 and 4): (a) which columns the placement and BOM files carry, (b) the share of parts that each of the three signals decides and how often the signals
         that both speak agree (agreement is not accuracy: there is no labelled ground truth), (c) two physical proxies that are not made by the rule: the parts whose paste
         openings give an exposed pad (program rule `parts.default_shape_kind`, a junction package with a pad) and the mount type of an X3 component layer (TH parts are not heat sources),
         checked against the role, (d) the BOM of the one real BOM in the library (Pulsonix "rabbit watch") against its placement file.
         Third-party files are read from the local library and only numbers and column names are printed or written (out/bom_roles.json, git-ignored); no file is copied.
         Run (from the repository root): .venv/bin/python research/bom-role-and-close-hook/scripts/study_bom_roles.py   (a few seconds, under 300 MB)
"""

import collections
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.append(str(ROOT))
import bomroles as br  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402
from pcbthermal.gerber import components as comp  # noqa: E402
from pcbthermal.gerber import parts as P  # noqa: E402

OUT = HERE.parent / "out"


def library():
    """!
    @brief The local boards library: the environment variable PCBT_LIBRARY, or the first folder `pcb-library` found above this checkout.
    @return Path or None.
    """
    env = os.environ.get("PCBT_LIBRARY")
    if env and Path(env).is_dir():
        return Path(env)
    for p in HERE.parents:
        if (p / "pcb-library").is_dir():
            return p / "pcb-library"
    return None


BOARDS = [  # (label, placement files relative to the library, paste folder or None)
    ("cmm2", ["real/cmm2/placement/pos.csv"], "real/cmm2/gerber"),
    ("co60", ["real/co60/placement/pos.csv"], "real/co60/gerber"),
    ("isastm", ["real/isastm/placement/pos.csv"], "real/isastm/gerber"),
    ("oswlight", ["real/oswlight/placement/pos.csv"], "real/oswlight/gerber"),
    ("rp2040", ["real/rp2040/placement/pos.csv"], "real/rp2040/gerber"),
    ("vstcm", ["real/vstcm/placement/pos.csv"], "real/vstcm/gerber"),
    ("librevna", ["samples/heldout/kicad__librevna/VNA-top-pos.csv", "samples/heldout/kicad__librevna/VNA-bottom-pos.csv"], None),
    ("rabbit", ["samples/pulsonix/rabbit/rabbit watch(Component Positions).csv"], None),
    ("paste-board", ["generated/synthetic/paste-board/files/pos.csv"], "generated/synthetic/paste-board/files"),
]


def placement_rows(lib, files):
    """!
    @brief Read and join the placement files of one board with the program's reader.
    @param lib Library path.
    @param files Relative paths.
    @return list of placement dicts.
    """
    rows = []
    for f in files:
        rows += P.read_placement(lib / f)
    return rows


def classify_rows(rows):
    """!
    @brief Classify every placement row with the three signals.
    @param rows Placement dicts (ref, value, package).
    @return list of (row, classify result).
    """
    return [(r, br.classify(r["ref"], r.get("value", ""), r.get("package", ""))) for r in rows]


def signal_table(results):
    """!
    @brief For each pair of signals, how many parts both decide and how many of those agree; and how many parts each signal decides.
    @param results Output of classify_rows.
    @return dict.
    """
    n = len(results)
    out = {"n": n, "decided": {}, "pairs": {}, "final": collections.Counter(r["role"] for _, r in results), "conflicts": sum(r["conflict"] for _, r in results)}
    for s in ("prefix", "package", "value"):
        out["decided"][s] = sum(1 for _, r in results if r["votes"][s])
    for a, b in (("prefix", "package"), ("prefix", "value"), ("package", "value")):
        both = [(r["votes"][a], r["votes"][b]) for _, r in results if r["votes"][a] and r["votes"][b]]
        out["pairs"][f"{a}/{b}"] = (len(both), sum(1 for x, y in both if x == y))
    return out


def exposed_proxy(lib, label, files, paste_dir, results):
    """!
    @brief Parts that the program's paste rule gives an exposed pad, and the role the text rule gives them.
    @param lib Library path.
    @param label Board label.
    @param files Placement files.
    @param paste_dir Folder with pasteF.gbr / pasteB.gbr, or None.
    @param results Output of classify_rows.
    @return dict or None.
    """
    if not paste_dir:
        return None
    paste = {}
    for side, name in (("top", "pasteF.gbr"), ("bottom", "pasteB.gbr")):
        p = lib / paste_dir / name
        if p.exists():
            try:
                paste[side] = G.read_layer(str(p))
            except Exception:                                            # a layer that cannot be read is simply not used here
                pass
    if not paste:
        return None
    res = P.build_parts(paste=paste, placement=placement_rows(lib, files))
    role = {r["ref"]: c["role"] for r, c in results}
    exposed = [p.designator for p in res.parts if p.shape == "exposed"]
    return {"parts_with_openings": len(res.parts), "exposed": len(exposed), "exposed_role": dict(collections.Counter(role.get(d, "absent") for d in exposed)),
            "exposed_names": exposed}


def x3_proxy(lib):
    """!
    @brief StickHub X3 component layers: mount type of every component against the role of its value and footprint.
    @param lib Library path.
    @return dict or None.
    """
    out = collections.Counter()
    seen = False
    for f in ("compF.gbr", "compB.gbr"):
        p = lib / "real/stickhub/gerber" / f
        if not p.exists():
            continue
        seen = True
        for c in comp.read_components(str(p)):
            r = br.classify(c.ref, c.value, c.footprint)
            out[(c.mount or "?", r["role"])] += 1
    return {f"{m}/{r}": n for (m, r), n in sorted(out.items())} if seen else None


def bom_check(lib):
    """!
    @brief The one real BOM of the library: its columns, its rows, and the BOM role against the placement role of the same designators.
    @param lib Library path.
    @return dict.
    """
    bom = br.read_bom((lib / "samples/pulsonix/rabbit/rabbit watch(Bill of Materials).csv").read_text(encoding="utf-8", errors="replace"))
    # the program's placement reader refuses this Pulsonix file (preamble lines before the header), so the prototype reader gives the refs of the placement
    pl = br.read_bom((lib / "samples/pulsonix/rabbit/rabbit watch(Component Positions).csv").read_text(encoding="utf-8", errors="replace"))
    plc = {r["ref"]: br.classify(r["ref"], r.get("value", ""), "")["role"] for r in pl["rows"]}
    rows = [(r, br.classify(r["ref"], r.get("value", ""), r.get("package", ""), r.get("description", ""))) for r in bom["rows"]]
    in_plc = [(r, c) for r, c in rows if r["ref"] in plc]
    agree = sum(1 for r, c in in_plc if c["role"] == plc[r["ref"]])
    dnp = [r["ref"] for r, _ in rows if r["dnp"]]
    return {"columns": bom["columns"], "unknown_columns": bom["unknown_columns"], "sections": bom["sections"], "designators": len(rows), "in_placement": len(in_plc),
            "role_agrees_with_placement_rule": agree, "dnp": len(dnp), "dnp_in_placement": sum(1 for d in dnp if d in plc),
            "bom_roles": dict(collections.Counter(c["role"] for _, c in rows))}


def prefix_table(all_results):
    """!
    @brief For every designator prefix seen, the role the text signals (package, value) give, to show where the prefix is and is not reliable.
    @param all_results List of (row, classify result) over all boards.
    @return dict prefix -> Counter of roles from package+value only.
    """
    out = collections.defaultdict(collections.Counter)
    for r, c in all_results:
        pk = c["votes"]["package"] or c["votes"]["value"]
        out[br.prefix_of(r["ref"])][pk or "silent"] += 1
    return out


def main():
    """!
    @brief Run every check and print the tables the README quotes.
    @return int exit code.
    """
    lib = library()
    if lib is None:
        print("pcb-library not found (set PCBT_LIBRARY)")
        return 1
    OUT.mkdir(exist_ok=True)
    report, everything = {}, []
    print(f"{'board':12s}{'parts':>6s}{'prefix':>8s}{'package':>9s}{'value':>7s}  final: component/source/none/unknown  conflicts")
    for label, files, paste_dir in BOARDS:
        try:
            rows = placement_rows(lib, files)
        except (OSError, ValueError) as e:
            print(f"{label}: not read ({e})")
            continue
        res = classify_rows(rows)
        everything += res
        t = signal_table(res)
        f = t["final"]
        print(f"{label:12s}{t['n']:6d}{t['decided']['prefix']:8d}{t['decided']['package']:9d}{t['decided']['value']:7d}  "
              f"{f['component']:5d}/{f['source']:4d}/{f['none']:4d}/{f['unknown']:4d}   {t['conflicts']}")
        report[label] = {**t, "final": dict(f), "exposed": exposed_proxy(lib, label, files, paste_dir, res)}
    tot = signal_table(everything)
    print(f"{'ALL':12s}{tot['n']:6d}{tot['decided']['prefix']:8d}{tot['decided']['package']:9d}{tot['decided']['value']:7d}  "
          f"{tot['final']['component']:5d}/{tot['final']['source']:4d}/{tot['final']['none']:4d}/{tot['final']['unknown']:4d}   {tot['conflicts']}")
    print("\nagreement of the signals that both decide (pairs decided, agreeing):")
    for k, (n, a) in tot["pairs"].items():
        print(f"  {k:16s}{n:6d}{a:6d}  {100 * a / max(n, 1):5.1f} %")
    report["ALL"] = {**tot, "final": dict(tot["final"])}
    print("\nexposed-pad parts (program paste rule) and the role of the text rule:")
    for label, v in report.items():
        e = v.get("exposed") if label != "ALL" else None
        if e:
            print(f"  {label:12s}{e['exposed']:3d} exposed of {e['parts_with_openings']:4d} parts with openings, roles {e['exposed_role']}")
    x3 = x3_proxy(lib)
    print("\nX3 stickhub: mount/role counts:", x3)
    report["x3"] = x3
    pt = prefix_table(everything)
    print("\nprefix -> role of the package/value signals (only prefixes with 5 or more parts):")
    for p, c in sorted(pt.items(), key=lambda kv: -sum(kv[1].values())):
        if sum(c.values()) >= 5:
            print(f"  {p or '(none)':8s}{sum(c.values()):5d}  {dict(c)}")
    report["prefix"] = {p: dict(c) for p, c in pt.items()}
    # the disagreements, as designator prefix + package names (not values), for the README
    dis = collections.Counter()
    for r, c in everything:
        v = c["votes"]
        if v["prefix"] and v["package"] and v["prefix"] != v["package"]:
            dis[(br.prefix_of(r["ref"]), r.get("package", "")[:40], v["prefix"], v["package"])] += 1
    print("\nprefix against package, disagreements (prefix, footprint, prefix role, footprint role):")
    for k, n in dis.most_common(12):
        print(f"  {n:3d}  {k}")
    report["bom"] = bom_check(lib)
    print("\nBOM (Pulsonix rabbit):", json.dumps(report["bom"], indent=1))
    (OUT / "bom_roles.json").write_text(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
