#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file labels.py
@brief Hand labels: the layer function each tool gives to its own file names (the truth for the layer-detection accuracy).
@details Two sources of truth, in this order: (1) the X2 attribute `TF.FileFunction` written in the file by the tool (taken from the
         file by `x2_truth`, it is the tool saying what the file is); (2) for files without it, the table `RULES` below, written by
         reading the names and the layer comments of the sample sets (Allegro's film names, Xpedition's output definition names,
         Altium's extension report, the PADS and EAGLE conventions known from their manuals: those two are marked "M" in the README,
         memory, because no document of the tool was opened).  A rule gives (kind, side); side None means "not judged".
         Kinds follow `pcbthermal.gerber.functions`: copper, paste, soldermask, silkscreen, outline, drill, other.
"""
import re
from typing import Optional, Tuple

Label = Tuple[str, Optional[str]]

# tool -> list of (regex on the lower-case file name, kind, side); the first rule that matches wins
RULES = {
    "xpedition": [
        (r"\.ncd$", "drill", None), (r"drilldrawing|^drill\.gdo", "other", None),
        (r"boardoutl+ine", "outline", None),
        (r"solderpaste.*(top|1)\.gdo|solderpaste1", "paste", "top"), (r"solderpaste.*(bottom|bot|2)\.gdo", "paste", "bottom"),
        (r"soldermask.*(top|1)\.gdo|soldermask1", "soldermask", "top"), (r"soldermask.*(bottom|bot|2)\.gdo", "soldermask", "bottom"),
        (r"silkscreen.*(top|1)\.gdo", "silkscreen", "top"), (r"silkscreen.*(bottom|bot|2)\.gdo", "silkscreen", "bottom"),
        (r"etchlayer.*top|etchlayer_top|l01_top|layer1\.gdo", "copper", "top"),
        (r"etchlayer.*bot|l12_bottom|etchlayer_bot", "copper", "bottom"),
        (r"etchlayer\d|_l\d\d(_|\.)|layer\d\.gdo", "copper", "inner"),
    ],
    "pads": [
        (r"\.drl$", "drill", None), (r"^(top|top-art)\.pho$|top-art\.pho", "copper", "top"), (r"^bottom\.pho|bot-art\.pho", "copper", "bottom"),
        (r"^layer\d\.pho", "copper", "inner"), (r"^smt\.pho|top-sm\.pho", "soldermask", "top"), (r"^smb\.pho|bot-sm\.pho", "soldermask", "bottom"),
        (r"^sst\.pho|top-ss\.pho", "silkscreen", "top"), (r"^ssb\.pho", "silkscreen", "bottom"), (r"fabnotes", "other", None),
    ],
    "allegro": [
        (r"\.drl$", "drill", None), (r"\.rou$", "drill", None),
        (r"assy|assem|fab\d?\.art|drawing", "other", None),
        (r"(paste|_spc|_sps|spt\.art|spb\.art)", "paste", None),
        (r"(mask|solder_|smc_|sms_|smt\.art|smb\.art)", "soldermask", None),
        (r"(silk|slk|sst\.art|ssb\.art)", "silkscreen", None),
        (r"outline", "outline", None),
        (r"(^top\.art|^bot\.art|^bottom\.art|gnd|pwr|lyr\d|layer_\d|l\d_|^l\d\.)", "copper", None),
    ],
    "diptrace": [
        (r"\.drl$", "drill", None), (r"boardoutline|^border", "outline", None),
        (r"(top|bottom)mask", "soldermask", None), (r"(top|bottom)silk", "silkscreen", None), (r"(top|bottom)paste", "paste", None),
        (r"top\.gbr|^1 - top", "copper", "top"), (r"bottom\.gbr|^2 - bottom", "copper", "bottom"),
    ],
    "upverter": [(r"\.(drl|xln)$", "drill", None), (r"\.gtl$", "copper", "top"), (r"\.gbl$", "copper", "bottom"), (r"\.gts$", "soldermask", "top"),
                 (r"\.gbs$", "soldermask", "bottom"), (r"\.gto$", "silkscreen", "top"), (r"\.gbo$", "silkscreen", "bottom"),
                 (r"\.gtp$", "paste", "top"), (r"\.gbp$", "paste", "bottom"), (r"\.gko$", "outline", None)],
    "pcad": [(r"\.drl$", "drill", None), (r"\.gtl$", "copper", "top"), (r"\.gbl$", "copper", "bottom"), (r"\.gts$", "soldermask", "top"),
             (r"\.gbs$", "soldermask", "bottom"), (r"\.gto$", "silkscreen", "top"), (r"\.gbo$", "silkscreen", "bottom"), (r"\.gko$", "outline", None)],
    "pcbrnd": [(r"\.xln$", "drill", None), (r"\.gtl$", "copper", "top"), (r"\.gbl$", "copper", "bottom"), (r"\.gts$", "soldermask", "top"),
               (r"\.gbs$", "soldermask", "bottom"), (r"\.gto$", "silkscreen", "top"), (r"\.gbo$", "silkscreen", "bottom"),
               (r"\.gtp$", "paste", "top"), (r"\.gbp$", "paste", "bottom"), (r"\.gko$", "outline", None), (r"\.(asb|ast|fab)$", "other", None)],
    "geda": [(r"\.cnc$", "drill", None), (r"\.top\.gbr", "copper", "top"), (r"\.bottom\.gbr", "copper", "bottom"), (r"\.group\d", "copper", "inner"),
             (r"topmask", "soldermask", "top"), (r"bottommask", "soldermask", "bottom"), (r"topsilk", "silkscreen", "top"), (r"\.fab\.", "other", None)],
    "fritzing": [(r"\.txt$", "drill", None), (r"\.gtl$", "copper", "top"), (r"\.gbl$", "copper", "bottom"), (r"\.gts$", "soldermask", "top"),
                 (r"\.gbs$", "soldermask", "bottom"), (r"\.gto$", "silkscreen", "top"), (r"\.gbo$", "silkscreen", "bottom"), (r"\.(gko|gm1)$", "outline", None)],
    "easyeda": [(r"\.drl$", "drill", None), (r"boardoutline", "outline", None), (r"toplayer", "copper", "top"), (r"bottomlayer", "copper", "bottom"),
                (r"topsoldermask", "soldermask", "top"), (r"bottomsoldermask", "soldermask", "bottom"), (r"toppastemask", "paste", "top"),
                (r"bottompastemask", "paste", "bottom"), (r"topsilk", "silkscreen", "top"), (r"bottomsilk", "silkscreen", "bottom")],
    "target3001": [(r"\.drill$", "drill", None), (r"\.outline$", "outline", None), (r"\.top$", "copper", "top"), (r"\.bot$", "copper", "bottom"),
                   (r"\.pastetop$", "paste", "top"), (r"\.pastebot$", "paste", "bottom"), (r"\.stoptop$", "soldermask", "top"),
                   (r"\.stopbot$", "soldermask", "bottom"), (r"\.positop$", "silkscreen", "top"), (r"\.posibot$", "silkscreen", "bottom")],
    # Altium without X2 (older versions) and the Protel names of the families that follow Altium
    "altium": [(r"\.(txt|drl)$", "drill", None), (r"\.gtl$", "copper", "top"), (r"\.gbl$", "copper", "bottom"), (r"\.g\d+$|\.gp\d+$", "copper", "inner"),
               (r"\.gts$", "soldermask", "top"), (r"\.gbs$", "soldermask", "bottom"), (r"\.gto$", "silkscreen", "top"), (r"\.gbo$", "silkscreen", "bottom"),
               (r"\.gtp$", "paste", "top"), (r"\.gbp$", "paste", "bottom"), (r"\.(gko|gm1)$", "outline", None), (r"\.(gm\d+|gd\d+|gg\d+)$", "other", None)],
    "eagle": [(r"\.(xln|drd)$", "drill", None), (r"\.cmp$", "copper", "top"), (r"\.sol$", "copper", "bottom"), (r"\.plc$", "silkscreen", "top"),
              (r"\.pls$", "silkscreen", "bottom"), (r"\.stc$", "soldermask", "top"), (r"\.sts$", "soldermask", "bottom"),
              (r"\.crc$", "paste", "top"), (r"\.crs$", "paste", "bottom"), (r"\.(dim|oln)$", "outline", None)],
    "zuken": [(r"conductive-1", "copper", "top"), (r"conductive-2", "copper", "bottom"), (r"metalmask-a", "paste", "top"), (r"metalmask-b", "paste", "bottom"),
              (r"resist-a", "soldermask", "top"), (r"resist-b", "soldermask", "bottom"), (r"symbol-a", "silkscreen", "top"), (r"symbol-b", "silkscreen", "bottom"),
              (r"\.fdr$", "drill", None)],
}

_SIDES = {"top": "top", "bot": "bottom", "bottom": "bottom", "inr": "inner"}
_KINDS = {"Copper": "copper", "Soldermask": "soldermask", "Paste": "paste", "Legend": "silkscreen", "Profile": "outline",
          "Plated": "drill", "NonPlated": "drill", "MixedPlating": "drill", "Component": "component"}


def x2_truth(head: str) -> Optional[Label]:
    """!
    @brief The function the tool itself wrote in the file (X2 `TF.FileFunction`, Gerber or the drill-file comment).
    @param head  First kilobytes of the file.
    @return tuple (kind, side) or None when the file has no file function.
    """
    m = re.search(r"TF\.FileFunction,([^*%\r\n]*)", head)
    if not m:
        return None
    f = [v.strip() for v in m.group(1).split(",")]
    kind = _KINDS.get(f[0], "other")
    side = None
    for v in f[1:]:
        if v.lower() in _SIDES:
            side = _SIDES[v.lower()]
    return kind, side


def rule_truth(tool: str, name: str) -> Optional[Label]:
    """!
    @brief The hand label of a file of a tool without X2 file functions.
    @param tool  Truth profile key of the set.
    @param name  File name (any case, any folder).
    @return tuple (kind, side) or None when no rule matches (the file is not judged).
    """
    base = name.replace("\\", "/").split("/")[-1].lower()
    for rx, kind, side in RULES.get(tool, []):
        if re.search(rx, base):
            return kind, side
    return None
