#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file import_session.py
@brief The state of one Gerber import, with no Qt: the files of a folder, a ZIP or a list, the function of each file, the board read from them and the hooks of the features that are not merged yet.
@details The import window (`import_window.py`) talks only to `ImportSession`. Step 1 (files and layers) is complete here and uses the reader of `pcbthermal.gerber`
         (function detector, safe ZIP archive, Excellon drills, outline, rasteriser). The calls that belong to features still being implemented sit behind five methods
         with a stable interface, so that the dialog does not change when the real implementations arrive:
         * `parts()` - the parts table (paste openings, placement file, heat-source shapes): `feature/paste-parts`; empty now.
         * `copper()` - the imported copper of the model (`ImportedCopper`, mapping faces / fill / lambda): `feature/imported-copper`; None now.
         * `build_problem()` - the new Problem with its import record (project format 2): raises `ImportNotAvailable` now.
         * `memory_verdict()` - the guard verdict of the model grid and of the rasters of the import; the FVM law of `pcbthermal.memory` plus the raster estimate of the
           reader now, the measured import term when `feature/imported-copper` merges.
         * `warnings()` - the list under the Model step; the always-on notes of the Lumped and Analytic models on imported copper are part of it.
         Lengths are in millimetres, the Gerber axes (Y up); rasters run from the top edge downwards, one byte of coverage per pixel.
"""

import copy
import dataclasses
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

import numpy as np

from .. import copper as copper_mod
from .. import memory
from ..gerber import (DrillFile, GerberArchive, GerberError, LayerFunction, detect_set, limits, parse_layer, pixel_counts, rasterize, read_drill, read_outline,
                      window_of)
from ..gerber import bom as bom_mod
from ..gerber import components as comp_mod
from ..gerber import profiles as prof_mod
from ..gerber import parts as parts_mod
from ..model import ImportFile, ImportRecord, Problem, new_problem, stackup_template

log = logging.getLogger(__name__)

INNER_MAX = 8                                                   # Inner copper layers the role list offers (a 10 layer board)
COPPER_TOP, COPPER_BOTTOM = "Top copper", "Bottom copper"
INNER = tuple(f"Inner copper {n}" for n in range(1, INNER_MAX + 1))
COPPER = (COPPER_TOP,) + INNER + (COPPER_BOTTOM,)
OUTLINE, PLATED, NONPLATED = "Board outline / profile", "Plated drill", "Non-plated drill"
PASTE = ("Solder paste top", "Solder paste bottom")
MASK = ("Solder mask top", "Solder mask bottom")
LEGEND = ("Legend (silkscreen) top", "Legend (silkscreen) bottom")
COMPONENT, PLACEMENT, IGNORE = "Component layer (X3)", "Placement (pick and place)", "Ignore"
BOM = "BOM (bill of materials)"
ROLES = COPPER + (OUTLINE, PLATED, NONPLATED) + PASTE + MASK + LEGEND + (COMPONENT, PLACEMENT, BOM, IGNORE)
# Functions that change the board itself (copper masks, outline, vias): "Add files" never takes them, because it keeps the stored masks and the board as they are
GEOMETRY = COPPER + (OUTLINE, PLATED, NONPLATED)
# Functions that give the parts: an added one, or a conflict answered "use the new file", matches the stored parts again against the new files
PARTS_FUNCTIONS = PASTE + (PLACEMENT, COMPONENT)
# Roles that are read when the file is in use; the others (mask, legend) are listed and ignored by the models
USED_BY_DEFAULT = COPPER + (OUTLINE, PLATED, NONPLATED) + PASTE + (COMPONENT, PLACEMENT, BOM)
# Roles of which only one file can exist (two files claiming one are shown and stop the import)
UNIQUE = COPPER + (OUTLINE,) + PASTE + (COMPONENT, PLACEMENT)
PREVIEW_PIXELS = 900                                            # The preview raster is about this many pixels on the long side
PREVIEW_PIXEL_MIN_MM = 0.1                                      # Finest pixel of the preview
VIA_MAX_MM = 0.5                                                # Default largest plated hole that is a via
HASH_WHOLE_BYTES = 64 * 1024 ** 2                               # Archive members up to this size are hashed whole
HASH_EDGE_BYTES = 1 << 20                                       # Larger members: the first and the last megabyte and the size
HEAD_BYTES = 8192


class ImportNotAvailable(RuntimeError):
    """!@brief Raised by the hooks whose feature is not merged yet (the dialog tells the user and keeps the import window open)."""


class LayerInfo(NamedTuple):
    """!@brief One copper layer in stack order: its role, the file name and its position from the top (1 = top)."""
    role: str
    name: str
    position: int


class Hole(NamedTuple):
    """!@brief One drilled hole for the preview and the vias: centre (mm), diameter (mm) and whether it is plated."""
    x: float
    y: float
    diameter: float
    plated: bool


class BoardData(NamedTuple):
    """!
    @brief Everything the preview and the stack-up summary need, read from the used files.
    @details box (xmin, ymin, xmax, ymax) in mm; pixel_mm the preview pixel; copper a list of (role, file name, uint8 coverage) in stack order; outline a list of (outer, holes)
             arrays of an `Outline` or empty; outline_area_mm2 None without an outline; thinnest_mm the thinnest line of the copper files (None if none has a width).
    """
    box: tuple
    width: float
    height: float
    pixel_mm: float
    copper: list
    outline: list
    outline_area_mm2: Optional[float]
    holes: list
    thinnest_mm: Optional[float]


class SourceFile:
    """!
    @brief One file of the set: name, size, hash, the detected and the chosen function, and the error of the reader when it could not read it.
    """

    def __init__(self, name: str, size: int, sha256: str, detected: LayerFunction, role: str, how: str, reader: Callable[[], str]):
        """!
        @param name File name (the path inside an archive).
        @param size Size in bytes.
        @param sha256 SHA-256 hex digest of the content.
        @param detected The detector's answer.
        @param role The role chosen (starts as the detected one), one of ROLES.
        @param how Text that says how the role was found ("Gerber X2 attribute", "file name", ...).
        @param reader Function that returns the text of the file.
        """
        self.name, self.size, self.sha256, self.detected, self.role, self.how, self.reader = name, size, sha256, detected, role, how, reader
        self.use = role in USED_BY_DEFAULT
        self.error = ""                                       # Why the reader could not use it ("" when it could or was not tried)
        self.user_role = False                                # True once the user chose the function of this file
        self.limit_error = ""                                 # Set when the file is above the size limit: it stays listed with this message and is never read
        self.warnings = []                                    # Tolerances the reader used on this file (Layer.warnings), text

    def text(self) -> str:
        """!
        @brief The text of the file.
        @return str
        @throws GerberError If the file is above the size limit (it is listed, never read).
        """
        if self.limit_error:
            raise GerberError(self.limit_error)
        return self.reader()


def role_of(fn: LayerFunction) -> str:
    """!
    @brief The role of the window's list that a detected function means.
    @param fn LayerFunction of the detector.
    @return str, one of ROLES (an inner copper layer without a number is Inner copper 1; the session renumbers duplicates).
    """
    side = fn.side
    if fn.kind == "copper":
        if side == "top":
            return COPPER_TOP
        if side == "bottom":
            return COPPER_BOTTOM
        # An X2 copper index counts from the top, so L2 is the first inner layer; a name-based index is the ordinal among the inner layers
        n = (fn.index - 1 if fn.source == "x2" and fn.index else fn.index) or 1
        return INNER[max(1, min(INNER_MAX, n)) - 1]
    if fn.kind == "outline":
        return OUTLINE
    if fn.kind == "drill":
        return NONPLATED if fn.plated is False else PLATED
    table = {"paste": PASTE, "soldermask": MASK, "silkscreen": LEGEND}
    if fn.kind in table:
        return table[fn.kind][1 if side == "bottom" else 0]
    if fn.kind == "component":
        return COMPONENT
    return IGNORE


def _how(fn: LayerFunction) -> str:
    """!
    @brief Text for the "Detected from" column.
    @param fn LayerFunction.
    @return str
    """
    if fn.kind == "unknown":
        return "unknown: choose the function"
    if fn.confidence == "low":
        return "file name, low confidence: check"                  # A guess from the name alone: the window shows it in the alert colour
    return {"x2": "Gerber X2 attribute", "excellon": "Excellon header", "name": "file name"}.get(fn.source, fn.source)


def _looks_like_placement(head: str) -> bool:
    """!
    @brief Whether the head of a text file is the header of a pick-and-place table (a reference column and X, Y columns).
    @details A first rule for the file list; the placement reader of `feature/paste-parts` decides what a table means.
    @param head First kilobytes of the file.
    @return bool
    """
    for line in head.splitlines()[:12]:
        cols = [c.strip().strip('"').lower() for c in re.split(r"[,;\t]", line)]
        if len(cols) >= 4 and any(re.fullmatch(r"(ref(erence)?( des(ignator)?)?|designator|part)", c) for c in cols) and any(re.search(r"(^|\W)(x|pos ?x|mid ?x|center-?x)$", c) for c in cols) \
                and any(re.search(r"(^|\W)(y|pos ?y|mid ?y|center-?y)$", c) for c in cols):
            return True
    return False


TABLE_SUFFIXES = (".csv", ".pos", ".txt", ".xy", ".tsv", ".tab")
WORKBOOK_SUFFIXES = (".xlsx", ".xls")


def _role_by_content(name: str, fn: LayerFunction, head: str):
    """!
    @brief The role of a file the detector could not place, from the columns of a table: a placement table (a reference column and X, Y columns) or a BOM (a designator column and a
           value, footprint, quantity or part-number column, no X and Y). An Excel workbook is a BOM that is not read.
    @param name File name.
    @param fn The detector's answer.
    @param head First kilobytes of the file, decoded.
    @return tuple (role, how) or None when the file is not a table of these kinds.
    """
    suffix = Path(name).suffix.lower()
    if fn.kind not in ("unknown", "other"):
        return None
    # The detector calls a table it does not know "other" (low confidence, by the name): its columns decide; a placement table is recognised only where it always was ("unknown")
    if suffix in WORKBOOK_SUFFIXES:
        return BOM, "Excel workbook: not read, save the table as CSV"
    if suffix in TABLE_SUFFIXES:
        if fn.kind == "unknown" and _looks_like_placement(head):
            return PLACEMENT, "columns of a placement table"
        if bom_mod.looks_like_bom(head):
            return BOM, "columns of a BOM table"
    return None


def _sha256(data: bytes) -> str:
    """!
    @brief SHA-256 of a byte string.
    @param data Bytes.
    @return str hex digest.
    """
    return hashlib.sha256(data).hexdigest()


class ImportSession:
    """!
    @brief The state of one import: the files, the roles, the board read from them, and the hooks of the features that are not merged yet.
    """

    # What the window reads to enable the later steps; `feature/paste-parts` and `feature/imported-copper` switch them on
    PARTS_AVAILABLE = False
    COPPER_AVAILABLE = False

    def __init__(self):
        """!@brief Create an empty session."""
        self.files: List[SourceFile] = []
        self.source_text = ""                                 # What was opened (shown in the window)
        self.paths = {}                                       # file name -> Path on the disk (folder or list of files; a ZIP member has none)
        self.name = "board"
        self.mapping = "faces"                                # Copper mapping key for the Model step
        self.cell_mm = 1.0
        self._archive: Optional[GerberArchive] = None
        self._board: Optional[BoardData] = None
        self._board_error = ""
        self.job = None                                       # Dict of the Gerber job file (.gbrjob) when the set has one
        self.via_max_mm = VIA_MAX_MM                          # Largest plated hole that is a via (mm)
        self.pixel_mm = None                                  # Pixel of the copper masks (mm); None: automatic
        self.offset = (0.0, 0.0)                              # Offset added to the placement file positions (mm), the user's answer to the frame check
        self.offset_answer = ""                               # "", "accepted" or "rejected"
        self.profile_result = None                            # profiles.ProfileResult of the last set_files() (the CAD tool that wrote the files)
        self.profile_choice = None                            # profiles.ProfileChoice: the profile whose name rules were used, and who chose it
        self.reuse_profile = None                             # Profile key a re-import takes from the stored import (the user's choice then)
        self.user_profile = None                              # Profile key the user chose (or a re-import reuses); None keeps the detection
        self.auto_note = ""                                   # The sentence of the last auto_cell() when the cell left the imported-copper cap
        self.record = None                                    # ImportRecord of the last build_problem()
        self._stored_values = {}                              # Re-import: designator -> the step-2 fields taken from the stored import (`take_stored_parts`)
        self.thickness_mm = None                              # Board thickness of the last build (mm)
        self._outline = None                                  # gerber.Outline of the profile file, when it could be read
        self._parts_dirty = True
        self._res = None                                      # parts.PartsResult of the last build
        self._parts: List = []                                # ImportPart: heat-source candidates, hand-picked parts and orphans
        self._listed: List = []                               # ImportPart that are listed only (no opening, not SMD)
        self._unmatched: List = []                            # Opening that no file names
        self._owner_cache = None
        self._layer_cache = {}                                # sha256 -> parsed Layer
        self._raster_cache = {}                               # (sha256, window, pixel) -> (coverage, thinnest mm)
        self._bom = None                                      # bom.BomSet of the BOM files in use, None without one (`bom_set`)
        self._bom_key = None                                  # the sha256 of those files when `_bom` was read; None: read again
        # Hooks `fn(session, reason)` of the features that must act before the files are released (reason "close" or "new_files"); each runs once and is then dropped
        self.before_release: List[Callable] = []

    # ------------------------------------------------------------------------------------------------------------------------------------ files
    def run_before_release(self, reason: str = "close"):
        """!
        @brief Run the `before_release` hooks once, in registration order, and drop them; an exception of a hook is logged and does not stop the next one or the release.
        @details Thread rule: the window calls this from the GUI thread BEFORE the reader's worker thread starts (the worker runs with the cyclic garbage collector disabled, because
                 a collection in that thread destroyed Qt objects and crashed the process), so a hook may touch Qt objects; when a caller reaches `set_files()` without calling it
                 first, the hooks run in that caller's thread and must not create, touch or drop a Qt object.
        @param reason "close" (the window closes the session) or "new_files" (other files replace the set).
        @return None
        """
        hooks, self.before_release = self.before_release, []
        for fn in hooks:
            try:
                fn(self, reason)
            except Exception:                                 # a hook never blocks the release nor the hooks after it
                log.exception("before_release hook %s failed", getattr(fn, "__name__", fn))

    def close(self, reason: str = "close"):
        """!
        @brief Run the `before_release` hooks, then release the archive and the caches.
        @param reason "close" or "new_files" (what the hooks are told).
        @return None
        """
        self.run_before_release(reason)
        if self._archive is not None:
            self._archive.close()
            self._archive = None
        self._layer_cache.clear()
        self._raster_cache.clear()

    def set_files(self, source):
        """!
        @brief Read the file list of a folder, a ZIP archive or a list of files, and detect the function of every file.
        @param source A folder, a .zip file, or a list of file paths.
        @return None
        @throws GerberError For an unsafe or unreadable archive.
        @throws OSError If a path cannot be read.
        @throws ValueError If the source holds no file.
        """
        self.close("new_files")
        self._bom_key = None
        self.files, self._board, self._board_error, self.job, self._pending = [], None, "", None, []
        self._parts_dirty, self.offset, self.offset_answer = True, (0.0, 0.0), ""
        self.user_profile = self.reuse_profile                # a new set starts from the detection, a re-import from the stored profile
        self._parts, self._listed, self._unmatched, self._res = [], [], [], None
        self.paths = {}                                       # file name -> Path of a file read from a folder or a list of files (none for a ZIP)
        if isinstance(source, (list, tuple)):
            paths = [Path(p) for p in source]
            self.source_text = f"{len(paths)} files"
            self.name = paths[0].parent.name or "board" if paths else "board"
            self._add_paths(paths)
        else:
            p = Path(source).expanduser()
            self.source_text, self.name = str(p), p.stem if p.is_file() else (p.name or "board")
            if p.is_dir():
                self._add_paths(sorted(f for f in p.iterdir() if f.is_file()))
            elif p.suffix.lower() == ".zip":
                self._add_archive(p)
            else:
                raise ValueError(f"{p.name} is neither a folder nor a ZIP archive")
        self._detect_all()
        if not self.files:
            raise ValueError("no fabrication file found")
        self._assign_inner_numbers()

    def _detect_all(self):
        """!
        @brief Detect the function of the whole set at once (`detect_set` orders copper layers that are only numbered, Layer1 to Layer4) and make the file entries.
        @return None
        """
        # The tool is found once per import from the names and the first 8 kB of every file (already read, through the size limit); nothing matched is kept
        self.profile_result = prof_mod.detect_profile({e[0]: e[3] for e in self._pending})
        self.profile_choice = prof_mod.choose(self.profile_result, self.user_profile)
        found = detect_set([(e[0], e[3]) for e in self._pending], profile=self.profile_choice.key)
        self._heads = {e[0]: e[3] for e in self._pending}
        for name, size, sha, head, reader, limit_error in self._pending:
            fn = found[name]
            role, how = role_of(fn), _how(fn)
            by_content = _role_by_content(name, fn, head)
            if by_content:
                role, how = by_content
            f = SourceFile(name, size, sha, fn, role, how, reader)
            f.limit_error = f.error = limit_error
            if role == BOM and Path(name).suffix.lower() in WORKBOOK_SUFFIXES and not limit_error:
                f.error = "an Excel workbook (.xlsx, .xls) is not read; save the table as CSV"
            self.files.append(f)
        self._pending = []

    def _add_paths(self, paths):
        """!
        @brief Add the files of a list of paths (hidden files, images, documents and project files are left out).
        @param paths List of Path.
        @return None
        """
        skip = {".zip", ".png", ".jpg", ".jpeg", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb", ".kicad_pro", ".svg", ".html", ".htm", ".rar", ".7z", ".py"}
        for f in paths:
            if f.suffix.lower() == ".gbrjob" and f.is_file():
                try:
                    self._read_job(limits.read_text(f, 1_000_000))
                except (GerberError, OSError):
                    self.job = None
            if f.name.startswith(".") or f.suffix.lower() in skip or not f.is_file():
                continue
            size = f.stat().st_size
            limit = limits.max_file_bytes()
            with open(f, "rb") as fh:
                head = fh.read(HEAD_BYTES)
            sha = hashlib.sha256()
            if size > limit:
                # Listed, never read: the message says where the limit is set (a file above the limit is not skipped silently)
                sha.update(head + str(size).encode())
                err = f"above the limit of {limit / limits.MB:.0f} MB (Preferences, Gerber import)"
            else:
                err = ""
                with open(f, "rb") as fh:                      # Hashed in blocks: a layer can be tens of megabytes
                    for block in iter(lambda: fh.read(1 << 20), b""):
                        sha.update(block)
            self._pending.append((f.name, size, sha.hexdigest(), bom_mod.decode_head(head), lambda p=f: limits.read_text(p), err))
            self.paths[f.name] = f                                 # the file on the disk, so that a project package can store its original bytes

    def _add_archive(self, path):
        """!
        @brief Add the members of a ZIP archive, read in memory through the safe reader (nothing is written to disk).
        @param path Path of the ZIP.
        @return None
        @throws GerberError For an unsafe archive.
        """
        self._archive = GerberArchive(path)
        for name in self._archive.names():
            if name.lower().endswith(".gbrjob") and self._archive._infos[name].file_size < 1_000_000:
                try:
                    self._read_job(self._archive.read_text(name))
                except GerberError:
                    self.job = None
            if name.lower().endswith(("/", ".png", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb", ".zip", ".jpg", ".svg")):
                continue
            raw_head = self._archive.read_head_bytes(name)
            head = raw_head.decode("utf-8", "replace")             # as before for the digest of a large member
            info = self._archive._infos[name]
            # The hash of an archive member needs the whole member: read it once, bounded by the declared size (the archive reader checks the CRC)
            if info.file_size <= HASH_WHOLE_BYTES:
                digest = _sha256(self._archive.read_text(name).encode("utf-8", "replace"))
            else:
                # A very large member is hashed by its head, its tail and its size (reading it whole only to hash it would hold it in memory twice)
                tail = self._archive.read_text(name)[-HASH_EDGE_BYTES:]
                digest = _sha256((head + "\0" + tail + "\0" + str(info.file_size)).encode("utf-8", "replace"))
            self._pending.append((name, info.file_size, digest, bom_mod.decode_head(raw_head), lambda n=name: self._archive.read_text(n), ""))

    def _assign_inner_numbers(self):
        """!
        @brief Give distinct numbers to inner copper files that were detected without a number (several "inner" files from names such as `.G1 .G2`, or no index at all).
        @return None
        """
        inner = [f for f in self.files if f.role in INNER]
        by_number = {}
        for f in inner:
            by_number.setdefault(f.role, []).append(f)
        free = [r for r in INNER if r not in by_number]
        for role, group in by_number.items():
            if len(group) > 1:
                for f in sorted(group, key=lambda f: f.name)[1:]:      # The first keeps the number; the others take the next free ones
                    if free:
                        f.role = free.pop(0)

    def set_role(self, i: int, role: str):
        """!
        @brief Change the function of file i (the board is read again on the next `load`).
        @param i Index in `files`.
        @param role One of ROLES.
        @return None
        """
        f = self.files[i]
        f.role, f.use, f.error = role, role != IGNORE, f.limit_error
        f.user_role = True                                    # the user's assignment of a file is final: a change of profile never touches it
        self._board, self._parts_dirty, self._bom_key = None, True, None

    def take_stored_roles(self, settings: dict) -> bool:
        """!
        @brief Give the files of a re-import the functions the user chose by hand in the stored import, and leave out the files the user left out (matched by file name).
        @details The detection runs again on the new files and could give another answer; what the user decided is final (as in `set_role`). The board is read again by the caller.
        @param settings `ImportRecord.settings` of the stored import (keys `user_roles`, `not_used`).
        @return bool True when a file was changed.
        """
        roles = (settings or {}).get("user_roles") or {}
        out = set((settings or {}).get("not_used") or [])
        changed = False
        for i, f in enumerate(self.files):
            r = roles.get(f.name)
            if r in ROLES:
                if f.role != r or not f.user_role:
                    changed = changed or f.role != r
                    self.set_role(i, r)
            elif f.name in out and f.use:
                self.set_use(i, False)
                changed = True
        return changed

    @staticmethod
    def _step2_fields(p) -> tuple:
        """!
        @brief The fields of a part that the user edits in the parts table of step 2.
        @param p ImportPart.
        @return tuple (power W, heat-source tick, Tj max degC, role).
        """
        return (float(p.power), bool(p.edits.get("use")), float(p.edits.get("tj_max", 0.0) or 0.0), p.edits.get("role"))

    def take_stored_parts(self, stored: ImportRecord) -> int:
        """!
        @brief A re-import shows in step 2 the values the project already has (power, heat-source tick, Tj max, role) for the parts named by the files, so that what the table shows is
               what Replace and Update keep, and a value the user changes there is known as the user's (`step2_edits`).
        @details Review: the table of a re-import started at zero powers while the merge kept the stored ones, so a power typed or a part ticked in step 2 was silently dropped and the
                 re-import "changed nothing". Parts picked by hand or grouped by proximity are matched by position at the merge, not by name, and are not filled here.
        @param stored The stored ImportRecord, with the powers of the editor (the main window copies them in).
        @return int Number of parts filled.
        """
        by = {a.designator: a for a in getattr(stored, "parts", []) or [] if not parts_mod._positional(a)}
        self._stored_values = {}
        for p in self.parts():
            a = by.get(p.designator)
            if a is None or parts_mod._positional(p):
                continue
            p.power = float(a.power)
            p.edits["use"] = bool(a.edits.get("use")) and bool(p.polygon_mm)
            for k in ("tj_max", "role"):
                if k in a.edits:
                    p.edits[k] = copy.deepcopy(a.edits[k])
                else:
                    p.edits.pop(k, None)
            self._stored_values[p.designator] = self._step2_fields(p)
        return len(self._stored_values)

    def take_file_values(self) -> int:
        """!
        @brief For files that look like ANOTHER board: step 2 starts from the values of the files, and they become the reference against which a change in step 2 is the user's.
        @details Review: step 2 of another board skipped `take_stored_parts` and left `_stored_values` empty (or stale from an earlier set of files of the same window), so with
                 the box 'Carry the parts of the stored import over by designator' ticked a power typed in step 2 was dropped and the stored power kept (U1 typed 7 W read 3 W).
                 With the values of the files as the reference, a value changed in step 2 wins as on the same board.
        @return int Number of parts recorded.
        """
        self._stored_values = {p.designator: self._step2_fields(p) for p in self.parts() if not parts_mod._positional(p)}
        return len(self._stored_values)

    def step2_edits(self) -> dict:
        """!
        @brief The parts of a re-import whose step-2 fields the user changed from the stored values (`take_stored_parts`).
        @return dict designator -> ImportPart of the session.
        """
        return {p.designator: p for p in self.parts() if p.designator in self._stored_values and self._step2_fields(p) != self._stored_values[p.designator]}

    @staticmethod
    def _drop_kept_power(lines: list, typed) -> list:
        """!
        @brief Take "kept power X W" out of the merge lines of the parts whose power the user typed in step 2 (the line of step 2 says what they got).
        @param lines Text lines of the merge.
        @param typed Designators of `_apply_step2`.
        @return list of text lines.
        """
        return [re.sub(r", kept power [^,;]* W", "", c) if any(c.startswith(f"{d}: ") for d in typed) else c for c in lines]

    def _apply_step2(self, parts: list) -> tuple:
        """!
        @brief Give the merged parts the values the user typed in step 2 of the re-import (they win over the stored ones and over the editor).
        @param parts Merged ImportPart list; changed in place.
        @return tuple (set of designators, list of text lines).
        """
        edits, done, lines = self.step2_edits(), set(), []
        for q in parts:
            p = edits.get(q.designator)
            if p is None or q.from_file.get("orphan"):
                continue
            q.power = float(p.power)
            q.edits["use"] = bool(p.edits.get("use")) and bool(q.polygon_mm)
            for k in ("tj_max", "role"):
                if k in p.edits:
                    q.edits[k] = copy.deepcopy(p.edits[k])
            done.add(q.designator)
            lines.append(f"{q.designator}: took the values of step 2 ({q.power:g} W, " + ("heat source" if q.edits["use"] else "not heating") + ")")
        return done, lines

    def profile_line(self) -> tuple:
        """!
        @brief The CAD-tool line of step 1: text (plain), whether it needs a check, and the tooltip (public facts only, never text matched in a file).
        @details A result with only name evidence (low confidence) says "tool not recognised" instead of naming a program. A choice of the user is said so.
        @return tuple (text, check bool, tooltip str); ("", False, "") before a set is read.
        """
        r = self.profile_result
        if r is None:
            return "", False, ""
        ev = prof_mod.public_evidence(r)
        text = ev["line"]
        if r.confidence == "low":
            text = "Tool not recognised: only the file names hint at a program, generic rules are used"
        if self.profile_choice is not None and self.profile_choice.source == "user":
            text += f"  [your choice: {prof_mod.profile_name(self.profile_choice.key)}]" if self.profile_choice.key != "unknown" else "  [your choice: none, generic rules]"
        marks = ", ".join(f"{m} ({n} file{'s' if n != 1 else ''})" for m, n in ev["markers"]) or "none"
        tip = (f"The program that wrote the files, found from their headers and names. Markers: {marks}. It only gives better defaults for the file names; the X2 attributes, the "
               "Excellon header and your own choice of a function always win, and the bottom-side X sign of a placement file is never preset by it. "
               "Help us test your CAD tool: a sample of the files of another program makes its profile possible (see the user guide, Import Gerber board).")
        return text, bool(ev["check"] or r.confidence == "low"), tip

    def profile_keys(self) -> list:
        """!
        @brief The profiles the user can choose from: (key, name) pairs, "unknown" (generic rules) first.
        @return list of tuples.
        """
        return [(k, prof_mod.profile_name(k)) for k in prof_mod.profile_keys()]

    def set_profile(self, key):
        """!
        @brief The user chooses the CAD profile (None: back to the detection). Only the name rules of the files whose function the user did not choose are applied again.
        @param key Profile key of the table, or None.
        @return None
        @throws ValueError If the key is not a profile of the table.
        """
        if self.profile_result is None:
            return
        self.profile_choice = prof_mod.choose(self.profile_result, key)
        self.user_profile = key
        found = detect_set([(f.name, self._heads.get(f.name, "")) for f in self.files], profile=self.profile_choice.key)
        for f in self.files:
            if f.user_role:
                continue
            fn = found[f.name]
            role, how = role_of(fn), _how(fn)
            by_content = _role_by_content(f.name, fn, self._heads.get(f.name, ""))
            if by_content:
                role, how = by_content
            f.detected, f.role, f.how, f.use = fn, role, how, role in USED_BY_DEFAULT
        self._assign_inner_numbers()
        self._board, self._parts_dirty, self._bom_key = None, True, None

    def set_use(self, i: int, use: bool):
        """!
        @brief Use or leave out file i.
        @param i Index in `files`.
        @param use True to read it.
        @return None
        """
        self.files[i].use = bool(use)
        self._board, self._parts_dirty, self._bom_key = None, True, None

    def used(self, *roles) -> List[SourceFile]:
        """!
        @brief The files in use with a role (all roles when none is given).
        @param roles Roles to select.
        @return list of SourceFile
        """
        return [f for f in self.files if f.use and f.role != IGNORE and (not roles or f.role in roles)]

    # ------------------------------------------------------------------------------------------------------------------------------------ checks
    def problems(self) -> List[str]:
        """!
        @brief What stops the import: no files, two files for one function, no copper, a copper or outline file the reader refused.
        @return list of text lines; empty when step 1 is complete.
        """
        if not self.files:
            return ["No folder, ZIP or files chosen"]
        out, seen = [], {}
        for f in self.used():
            if f.role in UNIQUE:
                if f.role in seen:
                    out.append(f"Two files claim '{f.role}': {seen[f.role]} and {f.name}")
                seen[f.role] = f.name
            if f.error and f.role in COPPER + PASTE:
                out.append(f"{f.name} cannot be read: {f.error}")
        if not self.used(*COPPER):
            out.append("No copper layer is selected")
        inner = sorted(int(r.split()[-1]) for r in {f.role for f in self.used(*INNER)})
        if inner and inner != list(range(1, len(inner) + 1)):
            out.append("The inner copper layers are not numbered 1, 2, 3 ... without a gap: change a function in the table")
        if self._board_error:
            out.append(self._board_error)
        return out

    def notes(self) -> List[str]:
        """!
        @brief What the import goes on without (not blocking): no outline, no drills, an outline that is not closed, a drill file the reader refused.
        @return list of text lines.
        """
        out = []
        if not self.used(OUTLINE):
            out.append("No board outline: the box of the copper is used")
        if not self.used(PLATED, NONPLATED):
            out.append("No drill file: no vias are imported")
        for f in self.used():
            if f.error and f.role not in COPPER + PASTE:
                out.append(f"{f.name} is not used: {f.error}")
        n = len(self.used(*COPPER))
        if n > 1 and not (self.used(COPPER_TOP) and self.used(COPPER_BOTTOM)):
            out.append("The set lacks the top or the bottom copper layer")
        for f in self.used():
            out += [f"{f.name}: {w}" for w in f.warnings]                  # tolerances the reader applied (a macro name, a deprecated command)
            if f.error and f.limit_error and f.role not in COPPER + PASTE:
                continue
        if self.record is not None:
            out += [w for w in self.record.warnings if w not in out]       # warnings of the last import (no outline, slots, unplated holes, sample spacing)
        low = [f.name for f in self.used() if f.detected.confidence == "low" and f.detected.kind != "unknown" and f.role == role_of(f.detected)]
        if low:
            out.append("The function of " + ", ".join(low) + " was guessed from the file name alone: check it in the list")
        return out

    def complete(self) -> bool:
        """!
        @brief Step 1 is complete: the problems list is empty and the board can be read.
        @return bool
        """
        return not self.problems()

    # ------------------------------------------------------------------------------------------------------------------------------------ board
    def layers(self) -> List[LayerInfo]:
        """!
        @brief The copper layers in use in stack order (top, inner 1.., bottom).
        @return list of LayerInfo
        """
        files = sorted(self.used(*COPPER), key=lambda f: COPPER.index(f.role) if f.role != COPPER_BOTTOM else 99)
        return [LayerInfo(f.role, f.name, k + 1) for k, f in enumerate(files)]

    def stackup(self) -> dict:
        """!
        @brief The proposed stack-up for the number of copper layers (the typical stack-up of the program, not a fabricator table).
        @return dict of `model.stackup_template`, or None without copper.
        """
        n = len(self.layers())
        return stackup_template(n) if n else None

    def stackup_text(self) -> str:
        """!
        @brief One line for the stack-up group.
        @return str
        """
        st = self.stackup()
        if st is None:
            return "No copper layers"
        return f"{len(self.layers())} copper layers: {st['name']}"

    def board(self) -> Optional[BoardData]:
        """!
        @brief The board read by the last `load`.
        @return BoardData, or None before a successful load.
        """
        return self._board

    def load(self) -> Optional[BoardData]:
        """!
        @brief Read the files in use: the copper layers at the preview pixel, the outline and the drills.
        @details A file the reader refuses is marked with its error (a copper file stops the import, the others are left out with a note). The window of the preview is the
                 outline box, else the box of the copper files.
        @return BoardData, or None when step 1 is not complete.
        """
        self._board, self._board_error = None, ""
        for f in self.files:
            f.error = f.limit_error
        copper = [(f, self._layer(f)) for f in sorted(self.used(*COPPER), key=lambda f: COPPER.index(f.role) if f.role != COPPER_BOTTOM else 99)]
        # Several used files may fail: all are marked before the problems list is read
        for f in self.used(*PASTE):
            self._layer(f)
        if self.problems() or not copper:
            return None
        outline_polys, area, boxes = [], None, []
        self._outline = None
        for f in self.used(OUTLINE):
            try:
                out = read_outline(f.text(), f.name)
                self._outline = out
                outline_polys = [(p.outer, p.holes) for p in out.polygons]
                area = out.area_mm2
                boxes.append(out.bbox)
            except (GerberError, OSError) as exc:
                f.error = str(exc)                             # Not closed: the box of the copper is used (a note)
        if not boxes:
            boxes = [lay.bbox() for _, lay in copper if lay is not None and lay.bbox()]
        if not boxes:
            self._board_error = "The copper files draw nothing: there is no board to show"
            return None
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        w, h = box[2] - box[0], box[3] - box[1]
        pix = max(PREVIEW_PIXEL_MIN_MM, max(w, h) / PREVIEW_PIXELS)
        win = window_of(box)
        layers, thin = [], []
        for f, lay in copper:
            key = (f.sha256, tuple(win), pix)
            if key not in self._raster_cache:
                try:
                    cov = rasterize(lay, win, pix, supersample=2)
                except GerberError as exc:
                    f.error = str(exc)
                    self._board_error = f"{f.name} cannot be drawn: {exc}"
                    return None
                self._raster_cache[key] = (cov, lay.thinnest_feature_mm())
            cov, t = self._raster_cache[key]
            layers.append((f.role, f.name, cov))
            if t:
                thin.append(t)
        holes = []
        for f in self.used(PLATED, NONPLATED):
            try:
                drill = read_drill(f.text(), f.name)
            except (GerberError, OSError) as exc:
                f.error = str(exc)
                continue
            for hole in drill.holes:
                plated = hole.plated if hole.plated is not None else (drill.plated if drill.plated is not None else f.role == PLATED)
                holes.append(Hole(hole.x, hole.y, hole.diameter, bool(plated)))
        self._board = BoardData(box, w, h, pix, layers, outline_polys, area, holes, min(thin) if thin else None)
        return self._board

    def _layer(self, f: SourceFile):
        """!
        @brief Parse a Gerber file once (cached by hash); a refusal is written in the file's error and None is returned.
        @param f SourceFile.
        @return Layer or None.
        """
        if f.sha256 not in self._layer_cache:
            try:
                self._layer_cache[f.sha256] = parse_layer(f.text(), f.name)
            except (GerberError, OSError) as exc:
                f.error = str(exc)
                return None
        f.warnings = list(getattr(self._layer_cache[f.sha256], "warnings", []))
        return self._layer_cache[f.sha256]

    def vias(self, max_mm: float = None) -> tuple:
        """!
        @brief The plated holes split into vias (up to `max_mm`) and component holes, and the count of non-plated holes.
        @param max_mm Largest diameter of a plated hole that is a via (mm); None: the session's.
        @return tuple (vias, component holes, non-plated holes) as counts.
        """
        max_mm = self.via_max_mm if max_mm is None else max_mm
        b = self._board
        if b is None:
            return 0, 0, 0
        plated = [h for h in b.holes if h.plated]
        n = sum(1 for h in plated if h.diameter <= max_mm)
        return n, len(plated) - n, len(b.holes) - len(plated)

    # ------------------------------------------------------------------------------------------------------------------------------------ job file
    def _read_job(self, text):
        """!
        @brief Read the Gerber job file (`.gbrjob`): the layer count and the board thickness it declares (a damaged file is ignored).
        @param text Content of the file.
        @return None
        """
        try:
            d = json.loads(text)
            spec = d.get("GeneralSpecs", {})
            self.job = {"layers": int(spec["LayerNumber"]) if "LayerNumber" in spec else None,
                        "thickness_mm": float(spec["BoardThickness"]) if "BoardThickness" in spec else None}
        except (ValueError, TypeError, AttributeError, KeyError):
            self.job = None

    def job_warnings(self) -> List[str]:
        """!
        @brief Where the job file and the file list disagree (layer count, board thickness against the typical stack-up).
        @return list of text lines (empty without a job file or when they agree).
        """
        out = []
        if not self.job:
            return out
        n = len(self.layers())
        if self.job.get("layers") and n and self.job["layers"] != n:
            out.append(f"The job file says {self.job['layers']} copper layers, the file list has {n}: check the functions in step 1")
        t = self.job.get("thickness_mm")
        st = self.stackup()
        if t and st and abs(st["total_thickness_um"] / 1000.0 - t) > 0.1 * t:
            out.append(f"The job file says a board thickness of {t:g} mm, the typical stack-up for {n} layers is {st['total_thickness_um'] / 1000.0:g} mm: the job thickness is used")
        return out

    # ------------------------------------------------------------------------------------------------------------------------------------ parts (step 2)
    def parts_ready(self) -> bool:
        """!
        @brief Whether the parts of the current files have been built.
        @return bool
        """
        return not self._parts_dirty

    def build_parts(self):
        """!
        @brief Build the parts from the paste layers, the placement file and the X3 component layers in use, keeping what the user entered for parts that still exist.
        @details The frame check offset is applied when the user accepted it. A placement or component file the reader refuses is marked in its `error` and left out.
                 The new parts are merged with the old ones by `parts.merge_parts` (power, edits, a shape the user chose, parts picked by hand by position; a part that left the files
                 becomes an orphan: kept, not heating).
        @return None
        """
        paste = {}
        for f in self.used(*PASTE):
            lay = self._layer(f)
            if lay is not None:
                paste["top" if f.role == PASTE[0] else "bottom"] = lay
        placement, comps, pnotes = None, [], []
        for f in self.used(PLACEMENT):
            pinfo = {}
            try:
                placement = parts_mod.parse_placement(f.text(), f.name, pinfo)
                if pinfo.get("preamble_lines"):
                    # Said in plain words so that nobody wonders why the first rows of the file are not parts
                    pnotes.append(f"{f.name}: the header row of the placement file is on line {pinfo['header_line']}; the {pinfo['preamble_lines']} lines of text above it "
                                  f"(title, date, units) were skipped and the unit is {pinfo['unit']}")
            except ValueError as exc:
                f.error = str(exc)
        for f in self.used(COMPONENT):
            try:
                comps += comp_mod.parse_components(f.text(), f.name)
            except (GerberError, ValueError) as exc:
                f.error = str(exc)
        try:
            res = parts_mod.build_parts(paste, placement, comps or None, shape="auto", offset=self.offset if self.offset_answer == "accepted" else (0.0, 0.0))
        except GerberError as exc:
            # A paste layer with a negative image or another refusal: the parts are left empty and the file says why
            for f in self.used(*PASTE):
                f.error = str(exc)
            res = parts_mod.PartsResult()
            res.info = {"warnings": [str(exc)], "frame": None, "counts": {}}
        res.info.setdefault("warnings", []).extend(pnotes)
        res.info["placement_read"] = placement is not None
        new = res.parts + res.listed
        old = self._parts + self._listed
        merged = parts_mod.merge_parts(old, new, res.shapes, openings=res.openings).parts if old else new
        for p in merged:
            p.edits.setdefault("use", False)
        self.apply_bom(merged)                                # what the BOM says about each part (nothing is written without a BOM file)
        self._res = res
        self._parts = [p for p in merged if p.polygon_mm and p.from_file.get("heat_source", True) or p.from_file.get("orphan")]
        self._listed = [p for p in merged if p not in self._parts]
        self._unmatched = list(res.unmatched)
        self._owner_cache = None
        self._parts_dirty = False

    # ------------------------------------------------------------------------------------------------------------------------------------ BOM
    def _bom_bytes(self, f: SourceFile) -> bytes:
        """!
        @brief The original bytes of a BOM file (a text decoder would spoil UTF-16), never more than the size limit.
        @param f SourceFile of the role BOM.
        @return bytes
        @throws GerberError If the file is above the limit or cannot be read.
        """
        if f.limit_error:
            raise GerberError(f.limit_error)
        if f.name in self.paths:
            limit = limits.max_file_bytes()
            limits.check_path(self.paths[f.name], limit)
            with open(self.paths[f.name], "rb") as fh:
                data = fh.read(limit + 1)
            limits.check_size(len(data), f.name, limit)
            return data
        if self._archive is not None:
            return self._archive.read_bytes(f.name)
        raise GerberError(f"{f.name}: the file is no longer available")

    def bom_set(self):
        """!
        @brief The BOM files in use read and merged by designator (cached until the files, their functions or their ticks change).
        @details A file the reader refuses (an Excel workbook, a table without a header, a limit) gets its message in `error` and is left out; the others are still merged.
        @return bom.BomSet, or None when no BOM file is in use or none could be read.
        """
        files = self.used(BOM)
        key = tuple(f.sha256 for f in files)
        if self._bom_key == key and (self._bom is not None or not files):
            return self._bom
        tables = []
        for f in files:
            try:
                tables.append(bom_mod.read_bom(self._bom_bytes(f), f.name))
                f.error = f.limit_error
            except (GerberError, ValueError, OSError) as exc:
                f.error = str(exc)
        self._bom = bom_mod.merge(tables) if tables else None
        self._bom_key = key
        return self._bom

    def bom_line(self) -> tuple:
        """!
        @brief The one-line summary of the BOM for step 1 (empty without a BOM file).
        @return tuple (text, needs a check bool, tooltip).
        """
        files = self.used(BOM)
        if not files:
            return "", False, ""
        bs = self.bom_set()
        if bs is None:
            return "BOM: no file could be read (see the list)", True, "A BOM that cannot be read is left out; the message is in the file list. An Excel workbook is not read: save it as CSV."
        nf = sum(1 for r in bs.rows.values() if r.not_fitted)
        text = f"BOM: {len(bs.rows)} designators from {len(bs.files)} file(s)"
        if bs.sections > len(bs.files):
            text += f", {bs.sections} sections"
        text += f", {nf} marked not fitted"
        text += f"; assembly variant: {', '.join(bs.variants)}" if bs.variants else "; the file names no assembly variant"
        bad = [f for f in files if f.error]
        if bad:
            text += f"; {len(bad)} file(s) not read"
        tip = ("The bill of materials read from its columns. It proposes a role for each part (a guess from the designator, the footprint and the value) and marks the parts it says are "
               "not fitted (DNP, DNI, NF, NM, DNF, or a Fitted column with No). It never sets a power and never moves a part. If your CAD program writes several assembly variants, "
               "this is the one in the file you chose. " + " ".join(bs.warnings[:3]))
        return text, bool(bad or bs.warnings), tip

    def apply_bom(self, parts: list) -> None:
        """!
        @brief Write what the BOM says about each part into `from_file["bom"]`, or remove it when there is no BOM; never touches a power, a position or an edit.
        @details The key is written only for a part the BOM names (role guessed from the names, `dnp`, and the part number, supplier number and quantity when the BOM has them), so a project
                 imported without a BOM is byte-identical to one written before this feature. Parts made up by the import (`H<n>`, `P<n>`: grouping by hand or by proximity) and orphans
                 are skipped: their names are not designators.
        @param parts ImportPart list; changed in place.
        @return None
        """
        bs = self.bom_set()
        for p in parts:
            p.from_file.pop("bom", None)
            if bs is None or p.from_file.get("orphan") or parts_mod._positional(p):
                continue
            row = bs.get(p.designator)
            if row is None:
                continue
            guess = bom_mod.classify(p.designator, row.value or str(p.from_file.get("value", "")), row.package or p.footprint or str(p.from_file.get("package", "")), row.description)
            info = {"role": bom_mod.proposal(guess), "dnp": bool(row.not_fitted)}
            for key in ("mpn", "lcsc", "qty"):
                if getattr(row, key):
                    info[key] = getattr(row, key)[:80]
            p.from_file["bom"] = info

    def bom_match(self) -> Optional[dict]:
        """!
        @brief How the BOM and the parts fit: the parts the BOM does not name, the designators of the BOM that no part has, the parts it marks not fitted.
        @return dict (`in_bom` count, `not_in_bom`, `bom_only`, `not_fitted` lists of designators), or None without a BOM.
        """
        bs = self.bom_set()
        if bs is None:
            return None
        named = [p for p in self.parts() if not p.from_file.get("orphan") and not parts_mod._positional(p)]
        have = {p.designator.upper() for p in named}
        missing = sorted(p.designator for p in named if "bom" not in p.from_file)
        only = sorted(r.ref for r in bs.rows.values() if r.ref.upper() not in have)
        return {"in_bom": len(named) - len(missing), "not_in_bom": missing, "bom_only": only, "not_fitted": sorted(p.designator for p in named if p.from_file.get("bom", {}).get("dnp"))}

    def bom_proposal_text(self, p) -> str:
        """!
        @brief The text of the BOM column of step 2 for a part.
        @param p ImportPart.
        @return str "not fitted", "<role> (guess)", "unknown", "not in BOM", or "" without a BOM.
        """
        bs = self.bom_set()
        if bs is None or p.from_file.get("orphan") or parts_mod._positional(p):
            return ""
        b = p.from_file.get("bom")
        if b is None:
            return "not in BOM"
        if b.get("dnp"):
            return "not fitted"
        role = b.get("role", "unknown")
        return "unknown" if role == "unknown" else f"{bom_mod.ROLE_TEXT.get(role, role)} (guess)"

    def use_bom_roles(self) -> int:
        """!
        @brief Set the Role of the parts to the role the BOM guessed (component or source), for the parts whose Role the user has not set; "no heat source" and unknown change nothing.
        @details This is the user's command ("Use the BOM roles"), never applied on its own. A role the user chose by hand (`edits["role"]` already present) stays.
        @return int Number of parts changed.
        """
        n = 0
        for p in self.parts():
            role = (p.from_file.get("bom") or {}).get("role")
            if role in ("component", "source") and "role" not in p.edits:
                p.edits["role"] = role.capitalize()
                n += 1
        return n

    @staticmethod
    def bom_changes(old_parts: list, new_parts: list) -> list:
        """!
        @brief The lines of a re-import about parts whose BOM role or not-fitted mark changed.
        @param old_parts ImportPart list before.
        @param new_parts ImportPart list after.
        @return list of text lines.
        """
        old = {p.designator: (p.from_file.get("bom") or {}) for p in old_parts}
        out = []
        for p in new_parts:
            a, b = old.get(p.designator), p.from_file.get("bom") or {}
            if not a or not b:
                continue
            if a.get("role") != b.get("role"):
                out.append(f"{p.designator}: BOM role {a.get('role')} -> {b.get('role')} (your Role is kept)")
            if bool(a.get("dnp")) != bool(b.get("dnp")):
                out.append(f"{p.designator}: BOM now says {'not fitted' if b.get('dnp') else 'fitted'}")
        return out


    def _ensure_parts(self):
        """!
        @brief Build the parts when the files changed since the last build.
        @return None
        """
        if self._parts_dirty:
            self.build_parts()

    def parts(self) -> list:
        """!
        @brief The parts table: the candidates (a polygon), the parts picked by hand and the orphans, then the parts that are only listed.
        @return list of model.ImportPart; the user's edits are `edits["use"]`, `edits["tj_max"]`, `edits["role"]` and `power`.
        """
        self._ensure_parts()
        return self._parts + self._listed

    def part(self, designator: str):
        """!
        @brief A part by designator.
        @param designator Designator.
        @return ImportPart or None.
        """
        return next((p for p in self.parts() if p.designator == designator), None)

    def unmatched(self) -> list:
        """!
        @brief The paste openings no file names (red in the preview; a click turns one into a part).
        @return list of parts.Opening.
        """
        self._ensure_parts()
        return self._unmatched

    def openings(self) -> list:
        """!
        @brief Every paste opening read.
        @return list of parts.Opening.
        """
        self._ensure_parts()
        return self._res.openings if self._res else []

    def parts_info(self) -> dict:
        """!
        @brief What the build found on the way: the counts by source, the frame check, the bottom convention and its warnings.
        @return dict (`counts`, `frame`, `warnings`, `convention`, `x3_vs_placement`).
        """
        self._ensure_parts()
        return self._res.info if self._res else {"counts": {}, "frame": None, "warnings": []}

    def is_orphan(self, p) -> bool:
        """!
        @brief Whether a part was kept after it left the files.
        @param p ImportPart.
        @return bool
        """
        return bool(p.from_file.get("orphan"))

    def is_source(self, p) -> bool:
        """!
        @brief Whether a part is a heat source now: ticked, with a polygon, not an orphan.
        @param p ImportPart.
        @return bool
        """
        return bool(p.edits.get("use")) and bool(p.polygon_mm) and not self.is_orphan(p)

    def source_label(self, p) -> str:
        """!
        @brief The text of the Source column of the parts table.
        @param p ImportPart.
        @return str
        """
        if self.is_orphan(p):
            return "orphan (not in the files)"
        return {"x3": "X3 component layer", "to.c+placement": "paste TO.C + placement", "placement by position": "by position (approx.)",
                "paste only": "paste only", "placement only": "placement only"}.get(p.from_file.get("source", ""), p.from_file.get("source", "") or "-")

    SOURCE_EXPLANATION = {
        "x3": "Found in the X3 component layer of the Gerber files: the designator, the outline and the pins come from the CAD program.",
        "to.c+placement": "The paste file names this part (the TO.C attribute) and the placement file gives its package and position.",
        "placement by position": "The paste file names no parts, so each opening was given to the part of the placement file whose pad outline contains it. The outline is rebuilt from the package "
                                 "name and the part's rotation and grown by 0.3 mm. Usually right; look at the part in the preview before you give it a power.",
        "paste only": "A paste opening that no file names: a part made from the opening alone (named H1, H2, ...).",
        "placement only": "A part of the placement file with no paste opening (a connector, a through-hole part): listed, with no area to heat.",
    }

    def source_explanation(self, p) -> str:
        """!
        @brief The tooltip of the Source column: what the way the part was found means and what to check.
        @param p ImportPart.
        @return str
        """
        if self.is_orphan(p):
            return "The part is no longer in the files of the re-import: it is kept with its power and does not heat the board."
        return self.SOURCE_EXPLANATION.get(p.from_file.get("source", ""), self.source_label(p))

    def set_part(self, designator: str, power: float = None, tj_max: float = None, role: str = None, use: bool = None):
        """!
        @brief Edit a part: its power (W), junction limit (degC), role ("Component" or "Source") or heat-source tick.
        @details A power above zero ticks the part as a heat source (as the editor does for a heater with a power).
        @param designator Designator.
        @param power Power in W, or None.
        @param tj_max Junction temperature limit in degC (0 = none), or None.
        @param role "Component" or "Source", or None.
        @param use True or False to tick, or None.
        @return None
        """
        p = self.part(designator)
        if p is None:
            return
        if power is not None:
            p.power = float(power)
            if power > 0 and p.polygon_mm and use is None:
                p.edits["use"] = True
        if tj_max is not None:
            p.edits["tj_max"] = float(tj_max)
        if role is not None:
            p.edits["role"] = role
        if use is not None:
            p.edits["use"] = bool(use) and bool(p.polygon_mm)

    def _openings_of(self, p) -> list:
        """!
        @brief The openings that belong to a part.
        @param p ImportPart.
        @return list of Opening (by `TO.C` designator, else by the centre inside the polygon).
        """
        return [self.openings()[i] for i in self._owners().get(p.designator, [])]

    def _owners(self) -> dict:
        """!
        @brief Map designator -> indices of its openings (cached per build).
        @return dict
        """
        if self._owner_cache is None:
            out = {}
            ops = self.openings()
            # The region of a part is the hull of all its openings (`outer_mm` when the heat source is only an exposed pad), else its polygon
            hulls = [(p, comp_mod.hull([tuple(q) for q in (p.from_file.get("outer_mm") or p.polygon_mm)])) for p in self._parts if len(p.polygon_mm) >= 3]
            names = {p.designator for p in self._parts + self._listed}
            for i, o in enumerate(ops):
                owner = o.ref if o.ref and o.ref in names else None
                if owner is None:
                    for p, h in hulls:
                        if p.side == o.side and parts_mod._point_to_hull(h, o.x, o.y) <= 1e-6:
                            owner = p.designator
                            break
                if owner is not None:
                    out.setdefault(owner, []).append(i)
            self._owner_cache = out
        return self._owner_cache

    def owned_indices(self) -> set:
        """!
        @brief The indices of the openings that belong to a part (the others are red).
        @return set of int.
        """
        return {i for idx in self._owners().values() for i in idx}

    def owner_of_opening(self, i: int):
        """!
        @brief The part an opening belongs to.
        @param i Index in `openings()`.
        @return designator or None (the opening is red).
        """
        for des, idx in self._owners().items():
            if i in idx:
                return des
        return None

    def shapes_of(self, p) -> list:
        """!
        @brief The shapes the user can choose for a part: those its openings give ("hull", "box", and "exposed" when the part has an exposed pad or a tab).
        @details The 'largest opening' choice is not offered any more (several equal pads: +22 to +299 % of the hottest point in the study); a single tab is the exposed pad.
        @param p ImportPart.
        @return list of str (empty when the part has no opening).
        """
        ops = self._openings_of(p)
        if not ops:
            return []
        return ["hull", "box"] + (["exposed"] if parts_mod.dominant_group(ops) else [])

    def default_shape(self, p) -> str:
        """!
        @brief The shape the program proposes for a part: "exposed" for a part with an exposed pad or a tab, else "hull".
        @param p ImportPart.
        @return str ("hull" when the part has no opening of its own).
        """
        return parts_mod.default_shape_kind(self._openings_of(p))

    def shape_note(self, p) -> str:
        """!
        @brief Text for the table: which heat-source shape the part has and, for an exposed pad, why.
        @param p ImportPart.
        @return str (empty for a part with no heat-source polygon).
        """
        if not p.polygon_mm:
            return ""
        ops = self._openings_of(p)
        auto = self.default_shape(p) if ops else "hull"
        label = {"exposed": "exposed pad", "hull": "convex hull", "box": "bounding box", "largest": "largest opening (older project)", "outline": "part outline"}.get(p.shape, p.shape)
        who = "chosen by you" if p.edits.get("shape_user") else "proposed" if p.shape == auto else "from the file"
        return f"{label} ({who})"

    def part_hull(self, p):
        """!
        @brief The convex hull of the openings of a part whose heat source is not that hull (the exposed pad or the box): the dashed outline of where the part is, whether or not it is ticked.
        @param p ImportPart.
        @return list of (x, y) in mm, or None when the heat source is the whole hull or the part has no opening.
        """
        if p is None or p.shape == "hull":
            return None
        ops = self._openings_of(p)
        return parts_mod.shape_polygon(ops, "hull") if ops else (p.from_file.get("outer_mm") or None)

    def set_shape(self, designator: str, kind: str):
        """!
        @brief Choose the heat-source shape of a part from its openings (always allowed; the choice is remembered as the user's).
        @param designator Designator.
        @param kind "hull", "box" or "exposed"; the retired "largest" (and an unknown name) is taken as the proposed shape.
        @return None
        """
        p = self.part(designator)
        ops = self._openings_of(p) if p else []
        if not ops:
            return
        if kind not in ("hull", "box", "exposed"):
            kind = self.default_shape(p)
        # The region of the part (which openings are its own) must not shrink with the shape: keep the hull of all its openings beside a heat source that is smaller
        parts_mod._set_outer(p.from_file, ops)
        p.shape = kind
        p.polygon_mm = [list(map(float, q)) for q in parts_mod.shape_polygon(ops, kind)]
        # The choice is the user's when it differs from what the rule proposes (a hull on a QFN is a choice, a hull on a SOIC is the default)
        p.edits["shape_user"] = kind != self.default_shape(p)
        self._owner_cache = None

    def click(self, x: float, y: float, add: bool = False, selected: str = None, side: str = None):
        """!
        @brief A click on the preview at a point of the Gerber frame: select the part of an opening, create a heat source from a red opening, or (`add`) add it to the selected part.
        @details The opening under the click is the largest one within 0.1 mm (`parts.opening_at`); a new part is made by `parts.part_from_openings(..., grouping="hand")` and named H<n>; the
                 re-import matches it by position.
        @param x X in mm (Gerber frame).
        @param y Y in mm.
        @param add True when the Ctrl key was held: add a red opening to the selected part.
        @param selected Designator of the selected part, or None.
        @param side "top" or "bottom": the side shown, or None for both.
        @return designator of the part now selected, or None when nothing was under the click.
        """
        self._ensure_parts()
        i = parts_mod.opening_at(self.openings(), x, y, side)
        if i is None:
            return None
        owner = self.owner_of_opening(i)
        if owner is not None:
            return owner
        o = self.openings()[i]
        sel = self.part(selected) if selected else None
        if add and sel is not None and sel.polygon_mm:
            ops = self._openings_of(sel) + [o]
            # Review: a retired 'largest' (or an X3 outline, which the openings cannot redraw) becomes the proposed shape of the grown part, and the shape name follows the polygon
            # (the first version kept the name 'largest' over a hull polygon)
            if sel.shape in ("hull", "box", "exposed"):
                kind = sel.shape
            else:
                kind = parts_mod.default_shape_kind(ops)
                sel.edits["shape_user"] = False
            sel.shape = kind
            ff = dict(sel.from_file)
            ff["n_openings"] = len(ops)
            sel.polygon_mm = [list(map(float, q)) for q in parts_mod.shape_polygon(ops, kind)]
            parts_mod._set_outer(ff, ops)
            sel.from_file = ff
            self._unmatched = [u for u in self._unmatched if u is not o]
            self._owner_cache = None
            return sel.designator
        # The first free H<n>: a board may have parts named H2, H3 (mounting holes), so a count of the H names could give a name that is taken
        taken = {q.designator for q in self.parts()}
        n = 1
        while f"H{n}" in taken:
            n += 1
        q = parts_mod.part_from_openings(f"H{n}", [o], "auto", "paste only", side=o.side, grouping="hand")
        q.edits["use"], q.edits["role"] = True, "Source"
        self._parts.append(q)
        self._unmatched = [u for u in self._unmatched if u is not o]
        self._owner_cache = None
        return q.designator

    def frame_proposal(self) -> Optional[dict]:
        """!
        @brief The frame check's answer: an offset of the placement file, or "the files do not fit".
        @return dict `propose` (offset dx, dy in mm), `misfit`, `given` and `best` shares, or None when there is nothing to say.
        """
        fr = self.parts_info().get("frame")
        if fr and (fr.get("propose") or fr.get("misfit")):
            return fr
        return None

    def answer_frame(self, accept: bool):
        """!
        @brief The user's answer to the proposed offset: accept it (the parts are built again with the placement moved) or reject it (the file stays as it is).
        @param accept True to accept.
        @return None
        """
        fr = self.parts_info().get("frame") or {}
        if accept and fr.get("propose"):
            self.offset, self.offset_answer = (fr["dx"], fr["dy"]), "accepted"
            self._parts_dirty = True
        elif not accept:
            self.offset, self.offset_answer = (0.0, 0.0), "rejected"
            self._parts_dirty = True

    def heat_sources(self) -> list:
        """!
        @brief The parts that are heat sources (ticked, with a polygon, not orphans).
        @return list of ImportPart.
        """
        return [p for p in self.parts() if self.is_source(p)]

    def parts_warnings(self) -> List[str]:
        """!
        @brief Warnings of the Parts step: the frame check, the X3 comparison with the placement file, duplicates, parts by position only, files the reader refused.
        @return list of text lines.
        """
        info = self.parts_info()
        out = list(info.get("warnings", []))
        fr = info.get("frame")
        if fr and fr.get("propose") and self.offset_answer != "accepted":
            out.append(f"The origin of the placement file differs from the Gerber files: moving its parts by {fr['dx']:+.2f}, {fr['dy']:+.2f} mm would put "
                       f"{fr['best'] * 100:.0f} % of the parts on their openings instead of {fr['given'] * 100:.0f} %")
        if fr and fr.get("misfit"):
            out.append("The placement file and the Gerber files do not fit (another origin beyond 10 mm, a rotation, a mirror or a unit): the parts matched by position are not reliable")
        # Only when a placement file was actually read: a refused file (its reason is in the notes of the files) matched nothing by position
        if info.get("placement_read") and self.used(PLACEMENT) and self.used(*PASTE) and self.openings() and not any(o.ref for o in self.openings()) and not self.used(COMPONENT):
            n = sum(1 for p in self.parts() if p.from_file.get("source") == "placement by position")
            out.append(f"The paste layer names no parts, so {n} parts were matched to the placement file by position: each opening went to the part whose pad outline (from its package name, "
                       f"grown by 0.3 mm) contains it. Usually right; check in the preview that the parts you give a power sit on their own pads")
        x3 = info.get("x3_vs_placement")
        if x3 and (x3.get("only_x3") or x3.get("only_placement") or x3.get("moved")):
            out.append(f"The X3 layer and the placement file differ: {len(x3['only_x3'])} parts only in the X3 layer, {len(x3['only_placement'])} only in the placement file, {len(x3['moved'])} moved")
        return out

    # ------------------------------------------------------------------------------------------------------------------------------------ model (step 3)
    def thinnest_mm(self) -> Optional[float]:
        """!
        @brief The thinnest line of the copper files in use.
        @return float mm or None.
        """
        b = self._board
        return b.thinnest_mm if b else None

    def auto_pixel(self, cell_mm: Optional[float] = None) -> float:
        """!
        @brief The automatic pixel of the masks: `min(m * w / 4, cell / 10)` with the supersampling m = 4 and the thinnest feature w (the rule of `copper.import_copper`).
        @param cell_mm Cell in mm (None: the session's).
        @return float mm.
        """
        cell = cell_mm or self.cell_mm
        w = self.thinnest_mm()
        return min(w, cell / 10.0) if w else cell / 10.0

    def auto_cell(self) -> float:
        """!
        @brief The automatic cell, by the program's rule (`api.suggest_cell_mm`): the smallest heat source resolved by about four cells, imported copper capped at 1 mm, enlarged by the memory guard when it must.
        @details The note for the user (`copper.auto_cell_note`) is kept in `auto_note` (empty when the cell is within the cap).
        @return float mm.
        """
        from ..api import suggest_cell_mm
        import numpy as np
        b = self._board
        self.auto_note = ""
        if b is None:
            return 1.0
        prob = Problem.new(b.width, b.height, layers=max(2, len(b.copper)))
        # A one-pixel mask per layer makes the board "imported" for the rule (the cap and its note) without drawing anything
        prob.imported = copper_mod.imported_from_rasters([np.zeros((1, 1), np.uint8)] * max(1, len(b.copper)), max(b.width, b.height), self.mapping)
        box = b.box
        for p in self.heat_sources():
            prob.add_heater(1, p.power, polygon=[[x - box[0], y - box[1]] for x, y in p.polygon_mm], name=p.designator)
        cell = float(suggest_cell_mm(prob, models=("fvm",)))
        self.auto_note = copper_mod.auto_cell_note(prob, cell)
        return cell

    def effective_pixel(self) -> float:
        """!
        @brief The pixel in use: the user's or the automatic one.
        @return float mm.
        """
        return self.pixel_mm if self.pixel_mm else self.auto_pixel()

    def memory_verdict(self, cell_mm: Optional[float] = None, pixel_mm: Optional[float] = None) -> Optional[dict]:
        """!
        @brief The memory guard's verdict for the model grid and for the import of the masks.
        @details `memory.check` on a board of the outline box (the FVM law) and `memory.check_import` (the masks, the draw and the face construction), both before anything is drawn.
        @param cell_mm Solver cell (mm); None: the session's.
        @param pixel_mm Pixel of the masks (mm); None: the one in use.
        @return dict `fvm` (memory.Verdict), `import_peak` (bytes or None), `import_error` (text, "" when it fits), `rows`, `cols`; None before the board is read.
        """
        b = self._board
        if b is None:
            return None
        cell = cell_mm if cell_mm else self.cell_mm
        pix = pixel_mm if pixel_mm else self.effective_pixel()
        prob = Problem.new(b.width, b.height, layers=max(2, len(b.copper)))
        v = memory.check(prob, ["fvm"], cell, base=memory.BASE_DEFAULT, refuse="return", quiet=True)[0]
        rows, cols = pixel_counts(window_of(b.box), pix)
        out = {"fvm": v, "import_peak": None, "import_error": "", "rows": rows, "cols": cols, "pixel_mm": pix}
        try:
            out["import_peak"] = memory.check_import(rows, cols, len(b.copper), cell, pixel_mm=pix)
        except memory.MemoryGuardError as exc:
            out["import_error"] = str(exc)
        return out

    def warnings(self) -> List[str]:
        """!
        @brief The warnings of the Model step (the import still runs): the notes the program owes on imported copper (Lumped and Analytic always), a coarse cell or pixel, the job file and the parts.
        @return list of text lines.
        """
        out = []
        if not self.heat_sources():
            out.append("No heat source is defined: the board will have no power until you add one.")
        out.append(copper_mod.REDUCED_MODEL_WARNING)
        if self.mapping == "fill":
            out.append("imported copper with the 'fill' mapping: the arithmetic copper fraction of every cell reads 10 to 30 % too cool on thin copper; choose 'faces' for a result")
        else:
            out.append(copper_mod.FILL_NOTE)
        if self.cell_mm > copper_mod.COARSE_CELL_MM + 1e-9 and self.mapping != "fill":
            out.append(copper_mod.coarse_cell_warning("gui"))
        pix = self.effective_pixel()
        if self.mapping != "fill" and self.cell_mm / pix < copper_mod.COARSE_RASTER_PIXELS:
            out.append(f"the masks have {self.cell_mm / pix:.1f} pixels per cell ({pix:g} mm pixel, {self.cell_mm:g} mm cell): below about {copper_mod.COARSE_RASTER_PIXELS:g} the face "
                       "conductances cannot resolve the copper; use a finer pixel or a coarser cell")
        out += self.job_warnings()
        out += [w for w in self.parts_warnings() if "do not fit" in w or "origin" in w]
        if self._board is not None:
            v, comp, _ = self.vias()
            if comp:
                out.append(f"{comp} plated holes above {self.via_max_mm:g} mm are component holes and are not modelled as vias")
        return out

    # ------------------------------------------------------------------------------------------------------------------------------------ building the project
    def _copper_layers(self):
        """!
        @brief The parsed copper layers in stack order.
        @return list of (SourceFile, Layer).
        """
        files = sorted(self.used(*COPPER), key=lambda f: COPPER.index(f.role) if f.role != COPPER_BOTTOM else 99)
        return [(f, self._layer(f)) for f in files]

    def _drills(self) -> list:
        """!
        @brief The drill files in use with the plated holes up to `via_max_mm` (the vias); the larger plated holes are component holes.
        @return list of gerber.DrillFile.
        """
        out = []
        for f in self.used(PLATED, NONPLATED):
            try:
                d = read_drill(f.text(), f.name)
            except (GerberError, OSError):
                continue
            plated = d.plated if d.plated is not None else f.role == PLATED
            keep = [h for h in d.holes if (h.plated if h.plated is not None else plated) and h.diameter <= self.via_max_mm]
            out.append(DrillFile(keep, True, d.span, d.tools))
        return out

    def _component_holes(self, box) -> list:
        """!
        @brief The plated holes above the via limit, in board coordinates, for the record (not vias).
        @param box Board box (x0, y0, x1, y1) in the Gerber frame.
        @return list of hole dicts with kind "component".
        """
        b = self._board
        return [{"x_mm": float(h.x - box[0]), "y_mm": float(h.y - box[1]), "d_mm": float(h.diameter), "kind": "component"} for h in (b.holes if b else [])
                if h.plated and h.diameter > self.via_max_mm]

    def import_files(self) -> List[ImportFile]:
        """!
        @brief The files in use as records of the project (name, size, hash and function; never the path).
        @return list of model.ImportFile.
        """
        return [ImportFile(f.name, f.size, f.sha256, f.role) for f in self.used()]

    def build_problem(self) -> Problem:
        """!
        @brief Build the new project from the files and the choices: rasterise the copper at the pixel, make the Problem (outline, vias, typical stack-up, job thickness, one heater per heat source) and the import record.
        @details The record (`self.record`) holds the files, the parts with the user's edits, the masks, the plated holes (vias and component holes) and the settings; the window gives
                 `Project(problem, imports=[record])` to the document.
        @return Problem
        @throws ValueError For a panel outline (several boards), no copper, or an import the files cannot make.
        @throws memory.MemoryGuardError If the masks would not fit in memory.
        """
        if not self.complete():
            raise ValueError("; ".join(self.problems()))
        cl = self._copper_layers()
        ib = copper_mod.import_copper([lay for _, lay in cl], self._outline if self.used(OUTLINE) else None, self._drills(), pixel_mm=self.effective_pixel(),
                                      cell_mm=self.cell_mm, mapping=self.mapping, names=[f.name for f, _ in cl])
        st = self.stackup()
        thickness = (self.job or {}).get("thickness_mm") or (st["total_thickness_um"] / 1000.0 if st else 1.6)
        prob = ib.to_problem(thickness_mm=thickness, name=self.name)
        nb = new_problem().board                              # the user's defaults for a new board: ambient, heat transfer, plating, materials
        for k in ("ambient", "h_top", "h_bottom", "h_side", "via_plating", "h_mode", "emissivity_top", "emissivity_bottom", "orientation", "air_speed", "h_calibration", "natural_form",
                  "materials"):
            setattr(prob.board, k, copy.deepcopy(getattr(nb, k)))
        try:
            prob.board.apply_template()                      # the typical stack-up of the layer count
        except (ValueError, KeyError):
            pass
        if (self.job or {}).get("thickness_mm") and prob.board.dielectrics is None:
            prob.board.thickness = thickness / 1000.0
        self._add_heaters(prob, ib.box_mm, self.parts())
        rec = ib.record(self.name)
        rec.files = self.import_files()
        rec.parts = copy.deepcopy(self.parts())
        rec.holes = rec.holes + self._component_holes(ib.box_mm)
        rec.warnings = list(ib.warnings) + self.warnings()
        rec.cad_profile = self.profile_choice.record() if self.profile_choice is not None else None
        rec.settings = {"mapping": self.mapping, "cell_mm": self.cell_mm, "pixel_mm": ib.pixel_mm, "via_max_mm": self.via_max_mm, "offset_mm": list(self.offset),
                        "roles": {f.name: f.role for f in self.used()}}
        # What the user decided by hand about the files, so that a re-import does not undo it (written only when there is something, older files stay byte-identical)
        user_roles = {f.name: f.role for f in self.files if f.user_role}
        left_out = [f.name for f in self.files if not f.use and not f.user_role]
        if user_roles:
            rec.settings["user_roles"] = user_roles
        if self.pixel_mm is not None:
            rec.settings["pixel_user"] = True                # the user typed the pixel: a re-import takes it again (an automatic pixel is proposed again)
        if left_out:
            rec.settings["not_used"] = left_out
        self.record, self.thickness_mm = rec, thickness
        return prob

    def _add_heaters(self, prob: Problem, box, parts):
        """!
        @brief Add one heater per heat source (board coordinates, the layer of its side).
        @param prob Problem to change.
        @param box Board box (x0, y0, x1, y1) of the import in the Gerber frame, mm.
        @param parts List of ImportPart.
        @return None
        """
        for p in parts:
            if not self.is_source(p):
                continue
            poly = [[x - box[0], y - box[1]] for x, y in p.polygon_mm]
            layer = 1 if p.side != "bottom" else max(prob.board.layers, 1)
            prob.add_heater(layer, p.power, polygon=poly, name=p.designator, tj_max=float(p.edits.get("tj_max", 0.0)),
                            role="source" if p.edits.get("role") == "Source" else "component" if p.edits.get("role") == "Component" else "")

    # ------------------------------------------------------------------------------------------------------------------------------------ re-import
    def part_diff(self, old: ImportRecord) -> list:
        """!
        @brief The table of what changed between the parts of a stored import and the parts of the current files (new, removed, moved, resized, rotated, kept).
        @param old Stored ImportRecord.
        @return list of dicts ref, change, detail.
        """
        return parts_mod.diff_parts(old.parts, self.parts())

    @staticmethod
    def classify_files(old: ImportRecord, new: ImportRecord) -> list:
        """!
        @brief Compare the file sets of a stored import and the new files, per function.
        @param old Stored import.
        @param new Record of the new files.
        @return list of dicts function, status ("identical", "changed", "added", "only stored"), old, new (ImportFile or None).
        """
        out = []
        for fn in ROLES:
            olds = [f for f in old.files if f.function == fn]
            news = [f for f in new.files if f.function == fn]
            if not olds and not news:
                continue
            # Several files may share a function (two drill files, masks, legends): pair them by content first, then by name, so that none is lost or compared with another
            pairs, left_o, left_n = [], list(olds), list(news)
            for f in list(left_n):
                m = next((a for a in left_o if a.sha256 == f.sha256), None)
                if m is not None:
                    pairs.append((m, f))
                    left_o.remove(m)
                    left_n.remove(f)
            for f in list(left_n):
                m = next((a for a in left_o if a.name == f.name), None)
                if m is not None:
                    pairs.append((m, f))
                    left_o.remove(m)
                    left_n.remove(f)
            if fn in UNIQUE and left_o and left_n:                      # one file per function: the only two are the same file, changed (and renamed)
                pairs.append((left_o.pop(0), left_n.pop(0)))
            pairs += [(a, None) for a in left_o] + [(None, b) for b in left_n]
            for a, b in pairs:
                status = "added" if a is None else "only stored" if b is None else "identical" if a.sha256 == b.sha256 else "changed"
                out.append({"function": fn, "status": status, "old": a, "new": b})
        return out

    @staticmethod
    def choice_key(item: dict) -> str:
        """!
        @brief The key of a file conflict in `file_choice`: the function when it can hold only one file, else the function and the file name.
        @param item An element of `classify_files`.
        @return str
        """
        return item["function"] if item["function"] in UNIQUE else f"{item['function']}: {(item['new'] or item['old']).name}"

    @staticmethod
    def _parts_in_place(old_parts, new_parts, old_box, new_box, tol_mm: float = 1.0) -> tuple:
        """!
        @brief How many parts of a stored import sit, under the same designator, where a part of the new files sits: the strongest sign of a revision of the same board.
        @details The centre of the polygon of each part with a polygon is compared in the Gerber frame of the files and also after the change of the board box (a revision may move
                 the origin of the export); the better of the two counts is taken.
        @param old_parts Stored ImportPart list.
        @param new_parts ImportPart list of the new files.
        @param old_box Stored box [x0, y0, x1, y1] in mm (or empty).
        @param new_box Box of the new files in mm (or empty).
        @param tol_mm Largest distance in mm between the two centres of a part that still counts as the same place.
        @return tuple (designators in both with a polygon, of them at the same place).
        """
        def centres(parts):
            """!
            @brief Centre of the bounding box of the polygon of every part that has one (the box of the hull and of the pads is the same, so a shape the user changed
                   between hull, box and pads moves it little).
            @param parts ImportPart list.
            @return dict designator -> (x, y) in mm.
            """
            out = {}
            for p in parts:
                if p.polygon_mm and not p.from_file.get("orphan"):
                    a = np.asarray(p.polygon_mm, float)
                    out[p.designator] = (a.min(axis=0) + a.max(axis=0)) / 2
            return out
        co, cn = centres(old_parts), centres(new_parts)
        common = sorted(set(co) & set(cn))
        if not common:
            return 0, 0
        shifts = [np.zeros(2)]
        if len(old_box) == 4 and len(new_box) == 4:
            shifts.append(np.array([new_box[0] - old_box[0], new_box[1] - old_box[1]], float))
        best = max(sum(1 for d in common if np.hypot(*(cn[d] - co[d] - s)) <= tol_mm) for s in shifts)
        return len(common), best

    @staticmethod
    def _same_core(old_box, new_box, old_files, new_files, tol: float = 0.05, old_parts=(), new_parts=()) -> tuple:
        """!
        @brief The rule that tells a revision of the same board from another board.
        @details When at least three designators with a heat-source polygon are in both sets, the parts decide: the board is the SAME when at least half of them sit at the same place
                 (within 1 mm), whatever the files and the outline say, and DIFFERENT otherwise. Without that evidence the board is DIFFERENT when the width or the height of the
                 outline box differs by more than `tol` of the stored one, or when no new file shares its content or its base name with a stored one (names compared without the
                 folders of an archive and without case). Review: the first rule called a board different when no file was byte-identical, but every
                 CAD export stamps the date in the files, so a plain re-export with one moved part (the placement file changes too) dropped the powers of the revision; a set renamed
                 or re-zipped into a folder was taken for another board in the same way. Parts at the same place (three or more, at least half) make it the same board whatever
                 the files are called.
        @param old_box Stored box [x0, y0, x1, y1] in mm (or empty).
        @param new_box Box of the new files in mm (or empty).
        @param old_files Stored ImportFile list.
        @param new_files New ImportFile list.
        @param tol Relative difference of width or height accepted.
        @param old_parts Stored ImportPart list (empty: the parts are not used).
        @param new_parts ImportPart list of the new files (empty: the parts are not used).
        @return tuple (same bool, reasons list of str).
        """
        reasons = []
        n_common, n_place = ImportSession._parts_in_place(old_parts, new_parts, old_box, new_box)
        in_place = n_common >= 3 and 2 * n_place >= n_common
        if in_place:
            return True, []                                    # the same parts at the same places: a revision (a grown outline, renamed or re-exported files)
        if len(old_box) == 4 and len(new_box) == 4:
            ow, oh = old_box[2] - old_box[0], old_box[3] - old_box[1]
            nw, nh = new_box[2] - new_box[0], new_box[3] - new_box[1]
            if abs(ow - nw) > tol * ow or abs(oh - nh) > tol * oh:
                reasons.append(f"the outline is {nw:.1f} x {nh:.1f} mm, the stored one {ow:.1f} x {oh:.1f} mm")
        def base(name):
            """!
            @brief File name without the folders of an archive, in lower case.
            @param name Stored file name.
            @return str
            """
            return name.replace("\\", "/").rsplit("/", 1)[-1].lower()
        shared_content = bool({f.sha256 for f in old_files} & {f.sha256 for f in new_files})
        shared_name = bool({base(f.name) for f in old_files} & {base(f.name) for f in new_files})
        if old_files and new_files and not shared_content and not shared_name:
            reasons.append("no file shares its name or its content with a stored one")
        if n_common >= 3:
            reasons.append(f"of the {n_common} parts with a stored designator only {n_place} sit at the same place")
        return not reasons, reasons

    @staticmethod
    def same_board(old: ImportRecord, new: ImportRecord, tol: float = 0.05) -> tuple:
        """!
        @brief Decide whether new files look like the same board as a stored import (see `_same_core`: the outline box, the files by name or content, the parts by place).
        @param old Stored import.
        @param new Record of the new files.
        @param tol Relative difference of width or height accepted.
        @return tuple (same bool, reasons list of str).
        """
        return ImportSession._same_core(list(old.box_mm), list(new.box_mm), old.files, new.files, tol, old.parts, new.parts)

    def looks_different(self, stored: ImportRecord) -> bool:
        """!
        @brief The same test as `same_board`, made before the import is built (from the files in use, the box of the board read by `load` and the parts of step 2), so that step 2
               can leave the stored parts out for another board.
        @param stored The stored ImportRecord.
        @return bool True when the files look like another board; False when they look like a revision or nothing can be told yet.
        """
        b = self.board()
        if b is None or not self.files:
            return False
        return not self._same_core(list(stored.box_mm), list(b.box), stored.files, self.import_files(), 0.05, stored.parts, self.parts())[0]

    def merge_import(self, mode: str, old: ImportRecord, remove=(), file_choice=None, carry: bool = True) -> dict:
        """!
        @brief Merge the new import (`build_problem` was just run) into the stored record by the chosen command.
        @details "replace" and "update": copper, drills and outline come from the new files; a part with the same designator keeps its power and edits, a part that left the files is an
                 orphan (kept, not heating) unless listed in `remove`. "add": the stored copper, outline, drills and settings stay (a copper, outline or drill file is never taken:
                 the masks and the vias of the board would not follow it, so it is listed as needing Replace or Update); the other functions the store lacks are taken from the new files
                 (for a function both have, `file_choice[function]` "stored", the default, or "new"). The stored parts are kept as they are and the new designators are added; only
                 when a paste, placement or component file is taken are the stored parts matched again against the new files (their power and edits kept), and even then no stored
                 part becomes an orphan (its heater stays in the project).
        @param mode "replace", "update" or "add".
        @param old Stored ImportRecord.
        @param remove Designators the user confirmed to remove.
        @param file_choice dict function -> "stored" or "new" for conflicts (mode "add").
        @param carry False for another board: the stored parts are not matched by designator (no orphans, no carried power); the parts are those of the new files.
        @return dict `record` (ImportRecord), `changes` (text lines), `parts` (the merged ImportPart list), `orphans` (designators), `typed` (designators whose power, tick, Tj max
                or role the user changed in step 2: these values win over the stored ones, see `take_stored_parts`).
        """
        new = self.record
        shapes = self._res.shapes if self._res else None
        if mode == "add":
            rec = copy.deepcopy(old)
            files = list(rec.files)
            changes, rematch, bom_taken = [], False, False
            for item in self.classify_files(old, new):
                fn, status = item["function"], item["status"]
                if status not in ("added", "changed"):
                    continue
                if fn in GEOMETRY:
                    # Review: the record listed an added copper layer that the stored masks do not hold (and a drill file whose vias were not made)
                    changes.append(f"not taken: {fn} ({item['new'].name}) changes the board itself; use Replace or Update to import it")
                    continue
                take = status == "added" or (file_choice or {}).get(self.choice_key(item), "stored") == "new"
                if take:
                    # The new file replaces the one it was paired with, or joins the list: the other files of the same function stay
                    files = [f for f in files if f is not item["old"] and not (item["old"] is not None and f.name == item["old"].name and f.sha256 == item["old"].sha256)]
                    files.append(item["new"])
                    rematch = rematch or fn in PARTS_FUNCTIONS
                    bom_taken = bom_taken or fn == BOM
                changes.append(f"added {fn}: {item['new'].name}" if status == "added" else
                               f"conflict on {fn}: " + (f"took the new file {item['new'].name}" if take else f"kept the stored file {item['old'].name}"))
            rec.files = files
            res = parts_mod.merge_parts(old.parts, new.parts, shapes, openings=self.openings())
            stored = {p.designator: p for p in old.parts}
            # A stored part stays as it is unless the parts files were taken (then it takes the new match); it never becomes an orphan here
            parts = [copy.deepcopy(stored[p.designator]) if p.designator in stored and (not rematch or p.from_file.get("orphan")) else p for p in res.parts]
            if bom_taken:
                self.apply_bom(parts)                                  # the kept copies get what the new BOM says; powers, positions and edits are untouched
            else:
                for p in parts:
                    if p.designator not in stored:
                        p.from_file.pop("bom", None)                   # the stored BOM stays the one of the project
            rec.parts = parts
            changes += [c for c in res.changes if "orphan" not in c] if rematch else [f"{p.designator}: added" for p in parts if p.designator not in stored]
            changes += self.bom_changes(old.parts, parts)
            typed, lines = self._apply_step2(parts)
            return {"record": rec, "changes": lines + self._drop_kept_power(changes, typed), "parts": parts, "orphans": [], "typed": typed}
        if not carry:
            # Another board: a designator of the old board names an unrelated part here, so nothing is matched, nothing is orphaned and the powers start from the files
            parts = copy.deepcopy(self.parts())
            typed, lines = self._apply_step2(parts)
            rec = copy.deepcopy(new)
            rec.parts = parts
            return {"record": rec, "changes": lines + ["another board: the stored parts were not carried over"], "parts": parts, "orphans": [], "typed": typed}
        res = parts_mod.merge_parts(old.parts, self.parts(), shapes, remove=remove, openings=self.openings())
        typed, lines = self._apply_step2(res.parts)
        rec = copy.deepcopy(new)
        rec.parts = res.parts
        return {"record": rec, "changes": lines + self._drop_kept_power(res.changes, typed) + self.bom_changes(old.parts, res.parts), "parts": res.parts, "orphans": res.orphans, "typed": typed}


def reimport_summary(old: ImportRecord, new: ImportRecord, mode: str) -> str:
    """!
    @brief One sentence with the numbers of what a re-import changed (never empty).
    @param old The ImportRecord before the re-import.
    @param new The ImportRecord after it.
    @param mode "replace", "update" or "add".
    @return str
    """
    def masks(rec):
        """!
        @brief The packed mask text of every copper layer of a record, by layer index.
        @param rec ImportRecord.
        @return dict index -> str.
        """
        c = getattr(rec, "copper", None)
        return {int(e.get("index", k)): str((e.get("mask") or {}).get("data", "")) for k, e in enumerate(getattr(c, "layers", []) or [])}
    mo, mn = masks(old), masks(new)
    replaced = sum(1 for k, v in mn.items() if mo.get(k) != v)
    po, pn = {p.designator: p for p in old.parts}, {p.designator: p for p in new.parts}
    added = sorted(set(pn) - set(po))
    orphans = sorted(d for d, p in pn.items() if p.from_file.get("orphan") and not (po.get(d) and po[d].from_file.get("orphan")))
    gone = sorted(set(po) - set(pn))
    moved = sum(1 for d, p in pn.items() if d in po and parts_mod.MOVED_MM < parts_mod._moved_mm(po[d].polygon_mm, p.polygon_mm))
    ofiles = {(f.function, f.name, f.sha256) for f in old.files}
    files = sum(1 for f in new.files if (f.function, f.name, f.sha256) not in ofiles)
    holes = f"{len(new.holes)} holes" + ("" if len(new.holes) == len(old.holes) else f" (were {len(old.holes)})")
    if mode == "add":
        return (f"{files} file(s) taken, {len(added)} part(s) added, copper, outline and holes untouched ({len(mn)} copper layers, {holes})" if files or added
                else "nothing was added; copper, outline and holes untouched")
    return (f"{replaced} of {len(mn)} copper layer(s) replaced, {holes}, {files} file(s) new or changed; parts: {len(added)} added, {moved} moved, "
            f"{len(orphans)} orphaned, {len(gone)} removed, {len(pn) - len(added)} kept")


def editor_part_values(record: ImportRecord, problem: Problem) -> None:
    """!
    @brief Write into a copy of the stored record the values the editor holds for its parts (power, Tj max, role, and no heat source when the user deleted the heater), so that the
           re-import window shows them in step 2 and the merge keeps them.
    @details A heater is the part's when it has its designator or, renamed, the polygon of the part (the rule of `carry_over`). The record itself is not the project's: the caller passes
             a copy.
    @param record Copy of the stored ImportRecord; changed in place.
    @param problem The Problem of the open project.
    @return None
    """
    box = list(record.box_mm)
    x0, y0 = (box[0], box[1]) if len(box) == 4 else (0.0, 0.0)
    by_name = {h.name: h for h in problem.heaters}
    for p in record.parts:
        h = by_name.get(p.designator)
        if h is None and p.polygon_mm:
            poly = [[(x - x0) * 1e-3, (y - y0) * 1e-3] for x, y in p.polygon_mm]
            h = next((g for g in problem.heaters if _same_polygon(poly, g.polygon)), None)
        if h is not None:
            p.power = float(h.power)
            p.edits["tj_max"] = float(h.tj_max)
            if h.role in ("source", "component"):
                p.edits["role"] = h.role.capitalize()
        elif p.edits.get("use") and p.polygon_mm and not p.from_file.get("orphan"):
            p.edits["use"] = False                             # the user deleted its heater in the editor: the re-import does not make it again (as `carry_over`)


def sync_add_heaters(session, problem: Problem, old_record: ImportRecord, new_record: ImportRecord, typed=()) -> List[str]:
    """!
    @brief Bring the heaters of the open project in line with the record of an Add files: a heater for every new part that heats, the heater of a stored part moved with it when the new
           placement or paste file moved the part, and the step-2 values of the parts the user changed there.
    @details Review: Add files with a new placement file moved the parts of the record (the merge took the new files) but left their heaters where they were, so the editor showed
             nothing changed while the status line said "moved by 4.00 mm". A heater whose polygon the user changed in the editor is not moved (the line says so). Add files keeps the
             board box, so the record and the heaters share the frame.
    @param session The ImportSession of the new files (for `_add_heaters` and `is_source`).
    @param problem The Problem of the open project; changed in place.
    @param old_record The stored ImportRecord before the re-import.
    @param new_record The merged ImportRecord of the Add files.
    @param typed Designators whose step-2 values win (`ImportSession.step2_edits`).
    @return list of text lines.
    """
    box = list(new_record.box_mm)
    x0, y0 = (box[0], box[1]) if len(box) == 4 else (0.0, 0.0)

    def metres(poly):
        """!
        @brief A record polygon (mm, Gerber frame) in board metres.
        @param poly List of [x, y] in mm.
        @return numpy.ndarray (n, 2)
        """
        return np.array([[(x - x0) * 1e-3, (y - y0) * 1e-3] for x, y in poly], float).reshape(-1, 2)

    oldp = {p.designator: p for p in old_record.parts}
    session._add_heaters(problem, box, [p for p in new_record.parts if p.designator not in oldp])
    heaters = {h.name: h for h in problem.heaters}
    moved, left, typed_set, out = [], [], set(typed or ()), []
    for q in new_record.parts:
        a, h = oldp.get(q.designator), heaters.get(q.designator)
        if a is None:
            continue
        if h is not None and q.polygon_mm and a.polygon_mm and not _same_polygon(q.polygon_mm, a.polygon_mm, 1e-6):
            if _same_polygon(metres(a.polygon_mm), h.polygon, 1e-9):
                h.polygon = metres(q.polygon_mm)
                moved.append(q.designator)
            else:
                left.append(q.designator)
        if q.designator in typed_set:
            if not session.is_source(q):
                if h is not None:
                    problem.heaters = [g for g in problem.heaters if g is not h]      # by identity: the == of a Heater compares arrays
            elif h is None:
                session._add_heaters(problem, box, [q])
            else:
                h.power, h.tj_max = float(q.power), float(q.edits.get("tj_max", h.tj_max))
                if q.edits.get("role") in ("Source", "Component"):
                    h.role = q.edits["role"].lower()
    if moved:
        out.append(f"moved the heater of {len(moved)} part(s) with the new files: {', '.join(moved[:8])}" + (" ..." if len(moved) > 8 else ""))
    if left:
        out.append(f"not moved: the heater of {', '.join(left[:8])} was changed in the editor" + (" ..." if len(left) > 8 else ""))
    return out


def _same_polygon(a, b, tol=1e-7) -> bool:
    """!
    @brief Whether two polygons have the same vertices within a tolerance.
    @param a Array-like (n, 2).
    @param b Array-like (m, 2).
    @param tol Largest difference of a coordinate, in the unit of the polygons.
    @return bool
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a.shape == b.shape and bool(np.all(np.abs(a - b) <= tol))


def carry_over(old_problem: Problem, old_record: ImportRecord, new_problem: Problem, new_record: ImportRecord, typed=(), carry_parts: bool = True) -> List[str]:
    """!
    @brief Bring what the user did in the editor after an import into the Problem of a Replace or Update, so that a re-import loses nothing the files do not give.
    @details The files give the copper, the outline, the vias and the parts; the user gives the rest. Kept, in the Gerber frame (moved by the change of the board box):
             * the fields of the heaters of the imported parts (power, theta, Tj max, role, top path, profile, ...) edited in the editor, onto the heater of the same part (matched by
               designator, or by its polygon when the user renamed it); the merged record takes the power, Tj max and role too, so that it agrees with the editor (an orphan as well);
             * an imported part whose heater the user deleted stays without a heater (its record part is unticked);
             * the heaters, zones and heatsinks drawn by hand, and the vias drawn by hand (a via not at a hole of the stored import); the fill of an imported via is kept on the via at the
               same place;
             * the stack-up (thickness, copper per layer, dielectrics, inner copper weight) when the number of copper layers did not change.
             A heater, zone or heatsink on the bottom layer stays on the bottom layer when the layer count changes; an inner one is clipped to the last inner layer.
    @param old_problem The Problem of the open project (before the re-import).
    @param old_record The stored ImportRecord (before the merge).
    @param new_problem The Problem built from the new files with the heaters of the merged parts; changed in place.
    @param new_record The merged ImportRecord; its parts are changed in place.
    @param typed Designators whose power, heat-source tick, Tj max and role the user changed in step 2 of the re-import (`ImportSession.step2_edits`): for these the values of the
                 merged record win over the editor's (the other fields of the heater are still the editor's).
    @param carry_parts False for another board: the heaters of the stored parts are dropped (they name unrelated parts), only what the user drew by hand is kept.
    @return list of text lines (what was kept), for the status line and the record warnings.
    """
    ob, nb = list(old_record.box_mm), list(new_record.box_mm)
    # Board coordinates are relative to the box of the import: the same place on the Gerber frame moves by the change of the box corner (metres)
    dx, dy = ((ob[0] - nb[0]) * 1e-3, (ob[1] - nb[1]) * 1e-3) if len(ob) == 4 and len(nb) == 4 else (0.0, 0.0)
    shift = np.array([dx, dy])
    lo, ln = old_problem.board.layers, new_problem.board.layers

    def layer_of(k):
        """!
        @brief The layer of the new board for a layer of the old one (bottom stays bottom, an inner layer is clipped).
        @param k Old 0-based layer.
        @return int
        """
        return ln - 1 if (k == lo - 1 and k > 0) else min(k, ln - 1)

    out = []
    # 1. Heaters: those of the imported parts (by designator, or by the polygon of a part when renamed) and those drawn by hand
    oldx = ob[0] if len(ob) == 4 else 0.0
    oldy = ob[1] if len(ob) == 4 else 0.0
    # Only the parts that were heat sources made a heater; a heater named like a listed part (no heater of its own) is the user's
    part_poly = {p.designator: [[(x - oldx) * 1e-3, (y - oldy) * 1e-3] for x, y in p.polygon_mm] for p in old_record.parts
                 if p.polygon_mm and p.edits.get("use") and not p.from_file.get("orphan")}
    rec_parts = {p.designator: p for p in new_record.parts}
    new_by_name = {h.name: h for h in new_problem.heaters}
    geometry_fields = {"layer", "polygon", "name"}
    typed = set(typed or ())
    step2_fields = {"power", "tj_max", "role"}                         # what the parts table of step 2 edits
    seen, edited, drawn = set(), [], []
    for h in old_problem.heaters:
        des = h.name if h.name in part_poly else next((d for d, poly in part_poly.items() if _same_polygon(poly, h.polygon)), None)
        if des is not None and not carry_parts:
            continue                                                       # a heater of the other board's part: it has no meaning here
        if des is None:
            q = copy.deepcopy(h)
            q.polygon, q.layer = np.asarray(h.polygon, float) + shift, layer_of(h.layer)
            new_problem.heaters.append(q)
            drawn.append(h.name or "unnamed")
            continue
        seen.add(des)
        nh = new_by_name.get(des)
        if nh is not None:
            changed = False
            for f in dataclasses.fields(h):
                if f.name not in geometry_fields and not (des in typed and f.name in step2_fields):
                    v = copy.deepcopy(getattr(h, f.name))
                    changed = changed or not _equal(getattr(nh, f.name), v)
                    setattr(nh, f.name, v)
            nh.name = h.name or des                                        # a name the user gave stays
            if changed:
                edited.append(h.name or des)
        p = rec_parts.get(des)
        if p is not None and des not in typed:
            p.power = float(h.power)
            p.edits["tj_max"] = float(h.tj_max)
            if h.role:
                p.edits["role"] = "Source" if h.role == "source" else "Component"
    # 2. An imported heat source whose heater the user deleted stays deleted
    deleted = [p.designator for p in old_record.parts if carry_parts and p.edits.get("use") and p.polygon_mm and not p.from_file.get("orphan") and p.designator not in seen and p.designator not in typed]
    if deleted:
        new_problem.heaters = [h for h in new_problem.heaters if h.name not in deleted]
        for d in deleted:
            if d in rec_parts:
                rec_parts[d].edits["use"] = False
        out.append(f"kept deleted: no heater for {', '.join(deleted)} (deleted in the editor)")
    if edited:
        out.append(f"kept the editor's values of {len(edited)} imported part(s): {', '.join(edited[:8])}" + (" ..." if len(edited) > 8 else ""))
    if drawn:
        out.append(f"kept {len(drawn)} heater(s) drawn by hand: {', '.join(drawn[:8])}" + (" ..." if len(drawn) > 8 else ""))
    # 3. Zones and heatsinks are never made by the import: all are the user's
    for z in old_problem.zones:
        q = copy.deepcopy(z)
        q.polygon, q.layer = np.asarray(z.polygon, float) + shift, layer_of(z.layer)
        new_problem.zones.append(q)
    for s in old_problem.heatsinks:
        q = copy.deepcopy(s)
        q.polygon, q.layer = np.asarray(s.polygon, float) + shift, (0 if s.layer == 0 else ln - 1)
        new_problem.heatsinks.append(q)
    if old_problem.zones or old_problem.heatsinks:
        out.append(f"kept {len(old_problem.zones)} zone(s) and {len(old_problem.heatsinks)} heatsink(s)")
    # 4. Vias: the stored import's holes in board metres; a via elsewhere was drawn by hand, a via at a hole keeps its fill on the new via at the same place
    holes = np.array([[(h["x_mm"]) * 1e-3, (h["y_mm"]) * 1e-3] for h in old_record.holes if h.get("kind") != "component"]).reshape(-1, 2)
    new_xy = np.array([[v.x, v.y] for v in new_problem.vias]).reshape(-1, 2)
    hand, fills = 0, 0
    for v in old_problem.vias:
        imported = holes.size and np.min(np.hypot(holes[:, 0] - v.x, holes[:, 1] - v.y)) < 1e-6
        if not imported:
            q = copy.deepcopy(v)
            q.x, q.y = v.x + dx, v.y + dy
            new_problem.vias.append(q)
            hand += 1
        elif (v.filled or v.fill_k or v.fill or v.name) and new_xy.size:
            d = np.hypot(new_xy[:, 0] - (v.x + dx), new_xy[:, 1] - (v.y + dy))
            k = int(np.argmin(d))
            if d[k] < 1e-6:
                nv = new_problem.vias[k]
                nv.filled, nv.fill_k, nv.fill, nv.name = v.filled, v.fill_k, v.fill, v.name
                fills += 1
    if hand:
        out.append(f"kept {hand} via(s) drawn by hand")
    if fills:
        out.append(f"kept the fill of {fills} imported via(s)")
    # 5. The stack-up the user edited, when the layer count is the same
    if lo == ln:
        ob_, nb_ = old_problem.board, new_problem.board
        for k in ("thickness", "copper_thickness", "dielectrics", "template_inner_oz"):
            setattr(nb_, k, copy.deepcopy(getattr(ob_, k)))
    else:
        out.append(f"the stack-up is the typical one of {ln} layers (the board had {lo}): check it in the Stack-up tab")
    return out


def _equal(a, b) -> bool:
    """!
    @brief Equality that also works for arrays and profiles.
    @param a Value.
    @param b Value.
    @return bool
    """
    try:
        return bool(np.all(np.asarray(a) == np.asarray(b))) if isinstance(a, np.ndarray) or isinstance(b, np.ndarray) else bool(a == b)
    except (ValueError, TypeError):
        return False


__all__ = ["BoardData", "Hole", "ImportNotAvailable", "ImportSession", "LayerInfo", "ROLES", "SourceFile", "carry_over", "editor_part_values", "reimport_summary", "sync_add_heaters"]
