#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file package.py
@brief The project package `.pcbtz`: a standard ZIP that holds the project JSON, the images it uses and, on request, the Gerber files it was imported from.

A package is a ZIP file (deflate, readable by any zip tool) with these members:

  - `manifest.json`: `{"package_format": 1, "writer": "pcbthermal <version>", "created": <UTC timestamp>, "members": [{"name", "size", "sha256"}, ...]}`.
  - `project.pcbt.json`: exactly the JSON that a `.pcbt.json` file holds (format 1 or 2, the same code reads and writes it, `project.project_to_dict`).
  - `images/<name>`: the background image; inside a package the `path` of the background in the JSON is the relative name `images/<name>`.
  - `sources/<set>/<file>`: ALL the source files of an import under their ORIGINAL names (copper, mask, paste, silkscreen, outline, drills, the placement file, X3 component
    layers, a BOM when one was given), only when the user asked for them (Export package, 'Include the source files'). The manifest entry of each carries `kind` ("gerber",
    "drill", "placement", "bom", "x3", "other") and `function` (the role the import gave it), so a re-import reproduces the detection. The layout is not tied to Gerber: a later
    `sources/odbpp/...` or a normalised Gerber set made from it fits.
  - `renders/<name>`: preview pictures (none is written today; kept when a package holds them).
  - any other member: preserved on a round trip (it may come from a later version).

The file is HOSTILE, like a Gerber ZIP: the reader refuses an absolute or drive-lettered name, a backslash, a `..` component, a NUL or control character, a symbolic
link, an encrypted member, a duplicate name and two names that differ only in case, more than MAX_MEMBERS members, a declared total above MAX_TOTAL_BYTES, a member above its
limit and a compression ratio above MAX_RATIO; every member is read in memory with a bound on the bytes really read and checked against the SHA-256 of the manifest (a project
that does not match refuses the package; any other member that does not match is dropped with a warning). Nothing is written to disk by the reader. A nested ZIP is an
unknown member: kept as bytes, never opened. The type of a file is found by its CONTENT (the ZIP signature), never by its extension. A ZIP without `manifest.json` is not a
package.

The write is atomic (`project._write_atomic`) and keeps a `.bak` copy when it replaces a file of another kind (JSON by package or the reverse).
"""

import copy
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import struct
import tempfile
import zipfile
import zlib
from datetime import datetime, timezone

from . import __version__
from .fileschema import ProjectFormatError
from .gerber import limits
from .project import (FORMAT_1, FORMAT_2, Project, _backup_path, _write_atomic, loads_project_json, project_from_dict, project_to_dict, save_project)

PACKAGE_SUFFIX = ".pcbtz"
PACKAGE_FORMAT = 1                                  # The package layout this program writes and reads
MANIFEST = "manifest.json"
PROJECT_MEMBER = "project.pcbt.json"
IMAGES_DIR = "images/"
SOURCES_DIR = "sources/"                           # sources/<set>/<original file name>; the kind of each file is in the manifest ("gerber", "drill", "placement", "bom", "x3", "other"; room for "odbpp")
KINDS = ("gerber", "drill", "placement", "bom", "x3", "other")
RENDERS_DIR = "renders/"

MAX_MEMBERS = 5000
MAX_TOTAL_BYTES = 2 * 1024 ** 3                     # Declared uncompressed total
MAX_RATIO = 1000.0                                  # Uncompressed over compressed bytes of one member (a zip bomb)
RATIO_FREE_BYTES = 64 * 1024                        # A member this small is not judged by the ratio (a tiny file of zeros has a big ratio and no danger)
MAX_MANIFEST_BYTES = 16 * 1024 ** 2
MAX_PROJECT_BYTES = 512 * 1024 ** 2
MAX_OTHER_BYTES = 256 * 1024 ** 2                   # Images, renders and unknown members
NOT_A_PACKAGE = ("This ZIP is not a project package (no manifest.json); to import Gerber files use File - Import Gerber board")
GERBER_NOTE = ("Gerber file headers may carry folder paths and user names, and a third-party board keeps its owner's licence. The files are stored as they are "
               "(no comment is removed).")
_ZIP_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, ValueError, UnicodeDecodeError, struct.error, OverflowError, OSError)
_SAFE_PART = re.compile(r"[^\w.\- +()]")


class PackageExtras:
    """!
    @brief What a package holds besides the project JSON, kept in memory while the project is open (never written to disk by the reader).
    @details `images`, `renders`, `sources` and `unknown` map the member name to its bytes. `include_sources` says whether a save writes the Gerber files. The attribute `warnings`
             lists what the last read dropped or could not check.
    """

    def __init__(self):
        """!@brief Create empty extras (a package with nothing but the project)."""
        self.images, self.renders, self.sources, self.unknown = {}, {}, {}, {}
        self.source_meta = {}                       # source member -> {"kind", "function"} (manifest fields, written back)
        self.manifest_extra = {}                    # Top-level manifest keys of a later version, written back
        self.include_sources = False
        self.is_package = False                     # True when the open file is a package (read from one or saved as one): Save keeps that format
        self.writer = ""
        self.created = ""
        self.warnings = []

    def gerber_sets(self):
        """!
        @brief The stored Gerber files grouped by set.
        @return dict: set name -> list of (file name, member name).
        """
        out = {}
        for member in sorted(self.sources):
            parts = member[len(SOURCES_DIR):].split("/", 1)
            if len(parts) == 2:
                out.setdefault(parts[0], []).append((parts[1], member))
        return out

    def has_sources(self):
        """!
        @brief Whether the package stores Gerber files.
        @return bool.
        """
        return bool(self.sources)

    def extract_sources(self, set_name=None):
        """!
        @brief Write the stored Gerber files of one set to a new private folder (mode 0700), checking their hash again, so that the import can read a folder.
        @param set_name Set to extract (None: the first set).
        @return str: the folder; the caller removes it (`shutil.rmtree`) when the import is closed.
        @throws ProjectFormatError If the package stores no Gerber files or a member changed in memory.
        """
        sets = self.gerber_sets()
        if not sets:
            raise ProjectFormatError("this project stores no Gerber files")
        key = set_name if set_name in sets else sorted(sets)[0]
        folder = tempfile.mkdtemp(prefix="pcbtz_gerber_")
        try:
            os.chmod(folder, 0o700)
            for name, member in sets[key]:
                data = self.sources[member]
                want = self._hashes.get(member) if hasattr(self, "_hashes") else None
                if want and hashlib.sha256(data).hexdigest() != want:
                    raise ProjectFormatError(f"{member}: the stored file changed since the package was read")
                safe = _safe_file_name(name)
                with open(os.path.join(folder, safe), "wb") as fh:
                    fh.write(data)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return folder


# ------------------------------------------------------------------------------------------------------------------------------------ detection
def is_package(path):
    """!
    @brief Whether a file is a ZIP, by its first bytes (the extension is not looked at).
    @param path File path.
    @return bool: True for the ZIP signature (a local header or the end record of an empty ZIP); False for anything else or an unreadable file.
    """
    try:
        with open(path, "rb") as fh:
            return fh.read(4) in (b"PK\x03\x04", b"PK\x05\x06")
    except OSError:
        return False


def _safe_file_name(name):
    """!
    @brief A file name safe to create in a private folder.
    @param name Name taken from a package.
    @return str: the last component with unusual characters replaced (never empty, never starting with a dot).
    """
    base = _SAFE_PART.sub("_", name.rsplit("/", 1)[-1]).lstrip(".") or "file"
    return base


def _check_name(name):
    """!
    @brief Check one member name against zip-slip and odd names.
    @param name Name as stored.
    @return str: the name.
    @throws ProjectFormatError For an absolute name, a drive letter, a backslash, a `..` or empty component, a NUL or other control character.
    """
    bad = (not name or "\\" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name) is not None or any(ord(c) < 32 or ord(c) == 127 for c in name))
    parts = name.rstrip("/").split("/")
    if bad or any(p in ("", ".", "..") for p in parts):
        raise ProjectFormatError(f"unsafe member name in the package: {name!r}")
    return name


def _read_member(zf, info, limit, name):
    """!
    @brief Read one member in memory, never more than it declares.
    @param zf Open ZipFile.
    @param info ZipInfo of the member.
    @param limit Largest size accepted in bytes.
    @param name Name for the messages.
    @return bytes.
    @throws ProjectFormatError For a member above the limit, one that holds more bytes than it declares, or a damaged one (CRC, deflate).
    """
    if info.file_size > limit:
        raise ProjectFormatError(f"member {name!r} declares {info.file_size} bytes (limit {limit})")
    try:
        with zf.open(info) as fh:
            data = fh.read(info.file_size + 1)
    except _ZIP_ERRORS as exc:
        raise ProjectFormatError(f"member {name!r} cannot be read ({type(exc).__name__}: {exc}); the package may be damaged") from exc
    if len(data) > info.file_size:
        raise ProjectFormatError(f"member {name!r} holds more bytes than it declares")
    return data


def _limit_for(name):
    """!
    @brief The size limit of a member by its place in the package.
    @param name Member name.
    @return int bytes.
    """
    if name == PROJECT_MEMBER:
        return MAX_PROJECT_BYTES
    if name.startswith(SOURCES_DIR):
        return limits.max_file_bytes()
    return MAX_OTHER_BYTES


# ------------------------------------------------------------------------------------------------------------------------------------ reading
def read_package(path):
    """!
    @brief Read and verify a package.
    @param path File path.
    @return tuple (project JSON as a dict, PackageExtras).
    @throws ProjectFormatError If the file is not a package, is unsafe, damaged, of a newer package format, or its project does not match the manifest.
    """
    try:
        zf = zipfile.ZipFile(path)
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        raise
    except _ZIP_ERRORS as exc:
        raise ProjectFormatError(f"this file looks like a ZIP but cannot be read ({type(exc).__name__}: {exc}); it may be damaged") from exc
    with zf:
        infos = _validate(zf)
        if MANIFEST not in infos:
            raise ProjectFormatError(NOT_A_PACKAGE)
        manifest = _parse_manifest(_read_member(zf, infos[MANIFEST], MAX_MANIFEST_BYTES, MANIFEST))
        if PROJECT_MEMBER not in infos:
            raise ProjectFormatError(f"the package has no {PROJECT_MEMBER}")
        listed = {m["name"]: m for m in manifest["members"]}
        extras = PackageExtras()
        extras.writer, extras.created = str(manifest.get("writer", "")), str(manifest.get("created", ""))
        extras.manifest_extra = {k: v for k, v in manifest.items() if k not in ("package_format", "writer", "created", "members")}
        extras._hashes = {}
        data = None
        for name, info in infos.items():
            if name == MANIFEST:
                continue
            if name not in listed:                  # Present in the ZIP and not in the manifest: nothing to check it against
                if name == PROJECT_MEMBER:
                    raise ProjectFormatError(f"{PROJECT_MEMBER} is not listed in the manifest; the package may have been changed")
                extras.warnings.append(f"{name}: not listed in the manifest (kept, not verified)")
            blob = _read_member(zf, info, _limit_for(name), name)
            entry = listed.get(name)
            if entry is not None and hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                if name == PROJECT_MEMBER:
                    raise ProjectFormatError(f"{PROJECT_MEMBER} does not match the manifest (SHA-256 differs); the package was changed or damaged and is not opened")
                extras.warnings.append(f"{name}: does not match the manifest (SHA-256 differs); the member was dropped")
                continue
            if entry is not None:
                extras._hashes[name] = entry["sha256"]
                if name.startswith(SOURCES_DIR):
                    extras.source_meta[name] = {"kind": str(entry.get("kind", "other")), "function": str(entry.get("function", ""))}
            if name == PROJECT_MEMBER:
                data = blob
            elif name.startswith(IMAGES_DIR):
                extras.images[name] = blob
            elif name.startswith(SOURCES_DIR):
                extras.sources[name] = blob
            elif name.startswith(RENDERS_DIR):
                extras.renders[name] = blob
            else:
                extras.unknown[name] = blob
        for name in listed:
            if name not in infos:
                extras.warnings.append(f"{name}: listed in the manifest but missing from the package")
    extras.include_sources = bool(extras.sources)
    extras.is_package = True
    return loads_project_json(data), extras


def _validate(zf):
    """!
    @brief Check every member name, type and size of an open ZIP before anything is read.
    @param zf Open ZipFile.
    @return dict: name -> ZipInfo of the files (directory entries are checked and left out).
    @throws ProjectFormatError For an unsafe package.
    """
    all_infos = zf.infolist()
    for i in all_infos:
        _check_name(i.filename)
    files = [i for i in all_infos if not i.is_dir()]
    if len(files) > MAX_MEMBERS:
        raise ProjectFormatError(f"the package has {len(files)} members (limit {MAX_MEMBERS})")
    out, folded, total = {}, {}, 0
    for i in files:
        name = i.filename
        if name in out:
            raise ProjectFormatError(f"the package holds two members named {name!r}")
        if name.casefold() in folded:
            raise ProjectFormatError(f"the package holds two names that differ only in case: {folded[name.casefold()]!r} and {name!r}")
        mode = (i.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ProjectFormatError(f"member {name!r} is a symbolic link; the package is refused")
        if i.flag_bits & 0x1:
            raise ProjectFormatError(f"member {name!r} is encrypted")
        if i.file_size > RATIO_FREE_BYTES and i.compress_size > 0 and i.file_size / i.compress_size > MAX_RATIO:
            raise ProjectFormatError(f"member {name!r} has a compression ratio above {MAX_RATIO:.0f} (zip bomb?)")
        total += i.file_size
        out[name], folded[name.casefold()] = i, name
    if total > MAX_TOTAL_BYTES:
        raise ProjectFormatError(f"the package declares {total} uncompressed bytes (limit {MAX_TOTAL_BYTES})")
    return out


def _parse_manifest(raw):
    """!
    @brief Parse and check the manifest.
    @param raw Bytes of manifest.json.
    @return dict.
    @throws ProjectFormatError For a manifest that is not JSON, is malformed, or of a newer package format (the message names the writer).
    """
    try:
        m = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise ProjectFormatError(f"manifest.json cannot be read ({exc}); the package may be damaged") from exc
    if not isinstance(m, dict):
        raise ProjectFormatError("manifest.json is not an object; the package may be damaged")
    fmt = m.get("package_format")
    if isinstance(fmt, bool) or not isinstance(fmt, int):
        raise ProjectFormatError("manifest.json has no integer package_format; the package may be damaged")
    if fmt > PACKAGE_FORMAT:
        raise ProjectFormatError(f"this package has format {fmt}, newer than this program reads ({PACKAGE_FORMAT}); it was written by {m.get('writer', 'a later version')}. "
                                 f"Open it with that version or a later one")
    members = m.get("members")
    if not isinstance(members, list):
        raise ProjectFormatError("manifest.json has no list of members; the package may be damaged")
    for e in members:
        if not (isinstance(e, dict) and isinstance(e.get("name"), str) and isinstance(e.get("sha256"), str)):
            raise ProjectFormatError("manifest.json lists a member without a name or a hash; the package may be damaged")
    return m


def load_package(path):
    """!
    @brief Load a package as a Project; the extras are attached as `project.package`.
    @param path File path.
    @return Project.
    @throws ProjectFormatError As read_package and project_from_dict.
    """
    data, extras = read_package(path)
    project = project_from_dict(data)
    project.package = extras
    return project


def load_any(path):
    """!
    @brief Load a project file of either kind, detected by content.
    @param path File path (`.pcbt.json`, `.pcbtz` or a legacy editor file; the extension is not looked at).
    @return Project (with `package` set for a package, None otherwise).
    @throws ProjectFormatError For a file this program must not open.
    """
    if is_package(path):
        return load_package(path)
    from .project import load_project
    return load_project(path)


def background_bytes(project, path):
    """!
    @brief The bytes of a background image that the package of the project holds.
    @param project Project (its `package` may be None).
    @param path The `path` of the background as the view settings hold it.
    @return bytes or None (the image is not stored in the package: read the file).
    """
    extras = getattr(project, "package", None)
    if extras is None:
        return None
    return extras.images.get(path)


# ------------------------------------------------------------------------------------------------------------------------------------ writing
def _unique(name, taken):
    """!
    @brief A member name not in a set, by adding a number before the extension.
    @param name Wanted name.
    @param taken Names in use (compared without case).
    @return str.
    """
    low = {t.casefold() for t in taken}
    stem, ext = posixpath.splitext(name)
    candidate, n = name, 2
    while candidate.casefold() in low:
        candidate, n = f"{stem}_{n}{ext}", n + 1
    return candidate


def _sha(data):
    """!
    @brief SHA-256 hex digest.
    @param data Bytes.
    @return str.
    """
    return hashlib.sha256(data).hexdigest()


def build_members(project, include_sources=None):
    """!
    @brief The members of the package a save would write, and the notes about what could not be stored.
    @param project Project (its `package` extras are kept; None means a plain project).
    @param include_sources True or False to decide whether the Gerber files go in (None: the extras' own choice).
    @return tuple (dict name -> bytes in write order, list of warning texts, PackageExtras after the save).
    """
    extras = copy.copy(getattr(project, "package", None)) or PackageExtras()
    notes = []
    if include_sources is not None:
        extras.include_sources = bool(include_sources)
    d = project_to_dict(project)
    view = d["view"] if d.get("format") == FORMAT_1 else d["project"]["view"]
    view = copy.deepcopy(view)
    images = {}
    bg = view.get("background")
    if isinstance(bg, dict) and bg.get("path"):
        src = str(bg["path"])
        if src in extras.images:                     # Already a member of this package
            images[src] = extras.images[src]
        else:
            try:
                with open(src, "rb") as fh:
                    blob = fh.read(MAX_OTHER_BYTES + 1)
                if len(blob) > MAX_OTHER_BYTES:
                    raise OSError("the image is too large for a package")
                member = _unique(IMAGES_DIR + _safe_file_name(os.path.basename(src)), images)
                images[member] = blob
                bg["path"] = member                  # Inside a package the path is relative
            except OSError as exc:
                notes.append(f"the background image {src} could not be stored in the package ({exc}); its path is kept")
    # The serialised project must carry the rewritten path: patch the copy of the dict
    if d.get("format") == FORMAT_1:
        d["view"] = view
    else:
        d["project"]["view"] = view
    members = {PROJECT_MEMBER: json.dumps(d, indent=2).encode("utf-8")}
    members.update(images)
    members.update(extras.renders)
    if extras.include_sources:
        members.update(extras.sources)
    for name, blob in extras.unknown.items():
        members.setdefault(name, blob)
    extras = copy.copy(extras)
    extras.images = images
    return members, notes, extras


def _manifest_bytes(members, extras):
    """!
    @brief The manifest.json for a set of members.
    @param members dict name -> bytes.
    @param extras PackageExtras (the unknown manifest keys are written back).
    @return bytes.
    """
    entries = []
    for n, b in members.items():
        e = {"name": n, "size": len(b), "sha256": _sha(b)}
        if n.startswith(SOURCES_DIR):
            e.update(extras.source_meta.get(n, {"kind": "other", "function": ""}))
        entries.append(e)
    m = {"package_format": PACKAGE_FORMAT, "writer": f"pcbthermal {__version__}", "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "members": entries}
    for k, v in extras.manifest_extra.items():
        m.setdefault(k, copy.deepcopy(v))
    return json.dumps(m, indent=2).encode("utf-8")


def save_package(path, project, include_sources=None):
    """!
    @brief Write a project as a package, atomically (temporary file in the same folder, flushed, renamed); the old file is kept as `.bak` when it is of another kind.
    @param path Target path.
    @param project The Project; its extras become the ones of the written package (`project.package` is set).
    @param include_sources True/False: write the stored source files or not (None: as the extras say).
    @return tuple (backup path or None, list of notes about what could not be stored).
    @throws PermissionError If the existing file is read-only.
    """
    members, notes, extras = build_members(project, include_sources)
    manifest = _manifest_bytes(members, extras)
    target = os.path.realpath(os.fspath(path))
    backup = None
    if os.path.exists(target) and not _is_package_or_missing(target):
        backup = _backup_path(target)                 # A JSON (or unreadable) file is replaced by a package: keep it
        shutil.copy2(target, backup)

    def write(fh):
        """!
        @brief Write the ZIP to an open binary file.
        @param fh File object.
        """
        with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.writestr(MANIFEST, manifest)
            for name, blob in members.items():
                zf.writestr(name, blob)

    _write_atomic(target, write, binary=True)
    extras.writer = f"pcbthermal {__version__}"
    extras.is_package = True
    extras._hashes = {n: _sha(b) for n, b in members.items()}
    project.package = extras
    return backup, notes


def _is_package_or_missing(path):
    """!
    @brief Whether an existing file is a package.
    @param path File path.
    @return bool.
    """
    return is_package(path)


def save_any(path, project, as_package=None, include_sources=None):
    """!
    @brief Save a project in the format of the open file: a package stays a package, a JSON file stays JSON.
    @param path Target path.
    @param project The Project.
    @param as_package True for a package, False for JSON, None: by the suffix (`.pcbtz` package, `.pcbt.json` JSON), else the format of the open file.
    @param include_sources Passed to save_package.
    @return tuple (backup path or None, list of notes).
    """
    if as_package is None:
        low = str(path).lower()
        as_package = low.endswith(PACKAGE_SUFFIX) or (not low.endswith(".pcbt.json") and project.package is not None and project.package.is_package)
    if as_package:
        return save_package(path, project, include_sources)
    notes = []
    extras = getattr(project, "package", None)
    if extras is not None and extras.is_package:
        notes.extend(dropped_text(extras))
    backup = save_project(path, project)
    if extras is not None:
        extras.is_package = False                   # The open file is JSON now; the images and source files stay in memory for a later export
    return backup, notes


def dropped_text(extras):
    """!
    @brief What a plain `.pcbt.json` cannot hold, from the extras of a package.
    @param extras PackageExtras.
    @return list of texts (empty when nothing is lost).
    """
    notes = []
    if extras.images:
        notes.append(f"{len(extras.images)} image(s) are not stored in a plain project file")
    if extras.sources:
        notes.append(f"{len(extras.sources)} stored source file(s) are not stored in a plain project file")
    if extras.renders:
        notes.append(f"{len(extras.renders)} preview(s) are not stored in a plain project file")
    if extras.unknown:
        notes.append(f"{len(extras.unknown)} other member(s) of the package are not stored in a plain project file")
    return notes


def attach_sources(project, files, set_name=None, replace=True):
    """!
    @brief Remember the source files of an import so that a package can store them.
    @param project The Project.
    @param files Iterable of (file name, bytes, kind, function): the original name, the content, one of KINDS and the role the import gave the file.
    @param set_name Name of the set (None: from the first import record, or "board").
    @param replace True: the stored files of the set are replaced by these; False: these are added to them.
    @return int: number of files attached.
    """
    extras = getattr(project, "package", None) or PackageExtras()
    if set_name is None:
        set_name = (project.imports[0].name if project.imports else "") or "board"
    set_name = _safe_file_name(set_name).replace(" ", "_")[:60] or "board"
    for member in [m for m in extras.sources if replace and m.startswith(f"{SOURCES_DIR}{set_name}/")]:
        del extras.sources[member]
        extras.source_meta.pop(member, None)
    taken = list(extras.sources)
    n = 0
    for name, blob, kind, function in files:
        member = _unique(f"{SOURCES_DIR}{set_name}/{_safe_file_name(name)}", taken)
        taken.append(member)
        extras.sources[member] = bytes(blob)
        extras.source_meta[member] = {"kind": kind if kind in KINDS else "other", "function": str(function)}
        n += 1
    project.package = extras
    return n
