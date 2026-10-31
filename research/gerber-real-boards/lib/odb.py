#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file odb.py
@brief A small reader of the component part of an ODB++ job (directory or .tgz): the components of the top and bottom sides with position, rotation, side, package and part name, and the step profile (board outline).
@details ODB++ is a directory tree: matrix/matrix (layer list and order), steps/<step>/profile (outline), steps/<step>/layers/<layer>/features (graphics), steps/<step>/layers/comp_+_top/components and
         comp_+_bot/components (one `CMP` record per part, followed by `PRP` property lines and one `TOP` record per pin), steps/<step>/eda/data (packages, nets), steps/<step>/netlists. The record layouts
         used here are written FROM MEMORY of the published specification and of the open parsers; they are tolerant (unknown records are skipped) and MUST be checked against the specification and the sample archives
         (scripts/study_odb_structure.py prints what the samples really contain and fails loudly on a mismatch). Status in the README bibliography: specification not obtained (N), layout from memory (M).
         Assumed layout: `CMP <pkg_ref> <x> <y> <rot> <N|M> <ref> <part_name>;...`; `TOP <pin> <x> <y> <rot> <N|M> <net_num> <subnet> <name>`; units from the `UNITS=` line (INCH or MM) of the file.
"""

import re
import tarfile
from pathlib import Path


def _read_members(path):
    """!
    @brief Read the text files of an ODB++ job into a dict.
    @param path A directory or a .tgz/.tar.gz/.tar archive.
    @return dict relative path (with forward slashes, without the leading job folder) -> text.
    """
    path = Path(path)
    out = {}
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                out["/".join(f.relative_to(path).parts)] = f.read_text(errors="replace")
        return out
    with tarfile.open(path) as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            parts = m.name.split("/")
            f = tf.extractfile(m)
            raw = f.read() if f else b""
            if m.name.endswith(".Z"):                                     # compressed members (unix compress) are not read: reported by the study
                continue
            out["/".join(parts[1:]) if len(parts) > 1 else m.name] = raw.decode("latin-1", "replace")
    return out


def steps(files):
    """!
    @brief The step names found in the job.
    @param files dict returned by _read_members.
    @return sorted list of step names.
    """
    return sorted({k.split("/")[1] for k in files if k.startswith("steps/") and k.count("/") >= 2})


def components(files, step=None):
    """!
    @brief The parts of one step, both sides.
    @param files dict returned by _read_members.
    @param step Step name (None: the first step, usually "pcb").
    @return list of dicts: ref, part, package_index, x, y (in the unit of the file: see `unit`), rot, side ("top"/"bottom"), mirror (bool), pins (count of TOP records), unit ("inch"/"mm").
    """
    st = step or (steps(files) or [None])[0]
    out = []
    for side, layer in (("top", "comp_+_top"), ("bottom", "comp_+_bot")):
        text = files.get(f"steps/{st}/layers/{layer}/components")
        if text is None:
            continue
        unit = "mm" if re.search(r"UNITS\s*=\s*MM", text, re.I) else "inch"
        cur = None
        for ln in text.splitlines():
            ln = ln.strip()
            if ln.startswith("CMP"):
                body = ln.split(";")[0].split()
                # CMP pkg_ref x y rot mirror comp_name part_name
                if len(body) >= 8:
                    cur = {"ref": body[6], "part": body[7], "package_index": int(body[1]), "x": float(body[2]), "y": float(body[3]), "rot": float(body[4]),
                           "side": side, "mirror": body[5].upper().startswith("M"), "pins": 0, "unit": unit}
                    out.append(cur)
            elif ln.startswith("TOP") and cur is not None:
                cur["pins"] += 1
    return out


def profile(files, step=None):
    """!
    @brief The board outline of a step from its `profile` file (OB/OS/OC records of the surface).
    @param files dict returned by _read_members.
    @param step Step name (None: the first step).
    @return list of (x, y) vertices of the polygon (straight segments only; arcs are reported by their end points), in the unit of the file; empty when there is no profile.
    """
    st = step or (steps(files) or [None])[0]
    text = files.get(f"steps/{st}/profile")
    if text is None:
        return []
    pts = []
    for ln in text.splitlines():
        t = ln.split()
        if t and t[0] in ("OB", "OS", "OC") and len(t) >= 3:
            pts.append((float(t[1]), float(t[2])))
    return pts


def load(path):
    """!
    @brief Read a job and return its parts and outline.
    @param path Directory or archive of an ODB++ job.
    @return dict with files (names only), steps, components, profile.
    """
    f = _read_members(path)
    return {"files": sorted(f), "steps": steps(f), "components": components(f), "profile": profile(f)}


def parse_text(text, side="top"):
    """!
    @brief Parse the text of one `components` file (used by the tests, with no archive).
    @param text Content of a components file.
    @param side "top" or "bottom".
    @return list of components as in `components`.
    """
    files = {"steps/pcb/layers/comp_+_top/components" if side == "top" else "steps/pcb/layers/comp_+_bot/components": text}
    return components(files, "pcb")
