#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file profiles.py
@brief CAD profiles: which eCAD program wrote a set of Gerber and drill files, and the layer-name rules of that program.
@details A profile is a bundle of DEFAULTS, never an authority. The order of trust for what a file is (see functions.py): the user's assignment of the file,
         then the X2 attribute `TF.FileFunction`, then the Excellon header, then the content rules, then the NAME RULES OF THE PROFILE (this module), then the generic name
         rules, then "ask". The user's choice of a profile replaces only the profile tier, never X2 or the header. No physics model depends on the profile.

         Detection (`detect_profile`) takes the names and the first 8 kB of every file (the caller reads them: this module does no I/O) and applies the markers of
         `pcbthermal/data/cad_profiles.json`. Rule of the confidence (set level):
         - a marker of weight 9 or more is decisive (the file names its generator, or carries a quirk only that tool writes);
         - "high": a profile has decisive markers and no other eCAD profile does (a variant, e.g. CircuitMaker, wins over its parent, Altium);
         - "mixed": two eCAD profiles have decisive markers (files from several programs in one set): the one with more decisive files is proposed, to be confirmed;
         - "medium": no decisive marker but the weights add up to 5 or more (a quirk, a header sequence, a naming convention): "probably";
         - "low": only names of weight 1 to 4 (the Protel extensions are shared by a dozen programs): the profile is NOT applied;
         - "declared": nothing matches but an X2 `TF.GenerationSoftware` names a vendor and an application (profile "declared", generic rules);
         - "unknown": nothing at all (profile "unknown", generic rules).
         A CAM tool (kind "cam": CAM350, UcamX) never overrides an eCAD profile and is reported as the program that re-exported the set (the design program is then unknown).

         Safety: at most 8 kB of a file is looked at; every pattern of the table is bounded, so the worst case is linear in the head (a hostile head of blanks or of a
         repeated prefix costs milliseconds); the text matched in a file is NEVER kept or shown (the banners of some tools hold a path, a user and a computer name): only
         marker ids, file counts and a version or declared generator cut to 40 printable characters (`public_text`). The bottom-side X sign of a placement file is never
         preset by a profile (it is detected from the paste openings). Evidence of the table: only tools with real sample files have a profile; the name rules of PADS and EAGLE
         are marked "from memory".
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple

HEAD_BYTES = 8192                  # at most this many bytes of a file are looked at (the same as functions.HEAD_BYTES)
MAX_FILES = 5000                   # a set with more members is looked at in name order up to this many (a hostile archive costs a bounded time)
MAX_NAME_CHARS = 255               # only the end of a long file name is matched
DECISIVE = 9                       # weight from which a marker alone identifies the program
PUBLIC_TEXT_MAX = 40               # characters of a version or declared generator that may be shown or stored
TABLE_PATH = Path(__file__).resolve().parent.parent / "data" / "cad_profiles.json"

# The generic X2 declaration of any generator. Every field is bounded (a line of blanks must not make the search quadratic).
_X2_ANY = re.compile(r"TF\.GenerationSoftware,([^,*%\r\n]{1,60}),([^,*%\r\n]{1,60})(?:,([^*%\r\n]{0,60}))?")

SOURCES = ("detected", "user")


class Hit(NamedTuple):
    """!
    @brief One marker found in one file (without the matched text, which is never kept).
    @details profile: key of the profile; marker: marker id; weight: its weight; version: captured version text (public_text) or "";
             file: file name; status: evidence status string of the marker (R seen, D documented, M memory).
    """
    profile: str
    marker: str
    weight: int
    version: str
    file: str
    status: str


class ProfileResult(NamedTuple):
    """!
    @brief Result of the detection for a set.
    @details profile: key ("unknown" when nothing matches, "declared" when only a generic X2 generator is named); confidence: high, mixed, medium, low, declared or unknown;
             version: version text (public) or ""; evidence: list of Hit of the chosen profile, best first; candidates: other profiles with hits, as (key, score, decisive files);
             declared: the generic X2 text "vendor application version" (public) or "".
    """
    profile: str
    confidence: str
    version: str
    evidence: list
    candidates: list
    declared: str


class ProfileChoice(NamedTuple):
    """!
    @brief The profile that the name rules use for an import, and who chose it.
    @details key: profile key; source: "detected" or "user"; table: version of the table that was used.
    """
    key: str
    source: str
    table: int

    def record(self) -> dict:
        """!
        @brief The dict stored in the import record of the project (`ImportRecord.cad_profile`).
        @return dict Keys "key", "source" and "table".
        """
        return {"key": self.key, "source": self.source, "table": int(self.table)}


@lru_cache(maxsize=2)
def _load(path: str) -> dict:
    """!
    @brief Read and validate a table file (cached by path).
    @param path File path of the JSON table.
    @return dict The decoded table.
    @throws ValueError If a marker or a rule is malformed.
    """
    with open(path, encoding="utf-8") as fh:
        table = json.load(fh)
    _validate(table)
    return table


def load_table(path: Optional[str] = None) -> dict:
    """!
    @brief The marker and rule table.
    @param path JSON file (default: the shipped `pcbthermal/data/cad_profiles.json`).
    @return dict The table; do not modify it.
    @throws ValueError If the table is malformed.
    """
    return _load(str(path or TABLE_PATH))


def _validate(table: dict) -> None:
    """!
    @brief Check a table: patterns compile, ids are unique, weights are 1 to 10, statuses start with R, D or M, rules have a known kind.
    @param table The decoded table.
    @return None
    @throws ValueError On the first defect.
    """
    kinds = {"copper", "paste", "soldermask", "silkscreen", "outline", "drill", "other"}
    profiles = table.get("profiles", {})
    for key in ("unknown", "declared"):
        if key not in profiles:
            raise ValueError("cad profile table: the profile '%s' is missing" % key)
    for key, prof in profiles.items():
        if prof.get("kind") not in ("ecad", "cam", "generic"):
            raise ValueError("cad profile %s: bad kind" % key)
        if prof.get("parent") is not None and prof["parent"] not in profiles:
            raise ValueError("cad profile %s: unknown parent" % key)
        ids = [m["id"] for m in prof["markers"]]
        if len(ids) != len(set(ids)):
            raise ValueError("cad profile %s: duplicate marker id" % key)
        for m in prof["markers"]:
            try:
                re.compile(m["re"])
            except re.error as err:
                raise ValueError("cad profile %s marker %s: bad pattern (%s)" % (key, m["id"], err)) from err
            if not 1 <= int(m["w"]) <= 10 or m["scope"] not in ("gerber", "drill", "support", "name", "odb") or m["status"][:1] not in ("R", "D", "M"):
                raise ValueError("cad profile %s marker %s: bad weight, scope or status" % (key, m["id"]))
        for rx, kind, side in prof.get("name_rules", []):
            try:
                re.compile(rx)
            except re.error as err:
                raise ValueError("cad profile %s: bad name rule pattern (%s)" % (key, err)) from err
            if kind not in kinds or side not in (None, "top", "bottom", "inner"):
                raise ValueError("cad profile %s: bad name rule %r" % (key, rx))
        if prof.get("name_rules") and prof.get("name_rules_status") not in ("R", "D", "M"):
            raise ValueError("cad profile %s: name_rules_status must be R, D or M" % key)


def table_version(table: Optional[dict] = None) -> int:
    """!
    @brief Version number of the table (stored in the import record).
    @param table The table (default: the shipped one).
    @return int The version.
    """
    return int((table or load_table()).get("version", 0))


def profile_keys(table: Optional[dict] = None) -> List[str]:
    """!
    @brief Keys of every profile, for the combo of the import window ("unknown" first).
    @param table The table (default: the shipped one).
    @return list The keys.
    """
    keys = list((table or load_table())["profiles"])
    return ["unknown"] + [k for k in keys if k not in ("unknown", "declared")]


def profile_name(key: str, table: Optional[dict] = None) -> str:
    """!
    @brief Readable name of a profile.
    @param key   Profile key.
    @param table The table (default: the shipped one).
    @return str The name, or the key when it is not in the table.
    """
    prof = (table or load_table())["profiles"].get(key)
    return prof["name"] if prof else str(key)


@lru_cache(maxsize=256)
def _rx(pattern: str):
    """!
    @brief Compile a pattern of the table (cached).
    @param pattern Regular expression.
    @return re.Pattern The compiled pattern.
    """
    return re.compile(pattern)


def normalise(raw) -> str:
    """!
    @brief Decode the head of a file for matching: at most 8 kB, Latin-1 for bytes (never fails), no byte order mark, LF line ends.
    @param raw First bytes of the file (bytes) or its first characters (str).
    @return str Text.
    """
    if isinstance(raw, (bytes, bytearray, memoryview)):
        text = bytes(raw[:HEAD_BYTES]).decode("latin-1")
    else:
        text = str(raw)[:HEAD_BYTES]
    return text.lstrip("﻿ï»¿").replace("\r\n", "\n").replace("\r", "\n")


def file_scope(name: str, text: str) -> str:
    """!
    @brief Which kind of file it is, for choosing the markers: gerber, drill, odb or support.
    @param name File name (may include folders).
    @param text Normalised head.
    @return str One of "gerber", "drill", "odb", "support".
    """
    if name.replace("\\", "/").endswith("misc/info"):
        return "odb"
    if "%FS" in text or "%MO" in text or text.startswith("G04 ") or "\nG04 " in text:
        return "gerber"
    # Excellon: M48 is the first statement after comment lines, blank lines and a stray percent line (linear scan, no pattern)
    for line in text.split("\n", 400)[:400]:
        s = line.strip()
        if not s or s.startswith(";") or s == "%":
            continue
        return "drill" if s.startswith("M48") else "support"
    return "support"


def public_text(text: str) -> str:
    """!
    @brief Reduce a text taken from a file (a version, a declared generator) to what may be shown or stored.
    @details Only printable ASCII is kept; characters that a rich-text label would interpret (`<`, `>`, `&`) and the backslash are dropped; the result is cut to 40 characters.
    @param text Captured text.
    @return str The text safe to show.
    """
    kept = "".join(c for c in str(text) if 32 <= ord(c) < 127 and c not in "<>&\\")
    return kept.strip()[:PUBLIC_TEXT_MAX]


def _scan_file(table: dict, name: str, raw) -> List[Hit]:
    """!
    @brief Apply every marker of the table to one file.
    @param table The table.
    @param name  File name with its folders.
    @param raw   First bytes of the file.
    @return list Hits (the matched text is not kept).
    """
    text = normalise(raw)
    scope = file_scope(name, text)
    base = name.replace("\\", "/").split("/")[-1][-MAX_NAME_CHARS:]
    hits = []
    for key, prof in table["profiles"].items():
        for m in prof["markers"]:
            if m["scope"] == "name":
                target = base
            elif m["scope"] == scope:
                target = text
            else:
                continue
            found = _rx(m["re"]).search(target)
            if found:
                gi = m.get("version")
                ver = public_text(found.group(gi) or "") if gi and found.re.groups >= gi else ""
                hits.append(Hit(key, m["id"], int(m["w"]), ver, name, m["status"]))
    return hits


def _declared_generator(items: List[Tuple[str, str]]) -> str:
    """!
    @brief The generic X2 declaration `TF.GenerationSoftware,<vendor>,<application>[,<version>]` of the first file that has one.
    @param items Pairs (name, normalised head) in name order.
    @return str "vendor application version" (public text) or "".
    """
    for _, text in items:
        m = _X2_ANY.search(text)
        if m:
            return public_text(" ".join(x.strip() for x in m.groups() if x and x.strip()))
    return ""


def detect_profile(files: Mapping[str, object], table: Optional[dict] = None) -> ProfileResult:
    """!
    @brief Detect the program that wrote a set of files.
    @details No I/O: the caller reads the heads (as `functions.detect_file` and `GerberArchive.read_head` do). At most `MAX_FILES` files (in name order) and the first
             `HEAD_BYTES` of each are looked at.
    @param files Mapping file name (with folders) -> first bytes of the file (bytes, or str).
    @param table The table (default: the shipped one).
    @return ProfileResult With the profile key, the confidence, the public version, the evidence (marker ids only), the other candidates and the declared generator.
    """
    table = table or load_table()
    names = sorted(str(n) for n in files)[:MAX_FILES]
    hits: List[Hit] = []
    heads: List[Tuple[str, str]] = []
    for n in names:
        raw = files[n]
        heads.append((n, normalise(raw)))
        hits += _scan_file(table, n, raw)
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
    declared = _declared_generator(heads)
    kinds = {k: v["kind"] for k, v in table["profiles"].items()}
    ecad_dec = [p for p in dec_files if kinds[p] == "ecad"]
    # a variant (CircuitMaker writes the Altium Designer macro files too) wins over its parent and is not a conflict
    parents = {table["profiles"][p].get("parent") for p in ecad_dec}
    ecad_dec = [p for p in ecad_dec if p not in parents]
    cam_dec = [p for p in dec_files if kinds[p] == "cam"]
    cands = sorted(((p, score[p], len(dec_files.get(p, ()))) for p in score), key=lambda t: (-t[2], -t[1], t[0]))
    if ecad_dec:
        best = max(sorted(ecad_dec), key=lambda p: (len(dec_files[p]), score[p]))
        conf = "high" if len(ecad_dec) == 1 else "mixed"
    elif cam_dec:
        best = max(sorted(cam_dec), key=lambda p: (len(dec_files[p]), score[p]))
        conf = "high"
    elif score:
        best = max(sorted(score), key=lambda p: score[p])
        conf = "medium" if score[best] >= 5 else "low"
    elif declared:
        best, conf = "declared", "declared"
    else:
        best, conf = "unknown", "unknown"
    ev = sorted((h for h in hits if h.profile == best), key=lambda h: (-h.weight, h.marker, h.file))
    ver = next((h.version for h in ev if h.version), "")
    return ProfileResult(best, conf, ver, ev, [c for c in cands if c[0] != best], declared)


def needs_check(result: ProfileResult) -> bool:
    """!
    @brief Whether the line of the import window must be shown as a warning (the detection is not a plain "high").
    @details Medium, low, mixed and declared results, and every CAM tool (the design program is not known), are flagged; so is "unknown".
    @param result Detection.
    @return bool True when the user should check the profile.
    """
    if result.confidence != "high":
        return True
    return load_table()["profiles"][result.profile]["kind"] == "cam"


def summary(result: ProfileResult, table: Optional[dict] = None) -> str:
    """!
    @brief The one-line text of the import window ("Detected: ...").
    @details Built only from the names of the table and the public version or declared generator; never from text matched in a file. A label in rich-text mode should
             still be given plain text.
    @param result Detection.
    @param table  The table (default: the shipped one).
    @return str The line, in English.
    """
    table = table or load_table()
    name = profile_name(result.profile, table)
    ver = (" " + result.version) if result.version else ""
    kind = table["profiles"][result.profile]["kind"]
    if result.confidence == "unknown":
        return "Program not recognised: generic rules"
    if result.confidence == "declared":
        return "Declared by the files: %s (no profile, generic rules)" % (result.declared or "unknown program")
    if kind == "cam":
        return "Re-exported by %s%s: the design program is not known (generic rules)" % (name, ver)
    if result.confidence == "high":
        return "Detected: %s%s (high confidence)" % (name, ver)
    if result.confidence == "mixed":
        others = ", ".join(profile_name(c[0], table) for c in result.candidates if c[2] > 0)
        return "Files from several programs: %s%s and %s (check)" % (name, ver, others or "others")
    if result.confidence == "medium":
        return "Probably %s%s (%s confidence, check)" % (name, ver, result.confidence)
    return "Only the file names suggest %s: generic rules are used" % name


def choose(result: ProfileResult, user_key: Optional[str] = None, table: Optional[dict] = None) -> ProfileChoice:
    """!
    @brief The profile whose name rules the import uses.
    @details The user's choice replaces only the profile tier (X2 and the Excellon header still win in `functions.detect_function`). Without a user choice the detected
             profile is used when its confidence is high, mixed or medium; "low" (names alone), "declared" and "unknown" use the generic rules ("unknown").
    @param result   Detection of `detect_profile`.
    @param user_key Profile key chosen by the user (any key of the table, "unknown" for none), or None to keep the detection.
    @param table    The table (default: the shipped one).
    @return ProfileChoice The key, the source ("user" or "detected") and the table version.
    @throws ValueError If user_key is not a profile of the table.
    """
    table = table or load_table()
    if user_key is not None:
        if user_key not in table["profiles"]:
            raise ValueError("unknown CAD profile %r" % (user_key,))
        return ProfileChoice("unknown" if user_key == "declared" else user_key, "user", table_version(table))
    key = result.profile if result.confidence in ("high", "mixed", "medium") else "unknown"
    return ProfileChoice(key, "detected", table_version(table))


def public_evidence(result: ProfileResult, table: Optional[dict] = None) -> dict:
    """!
    @brief The part of a detection that the program may show in the import window, log or store.
    @details Never text matched in a file: the profile key and name, the confidence, the marker ids with the number of files, the version and the declared generator
             (both through `public_text`), the summary line and whether it needs a check.
    @param result Detection.
    @param table  The table (default: the shipped one).
    @return dict Keys profile, name, confidence, version, declared, markers (sorted list of (marker id, files)), line, check.
    """
    table = table or load_table()
    count: Dict[str, set] = {}
    for h in result.evidence:
        count.setdefault(h.marker, set()).add(h.file)
    return {"profile": result.profile, "name": profile_name(result.profile, table), "confidence": result.confidence, "version": public_text(result.version),
            "declared": public_text(result.declared), "markers": sorted((m, len(f)) for m, f in count.items()), "line": summary(result, table),
            "check": needs_check(result)}


def rules_for(key: Optional[str], table: Optional[dict] = None) -> Tuple[tuple, ...]:
    """!
    @brief The name rules of a profile, compiled.
    @param key   Profile key (None, "unknown", "declared" or a profile without rules: no rules).
    @param table The table (default: the shipped one).
    @return tuple Tuples (compiled regex on the lower-case file name, kind, side or None), in order; the first match wins.
    """
    if not key:
        return ()
    prof = (table or load_table())["profiles"].get(key)
    if not prof:
        return ()
    return tuple((_rx(rx), kind, side) for rx, kind, side in prof.get("name_rules", []))


def rules_from_memory(key: Optional[str], table: Optional[dict] = None) -> bool:
    """!
    @brief Whether the name rules of a profile are from memory (no document or file of the tool was read), to say so in the user guide and the import window.
    @param key   Profile key.
    @param table The table (default: the shipped one).
    @return bool True for PADS and EAGLE.
    """
    prof = (table or load_table())["profiles"].get(key or "")
    return bool(prof and prof.get("name_rules") and prof.get("name_rules_status") == "M")
