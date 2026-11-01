#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cadprofiles.py
@brief Prototype of the CAD-profile detector: which eCAD program wrote a set of Gerber/drill files.
@details Reads the table `cad_markers.json` (markers per tool, with a weight and the status of the evidence) and returns
         (profile, confidence, evidence) for a set of files, given only the file names and their first kilobytes.
         It is the research prototype of the proposed `pcbthermal/gerber/profiles.py` (see INTEGRATION.md): the same table
         would be a JSON file of the program, the same rule for the confidence, and no I/O (the caller reads the heads, as
         `functions.detect_file` already does).  Nothing here changes the program.

         Rule of the confidence (set level):
         - a marker of weight 9 or more is decisive (the file names its generator in so many words, or carries a quirk that
           only that tool writes);
         - "high": a profile has decisive markers and no other eCAD profile does;
         - "mixed": two eCAD profiles have decisive markers (files from several programs in one set): the profile with the
           most decisive files is proposed and the user must confirm;
         - "medium": no decisive marker but the weights add up to 5 or more (a quirk, a header sequence, a naming convention);
         - "low": only names of weight 1 to 4 (Protel-style extensions are shared by a dozen programs);
         - "declared": nothing in the table matches but an X2 `TF.GenerationSoftware` names a vendor and an application: the profile
           is "unknown" (generic conventions) and the declared text is shown;
         - "unknown": nothing at all.
         CAM tools (kind "cam", e.g. CAM350 or UcamX) never override an eCAD profile and are reported as the generator of a
         re-exported set (the original program is then unknown).
"""
import json
import os
import re
from typing import Dict, List, NamedTuple, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD_BYTES = 8192
DECISIVE = 9
_X2_ANY = re.compile(r"TF\.GenerationSoftware,\s*([^,*%\r\n]+),\s*([^,*%\r\n]+)(?:,\s*([^*%\r\n]*))?")


class Hit(NamedTuple):
    """!
    @brief One marker found in one file.
    @details profile: key of the profile; marker: marker id; weight: its weight; version: captured version text or "";
             file: file name; text: the matched text (shortened); status: evidence status string of the marker.
    """
    profile: str
    marker: str
    weight: int
    version: str
    file: str
    text: str
    status: str


class Detection(NamedTuple):
    """!
    @brief Result of the detection for a set.
    @details profile: key ("unknown" when none); name: readable name; confidence: high, mixed, medium, low, declared or unknown;
             version: version text or ""; evidence: list of Hit (best first); candidates: other profiles with hits (key, score, decisive files);
             declared: the generic X2 text "vendor application version" or "".
    """
    profile: str
    name: str
    confidence: str
    version: str
    evidence: List[Hit]
    candidates: list
    declared: str


def load_table(path: Optional[str] = None) -> dict:
    """!
    @brief Load the marker table.
    @param path  JSON file (default: cad_markers.json next to this module).
    @return dict The decoded table.
    """
    with open(path or os.path.join(HERE, "cad_markers.json"), encoding="utf-8") as fh:
        return json.load(fh)


def normalise(raw: bytes) -> str:
    """!
    @brief Decode the head of a file for matching: Latin-1 (never fails), no BOM, LF line ends.
    @param raw  First bytes of the file.
    @return str Text.
    """
    text = raw[:HEAD_BYTES].decode("latin-1")
    return text.lstrip("﻿ï»¿").replace("\r\n", "\n").replace("\r", "\n")


def file_scope(name: str, text: str) -> str:
    """!
    @brief Which kind of file is it, for choosing the markers: gerber, drill, odb or support.
    @param name  File name (may include folders).
    @param text  Normalised head.
    @return str One of "gerber", "drill", "odb", "support".
    """
    if name.replace("\\", "/").endswith("misc/info"):
        return "odb"
    body = text.lstrip()
    if "%FS" in text or re.search(r"(?m)^G04 ", text) or re.search(r"(?m)^%MO", text):
        return "gerber"
    if body.startswith("M48") or re.match(r"(;[^\n]*\n\s*)+M48", body) or re.match(r"%\s*\nM48", body):
        return "drill"
    return "support"


def scan_file(table: dict, name: str, raw: bytes) -> List[Hit]:
    """!
    @brief Apply every marker of the table to one file.
    @param table  The marker table.
    @param name   File name with its folders.
    @param raw    First bytes of the file.
    @return list Hits.
    """
    text = normalise(raw)
    scope = file_scope(name, text)
    base = name.replace("\\", "/").split("/")[-1]
    hits = []
    for key, prof in table["profiles"].items():
        for m in prof["markers"]:
            if m["scope"] == "name":
                target = base
            elif m["scope"] == scope:
                target = text
            else:
                continue
            found = re.search(m["re"], target)
            if found:
                ver = found.group(m["version"]).strip() if m.get("version") and found.lastindex else ""
                hits.append(Hit(key, m["id"], m["w"], ver, name, found.group(0)[:70].replace("\n", " "), m["status"]))
    return hits


def declared_generator(files: Dict[str, bytes]) -> str:
    """!
    @brief The generic X2 declaration `TF.GenerationSoftware,<vendor>,<application>[,<version>]` of the first file that has one.
    @param files  Mapping name -> first bytes.
    @return str "vendor application version" or "".
    """
    for name in sorted(files):
        m = _X2_ANY.search(normalise(files[name]))
        if m:
            return " ".join(x.strip() for x in m.groups() if x and x.strip())
    return ""


def detect_set(files: Dict[str, bytes], table: Optional[dict] = None) -> Detection:
    """!
    @brief Detect the generating program of a set of files.
    @param files  Mapping file name (with folders) -> first bytes of the file.
    @param table  The marker table (loaded when omitted).
    @return Detection with the profile, the confidence and the evidence.
    """
    table = table or load_table()
    hits: List[Hit] = []
    for name, raw in files.items():
        hits += scan_file(table, name, raw)
    # score per profile: the best weight of every marker id, summed; decisive files counted apart
    score: Dict[str, int] = {}
    dec_files: Dict[str, set] = {}
    seen: Dict[tuple, int] = {}
    for h in hits:
        k = (h.profile, h.marker)
        if h.weight > seen.get(k, 0):
            seen[k] = h.weight
        if h.weight >= DECISIVE:
            dec_files.setdefault(h.profile, set()).add(h.file)
    for (p, _), w in seen.items():
        score[p] = score.get(p, 0) + w
    declared = declared_generator(files)
    kinds = {k: v["kind"] for k, v in table["profiles"].items()}
    ecad_dec = [p for p in dec_files if kinds[p] == "ecad"]
    # a variant (CircuitMaker writes the Altium Designer files too) wins over its parent and is not a conflict
    parents = {table["profiles"][p].get("parent") for p in ecad_dec}
    ecad_dec = [p for p in ecad_dec if p not in parents]
    cam_dec = [p for p in dec_files if kinds[p] == "cam"]
    cands = sorted(((p, score[p], len(dec_files.get(p, ()))) for p in score), key=lambda t: (-t[2], -t[1]))
    if ecad_dec:
        best = max(ecad_dec, key=lambda p: (len(dec_files[p]), score[p]))
        conf = "high" if len(ecad_dec) == 1 else "mixed"
    elif cam_dec:
        best = max(cam_dec, key=lambda p: (len(dec_files[p]), score[p]))
        conf = "high"
    elif score:
        best = max(score, key=lambda p: score[p])
        conf = "medium" if score[best] >= 5 else "low"
    else:
        best, conf = "unknown", "declared" if declared else "unknown"
    ev = sorted([h for h in hits if h.profile == best], key=lambda h: -h.weight)
    ver = next((h.version for h in ev if h.version), "")
    name = "Unknown program" if best == "unknown" else table["profiles"][best]["name"]
    return Detection(best, name, conf, ver, ev, [c for c in cands if c[0] != best], declared)


def read_heads(paths: List[str], root: str) -> Dict[str, bytes]:
    """!
    @brief Read the first bytes of files (the I/O the program's detector also does).
    @param paths  Paths of the files.
    @param root   Folder the names are made relative to.
    @return dict Name relative to root -> first bytes.
    """
    out = {}
    for p in paths:
        with open(p, "rb") as fh:
            out[os.path.relpath(p, root)] = fh.read(HEAD_BYTES)
    return out
