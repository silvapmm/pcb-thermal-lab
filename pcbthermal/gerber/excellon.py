#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file excellon.py
@brief Excellon (and XNC) drill files, and Gerber X2 drill layers: the holes with position, diameter, plating and slot end.
@details Handles METRIC and INCH headers (or M71/M72), the format hint of the header (`METRIC,000.000`, `FILE_FORMAT=3:3` comments, default 3.3 metric and 2.4 inch),
         leading or trailing zero suppression (LZ/TZ, as the Excellon wording keeps the zeros that are written), explicit decimal points, tool definitions (`T01C0.8`) and the
         comment form some CAD tools use (`;T01 Holesize 1. = 12.000000 ... PLATED MILS`), the repeat command `R<n>X..Y..`, routed slots (`G00 .. M15 .. G01 .. M16`, one slot per
         straight segment) and canned slots (`X..Y..G85X..Y..`). Plating comes from the tool comment, the file function (`; #@! TF.FileFunction,Plated,1,4,PTH` or `NonPlated`)
         or `;TYPE=PLATED`; None when the file does not say (the caller falls back on the file name). Refused (`UnsupportedFeatureError`): incremental mode (ICI, G91), routed arcs
         (G02/G03), pattern commands (M25, M01 patterns), canned circles, origin shifts (G93), a tool used without a diameter, and a file without any unit.
"""

import re
from pathlib import Path
from typing import List, NamedTuple, Optional

from .errors import GerberError, UnsupportedFeatureError
from .parser import MAX_OPERATIONS, Layer, parse_number

MAX_HOLES = MAX_OPERATIONS     # holes and slots of one drill file (a repeat command R<n> must not multiply a line into a hang)


class Hole(NamedTuple):
    """!@brief One drilled hole or routed slot (mm): the centre (the start of a slot), the tool diameter, the plating and the end of the slot."""
    x: float
    y: float
    diameter: float
    plated: Optional[bool]
    x_end: Optional[float] = None
    y_end: Optional[float] = None

    @property
    def is_slot(self):
        """!
        @brief Whether the hole is a routed slot.
        @return bool True when the end point is set.
        """
        return self.x_end is not None


class DrillFile(NamedTuple):
    """!@brief The content of a drill file: the holes, the plating of the whole file (None when unknown), the copper layers spanned and the tool diameters (mm)."""
    holes: List[Hole]
    plated: Optional[bool]
    span: Optional[tuple]
    tools: dict


def drill_function(text):
    """!
    @brief The X2 file function that KiCad (and others) write in a comment, for example `; #@! TF.FileFunction,Plated,1,4,PTH`, or Altium's `;TYPE=PLATED`.
    @param text Excellon file content.
    @return tuple (plated True/False/None when the file does not say, first copper layer or None, last copper layer or None).
    """
    for line in text.splitlines()[:60]:
        s = line.strip()
        m = re.match(r";\s*#@!\s*TF\.FileFunction,([^,*]+)(?:,(\d+),(\d+))?", s)
        if m:
            kind = m.group(1)
            plated = True if kind == "Plated" else False if kind == "NonPlated" else None
            return plated, (int(m.group(2)) if m.group(2) else None), (int(m.group(3)) if m.group(3) else None)
        m = re.match(r";\s*TYPE\s*=\s*(NON_)?PLATED", s, re.I)
        if m:
            return (m.group(1) is None), None, None
    return None, None, None


def is_gerber_text(text):
    """!
    @brief Whether a drill file is in Gerber (X2) format instead of Excellon.
    @param text File content.
    @return bool True when the first kilobytes carry a Gerber format statement.
    """
    return bool(re.search(r"%FS[LTD]?[AI]X\d\dY\d\d", text[:4000]))


def read_drill(text, name=""):
    """!
    @brief Read the holes of an Excellon (or X2 Gerber) drill file.
    @param text File content.
    @param name File name, for the messages.
    @return DrillFile (holes in mm, file plating, layer span, tool diameters).
    @throws UnsupportedFeatureError For the constructs listed in the module description.
    @throws GerberError For a file that cannot be understood (also a malformed number or more than MAX_HOLES holes).
    """
    text = text.lstrip("\ufeff")                                               # a byte order mark would hide the first line (METRIC or M48)
    try:
        return _read_drill(text, name)
    except GerberError:
        raise
    except (ValueError, IndexError, KeyError, TypeError, ZeroDivisionError, OverflowError, MemoryError) as exc:
        # A malformed number or a hostile value: the reader's own error, naming the file, never a raw traceback
        raise GerberError(f"{name or 'file'}: malformed drill data ({type(exc).__name__}: {exc})") from exc


def _read_drill(text, name):
    """!
    @brief The body of read_drill (its errors are wrapped by the caller).
    @param text File content.
    @param name File name, for the messages.
    @return DrillFile.
    """
    if is_gerber_text(text):
        return drill_from_gerber(Layer(text, name))
    file_plated, first, last = drill_function(text)
    unit, zeros, ndec, nint = None, "L", None, None
    raw, mm_sizes, tool_plated = {}, {}, {}
    holes = []
    tool = None
    in_header = True
    slot_start = None
    cur_g = None                                                              # routing mode: "0" (move), "1" (cut) or None (drill hits)
    last_xy = (0.0, 0.0)

    def refuse(feature):
        """!@brief Raise the refusal. @param feature Description. @throws UnsupportedFeatureError Always."""
        raise UnsupportedFeatureError(name, feature)

    def diameter(t):
        """!@brief Diameter of a tool in mm. @param t Tool number. @return float. @throws GerberError If the tool has no diameter."""
        if t in mm_sizes:
            return mm_sizes[t]
        if t in raw:
            return raw[t] * (unit or 1.0)
        raise GerberError(f"{name}: tool T{t} is used without a diameter")

    def plating(t):
        """!@brief Plating of a tool, falling back on the file. @param t Tool number. @return True, False or None."""
        return tool_plated[t] if tool_plated.get(t) is not None else file_plated

    for rawline in text.splitlines():
        line = rawline.strip()
        if not line:
            continue
        if line.startswith(";"):
            ff = re.match(r";\s*FILE_FORMAT\s*=\s*(\d+):(\d+)", line)
            if ff:                                                          # P-CAD, Altium: the format as a comment (integer:decimal digits)
                nint, ndec = int(ff.group(1)), int(ff.group(2))
            m = re.match(r";\s*T(\d+)\s+Holesize\s+\d+\.\s*=\s*([\d.]+)", line)
            if m:
                u = re.search(r"\b(MILS|MM|INCH)\b", line)
                t, d = int(m.group(1)), float(m.group(2))
                mm_sizes[t] = d * (0.0254 if u and u.group(1) == "MILS" else 25.4 if u and u.group(1) == "INCH" else 1.0)
                tool_plated[t] = None if "PLATED" not in line else ("NON_PLATED" not in line)
            continue
        up = line.upper()
        if up.startswith(("METRIC", "INCH")):
            unit = 25.4 if up.startswith("INCH") else 1.0
            # Excellon names the zeros that are KEPT (LZ = leading zeros kept, trailing omitted; TZ = trailing zeros kept, leading omitted): the opposite of the Gerber FS wording
            zeros = "L" if "TZ" in up else "T" if "LZ" in up else zeros
            m = re.search(r"(0+)\.(0+)", line) or re.search(r"(\d)[.:](\d)", line)   # "000.000" or "3.3"
            if m:
                a, b = m.group(1), m.group(2)
                nint, ndec = (len(a), len(b)) if a.startswith("0") and len(a) + len(b) > 2 else (int(a), int(b))
            continue
        if up in ("M71", "M72"):                                           # the unit as a code: M71 metric, M72 inch
            unit = 25.4 if up == "M72" else 1.0
            continue
        if up in ("ICI", "ICI,ON") or up.startswith("G91") or up == "G93" or up.startswith("G93X"):
            refuse("incremental mode or origin shift (ICI, G91, G93)")
        if up in ("M25", "M01") or up.startswith("M02X") or up.startswith("M02Y"):
            refuse("Excellon pattern commands (M25, M01, M02 with offsets)")
        if up.startswith(("G82", "G83", "G84", "G32", "G33")):
            refuse(f"Excellon canned cycle {up[:3]}")
        if line == "%" or up.startswith("M95"):
            in_header = False
            continue
        m = re.match(r"T(\d+)(.*)$", line)
        if m and not re.match(r"T\d+[XY]", line):
            tool = int(m.group(1))
            c = re.search(r"C([\d.]+)", m.group(2))                           # other parameters (F, S, B, H, Z) may precede the diameter
            if c:
                raw[tool] = float(c.group(1))
            continue
        rep = re.match(r"R(\d+)(?:X([-+]?[\d.]+))?(?:Y([-+]?[\d.]+))?$", line)
        if rep and holes and nint is not None:                              # repeat the last hole n more times with an offset (Allegro, Excellon "R" command)
            n = int(rep.group(1))
            if len(holes) + n > MAX_HOLES:
                raise GerberError(f"{name}: the repeat {line} makes more than {MAX_HOLES} holes")
            ddx = parse_number(rep.group(2), nint, ndec, zeros) * unit if rep.group(2) else 0.0
            ddy = parse_number(rep.group(3), nint, ndec, zeros) * unit if rep.group(3) else 0.0
            h = holes[-1]
            for k in range(1, n + 1):
                holes.append(Hole(h.x + k * ddx, h.y + k * ddy, h.diameter, h.plated))
            last_xy = (h.x + n * ddx, h.y + n * ddy)
            continue
        if line in ("M16", "M17", "G05", "G81"):                                    # tool up / end of the route / back to drilling
            slot_start, cur_g = None, None
            continue
        g = re.match(r"G0([0-3])", line)
        if g:
            if g.group(1) in "23":
                refuse("routed arcs (G02/G03) in an Excellon file")
            cur_g = g.group(1)
        if g or line.startswith(("X", "Y")):
            if g and not in_header:                                           # a routed slot: G00 (start), M15 (tool down), G01 (end), M16 (tool up)
                line = line[3:]
            if unit is None:                                                  # no METRIC or INCH line: inch when the file talks about mils or inches (Allegro)
                if re.search(r"INCH|MILS", text.upper()):
                    unit = 25.4
                elif re.search(r"\bMM\b|METRIC", text.upper()):
                    unit = 1.0
                else:                                                         # no unit anywhere: guessing would place the holes 25 times wrong
                    refuse("an Excellon file without unit information (no METRIC, INCH, M71 or M72): the unit must be chosen by the user")
            if nint is None:
                nint, ndec = (2, 4) if unit == 25.4 else (3, 3)
            slot = re.match(r"(X[-+]?[\d.]+)?(Y[-+]?[\d.]+)?G85(X[-+]?[\d.]+)?(Y[-+]?[\d.]+)?$", line)
            if slot:                                                          # canned slot "X..Y..G85X..Y..": from the first point to the second
                def coord(word, prev):
                    """!@brief One coordinate of a slot line. @param word "X.." / "Y.." or None. @param prev Value kept when the word is missing. @return Value (mm)."""
                    return parse_number(word[1:], nint, ndec, zeros) * unit if word else prev
                sx, sy = coord(slot.group(1), last_xy[0]), coord(slot.group(2), last_xy[1])
                ex, ey = coord(slot.group(3), sx), coord(slot.group(4), sy)
                holes.append(Hole(sx, sy, diameter(tool), plating(tool), ex, ey))
                last_xy = (ex, ey)
                continue
            mx = re.search(r"X([-+]?[\d.]+)", line)
            my = re.search(r"Y([-+]?[\d.]+)", line)
            if not (mx or my):
                continue
            # A coordinate that is left out keeps its previous value (modal), as many CAD tools write repeated columns
            x = parse_number(mx.group(1), nint, ndec, zeros) * unit if mx else last_xy[0]
            y = parse_number(my.group(1), nint, ndec, zeros) * unit if my else last_xy[1]
            last_xy = (x, y)
            if cur_g == "0":
                slot_start = (x, y)
            elif cur_g == "1":
                if slot_start is not None:                                    # one slot per straight segment of the route
                    holes.append(Hole(slot_start[0], slot_start[1], diameter(tool), plating(tool), x, y))
                slot_start = (x, y)                                           # the route continues from here (modal G01 coordinates)
            else:
                holes.append(Hole(x, y, diameter(tool), plating(tool)))
            if len(holes) > MAX_HOLES:
                raise GerberError(f"{name}: more than {MAX_HOLES} holes")
    sizes = {t: diameter(t) for t in set(raw) | set(mm_sizes)}
    return DrillFile(holes, file_plated, (first, last) if first else None, sizes)


def drill_from_gerber(layer):
    """!
    @brief The holes of an X2 Gerber drill layer (flashes are holes, draws are slots; the aperture is the tool).
    @param layer Parsed Layer whose file function is Plated or NonPlated.
    @return DrillFile.
    """
    ff = layer.file_function
    plated = True if ff[:1] == ["Plated"] else False if ff[:1] == ["NonPlated"] else None
    span = (int(ff[1]), int(ff[2])) if plated is not None and len(ff) >= 3 and ff[1].isdigit() and ff[2].isdigit() else None
    holes = []
    for kind, dark, a in layer.ops:
        if not dark or kind == "region":
            continue
        if kind == "flash":
            holes.append(Hole(a[1], a[2], 2.0 * a[0].radius, plated))
        else:
            holes.append(Hole(a[1], a[2], 2.0 * a[0].radius, plated, a[3], a[4]))
    return DrillFile(holes, plated, span, {i: ap.p[0] for i, ap in layer.apertures.items() if ap.kind == "C"})


def read_drill_file(path):
    """!
    @brief Read a drill file from disk.
    @param path File path.
    @return DrillFile.
    """
    p = Path(path)
    return read_drill(p.read_text(encoding="utf-8", errors="replace"), p.name)
