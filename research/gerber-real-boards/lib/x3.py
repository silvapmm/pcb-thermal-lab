#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file x3.py
@brief The Gerber X3 component layer (`%TF.FileFunction,Component,L1,Top*%`): the parts of a board with reference designator, footprint, value, rotation, origin, courtyard outline and pins, read as text.
@details X3 is the assembly extension of Gerber: a component layer holds, for every part, the object attribute `TO.C` (reference designator) followed by `TO.CFtp` (footprint), `TO.CVal` (value), `TO.CMnt`
         (mount type: SMD, TH, ...), `TO.CRot` (rotation in degrees), `TO.CLbN` (library name), optionally `TO.CMfr`, `TO.CMPN` (manufacturer and part number), then the drawn objects: one flash with the aperture function
         `ComponentMain` (the origin of the part), the courtyard as a polyline with `ComponentOutline,Courtyard`, and one flash per pin with `TO.P,<ref>,<pin>,<name>` and `ComponentPin`. The layout used here is the one seen
         in the Ucamco X3 sample of KiCad 8 (StickHub); the attribute names are as in the specification (read by the review of the sample, the specification revision 2024.05 itself was not read in full: README bibliography).
         This reader is text-based and tolerant: it returns what it finds and ignores the rest. It needs no other module.
"""

import re
from pathlib import Path

_FS = re.compile(r"%FS[LT]?[AI]X(\d)(\d)Y(\d)(\d)\*%")
_MO = re.compile(r"%MO(MM|IN)\*%")
_ATTR = re.compile(r"%TO\.(C\w*),([^*]*)\*%")
_PIN = re.compile(r"%TO\.P,([^,*]*),([^,*]*)(?:,([^*]*))?\*%")
_XY = re.compile(r"X(-?\d+)Y(-?\d+)D0([123])\*")
_AP = re.compile(r"^D(\d+)\*$", re.M)
_APF = re.compile(r"%TA\.AperFunction,([^*]*)\*%\s*%ADD(\d+)")


def _scale(text):
    """!
    @brief The factor that turns the integer coordinates of a file into millimetres.
    @param text File content.
    @return float.
    @throws ValueError If the file has no format statement.
    """
    m = _FS.search(text)
    if not m:
        raise ValueError("no format statement (FS) in the file")
    unit = 25.4 if (_MO.search(text) and _MO.search(text).group(1) == "IN") else 1.0
    return unit / (10 ** int(m.group(2)))


def components(path):
    """!
    @brief The parts of an X3 component layer.
    @param path Component layer file.
    @return list of dicts: ref, footprint, value, mount, rotation (degrees), origin (x, y mm) or None, courtyard (list of (x, y) mm) or [], pins (list of dict pin, name, x, y), extra (other TO.C* attributes).
    @throws ValueError If the file is not a Gerber file with a format statement.
    """
    text = Path(path).read_text(errors="replace")
    s = _scale(text)
    # The aperture numbers by function, to tell the origin, the courtyard and the pins apart
    func = {int(n): f for f, n in _APF.findall(text)}
    main_d = {n for n, f in func.items() if f.startswith("ComponentMain")}
    court_d = {n for n, f in func.items() if f.startswith("ComponentOutline,Courtyard")}
    out = []
    rec = None
    cur = None                                                            # the aperture selected by the last D-code line (it is selected BEFORE the %TO.C line of the part)
    pending_pin = None
    for line in text.splitlines():
        line = line.strip()
        m = _AP.match(line)
        if m and int(m.group(1)) >= 10:
            cur = int(m.group(1))
            continue
        if line.startswith("%TO.C,"):                                      # a new part starts; its other C attributes follow on the next lines
            rec = {"ref": line[len("%TO.C,"):].rstrip("*%"), "footprint": "", "value": "", "mount": "", "rotation": 0.0, "origin": None, "courtyard": [], "pins": [], "extra": {}}
            out.append(rec)
            pending_pin = None
            continue
        am = _ATTR.match(line)
        if am and rec is not None:
            k, v = am.group(1), am.group(2)
            if k == "CFtp":
                rec["footprint"] = v
            elif k == "CVal":
                rec["value"] = v
            elif k == "CMnt":
                rec["mount"] = v
            elif k == "CRot":
                rec["rotation"] = float(v or 0.0)
            else:
                rec["extra"][k] = v
            continue
        pm = _PIN.match(line)
        if pm:
            pending_pin = (pm.group(2), pm.group(3) or "")
            continue
        if line.startswith("%TD"):
            pending_pin = None
            continue
        if rec is None:
            continue
        for x, y, d in _XY.findall(line):
            pt = (int(x) * s, int(y) * s)
            if d == "3" and cur in main_d and rec["origin"] is None:
                rec["origin"] = pt
            elif d == "3" and pending_pin is not None:
                rec["pins"].append({"pin": pending_pin[0], "name": pending_pin[1], "x": pt[0], "y": pt[1]})
            elif d in "12" and cur in court_d:
                rec["courtyard"].append(pt)
    return out


def courtyard_box(part):
    """!
    @brief The bounding box of the courtyard of a part (or of its pins when it has no courtyard).
    @param part A dict of `components`.
    @return tuple (xmin, ymin, xmax, ymax) in mm, or None when the part has neither.
    """
    pts = part["courtyard"] or [(p["x"], p["y"]) for p in part["pins"]]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)
