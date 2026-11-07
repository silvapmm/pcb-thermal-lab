#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file bom.py
@brief The bill-of-materials (BOM) reader of the Gerber import and the rule that guesses the thermal role of a part from its names. No GUI, no third-party dependency.
@details A BOM is a CSV, semicolon or tab separated table written by a CAD program (KiCad, JLCPCB, Altium, EasyEDA, PCBWay, Pulsonix, ...). The columns are found by the NAMES in
         the header, never by the file name; the header may follow a preamble and a file may hold several sections, each with its own header (the Pulsonix sample has three). Text is read
         as UTF-8, UTF-8 with a byte order mark, or UTF-16 with a byte order mark; an Excel workbook (.xlsx, .xls) is NOT read and says so. Every cell is text, nothing is evaluated.
         Hostile input is bounded: the file size (`limits.max_file_bytes`, at most MAX_BYTES), MAX_ROWS rows, MAX_COLUMNS columns, MAX_CELL characters per cell, MAX_RANGE members of a
         range such as `R1-R4` and MAX_DESIGNATORS designators in all; a file that breaks a limit raises `BomError` (a `GerberError`), never a raw exception.
         Two readings are made from a table: the "not fitted" mark (an explicit list of markers, see `NOT_FITTED_MARKERS`) and the guessed role of each part (`classify`: designator
         prefix, footprint words and value words; "component" a package with a junction, "source" a dissipator without one, "none" connectors, capacitors, test points, ..., "unknown").
         The role is a GUESS from English, KiCad-style names (agreement of the signals 99 % on KiCad-written boards, not accuracy): it only proposes, it never sets a power, never moves
         a part and never overrides an edit of the user. The study is `research/bom-role-and-close-hook` (README 3 and 4).
"""

import csv
import dataclasses
import io
import re
from typing import Dict, List, Optional, Tuple

from . import limits
from .errors import GerberError

MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 200000
MAX_COLUMNS = 64
MAX_CELL = 1000
MAX_RANGE = 2000
MAX_DESIGNATORS = 200000
MAX_TOKENS_PER_CELL = 20000
HEADER_SEARCH_LINES = 400                                  # Lines examined for the first header row (a preamble is a few lines)


class BomError(GerberError):
    """!@brief A BOM file that cannot be read (too large, an Excel workbook, no header with a designator column, a limit broken)."""


## Header cell (lower case, letters and digits only) -> canonical field.
FIELDS = {
    "designator": "ref", "designators": "ref", "reference": "ref", "references": "ref", "refdes": "ref", "ref": "ref", "refs": "ref", "components": "ref", "component": "ref",
    "referencedesignator": "ref", "referencedesignators": "ref", "refdesignator": "ref", "refdess": "ref",
    "value": "value", "val": "value", "comment": "value", "partname": "value", "name": "value", "partvalue": "value",
    "footprint": "package", "package": "package", "pattern": "package", "cadpackage": "package", "footprintname": "package", "packagecase": "package",
    "qty": "qty", "quantity": "qty", "count": "qty",
    "mpn": "mpn", "manufacturerpartnumber": "mpn", "partnumber": "mpn", "mfrpart": "mpn", "manufacturerpart": "mpn", "mfrpartnumber": "mpn", "mfrpartno": "mpn",
    "manufacturerpartno": "mpn",
    "lcsc": "lcsc", "lcscpart": "lcsc", "lcscpartno": "lcsc", "supplierpart": "lcsc", "jlcpcbpart": "lcsc", "distributorpartnumber": "lcsc", "supplierpartnumber": "lcsc",
    "description": "description", "desc": "description", "mfr": "manufacturer", "manufacturer": "manufacturer",
    # Do-not-place columns (a mark in the cell), and fitted columns (a "no" in the cell)
    "dnp": "dnp", "dni": "dnp", "dnf": "dnp", "nf": "dnp", "nm": "dnp", "donotplace": "dnp", "donotpopulate": "dnp", "donotinstall": "dnp", "donotfit": "dnp", "notfitted": "dnp",
    "nostuff": "dnp", "nofit": "dnp", "notmounted": "dnp", "notpopulated": "dnp",
    "populate": "populate", "populated": "populate", "fitted": "populate", "mount": "populate", "mounted": "populate", "install": "populate", "installed": "populate",
    "type": "type", "remarks": "note", "remark": "note", "notes": "note", "note": "note",
    "variant": "variant", "assemblyvariant": "variant",
}

## Cell text (lower case, words separated by single blanks) that means "do not place": the explicit list (maintainer's decision: DNP, DNI, NF, NM, DNF and a Fitted = No column).
NOT_FITTED_MARKERS = frozenset({"dnp", "dni", "dnf", "nf", "nm", "nofit", "nostuff", "do not place", "do not populate", "do not install", "do not fit", "do not stuff",
                                "not fitted", "not mounted", "not populated", "not installed", "not placed", "unpopulated", "no fit", "no stuff"})
## Free-text cells (value, comment, description) are searched only for the words that cannot be a unit: `nf` is a nanofarad and `nm` a nanometre.
_SAFE_WORDS = frozenset({"dnp", "dni", "dnf", "nofit", "nostuff"})
_PHRASES = frozenset(m for m in NOT_FITTED_MARKERS if " " in m)
_NEGATIVE = frozenset({"", "no", "n", "0", "false", "fitted", "populated", "yes fitted", "-", "none"})
_NO = frozenset({"no", "n", "0", "false", "not fitted", "not populated"})

_DEFAULT_ROW_KEYS = ("value", "package", "qty", "mpn", "lcsc", "description", "manufacturer")


def _key(cell: str) -> str:
    """!
    @brief A header cell reduced to lower-case letters and digits.
    @param cell Text of the cell.
    @return str.
    """
    return re.sub(r"[^a-z0-9]", "", cell.lower())


def _words(cell: str) -> str:
    """!
    @brief A cell as lower-case words separated by single blanks (punctuation and underscores are blanks).
    @param cell Text of the cell.
    @return str.
    """
    return " ".join(re.sub(r"[^a-z0-9]+", " ", cell.lower()).split())


def not_fitted_reason(cells: Dict[str, str]) -> str:
    """!
    @brief Whether the row of a BOM says "do not place", and in which column.
    @details Dedicated columns (DNP, DNI, DNF, NF, NM, Type, Remarks, Notes): a cell that is a marker of the explicit list, or for a column that is itself a do-not-place column
             any non-empty cell that is not a negative ("no", "0", "false"); a Fitted, Populate or Mount column: "no", "0" or "false"; free text (value, comment, description): only the
             words that cannot be a unit (`dnp`, `dni`, `dnf`, `nofit`, `nostuff` and the phrases), and a value that is exactly one of them. `NF` and `NM` count only in a dedicated
             column (a description with "100 nF" is not a not-fitted part).
    @param cells Canonical field -> cell text of the row.
    @return str "" when the part is fitted, else the field that says so ("dnp", "type", "note", "populate", "value", "description").
    """
    d = _words(cells.get("dnp", ""))
    if d and d not in _NEGATIVE:
        return "dnp"
    for key in ("type", "note"):
        w = _words(cells.get(key, ""))
        if w in NOT_FITTED_MARKERS or (w and set(w.split()) & {"dnp", "dni", "dnf"}):
            return key
    if _words(cells.get("populate", "")) in _NO:
        return "populate"
    for key in ("value", "description"):
        w = _words(cells.get(key, ""))
        if not w:
            continue
        if key == "value" and w in NOT_FITTED_MARKERS and w not in ("nf", "nm"):
            return key
        if set(w.split()) & _SAFE_WORDS or any(f" {ph} " in f" {w} " for ph in _PHRASES):
            return key
    return ""


def decode(data: bytes, name: str = "BOM") -> Tuple[str, str]:
    """!
    @brief Decode the bytes of a BOM file.
    @details UTF-8 (with or without a byte order mark) and UTF-16 with a byte order mark; an undecodable byte becomes U+FFFD. An Excel workbook (a ZIP or an OLE file) and UTF-16 without
             a byte order mark are refused with a message that says how to save the table.
    @param data File content.
    @param name File name for the messages.
    @return tuple (text, encoding name).
    @throws BomError If the file is a workbook, UTF-16 without a byte order mark, or too large.
    """
    if len(data) > min(MAX_BYTES, limits.max_file_bytes()):
        raise BomError(f"{name}: the file has {len(data) / limits.MB:.1f} MB, above the limit of a BOM ({min(MAX_BYTES, limits.max_file_bytes()) // limits.MB} MB)")
    if data[:4] == b"PK\x03\x04" or data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise BomError(f"{name}: an Excel workbook (.xlsx, .xls) is not read; save the table as CSV (comma separated) and use that file")
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace").lstrip("﻿"), "UTF-16"
    head = data[:4096]
    if head.count(b"\x00") > len(head) // 4:
        raise BomError(f"{name}: text in UTF-16 without a byte order mark is not read; save it as UTF-8 or as UTF-16 with a byte order mark")
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", errors="replace"), "UTF-8 with a byte order mark"
    return data.decode("utf-8", errors="replace"), "UTF-8"


def decode_head(raw: bytes) -> str:
    """!
    @brief Decode the first bytes of a file for the function detector: UTF-16 with a byte order mark is read as such, anything else as UTF-8 (undecodable bytes become U+FFFD).
    @param raw First bytes of the file.
    @return str.
    """
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace").lstrip("﻿")
    return raw.decode("utf-8", errors="replace")


def _split(line: str, delim: str) -> List[str]:
    """!
    @brief Split one line into cells by a delimiter.
    @param line Text of the line.
    @param delim "," ";" or a tab.
    @return list of str (empty on a malformed line).
    """
    try:
        return next(csv.reader([line], delimiter=delim), [])
    except csv.Error:
        return []


def _header_of(cells: List[str]) -> Optional[List[Optional[str]]]:
    """!
    @brief The canonical fields of a header row, or None when the row is not a header.
    @details A header has a designator column and at least one more known column.
    @param cells Cells of the row.
    @return list of canonical field or None per cell, or None.
    """
    mapped = [FIELDS.get(_key(c[:MAX_CELL])) for c in cells[:MAX_COLUMNS]]
    if "ref" in mapped and sum(1 for m in mapped if m) >= 2:
        return mapped
    return None


def looks_like_bom(head: str) -> bool:
    """!
    @brief Whether the head of a text file is a BOM table: a header with a designator column and a value, footprint, quantity or part-number column, and no X and Y columns.
    @details Used by the function detector of the import window (by content, not by file name). A table with X and Y columns is a placement table.
    @param head First kilobytes of the file, decoded.
    @return bool.
    """
    for line in head.splitlines()[:HEADER_SEARCH_LINES]:
        if not line.strip() or len(line) > 4000:
            continue
        for d in (",", ";", "\t"):
            if d not in line:
                continue
            cells = _split(line, d)
            h = _header_of(cells)
            if h is None:
                continue
            keys = [_key(c) for c in cells]
            if any(re.fullmatch(r"(pos|mid|center|centre)?x(mm|mil|in)?", k) for k in keys) and any(re.fullmatch(r"(pos|mid|center|centre)?y(mm|mil|in)?", k) for k in keys):
                return False                                   # a placement table
            if {"value", "package", "qty", "mpn", "lcsc", "description", "manufacturer"} & set(m for m in h if m):
                return True
    return False


def expand_designators(text: str) -> List[str]:
    """!
    @brief Split a grouped designator cell ("C2 C6, C7", "R1-R4") into designators.
    @details A range is expanded only for one prefix, with at most MAX_RANGE members and numbers of at most nine digits; an unreadable or absurd range is kept as written. At most
             MAX_TOKENS_PER_CELL tokens are read from a cell.
    @param text Cell text.
    @return list of str.
    """
    out = []
    for n, tok in enumerate(re.split(r"[\s,;]+", text.strip())):
        if n >= MAX_TOKENS_PER_CELL:
            break
        if not tok:
            continue
        m = re.fullmatch(r"([A-Za-z_]+)(\d{1,9})[-~](?:[A-Za-z_]+)?(\d{1,9})", tok)
        if m and 0 < int(m.group(3)) - int(m.group(2)) < MAX_RANGE:
            out.extend(f"{m.group(1)}{k}" for k in range(int(m.group(2)), int(m.group(3)) + 1))
        else:
            out.append(tok)
    return out


@dataclasses.dataclass
class BomRow:
    """!@brief One designator of a BOM: the fields of its row (text), the not-fitted mark and where it came from."""
    ref: str
    value: str = ""
    package: str = ""
    qty: str = ""
    mpn: str = ""
    lcsc: str = ""
    description: str = ""
    manufacturer: str = ""
    not_fitted: str = ""                                   # "" when fitted, else the field that says it is not
    section: int = 1


@dataclasses.dataclass
class BomTable:
    """!
    @brief One BOM file read: its rows (one per designator), the columns found, the columns not used, the sections, the assembly variants named and what the reader noted.
    """
    name: str = ""
    rows: List[BomRow] = dataclasses.field(default_factory=list)
    columns: Dict[str, str] = dataclasses.field(default_factory=dict)         # canonical field -> header text of the first column that gave it
    unknown_columns: List[str] = dataclasses.field(default_factory=list)
    sections: int = 0
    variants: List[str] = dataclasses.field(default_factory=list)
    encoding: str = ""
    delimiter: str = ","
    warnings: List[str] = dataclasses.field(default_factory=list)


def _delimiter(lines: List[str]) -> str:
    """!
    @brief The delimiter of the first header row found in the first lines (comma, semicolon, tab); the one that splits the header into the most cells wins.
    @param lines The first lines of the text.
    @return str.
    @throws BomError If no line is a header.
    """
    for line in lines:
        if not line.strip() or len(line) > 4000:
            continue
        best = None
        for d in (",", ";", "\t"):
            if d in line:
                cells = _split(line, d)
                if _header_of(cells) is not None and (best is None or len(cells) > best[0]):
                    best = (len(cells), d)
        if best:
            return best[1]
    raise BomError("no header row with a designator column and another known column (Designator, Reference, Value, Footprint, Quantity, ...)")


def read_bom(data, name: str = "BOM") -> BomTable:
    """!
    @brief Read a BOM table from bytes (or from text already decoded).
    @details The header is the first row with a designator column and one more known column; later rows are data until the next header (a new section, as in the Pulsonix export);
             grouped designators are expanded to one row each (the first row keeps a designator that appears twice, the repeat is counted in `warnings`). The not-fitted mark is read
             by `not_fitted_reason`. The assembly variant is read from a Variant column when there is one.
    @param data File content as bytes (decoded by `decode`) or as str.
    @param name File name for the messages.
    @return BomTable.
    @throws BomError If the file is too large, an Excel workbook, has no header, or breaks a limit (rows, designators, a cell larger than the csv module accepts).
    """
    if isinstance(data, str):
        if len(data) > min(MAX_BYTES, limits.max_file_bytes()):
            raise BomError(f"{name}: larger than the limit of a BOM")
        text, enc = data.lstrip("﻿"), "text"
    else:
        text, enc = decode(data, name)
    lines = text.split("\n", HEADER_SEARCH_LINES)[:HEADER_SEARCH_LINES]
    delim = _delimiter(lines)
    table = BomTable(name=name, encoding=enc, delimiter=delim)
    header, seen, nrows, dup = None, set(), 0, 0
    try:
        for cells in csv.reader(io.StringIO(text), delimiter=delim):
            nrows += 1
            if nrows > MAX_ROWS:
                raise BomError(f"{name}: more than {MAX_ROWS} rows")
            cells = [c[:MAX_CELL].strip() for c in cells[:MAX_COLUMNS]]
            while cells and not cells[-1]:
                cells.pop()
            if not cells:
                continue
            h = _header_of(cells)
            if h is not None:
                header, table.sections = h, table.sections + 1
                for c, m in zip(cells, h):
                    if m and m not in table.columns:
                        table.columns[m] = c
                    elif not m and c and c not in table.unknown_columns and len(table.unknown_columns) < MAX_COLUMNS:
                        table.unknown_columns.append(c)
                continue
            if header is None or len(cells) <= header.index("ref"):
                continue
            rec: Dict[str, str] = {}
            for c, m in zip(cells, header):
                if m and m not in rec:
                    rec[m] = c
            if not rec.get("ref"):
                continue
            reason = not_fitted_reason(rec)
            var = rec.get("variant", "")
            if var and var not in table.variants and len(table.variants) < 20:
                table.variants.append(var[:80])
            for d in expand_designators(rec["ref"]):
                if len(d) > 80:
                    d = d[:80]
                if d in seen:
                    dup += 1
                    continue
                if len(seen) >= MAX_DESIGNATORS:
                    raise BomError(f"{name}: more than {MAX_DESIGNATORS} designators")
                seen.add(d)
                table.rows.append(BomRow(d, not_fitted=reason, section=table.sections, **{k: rec.get(k, "")[:200] for k in _DEFAULT_ROW_KEYS}))
    except csv.Error as exc:
        raise BomError(f"{name}: the table cannot be read ({exc})") from exc
    if header is None:                                      # unreachable after _delimiter, kept for a header that csv splits differently
        raise BomError(f"{name}: no header row with a designator column")
    if dup:
        table.warnings.append(f"{dup} designator(s) appear more than once; the first row of each is used")
    if not table.rows:
        table.warnings.append("the table has a header but no part")
    return table


@dataclasses.dataclass
class BomSet:
    """!
    @brief The BOM files of an import merged by designator: the rows, the files they came from, the variants named, and the notes.
    """
    rows: Dict[str, BomRow] = dataclasses.field(default_factory=dict)
    files: List[str] = dataclasses.field(default_factory=list)
    variants: List[str] = dataclasses.field(default_factory=list)
    warnings: List[str] = dataclasses.field(default_factory=list)
    sections: int = 0
    _fold: Dict[str, str] = dataclasses.field(default_factory=dict)

    def get(self, designator: str) -> Optional[BomRow]:
        """!
        @brief The row of a designator (exact, else ignoring case).
        @param designator Designator of a part.
        @return BomRow or None.
        """
        r = self.rows.get(designator)
        return r if r is not None else self.rows.get(self._fold.get(designator.upper(), ""))


def merge(tables: List[BomTable]) -> BomSet:
    """!
    @brief Merge BOM tables by designator (two files for the two sides, or one with several sections): the first row of a designator wins and a repeat is noted.
    @param tables The tables, in file order.
    @return BomSet.
    """
    out = BomSet()
    clash = 0
    for t in tables:
        out.files.append(t.name)
        out.sections += t.sections
        out.warnings += [f"{t.name}: {w}" for w in t.warnings]
        out.variants += [v for v in t.variants if v not in out.variants]
        for r in t.rows:
            if r.ref in out.rows:
                clash += 1
                continue
            out.rows[r.ref] = r
            out._fold.setdefault(r.ref.upper(), r.ref)
    if clash:
        out.warnings.append(f"{clash} designator(s) are in more than one BOM file; the first file's row is used")
    return out


# ---------------------------------------------------------------------------------------------------------------------------------------------------- the role rule
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
## A word that names two different kinds of part (SMA is a diode package and an RF connector): the role it gives is a guess even for a guess.
AMBIGUOUS = re.compile(r"\bsma\b", re.I)
## How the role is named for the user (the BOM column of step 2).
ROLE_TEXT = {"component": "component", "source": "source", "none": "no heat source", "unknown": "unknown"}


def prefix_of(ref: str) -> str:
    """!
    @brief The letters of a designator before its first digit, upper case (BL_GND1 -> BL_GND, C12 -> C).
    @param ref Designator.
    @return str.
    """
    m = re.match(r"[A-Za-z_]+", ref.strip())
    return m.group(0).upper().rstrip("_") if m else ""


def role_from_prefix(ref: str) -> str:
    """!
    @brief The role the designator prefix says, or "" when the prefix is not in the table.
    @param ref Designator.
    @return str.
    """
    return PREFIX_ROLE.get(prefix_of(ref), "")


def role_from_text(text: str) -> str:
    """!
    @brief The role a footprint or description text says by its first pattern match, or "" when none matches.
    @param text Footprint name or description.
    @return str.
    """
    for rx, role in _KW:
        if rx.search((text or "")[:MAX_CELL]):
            return role
    return ""


def role_from_value(value: str) -> str:
    """!
    @brief The role a value says: a number with a unit (ohm, F, H) is a passive of that kind, otherwise the patterns of the text.
    @details A bare "10k" is read as a resistor (k and M are not capacitor prefixes), "100n" as a capacitor (n, u, p are capacitor prefixes in these tables; a "100n" inductor is
             "100nH"), "2.2uH" as an inductor.
    @param value Value or comment cell.
    @return str.
    """
    v = (value or "").strip()[:MAX_CELL]
    if re.fullmatch(r"\d+([.,]\d+)?\s*(ohm|r|k|m|meg|g|kohm|mohm|Ω|kΩ)?\d*", v, re.I) and re.search(r"[rkmgΩ]|ohm", v, re.I):
        return "source"
    if re.fullmatch(r"\d+([.,]\d+)?\s*(n|u|µ|m)h", v, re.I):
        return "source"
    if re.fullmatch(r"\d+([.,]\d+)?\s*(p|n|u|µ)f?", v, re.I):
        return "none"
    return role_from_text(v)


def classify(ref: str, value: str = "", package: str = "", description: str = "") -> dict:
    """!
    @brief The thermal role of a part from three independent signals (a guess from English, KiCad-style names).
    @details Signals: the designator prefix, the footprint name and the value (plus description). The answer is the role most signals say; a tie of one against one is "unknown".
             `ambiguous` is True when a word that names two kinds of part (SMA) is in the names: the proposal is then not offered even as a guess.
    @param ref Designator.
    @param value Value or comment.
    @param package Footprint or package name.
    @param description Description cell, when the BOM has one.
    @return dict with "role", "votes" (signal -> role or ""), "agree" (signals that agree with the answer), "conflict" (bool) and "ambiguous" (bool).
    """
    votes = {"prefix": role_from_prefix(ref), "package": role_from_text(package), "value": role_from_value(value) or role_from_text(description)}
    amb = any(AMBIGUOUS.search((t or "")[:MAX_CELL]) for t in (package, value, description))
    said = [r for r in votes.values() if r]
    if not said:
        return {"role": "unknown", "votes": votes, "agree": 0, "conflict": False, "ambiguous": amb}
    counts = {r: said.count(r) for r in set(said)}
    order = sorted(counts.values(), reverse=True)
    best = max(counts, key=counts.get)
    conflict = len(counts) > 1
    if conflict and order[0] == order[1]:
        return {"role": "unknown", "votes": votes, "agree": order[0], "conflict": True, "ambiguous": amb}
    return {"role": best, "votes": votes, "agree": counts[best], "conflict": conflict, "ambiguous": amb}


def proposal(c: dict) -> str:
    """!
    @brief The role a guess is willing to propose: the role of `classify`, or "unknown" when it is ambiguous (SMA) or the signals tie.
    @param c Result of `classify`.
    @return str "component", "source", "none" or "unknown".
    """
    return "unknown" if c.get("ambiguous") else c["role"]


__all__ = ["BomError", "BomRow", "BomSet", "BomTable", "NOT_FITTED_MARKERS", "classify", "decode", "decode_head", "expand_designators", "looks_like_bom", "merge", "not_fitted_reason",
           "prefix_of", "proposal", "read_bom", "role_from_prefix", "role_from_text", "role_from_value"]
