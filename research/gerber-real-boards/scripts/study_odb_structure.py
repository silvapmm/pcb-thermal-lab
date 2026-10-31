#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_odb_structure.py
@brief What does an ODB++ job really contain that the program could use (components with package and position, the step profile, layers and their order, the nets), checked on the three small sample archives?
@details The reader `lib/odb.py` was written from memory of the format; this study is where that memory meets the files. For every archive in data/odb/ (scripts/fetch_boards.py --odb) it lists the steps, the layers of
         the matrix (name, type, context), the number of members and of compressed (.Z) members (not read by the reader), the components of both sides (count, packages, a few rows), the profile (number of points, its box) and
         whether an eda/data file with packages and nets exists. It stops with an error when a components file exists and the reader found no component in it (the layout in odb.py is then wrong and must be corrected
         from the specification before anything is built on it). Units of the file are printed, not converted.
         Success criterion (before the run): components found with reference designators, positions and a side for every sample that has comp_+_top; the profile polygon closes. NOT verified: that the positions are
         the part origin in the same frame as the Gerber of the same job (no Gerber set of these jobs is available), IPC-2581 (another format, not read at all), the licence of the sample archives.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_odb_structure.py   (seconds)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import re
import sys

import odb
import rb_paths


def matrix_layers(files):
    """!
    @brief The layers listed in matrix/matrix.
    @param files Dict of the job's text files.
    @return list of dicts name, type, context, row.
    """
    text = files.get("matrix/matrix", "")
    out = []
    for blk in re.findall(r"LAYER\s*\{(.*?)\}", text, re.S):
        d = dict(re.findall(r"(\w+)\s*=\s*(\S+)", blk))
        out.append({"row": d.get("ROW"), "name": d.get("NAME"), "type": d.get("TYPE"), "context": d.get("CONTEXT")})
    return out


def describe(path):
    """!
    @brief The structure of one archive.
    @param path Archive path.
    @return dict with the findings.
    @throws RuntimeError If a components file exists and no component was read from it.
    """
    files = odb._read_members(path)
    st = odb.steps(files)
    comps = odb.components(files, st[0] if st else None)
    has_file = any(k.endswith("/components") and "comp_+_" in k for k in files)
    if has_file and not comps:
        raise RuntimeError(f"{path.name}: a components file exists but the reader found no component: fix lib/odb.py from the specification")
    prof = odb.profile(files, st[0] if st else None)
    pk = {}
    for c in comps:
        pk[c["part"]] = pk.get(c["part"], 0) + 1
    return {"members": len(files), "steps": st, "layers": matrix_layers(files), "components": len(comps), "top": sum(c["side"] == "top" for c in comps),
            "bottom": sum(c["side"] == "bottom" for c in comps), "unit": comps[0]["unit"] if comps else None, "first_rows": comps[:5],
            "parts_most_used": sorted(pk.items(), key=lambda kv: -kv[1])[:5], "profile_points": len(prof), "profile_box": ([min(p[0] for p in prof), min(p[1] for p in prof), max(p[0] for p in prof), max(p[1] for p in prof)] if prof else None),
            "has_eda_data": any(k.endswith("eda/data") for k in files), "has_netlist": any("netlists" in k for k in files), "has_user_attributes": sum(1 for k in files if k.endswith("/attrlist"))}


def main(argv):
    """!
    @brief Describe every archive of data/odb/ and write out/odb_structure.json.
    @param argv Unused.
    @return None.
    """
    d = rb_paths.DATA / "odb"
    archives = sorted(d.glob("*.tgz")) if d.exists() else []
    if not archives:
        raise SystemExit("no ODB++ archive in data/odb/: run scripts/fetch_boards.py --odb")
    res = {}
    for a in archives:
        res[a.name] = describe(a)
        print(a.name, json.dumps({k: v for k, v in res[a.name].items() if k != "first_rows"}, indent=1))
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "odb_structure.json", "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
