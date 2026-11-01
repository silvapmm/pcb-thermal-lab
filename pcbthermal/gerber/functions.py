#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file functions.py
@brief What is this file? The layer-function detector of a Gerber set: from the X2 file function, the Excellon header comments and the file name.
@details The order of trust is the X2 attribute (`%TF.FileFunction,Copper,L2,Inr*%`, also written as `G04 #@! TF.FileFunction,...`), then the Excellon header (M48, the
         `; #@! TF.FileFunction,Plated,1,4,PTH` comment, `;TYPE=PLATED`), then the file name with the conventions of KiCad (`-F_Cu.gbr`, `-In1_Cu`, `-B_Paste`, `-Edge_Cuts`,
         `-PTH.drl`), Altium and Protel (`.GTL .GBL .G1 .GP1 .GTP .GBP .GTO .GBO .GTS .GBS .GKO .GM1 .GML`), EAGLE (`.cmp .sol .plc .pls .stc .sts .crc .crs .dim .drd`)
         and the generic words (top, bottom, copper, outline, ...). The side of every non-copper layer is read as carefully as that of the copper: `B_Paste` and `B_Mask` are
         bottom side (an earlier rule that looked for copper words first filed them as top). The result is only a default for the assignment dialog: the user confirms it.
         Only the first kilobytes of a file are needed, so the detector works on the headers of the members of a ZIP without extracting anything.
"""

import re
from pathlib import Path
from typing import NamedTuple, Optional

from .excellon import drill_function
from .parser import attributes_as_commands

HEAD_BYTES = 8192


class LayerFunction(NamedTuple):
    """!
    @brief The detected function of a file.
    @details kind: "copper", "paste", "soldermask", "silkscreen", "outline", "drill", "component", "other" or "unknown". side: "top", "bottom", "inner" or None.
             index: the copper layer number counted from the top (X2, source "x2"), or the ordinal among the inner layers (names, source "name"); None when unknown.
             plated: True or False for a drill file when known. source: "x2", "excellon" or "name". The `confidence` follows the source: the file's own statement (X2, the Excellon
             header) is "high", a guess from the name alone is never more than "low" (names mislead: a mask named "top" or an assembly drawing named "Layer3").
    """
    kind: str
    side: Optional[str]
    index: Optional[int]
    plated: Optional[bool]
    source: str

    @property
    def confidence(self):
        """!
        @brief How far the detection can be trusted.
        @return str "high" when the file states its function (X2, Excellon header), "low" when only its name suggests it.
        """
        return "high" if self.source in ("x2", "excellon") else "low"


UNKNOWN = LayerFunction("unknown", None, None, None, "name")

_SIDE = {"top": "top", "bot": "bottom", "bottom": "bottom", "inr": "inner", "inner": "inner"}

# file extension -> (kind, side, inner ordinal)
_EXT = {
    "gtl": ("copper", "top", None), "gbl": ("copper", "bottom", None), "cmp": ("copper", "top", None), "sol": ("copper", "bottom", None),
    "gts": ("soldermask", "top", None), "gbs": ("soldermask", "bottom", None), "stc": ("soldermask", "top", None), "sts": ("soldermask", "bottom", None),
    "gto": ("silkscreen", "top", None), "gbo": ("silkscreen", "bottom", None), "plc": ("silkscreen", "top", None), "pls": ("silkscreen", "bottom", None),
    "gtp": ("paste", "top", None), "gbp": ("paste", "bottom", None), "crc": ("paste", "top", None), "crs": ("paste", "bottom", None),
    "gko": ("outline", None, None), "gm1": ("outline", None, None), "gml": ("outline", None, None), "dim": ("outline", None, None), "oln": ("outline", None, None),
    "drl": ("drill", None, None), "xln": ("drill", None, None), "exc": ("drill", None, None), "drd": ("drill", None, None), "txt": ("drill", None, None),
}


def _from_x2(head):
    """!
    @brief The function from the X2 attribute in the head of a Gerber file.
    @param head First kilobytes of the file.
    @return LayerFunction, or None when the file has no file function.
    """
    m = re.search(r"%TF\.FileFunction,([^*%]*)", attributes_as_commands(head))
    if not m:
        return None
    f = [v.strip() for v in m.group(1).split(",")]
    kind, rest = f[0], f[1:]
    side = None
    for v in rest:
        if v.lower() in _SIDE:
            side = _SIDE[v.lower()]
    if kind == "Copper":
        idx = int(re.sub(r"\D", "", rest[0]) or 0) if rest else None
        return LayerFunction("copper", side, idx or None, None, "x2")
    if kind == "Profile":
        return LayerFunction("outline", None, None, None, "x2")
    if kind in ("Plated", "NonPlated"):                                  # a drill layer written as Gerber
        return LayerFunction("drill", None, None, kind == "Plated", "x2")
    mapping = {"Soldermask": "soldermask", "Paste": "paste", "Legend": "silkscreen", "Component": "component"}
    if kind in mapping:
        idx = int(re.sub(r"\D", "", rest[0]) or 0) if kind == "Component" and rest else None
        return LayerFunction(mapping[kind], side, idx or None, None, "x2")
    return LayerFunction("other", side, None, None, "x2")


# KiCad's layer suffix (the last part of the name: "<project>-F_Cu", "-In2_Cu", "-B.SilkS", "-Edge_Cuts"): read exactly, so that a project name such as
# "bottle", "gasmask" or "edge-sensor" cannot decide the side or the kind
_KICAD = re.compile(r"[-_.](f|b|in(\d+))[._](cu|mask|paste|silks|silkscreen|fab|crtyd|courtyard|adhes|adhesive)$")
_KICAD_KIND = {"cu": "copper", "mask": "soldermask", "paste": "paste", "silks": "silkscreen", "silkscreen": "silkscreen"}
# Drawings of the drill (KiCad "-drl_map", Altium "Drill Drawing", EasyEDA "DrillDrawingLayer", "drill guide"): Gerber pictures, not drill files
_DRILL_DRAWING = re.compile(r"drl[-_ ]?map|drill[-_ ]?(map|drawing|guide|chart|dwg)|drilldrawing|drillmap|drillguide")


def _from_name(name):
    """!
    @brief The function guessed from the file name.
    @param name File name (no directory).
    @return LayerFunction (kind "unknown" when nothing matches).
    """
    low = name.lower()
    stem, _, ext = low.rpartition(".")
    if not stem:
        stem, ext = low, ""
    if _DRILL_DRAWING.search(stem):
        return LayerFunction("other", None, None, None, "name")
    k = _KICAD.search(stem)
    if k:                                                                # KiCad's own suffix beats the extension (KiCad may write Protel extensions too)
        side = "top" if k.group(1) == "f" else "bottom" if k.group(1) == "b" else "inner"
        kind = _KICAD_KIND.get(k.group(3), "other")
        if kind != "copper" and side == "inner":
            return UNKNOWN
        return LayerFunction(kind, side, int(k.group(2)) if k.group(2) else None, None, "name")
    if re.search(r"[-_.]edge[._]cuts$", stem):
        return LayerFunction("outline", None, None, None, "name")
    # The extension of the Protel/Altium/EAGLE families decides first (.GTP is top paste, whatever the stem says)
    if ext in _EXT:
        kind, side, _ = _EXT[ext]
        if kind == "drill" and ext == "txt" and not re.search(r"drill|drl|nc|pth", stem):
            return UNKNOWN
        plated = False if re.search(r"npth|non[-_]?plated", stem) else True if re.search(r"(^|[^n])pth|(?<!non)plated", stem) else None
        return LayerFunction(kind, side, None, plated if kind == "drill" else None, "name")
    m = re.fullmatch(r"g(p?)(\d+)", ext)                                  # Protel inner layers .G1 .G2, planes .GP1
    if m:
        return LayerFunction("copper", "inner", int(m.group(2)), None, "name")
    m = re.fullmatch(r"ly(\d+)", ext)                                     # EAGLE inner layers .ly2 ...
    if m:
        return LayerFunction("copper", "inner", max(int(m.group(1)) - 1, 1), None, "name")
    tokens = [t for t in re.split(r"[^a-z0-9]+", stem) if t]
    # A glued word such as "bottomlayer" or "topcopper" is split into its parts too
    parts = []
    for t in tokens:
        parts += re.findall(r"top|bottom|bot|inner|copper|layer|paste|mask|silk\w*|legend|overlay|outline|profile|edge|cuts|drill|drl|pth|npth|cu|[a-z]+|\d+", t)
    joined = " ".join(parts)
    # Which side? an isolated "f"/"b" is the KiCad prefix (F_Cu, B_Paste), "top"/"bottom"/"bot" the generic words
    # Whole words decide first ("b"/"f" are the KiCad prefixes, "top"/"bottom"/"bot" the generic words); a glued part ("bottomlayer") only when no word decides,
    # and the last word that names a side wins, because a project name comes first ("bottle-top" is top)
    side = None
    for t in reversed(tokens):
        if t in ("bottom", "bot", "b", "back"):
            side = "bottom"
            break
        if t in ("top", "f", "front"):
            side = "top"
            break
    if side is None:
        side = "bottom" if ("bottom" in parts or "bot" in parts) else "top" if "top" in parts else None
    if re.search(r"\bpaste\b|\bsolderpaste\b|\bsmdpaste\b", joined) or "paste" in tokens:
        return LayerFunction("paste", side, None, None, "name")
    if "mask" in joined or any(t in tokens for t in ("soldermask", "smask", "solder", "sm")):
        return LayerFunction("soldermask", side, None, None, "name")
    if re.search(r"silk|legend|overlay", joined) or "ss" in tokens:
        return LayerFunction("silkscreen", side, None, None, "name")
    if re.search(r"edge|cuts|outline|profile|border|boardoutline|mill|contour", joined) or "dim" in tokens:
        return LayerFunction("outline", None, None, None, "name")
    if re.search(r"drill|drl|pth|npth|ncdrill|excellon", joined):
        plated = False if "npth" in joined or "nonplated" in joined else True if "pth" in joined else None
        return LayerFunction("drill", None, None, plated, "name")
    if re.search(r"assem|assy|fab|adhes|glue|courtyard|crtyd|user|dwg|drawing|comment|doc|note", joined) or any(t in tokens for t in ("asb", "ast", "asm", "assembly")):
        return LayerFunction("other", side, None, None, "name")
    inner = re.search(r"\b(?:in|inner|l|layer|mid|int)[-_ ]?(\d+)\b|in(\d+)[-_ ]?cu", joined + " " + stem)
    if inner and ("cu" in tokens or "copper" in parts or "inner" in parts or "layer" in parts or re.search(r"in\d+", stem)) and side is None:
        return LayerFunction("copper", "inner", int(inner.group(1) or inner.group(2)), None, "name")
    if re.search(r"gnd|vcc|vdd|power|plane|pwr", joined) and side is None:
        return LayerFunction("copper", "inner", None, None, "name")
    if "cu" in tokens or "copper" in parts or "layer" in parts or side is not None:
        return LayerFunction("copper", side, None, None, "name") if side else UNKNOWN
    return UNKNOWN


def detect_function(name, head=""):
    """!
    @brief Detect the function of a file.
    @param name File name (a path is accepted; only the last part is used).
    @param head First kilobytes of the file content (may be empty: then only the name is used).
    @return LayerFunction.
    """
    base = Path(str(name).replace("\\", "/")).name
    head = head[:HEAD_BYTES].lstrip("\ufeff")                              # a byte order mark would hide the M48 of an Excellon header
    if head:
        x2 = _from_x2(head)
        if x2 is not None:
            return x2
        if re.match(r"\s*(?:(?:;[^\n]*|%[ \t\r]*)\n\s*)*M48", head):                   # Excellon header, after comments or a stray % line
            plated, _, _ = drill_function(head)
            by_name = _from_name(base)
            return LayerFunction("drill", None, None, plated if plated is not None else by_name.plated, "excellon")
    by_name = _from_name(base)
    if head and by_name.kind == "drill" and _gerber_head(head) and not re.search(r"D0?3\s*\*", head):
        # A Gerber file that draws strokes and flashes nothing (Xpedition DRILL.gdo, crosses at the holes) is a drawing of the holes, never an Excellon drill file; one that flashes
        # is a Gerber drill layer (the holes are the flashes) and keeps the kind. An X2 drill function returned above.
        return LayerFunction("other", None, None, None, "name")
    return by_name


def _gerber_head(head):
    """!
    @brief Whether the head of a file is Gerber (a format statement) and not Excellon.
    @param head First kilobytes of the file.
    @return bool True for a Gerber head.
    """
    return bool(re.search(r"%FS[LTD]?[AI]?X\d\dY\d\d", head))


def detect_file(path):
    """!
    @brief Detect the function of a file on disk, reading only its first kilobytes.
    @param path File path.
    @return LayerFunction.
    """
    p = Path(path)
    try:
        with open(p, "rb") as fh:
            head = fh.read(HEAD_BYTES).decode("utf-8", "replace")
    except OSError:
        head = ""
    return detect_function(p.name, head)


def order_copper_layers(items):
    """!
    @brief Sort copper layers from the top to the bottom: top, the inner layers by index, bottom.
    @param items List of (name, LayerFunction) of copper files.
    @return list The same pairs in stack order.
    """
    rank = {"top": 0, "inner": 1, "bottom": 2}
    return sorted(items, key=lambda it: (rank.get(it[1].side, 1), it[1].index or 0, it[0]))


_NUMBERED = re.compile(r"(?:^|[-_. ])(?:layer|lyr|l)[-_ ]?(\d+)$")


def detect_set(items):
    """!
    @brief Detect the function of every file of a set, then resolve what one file cannot tell: the copper layers that are only numbered.
    @details A name such as `Layer1.gdo` ... `Layer4.gdo` says the order but not the side, so alone every one reads as an inner layer. In a set whose copper has no
             file-stated or named top and bottom, and that has at least two such numbered files, the lowest number is the top, the highest the bottom and the others are inner layers
             in order (the stack counted from the top); these stay "low" confidence (source "name"), for the user to confirm.
    @param items List of (name, head) pairs (head may be empty).
    @return dict name -> LayerFunction.
    """
    out = {n: detect_function(n, h) for n, h in items}
    copper = [n for n, f in out.items() if f.kind == "copper"]
    if any(out[n].side in ("top", "bottom") for n in copper):
        return out                                                       # a top or bottom is known: the numbers are inner layers indeed
    numbered = {}
    for n in copper:
        stem = Path(str(n).replace("\\", "/")).stem.lower()
        m = _NUMBERED.search(stem)
        if m and out[n].source == "name":
            numbered[n] = int(m.group(1))
    if len(numbered) < 2 or len(set(numbered.values())) < len(numbered):
        return out
    order = sorted(numbered, key=numbered.get)
    for rank, n in enumerate(order):
        side = "top" if rank == 0 else "bottom" if rank == len(order) - 1 else "inner"
        out[n] = LayerFunction("copper", side, rank if side == "inner" else None, None, "name")
    return out
