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
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

from .. import copper as copper_mod
from .. import memory
from ..gerber import (DrillFile, GerberArchive, GerberError, LayerFunction, detect_function, parse_layer, pixel_counts, rasterize, read_drill, read_outline,
                      window_of)
from ..gerber import components as comp_mod
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
ROLES = COPPER + (OUTLINE, PLATED, NONPLATED) + PASTE + MASK + LEGEND + (COMPONENT, PLACEMENT, IGNORE)
# Roles that are read when the file is in use; the others (mask, legend) are listed and ignored by the models
USED_BY_DEFAULT = COPPER + (OUTLINE, PLATED, NONPLATED) + PASTE + (COMPONENT, PLACEMENT)
# Roles of which only one file can exist (two files claiming one are shown and stop the import)
UNIQUE = COPPER + (OUTLINE,) + PASTE + (COMPONENT, PLACEMENT)
PREVIEW_PIXELS = 900                                            # The preview raster is about this many pixels on the long side
PREVIEW_PIXEL_MIN_MM = 0.1                                      # Finest pixel of the preview
VIA_MAX_MM = 0.5                                                # Default largest plated hole that is a via
HASH_WHOLE_BYTES = 64 * 1024 ** 2                               # Archive members up to this size are hashed whole
HASH_EDGE_BYTES = 1 << 20                                       # Larger members: the first and the last megabyte and the size
MAX_FILE_BYTES = 1024 ** 3                                      # A file above 1 GB is not a PCB layer (the archive limit, applied to folders too)
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

    def text(self) -> str:
        """!
        @brief The text of the file.
        @return str
        """
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
        self.record = None                                    # ImportRecord of the last build_problem()
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

    # ------------------------------------------------------------------------------------------------------------------------------------ files
    def close(self):
        """!@brief Release the archive and the caches."""
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
        self.close()
        self.files, self._board, self._board_error, self.job = [], None, "", None
        self._parts_dirty, self.offset, self.offset_answer = True, (0.0, 0.0), ""
        self._parts, self._listed, self._unmatched, self._res = [], [], [], None
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
        if not self.files:
            raise ValueError("no fabrication file found")
        self._assign_inner_numbers()

    def _add_paths(self, paths):
        """!
        @brief Add the files of a list of paths (hidden files, images, documents and project files are left out).
        @param paths List of Path.
        @return None
        """
        skip = {".zip", ".png", ".jpg", ".jpeg", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb", ".kicad_pro", ".svg", ".html", ".htm", ".rar", ".7z", ".py"}
        for f in paths:
            if f.suffix.lower() == ".gbrjob" and f.is_file() and f.stat().st_size < 1_000_000:
                self._read_job(f.read_text(encoding="utf-8", errors="replace"))
            if f.name.startswith(".") or f.suffix.lower() in skip or not f.is_file():
                continue
            size = f.stat().st_size
            if size > MAX_FILE_BYTES:
                continue
            with open(f, "rb") as fh:
                head = fh.read(HEAD_BYTES)
            sha = hashlib.sha256()
            with open(f, "rb") as fh:                          # Hashed in blocks: a layer can be tens of megabytes
                for block in iter(lambda: fh.read(1 << 20), b""):
                    sha.update(block)
            self._add_entry(f.name, size, sha.hexdigest(), head.decode("utf-8", "replace"), lambda p=f: p.read_text(encoding="utf-8", errors="replace"))

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
                self._read_job(self._archive.read_text(name))
            if name.lower().endswith(("/", ".png", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb", ".zip", ".jpg", ".svg")):
                continue
            head = self._archive.read_head(name)
            info = self._archive._infos[name]
            # The hash of an archive member needs the whole member: read it once, bounded by the declared size (the archive reader checks the CRC)
            if info.file_size <= HASH_WHOLE_BYTES:
                digest = _sha256(self._archive.read_text(name).encode("utf-8", "replace"))
            else:
                # A very large member is hashed by its head, its tail and its size (reading it whole only to hash it would hold it in memory twice)
                tail = self._archive.read_text(name)[-HASH_EDGE_BYTES:]
                digest = _sha256((head + "\0" + tail + "\0" + str(info.file_size)).encode("utf-8", "replace"))
            self._add_entry(name, info.file_size, digest, head, lambda n=name: self._archive.read_text(n))

    def _add_entry(self, name, size, sha, head, reader):
        """!
        @brief Detect the function of one file and add it.
        @param name File name.
        @param size Size in bytes.
        @param sha SHA-256 hex digest.
        @param head First kilobytes of the text.
        @param reader Function that returns the whole text.
        @return None
        """
        fn = detect_function(name, head)
        role = role_of(fn)
        how = _how(fn)
        if fn.kind == "unknown" and Path(name).suffix.lower() in (".csv", ".pos", ".txt", ".xy") and _looks_like_placement(head):
            role, how = PLACEMENT, "columns of a placement table"
        self.files.append(SourceFile(name, size, sha, fn, role, how, reader))

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
        f.role, f.use, f.error = role, role != IGNORE, ""
        self._board, self._parts_dirty = None, True

    def set_use(self, i: int, use: bool):
        """!
        @brief Use or leave out file i.
        @param i Index in `files`.
        @param use True to read it.
        @return None
        """
        self.files[i].use = bool(use)
        self._board, self._parts_dirty = None, True

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
            f.error = ""
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
        placement, comps = None, []
        for f in self.used(PLACEMENT):
            try:
                placement = parts_mod.parse_placement(f.text(), f.name)
            except ValueError as exc:
                f.error = str(exc)
        for f in self.used(COMPONENT):
            try:
                comps += comp_mod.parse_components(f.text(), f.name)
            except (GerberError, ValueError) as exc:
                f.error = str(exc)
        try:
            res = parts_mod.build_parts(paste, placement, comps or None, shape="hull", offset=self.offset if self.offset_answer == "accepted" else (0.0, 0.0))
        except GerberError as exc:
            # A paste layer with a negative image or another refusal: the parts are left empty and the file says why
            for f in self.used(*PASTE):
                f.error = str(exc)
            res = parts_mod.PartsResult()
            res.info = {"warnings": [str(exc)], "frame": None, "counts": {}}
        new = res.parts + res.listed
        old = self._parts + self._listed
        merged = parts_mod.merge_parts(old, new, res.shapes, openings=res.openings).parts if old else new
        for p in merged:
            p.edits.setdefault("use", False)
        self._res = res
        self._parts = [p for p in merged if p.polygon_mm and p.from_file.get("heat_source", True) or p.from_file.get("orphan")]
        self._listed = [p for p in merged if p not in self._parts]
        self._unmatched = list(res.unmatched)
        self._owner_cache = None
        self._parts_dirty = False

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
        return {"x3": "X3 component layer", "to.c+placement": "paste TO.C + placement", "placement by position": "paste + placement by position",
                "paste only": "paste only", "placement only": "placement only"}.get(p.from_file.get("source", ""), p.from_file.get("source", "") or "-")

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
            hulls = [(p, comp_mod.hull([tuple(q) for q in p.polygon_mm])) for p in self._parts if len(p.polygon_mm) >= 3]
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
        @brief The shapes the user can choose for a part: those its openings give ("hull", "box", "largest").
        @param p ImportPart.
        @return list of str (empty when the part has no opening).
        """
        ops = self._openings_of(p)
        if not ops:
            return []
        return ["hull", "box"] + (["largest"] if len(ops) > 1 else [])

    def set_shape(self, designator: str, kind: str):
        """!
        @brief Choose the heat-source shape of a part from its openings (always allowed; the choice is remembered as the user's).
        @param designator Designator.
        @param kind "hull", "box" or "largest".
        @return None
        """
        p = self.part(designator)
        ops = self._openings_of(p) if p else []
        if not ops:
            return
        p.shape = kind
        p.polygon_mm = [list(map(float, q)) for q in parts_mod.shape_polygon(ops, kind)]
        p.edits["shape_user"] = kind != "hull"
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
            kind = sel.shape if sel.shape in ("hull", "box", "largest") else "hull"
            ff = dict(sel.from_file)
            ff["n_openings"] = len(ops)
            sel.polygon_mm = [list(map(float, q)) for q in parts_mod.shape_polygon(ops, kind)]
            sel.from_file = ff
            self._unmatched = [u for u in self._unmatched if u is not o]
            self._owner_cache = None
            return sel.designator
        n = 1 + sum(1 for q in self.parts() if re.fullmatch(r"H\d+", q.designator))
        q = parts_mod.part_from_openings(f"H{n}", [o], "hull", "paste only", side=o.side, grouping="hand")
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
        if self.used(PLACEMENT) and self.used(*PASTE) and self.openings() and not any(o.ref for o in self.openings()) and not self.used(COMPONENT):
            n = sum(1 for p in self.parts() if p.from_file.get("source") == "placement by position")
            out.append(f"The paste layer names no parts: {n} parts matched by position (approximate)")
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
        @brief The automatic cell: a 50th of the long side of the board, between 0.5 and 1 mm (a larger cell warns on imported copper).
        @return float mm.
        """
        b = self._board
        if b is None:
            return 1.0
        return float(min(max(max(b.width, b.height) / 50.0, 0.5), 1.0))

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
            out.append(copper_mod.COARSE_CELL_WARNING)
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
        rec.settings = {"mapping": self.mapping, "cell_mm": self.cell_mm, "pixel_mm": ib.pixel_mm, "via_max_mm": self.via_max_mm, "offset_mm": list(self.offset),
                        "roles": {f.name: f.role for f in self.used()}}
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
        o = {f.function: f for f in old.files}
        n = {f.function: f for f in new.files}
        out = []
        for fn in ROLES:
            a, b = o.get(fn), n.get(fn)
            if a is None and b is None:
                continue
            status = "added" if a is None else "only stored" if b is None else "identical" if a.sha256 == b.sha256 else "changed"
            out.append({"function": fn, "status": status, "old": a, "new": b})
        return out

    @staticmethod
    def same_board(old: ImportRecord, new: ImportRecord, tol: float = 0.05) -> tuple:
        """!
        @brief Decide whether new files look like the same board as a stored import (outline box within 5 %, a shared file name or hash).
        @param old Stored import.
        @param new Record of the new files.
        @param tol Relative difference of width or height accepted.
        @return tuple (same bool, reasons list of str).
        """
        reasons = []
        if len(old.box_mm) == 4 and len(new.box_mm) == 4:
            ow, oh = old.box_mm[2] - old.box_mm[0], old.box_mm[3] - old.box_mm[1]
            nw, nh = new.box_mm[2] - new.box_mm[0], new.box_mm[3] - new.box_mm[1]
            if abs(ow - nw) > tol * ow or abs(oh - nh) > tol * oh:
                reasons.append(f"the outline is {nw:.1f} x {nh:.1f} mm, the stored one {ow:.1f} x {oh:.1f} mm")
        if old.files and new.files and not ({f.sha256 for f in old.files} & {f.sha256 for f in new.files}):
            reasons.append("none of the files is byte-identical to a stored one")
        if not ({f.name for f in old.files} & {f.name for f in new.files}):
            reasons.append("no file name in common")
        return not reasons, reasons

    def merge_import(self, mode: str, old: ImportRecord, remove=(), file_choice=None) -> dict:
        """!
        @brief Merge the new import (`build_problem` was just run) into the stored record by the chosen command.
        @details "replace" and "update": copper, drills and outline come from the new files; a part with the same designator keeps its power and edits, a part that left the files is an
                 orphan (kept, not heating) unless listed in `remove`. "add": the stored copper, outline and settings stay; the functions the store lacks are taken from the new files
                 (for a function both have, `file_choice[function]` "stored", the default, or "new"), and the parts the added files bring are added to the stored ones.
        @param mode "replace", "update" or "add".
        @param old Stored ImportRecord.
        @param remove Designators the user confirmed to remove.
        @param file_choice dict function -> "stored" or "new" for conflicts (mode "add").
        @return dict `record` (ImportRecord), `changes` (text lines), `parts` (the merged ImportPart list), `orphans` (designators).
        """
        new = self.record
        shapes = self._res.shapes if self._res else None
        if mode == "add":
            rec = copy.deepcopy(old)
            files = {f.function: f for f in old.files}
            changes = []
            for item in self.classify_files(old, new):
                fn = item["function"]
                if item["status"] == "added":
                    files[fn] = item["new"]
                    changes.append(f"added {fn}: {item['new'].name}")
                elif item["status"] == "changed":
                    take = (file_choice or {}).get(fn, "stored") == "new"
                    if take:
                        files[fn] = item["new"]
                    changes.append(f"conflict on {fn}: " + (f"took the new file {item['new'].name}" if take else f"kept the stored file {item['old'].name}"))
            rec.files = list(files.values())
            res = parts_mod.merge_parts(old.parts, new.parts, shapes, remove=remove, openings=self.openings())
            rec.parts = res.parts
            return {"record": rec, "changes": changes + res.changes, "parts": res.parts, "orphans": res.orphans}
        res = parts_mod.merge_parts(old.parts, self.parts(), shapes, remove=remove, openings=self.openings())
        rec = copy.deepcopy(new)
        rec.parts = res.parts
        return {"record": rec, "changes": res.changes, "parts": res.parts, "orphans": res.orphans}


__all__ = ["BoardData", "Hole", "ImportNotAvailable", "ImportSession", "LayerInfo", "ROLES", "SourceFile"]
