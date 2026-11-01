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

import hashlib
import logging
import re
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

from .. import memory
from ..gerber import GerberArchive, GerberError, LayerFunction, detect_function, estimate_raster_bytes, parse_layer, rasterize, read_drill, read_outline, window_of
from ..model import Problem, stackup_template

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
        self.files, self._board, self._board_error = [], None, ""
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
            if name.lower().endswith(("/", ".png", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb", ".zip", ".jpg", ".svg")):
                continue
            head = self._archive.read_head(name)
            info = self._archive._infos[name]
            # The hash of an archive member needs the whole member: read it once, bounded by the declared size (the archive reader checks the CRC)
            digest = _sha256(self._archive.read_text(name).encode("utf-8", "replace")) if info.file_size <= 64 * 1024 ** 2 else _sha256(head.encode("utf-8", "replace"))
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
        self._board = None

    def set_use(self, i: int, use: bool):
        """!
        @brief Use or leave out file i.
        @param i Index in `files`.
        @param use True to read it.
        @return None
        """
        self.files[i].use = bool(use)
        self._board = None

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
        for f in self.used(OUTLINE):
            try:
                out = read_outline(f.text(), f.name)
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

    def vias(self, max_mm: float = VIA_MAX_MM) -> tuple:
        """!
        @brief The plated holes split into vias (up to `max_mm`) and component holes, and the count of non-plated holes.
        @param max_mm Largest diameter of a plated hole that is a via (mm).
        @return tuple (vias, component holes, non-plated holes) as counts.
        """
        b = self._board
        if b is None:
            return 0, 0, 0
        plated = [h for h in b.holes if h.plated]
        n = sum(1 for h in plated if h.diameter <= max_mm)
        return n, len(plated) - n, len(b.holes) - len(plated)

    # ------------------------------------------------------------------------------------------------------------------------------------ hooks of the features not merged yet
    def parts(self) -> list:
        """!
        @brief The parts table: placement file and paste openings matched to heat-source shapes.
        @details `feature/paste-parts` fills it; until then the list is empty and the Parts step says so.
        @return list of part dicts (empty now).
        """
        return []

    def copper(self):
        """!
        @brief The imported copper of the model (`ImportedCopper`) for the chosen mapping and cell.
        @details `feature/imported-copper` provides it.
        @return None now.
        """
        return None

    def build_problem(self) -> Problem:
        """!
        @brief Build the new Problem of the import (a new project in format 2 with the import record).
        @return Problem
        @throws ImportNotAvailable Until `feature/imported-copper` is merged.
        """
        raise ImportNotAvailable("The imported copper of the model is not part of this version yet, so the project cannot be created from the files.")

    def heat_sources(self) -> list:
        """!
        @brief The parts ticked as heat sources.
        @return list (empty now).
        """
        return [p for p in self.parts() if p.get("use")]

    def memory_verdict(self, cell_mm: Optional[float] = None, pixel_mm: float = 0.05):
        """!
        @brief The memory guard's verdict for the FVM grid of the board and the memory of the rasters of the import.
        @details The FVM law of `pcbthermal.memory` on a board of the outline box with the layers in use, plus `estimate_raster_bytes` for the copper masks at the mask pixel; the measured
                 term of the import (`feature/imported-copper`) replaces the raster line when it merges.
        @param cell_mm Solver cell (mm); None: the session's.
        @param pixel_mm Pixel of the copper masks (mm).
        @return tuple (memory.Verdict, raster bytes) or None before the board is read.
        """
        b = self._board
        if b is None:
            return None
        cell = cell_mm if cell_mm else self.cell_mm
        prob = Problem.new(b.width, b.height, layers=max(2, len(b.copper)))
        v = memory.check(prob, ["fvm"], cell, base=memory.BASE_DEFAULT, refuse="return", quiet=True)[0]
        est = estimate_raster_bytes(window_of(b.box), pixel_mm, n_layers=len(b.copper))
        return v, est.peak_bytes

    def warnings(self) -> List[str]:
        """!
        @brief The warnings of the Model step (the import still runs).
        @details Includes the always-on notes about the Lumped and Analytic models on imported copper and the missing heat source.
        @return list of text lines.
        """
        out = []
        if not self.heat_sources():
            out.append("No heat source is defined: the board will have no power until you add one.")
        out.append("Lumped and Analytic models read imported copper from the cell fill and run about 1 to 16 % cool (6 % on average in the study windows).")
        out.append("The cell model of imported copper is approximate to a few percent, up to about 8 %; isolated diagonal copper on a coarse grid is the largest known error.")
        out.append("No physical measurement of an imported board exists yet: the accuracy is against another model of the same physics.")
        return out


__all__ = ["BoardData", "Hole", "ImportNotAvailable", "ImportSession", "LayerInfo", "ROLES", "SourceFile"]
