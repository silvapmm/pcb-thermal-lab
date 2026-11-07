#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file bomroles.py
@brief Prototype (research only) of the BOM reader and of the thermal-role rule of a part: designator, value, footprint, description -> source / component / none / unknown.
@details Nothing here is in the program. The reader finds the header of a BOM table below a preamble, maps the column names of the common exporters (KiCad, JLCPCB, Altium, Pulsonix,
         PCBWay, generic) to canonical fields, expands grouped designators ("C2 C6 C7", "R1-R4") and flags do-not-populate rows. The rule has three independent signals (the designator
         prefix, the footprint name, the value or description words) so that their agreement can be measured; a part is "unknown" when no signal speaks or the signals tie.
         Roles: "component" (a junction: IC, transistor, diode, LED, regulator), "source" (a pure dissipator: resistor, inductor, ferrite, fuse),
         "none" (connector, switch, test point, mounting hole, fiducial, battery, crystal, capacitor: no heat source offered by default), "unknown".
         Hostile input: sizes are capped, a cell is read as text only, nothing is evaluated.
"""

import csv
import io
import re

MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 200000
MAX_RANGE = 2000

## Header cell (lower case, letters and digits only) -> canonical field.
FIELDS = {
    "designator": "ref", "designators": "ref", "reference": "ref", "references": "ref", "refdes": "ref", "ref": "ref", "refs": "ref", "components": "ref", "component": "ref",
    "value": "value", "val": "value", "comment": "value", "partname": "value", "name": "value", "partvalue": "value",
    "footprint": "package", "package": "package", "pattern": "package", "cadpackage": "package", "footprintname": "package",
    "qty": "qty", "quantity": "qty", "count": "qty",
    "mpn": "mpn", "manufacturerpartnumber": "mpn", "partnumber": "mpn", "mfrpart": "mpn", "manufacturerpart": "mpn", "mfrpartnumber": "mpn", "mfrpartno": "mpn",
    "lcsc": "lcsc", "lcscpart": "lcsc", "lcscpartno": "lcsc", "supplierpart": "lcsc", "jlcpcbpart": "lcsc", "distributorpartnumber": "lcsc", "supplierpartnumber": "lcsc",
    "description": "description", "desc": "description", "mfr": "manufacturer", "manufacturer": "manufacturer",
    "dnp": "dnp", "dni": "dnp", "populate": "populate", "type": "type",
}


def _key(cell):
    """!
    @brief A header cell reduced to lower-case letters and digits.
    @param cell Text of the cell.
    @return str.
    """
    return re.sub(r"[^a-z0-9]", "", cell.lower())


def expand_designators(text):
    """!
    @brief Split a grouped designator cell ("C2 C6, C7", "R1-R4") into designators.
    @details A range is expanded only for one prefix and at most MAX_RANGE members; an unreadable range is kept as written.
    @param text Cell text.
    @return list of str.
    """
    out = []
    for tok in re.split(r"[\s,;]+", text.strip()):
        if not tok:
            continue
        m = re.fullmatch(r"([A-Za-z_]+)(\d+)[-~](?:[A-Za-z_]+)?(\d+)", tok)
        if m and 0 < int(m.group(3)) - int(m.group(2)) < MAX_RANGE:
            out.extend(f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(3)) + 1))
        else:
            out.append(tok)
    return out


def read_bom(text):
    """!
    @brief Read a BOM table (CSV, semicolon or tab separated) that may have a preamble and several sections.
    @details The header is the first row that has a designator column and at least one more known column; later rows are data until the next header (another section such as BOTTOM SIDE).
             A row whose DNP, DNI or type cell says "do not place" gets dnp True.
    @param text File content.
    @return dict with "rows" (list of dicts with the canonical fields and "dnp"), "columns" (canonical field -> original header), "unknown_columns" (list of str), "sections" (int).
    @throws ValueError If the text is larger than MAX_BYTES, has too many rows or holds no header with a designator column.
    """
    if len(text) > MAX_BYTES:
        raise ValueError("BOM larger than the limit")
    text = text.lstrip("﻿")
    sample = text[:4096]
    delim = max((",", ";", "\t"), key=sample.count)
    rows_out, cols, unknown, header, sections = [], {}, [], None, 0
    for cells in csv.reader(io.StringIO(text), delimiter=delim):
        if len(rows_out) > MAX_ROWS:
            raise ValueError("BOM has too many rows")
        cells = [c.strip() for c in cells]
        while cells and not cells[-1]:
            cells.pop()
        if not cells:
            continue
        mapped = [FIELDS.get(_key(c)) for c in cells]
        if "ref" in mapped and sum(1 for m in mapped if m) >= 2:
            header, sections = mapped, sections + 1
            for c, m in zip(cells, mapped):
                if m and m not in cols:
                    cols[m] = c
                elif not m and c and c not in unknown:
                    unknown.append(c)
            continue
        if header is None or len(cells) <= header.index("ref"):
            continue
        rec = {}
        for c, m in zip(cells, header):
            if m and m not in rec:
                rec[m] = c
        if not rec.get("ref"):
            continue
        flag = (rec.get("dnp", "") + " " + rec.get("type", "")).lower()
        rec["dnp"] = bool(re.search(r"\b(dnp|dni|nf|nostuff|no ?fit|yes|true)\b", flag)) or rec.get("populate", "").lower() in ("no", "0", "false", "n")
        for d in expand_designators(rec["ref"]):
            rows_out.append({**rec, "ref": d})
    if header is None:
        raise ValueError("no header row with a designator column")
    return {"rows": rows_out, "columns": cols, "unknown_columns": unknown, "sections": sections}


## Designator prefix (letters before the first digit, upper case) -> thermal role.
PREFIX_ROLE = {
    "U": "component", "IC": "component", "Q": "component", "T": "component", "D": "component", "LED": "component", "VR": "component", "PQ": "component", "ZD": "component",
    "R": "source", "RN": "source", "RP": "source", "RV": "source", "L": "source", "FB": "source", "F": "source", "FU": "source", "RT": "source", "SH": "source",
    "C": "none", "CN": "none", "J": "none", "P": "none", "SW": "none", "S": "none", "TP": "none", "H": "none", "MH": "none", "FID": "none", "BT": "none", "BAT": "none",
    "Y": "none", "X": "none", "K": "none", "BZ": "none", "LS": "none", "JP": "none", "SP": "none", "A": "none",
}

## Footprint, value or description pattern -> thermal role; the first match in this order wins (more specific first).
KEYWORD_ROLE = [
    (r"mounting ?hole|fiducial|test ?point|^tp[_ -]|logo|mech", "none"),
    (r"connector|header|pinheader|socket|terminal|jst|molex|usb|barrel|jack|rj45|hdmi|screw|battery|holder|coin|molex", "none"),
    (r"crystal|oscillator|resonator|xtal|buzzer|speaker|switch|button|^sw[_ -]|tact|encoder|relay", "none"),
    (r"\bled\b|led[_ -]|_led|diode|^d_|sod[-_]?\d|\bsma\b|\bsmb\b|\bsmc\b|zener|schottky|tvs|rectifier|melf", "component"),
    (r"mosfet|transistor|\bbjt\b|^q_|sot[-_]?23|sot[-_]?89|sot[-_]?223|to[-_]?220|to[-_]?252|to[-_]?263|dpak|powerpak|sc[-_]?70|sot[-_]?323", "component"),
    (r"qfn|dfn|soic|tssop|msop|lqfp|tqfp|qfp|bga|lga|sop-?\d|sot[-_]?\d|ssop|wson|vson|regulator|ldo|buck|boost|driver|amplifier|op-?amp|mcu|stm32|esp32|atmega|atsam|rp2040", "component"),
    (r"resistor|^r_|ferrite|inductor|^l_|fuse|bead|shunt|ntc|ptc|thermistor|varistor|choke", "source"),
    (r"capacitor|^c_|cap_|mlcc|tantalum|electrolytic|cpol", "none"),
]
_KW = [(re.compile(p, re.I), r) for p, r in KEYWORD_ROLE]


def prefix_of(ref):
    """!
    @brief The letters of a designator before its first digit, upper case (BL_GND1 -> BL_GND, C12 -> C).
    @param ref Designator.
    @return str.
    """
    m = re.match(r"[A-Za-z_]+", ref.strip())
    return m.group(0).upper().rstrip("_") if m else ""


def role_from_prefix(ref):
    """!
    @brief The role the designator prefix says, or "" when the prefix is not in the table.
    @param ref Designator.
    @return str.
    """
    return PREFIX_ROLE.get(prefix_of(ref), "")


def role_from_text(text):
    """!
    @brief The role a footprint or description text says by its first pattern match, or "" when none matches.
    @param text Footprint name or description.
    @return str.
    """
    for rx, role in _KW:
        if rx.search(text or ""):
            return role
    return ""


def role_from_value(value):
    """!
    @brief The role a value says: a number with a unit (ohm, F, H) is a passive of that kind, otherwise the patterns of the text.
    @details A bare "10k" or "100n" is ambiguous only in the letter-less case; "10k" is read as a resistor (k and M are not capacitor prefixes), "100n" as a capacitor
             (n, u, p are capacitor prefixes in these tables; a "100n" inductor is "100nH"), "4.7u" as a capacitor, "2.2uH" as an inductor.
    @param value Value or comment cell.
    @return str.
    """
    v = (value or "").strip()
    if re.fullmatch(r"\d+([.,]\d+)?\s*(ohm|r|k|m|meg|g|kohm|mohm|Ω|kΩ)?\d*", v, re.I) and re.search(r"[rkmgΩ]|ohm", v, re.I):
        return "source"
    if re.fullmatch(r"\d+([.,]\d+)?\s*(n|u|µ|m)h", v, re.I):
        return "source"
    if re.fullmatch(r"\d+([.,]\d+)?\s*(p|n|u|µ)f?", v, re.I):
        return "none"
    return role_from_text(v)


def classify(ref, value="", package="", description=""):
    """!
    @brief The thermal role of a part from three independent signals.
    @details Signals: the designator prefix, the footprint name and the value (plus description). The answer is the role most signals say; a tie of one against one is "unknown".
    @param ref Designator.
    @param value Value or comment.
    @param package Footprint or package name.
    @param description Description cell, when the BOM has one.
    @return dict with "role", "votes" (signal -> role or ""), "agree" (signals that agree with the answer) and "conflict" (bool).
    """
    votes = {"prefix": role_from_prefix(ref), "package": role_from_text(package), "value": role_from_value(value) or role_from_text(description)}
    said = [r for r in votes.values() if r]
    if not said:
        return {"role": "unknown", "votes": votes, "agree": 0, "conflict": False}
    counts = {r: said.count(r) for r in set(said)}
    order = sorted(counts.values(), reverse=True)
    best = max(counts, key=counts.get)
    conflict = len(counts) > 1
    if conflict and order[0] == order[1]:
        return {"role": "unknown", "votes": votes, "agree": order[0], "conflict": True}
    return {"role": best, "votes": votes, "agree": counts[best], "conflict": conflict}


__all__ = ["classify", "expand_designators", "prefix_of", "read_bom", "role_from_prefix", "role_from_text", "role_from_value"]
