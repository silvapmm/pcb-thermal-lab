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
            "inside_profile_box": sum(1 for c in comps if prof and min(q[0] for q in prof) - 0.01 <= c["x"] <= max(q[0] for q in prof) + 0.01 and min(q[1] for q in prof) - 0.01 <= c["y"] <= max(q[1] for q in prof) + 0.01),
            "with_height_attribute": sum(1 for k, t in files.items() if k.endswith("comp_+_top/components") or k.endswith("comp_+_bot/components") for _ in re.finditer(r"^CMP .*;.*1=", t, re.M)),
            "with_body_description": sum(1 for k, t in files.items() if k.endswith("/components") for _ in re.finditer(r"^PRP PackageDescription ", t, re.M)),
            "has_eda_data": any(k.endswith("eda/data") for k in files), "has_netlist": any("netlists" in k for k in files), "has_user_attributes": sum(1 for k in files if k.endswith("/attrlist"))}


def pin_registration(path):
    """!
    @brief Do the pins of the component layers sit on the pad flashes of the paste and copper layers of the same job (the same frame, no registration needed)?
    @param path Archive path.
    @return dict layer name -> (pad flashes in the layer, pins within 1.5 micrometres of a flash, pins of the side the layer belongs to) for every layer of paste and outer copper.
    """
    import tarfile
    import numpy as np
    t = tarfile.open(path)
    mem = {m.name: m for m in t.getmembers() if m.isfile()}
    side_pins = {"top": [], "bot": []}
    for side, lay in (("top", "comp_+_top"), ("bot", "comp_+_bot")):
        for k in mem:
            if k.endswith(lay + "/components"):
                txt = t.extractfile(mem[k]).read().decode("latin-1")
                side_pins[side] += [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"^(?:TOP|BOT) \d+ (\S+) (\S+)", txt, re.M)]
    out = {}
    for k in mem:
        if "/layers/" not in k or not k.endswith("/features"):
            continue
        name = k.split("/layers/")[1].split("/")[0]
        low = name.lower()
        side = "top" if low.startswith(("top", "f.", "toppaste")) or low in ("top_copper",) else "bot" if low.startswith(("bottom", "b.", "bot")) else None
        if side is None or not any(w in low for w in ("paste", "copper", "layer")) and low not in ("top", "bottom"):
            continue
        txt = t.extractfile(mem[k]).read().decode("latin-1")
        pts = np.array([(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"^P (\S+) (\S+) ", txt, re.M)])
        if not len(pts) or not side_pins[side]:
            continue
        tol = 0.0015 * (1.0 if "UNITS=MM" in txt[:60] else 1.0 / 25.4)           # 1.5 micrometres in the units of the file
        hit = sum(1 for x, y in side_pins[side] if np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y)) < tol)
        out[name] = (len(pts), hit, len(side_pins[side]))
    return out


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
        res[a.name]["pin_registration"] = pin_registration(a)
        print(a.name, "pins on the pad flashes (layer: flashes, pins on a flash, pins of the side):", res[a.name]["pin_registration"])
        print(a.name, json.dumps({k: v for k, v in res[a.name].items() if k != "first_rows"}, indent=1))
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "odb_structure.json", "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
