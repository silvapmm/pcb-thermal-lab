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
import io
import json
import os
import posixpath
import re
import shutil
import stat
import struct
import tempfile
import unicodedata
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
ORIGINS = ("folder", "zip")                         # The container a stored set came from; extract_sources rebuilds the same one
RENDERS_DIR = "renders/"

MAX_MEMBERS = 5000
# A package is read WHOLE into memory when it is opened (the Gerber ZIP reader reads one member at a time), so its limits are tighter than those of `gerber/archive.py`:
# review: with the archive's 2 GB and ratio 1000 a 0.7 MB package took 280 MB (two members at ratio 449) and a 5 MB one could take 2 GB. Real members compress at most
# 8.6 times (143 files of the open boards above 64 kB) and a project JSON with imported copper about 2.5 times, so 200 leaves a margin of 20.
# Second review: a 6.5 MB package of four sources at ratio 164 took 1.4 GB before its project was refused, and a 0.12 MB project JSON of nested empty lists at ratio 565
# took 1.9 GB in `json.loads` (about 43 bytes of Python objects per structural character). Real Gerber sets are at most 4.3 MB (the open boards of the local library) and
# 509 real files above 64 kB compress at most 19 times, so the limits below are generous for real files and bound what a small hostile file can make the reader allocate.
MAX_TOTAL_BYTES = 512 * 1024 ** 2                   # Declared uncompressed total (all of it is held in memory)
MAX_RATIO = 200.0                                   # Uncompressed over compressed bytes of one member (a zip bomb)
MAX_PROJECT_RATIO = 1000.0                          # The project JSON itself: repeated objects (identical vias copied in the editor) reach 255 and the archive's limit is kept
RATIO_FREE_BYTES = 64 * 1024                        # A member this small is not judged by the ratio (a tiny file of zeros has a big ratio and no danger)
OVERALL_FREE_BYTES = 64 * 1024 ** 2                 # A package whose members add up to more than this ...
MAX_OVERALL_RATIO = 20.0                            # ... must not compress more than this as a whole (many small members, or members just under MAX_RATIO, are a bomb too)
MAX_PROJECT_TOKENS = 8_000_000                      # Structural characters ([ { , :) of the project JSON: each becomes a Python object (8 M is about 350 MB; a real project has
                                                    # tens of thousands: 100 000 vias are about 1.5 M)
MAX_MANIFEST_BYTES = 16 * 1024 ** 2
MAX_PROJECT_BYTES = 512 * 1024 ** 2
MAX_OTHER_BYTES = 256 * 1024 ** 2                   # Images, renders and unknown members
NOT_A_PACKAGE = ("This ZIP is not a project package (no manifest.json); to import Gerber files use File - Import Gerber board")
GERBER_NOTE = ("Gerber file headers may carry folder paths and user names, and a third-party board keeps its owner's licence. The files are stored as they are "
               "(no comment is removed).")
IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"BM", b"GIF87a", b"GIF89a")   # Only an image is read from the disk into a package
_ZIP_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, ValueError, UnicodeDecodeError, struct.error, OverflowError, OSError)
_SAFE_PART = re.compile(r"[^\w.\- +()]")
EXTRACT_PREFIX = "pcbtz_gerber_"
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
MAX_WARNINGS = 20                                   # Read warnings kept per kind (a manifest of 16 MB can list a million names)
MAX_NAME_CHARS = 120                               # Longest file name written by extract_sources (well under the 255 bytes of common file systems)


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
        self.image_paths = {}                       # Disk path of the background -> its member, for the images a save of this session read from the disk
        self.foreign_background = None              # A background path of the package's JSON that is not one of its images: never read from the disk into a package

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
        @details The files go into a sub-folder named after the set (`<temporary folder>/<set>/`), so that the import session, which names the board after the folder,
                 keeps the name of the stored import (review: the record of a re-import from the stored files was named `pcbtz_gerber_...` and the package then held the
                 files twice, under the old and the temporary set name). Names are made safe for every file system (`_safe_file_name`) and never overwrite each other.
        @param set_name Set to extract (None: the first set).
        @return str: the folder of the files, or a ZIP file when the set came from a ZIP (same member names); the caller removes it with `remove_extracted` when the
                import is closed.
        @throws ProjectFormatError If the package stores no Gerber files or a member changed in memory.
        """
        sets = self.gerber_sets()
        if not sets:
            raise ProjectFormatError("this project stores no Gerber files")
        key = set_name if set_name in sets else sorted(sets)[0]
        top = tempfile.mkdtemp(prefix=EXTRACT_PREFIX)
        try:
            os.chmod(top, 0o700)
            as_zip = any(self.source_meta.get(m, {}).get("origin") == "zip" for _, m in sets[key])
            if as_zip:
                # The set came from a ZIP: rebuild a ZIP with the original member names (nothing named by the package touches the file system; the import's own
                # archive reader checks the names), so that the re-import sees the same names and hashes the members the same way
                folder = os.path.join(top, _safe_file_name(key) + ".zip")
                with zipfile.ZipFile(folder, "x", zipfile.ZIP_DEFLATED) as zf:
                    used = set()
                    for name, member in sets[key]:
                        original = self.source_meta.get(member, {}).get("original") or name
                        if original in used:
                            original = name
                        used.add(original)
                        zf.writestr(original, self._checked(member))
                return folder
            folder = os.path.join(top, _safe_file_name(key))
            os.mkdir(folder, 0o700)
            taken = set()
            for name, member in sets[key]:
                original = (self.source_meta.get(member, {}).get("original") or name).rsplit("/", 1)[-1]
                safe = _unique(_safe_file_name(original), taken)       # two hostile names that become the same safe name: the second gets a number
                taken.add(safe)
                with open(os.path.join(folder, safe), "xb") as fh:     # exclusive: never writes through an existing name
                    fh.write(self._checked(member))
        except BaseException:
            shutil.rmtree(top, ignore_errors=True)
            raise
        return folder

    def _checked(self, member):
        """!
        @brief The bytes of a stored file, checked again against the hash read from the package.
        @param member Member name.
        @return bytes.
        @throws ProjectFormatError If the bytes changed in memory.
        """
        data = self.sources[member]
        want = self._hashes.get(member) if hasattr(self, "_hashes") else None
        if want and hashlib.sha256(data).hexdigest() != want:
            raise ProjectFormatError(f"{member}: the stored file changed since the package was read")
        return data


def remove_extracted(folder):
    """!
    @brief Remove a folder made by `PackageExtras.extract_sources` (the set folder and its private parent).
    @param folder The folder or ZIP file `extract_sources` returned.
    @return None
    """
    parent = os.path.dirname(os.path.abspath(folder))
    if os.path.basename(parent).startswith(EXTRACT_PREFIX):
        shutil.rmtree(parent, ignore_errors=True)
    else:
        shutil.rmtree(folder, ignore_errors=True)


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
    @brief A file name safe to create in a private folder on any common file system.
    @details Only the last component is kept; characters outside letters, digits and `.-_ +()` become `_`; leading dots and trailing dots and spaces (which Windows drops,
             making two names one) are removed; a Windows device name (`CON`, `NUL`, `COM1`, ... with or without an extension) gets a leading `_`; the name is cut to
             MAX_NAME_CHARS characters, keeping its extension.
    @param name Name taken from a package.
    @return str: never empty, never starting with a dot.
    """
    base = _SAFE_PART.sub("_", unicodedata.normalize("NFC", name).rsplit("/", 1)[-1]).lstrip(".").rstrip(". ") or "file"
    if base.split(".", 1)[0].upper() in _WINDOWS_DEVICES:
        base = "_" + base
    if len(base) > MAX_NAME_CHARS:
        stem, ext = posixpath.splitext(base)
        ext = ext[:16]
        base = stem[:MAX_NAME_CHARS - len(ext)] + ext
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
        # The project first: a package whose project is refused costs no more than its project (review: four sources of 255 MB were read before the refusal)
        if PROJECT_MEMBER not in listed:
            raise ProjectFormatError(f"{PROJECT_MEMBER} is not listed in the manifest; the package may have been changed")
        data = _read_member(zf, infos[PROJECT_MEMBER], MAX_PROJECT_BYTES, PROJECT_MEMBER)
        if hashlib.sha256(data).hexdigest() != listed[PROJECT_MEMBER]["sha256"]:
            raise ProjectFormatError(f"{PROJECT_MEMBER} does not match the manifest (SHA-256 differs); the package was changed or damaged and is not opened")
        extras._hashes[PROJECT_MEMBER] = listed[PROJECT_MEMBER]["sha256"]
        _check_project_cost(data)
        parsed = loads_project_json(data)
        data = None
        for name, info in infos.items():
            if name in (MANIFEST, PROJECT_MEMBER):
                continue
            if name not in listed:                  # Present in the ZIP and not in the manifest: nothing to check it against
                extras.warnings.append(f"{name}: not listed in the manifest (kept, not verified)")
            blob = _read_member(zf, info, _limit_for(name), name)
            entry = listed.get(name)
            if entry is not None and hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                extras.warnings.append(f"{name}: does not match the manifest (SHA-256 differs); the member was dropped")
                continue
            if entry is not None:
                extras._hashes[name] = entry["sha256"]
                if name.startswith(SOURCES_DIR):
                    extras.source_meta[name] = {"kind": str(entry.get("kind", "other")), "function": str(entry.get("function", ""))}
                    for key in ("original", "origin"):         # Written since the review; an older package has neither (folder, member name)
                        if isinstance(entry.get(key), str):
                            extras.source_meta[name][key] = entry[key][:1024]
            if name.startswith(IMAGES_DIR):
                extras.images[name] = blob
            elif name.startswith(SOURCES_DIR):
                extras.sources[name] = blob
            elif name.startswith(RENDERS_DIR):
                extras.renders[name] = blob
            else:
                extras.unknown[name] = blob
        missing = [name for name in listed if name not in infos]
        for name in missing[:MAX_WARNINGS]:
            extras.warnings.append(f"{name[:200]}: listed in the manifest but missing from the package")
        if len(missing) > MAX_WARNINGS:
            extras.warnings.append(f"and {len(missing) - MAX_WARNINGS} more members listed in the manifest but missing from the package")
    extras.include_sources = bool(extras.sources)
    extras.is_package = True
    return parsed, extras


def _check_project_cost(raw):
    """!
    @brief Refuse a project JSON whose parse would allocate far more than its size suggests (a JSON bomb: nested empty lists or objects).
    @param raw Bytes of the project JSON.
    @return None
    @throws ProjectFormatError If it holds more than MAX_PROJECT_TOKENS structural characters (`[`, `{`, `,`, `:`; base64 masks hold none).
    """
    tokens = raw.count(b",") + raw.count(b"[") + raw.count(b"{") + raw.count(b":")
    if tokens > MAX_PROJECT_TOKENS:
        raise ProjectFormatError(f"{PROJECT_MEMBER} holds {tokens} JSON items (limit {MAX_PROJECT_TOKENS}); no project is that large, the package is refused")


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
    out, folded, total, packed = {}, {}, 0, 0
    for i in files:
        name = i.filename
        if name in out:
            raise ProjectFormatError(f"the package holds two members named {name!r}")
        fold = unicodedata.normalize("NFC", name).casefold()     # also NFC against NFD: one file on macOS, two members in the ZIP
        if fold in folded:
            raise ProjectFormatError(f"the package holds two names that differ only in case or Unicode normalisation: {folded[fold]!r} and {name!r}")
        mode = (i.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ProjectFormatError(f"member {name!r} is a symbolic link; the package is refused")
        if i.flag_bits & 0x1:
            raise ProjectFormatError(f"member {name!r} is encrypted")
        ratio = MAX_PROJECT_RATIO if name == PROJECT_MEMBER else MAX_RATIO
        if i.file_size > RATIO_FREE_BYTES and i.compress_size > 0 and i.file_size / i.compress_size > ratio:
            raise ProjectFormatError(f"member {name!r} has a compression ratio above {ratio:.0f} (zip bomb?)")
        total += i.file_size
        packed += i.compress_size
        out[name], folded[fold] = i, name
    if total > MAX_TOTAL_BYTES:
        raise ProjectFormatError(f"the package declares {total} uncompressed bytes (limit {MAX_TOTAL_BYTES})")
    if total > OVERALL_FREE_BYTES and total > MAX_OVERALL_RATIO * max(packed, 1):
        raise ProjectFormatError(f"the package expands {total / max(packed, 1):.0f} times ({total} bytes from {packed}; limit {MAX_OVERALL_RATIO:.0f} above "
                                 f"{OVERALL_FREE_BYTES // 1024 ** 2} MB): zip bomb?")
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
    bg = project.view.get("background") if isinstance(project.view, dict) else None
    if isinstance(bg, dict) and bg.get("path") and str(bg["path"]) not in extras.images:
        # The JSON of a package names a file outside it: drawn if it exists (as a .pcbt.json would), never copied into a later package (a hostile package could name
        # any private file of the reader's disk, and a re-save would carry it away)
        extras.foreign_background = str(bg["path"])
    project.package = extras
    return project


def load_any(path):
    """!
    @brief Load a project file of either kind, detected by content.
    @param path File path (`.pcbt.json`, `.pcbtz` or a legacy editor file; the extension is not looked at).
    @return Project (with `package` set for a package, None otherwise).
    @throws ProjectFormatError For a file this program must not open.
    """
    from .project import load_project
    return load_project(path)                       # load_project itself detects a package by its content


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
    if path in extras.images:
        return extras.images[path]
    return extras.images.get(extras.image_paths.get(path))      # a disk image that a save of this session stored (the file may be gone since)


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
    images, image_paths = {}, {}
    bg = view.get("background")
    if isinstance(bg, dict) and bg.get("path"):
        src = str(bg["path"])
        if src in extras.images:                     # Already a member of this package
            images[src] = extras.images[src]
        elif src == extras.foreign_background:
            notes.append("the background image path of the opened package points outside it; the file is not stored (choose the image again to store it)")
        else:
            try:
                with open(src, "rb") as fh:
                    blob = fh.read(MAX_OTHER_BYTES + 1)
                if len(blob) > MAX_OTHER_BYTES:
                    raise OSError("the image is too large for a package")
                if not blob.startswith(IMAGE_SIGNATURES):
                    raise OSError("the file is not a PNG, JPEG, BMP or GIF image")
                member = _unique(IMAGES_DIR + _safe_file_name(os.path.basename(src)), images)
                images[member] = blob
                image_paths[src] = member
                bg["path"] = member                  # Inside a package the path is relative
            except OSError as exc:
                kept = extras.image_paths.get(src)
                if kept in extras.images:
                    # Saved into this package before and gone from the disk since: the stored copy is kept (review: the image was lost at the next save and the
                    # absolute path of the user's disk was written in its place)
                    images[kept] = extras.images[kept]
                    image_paths[src] = kept
                    bg["path"] = kept
                else:
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
    extras.image_paths = image_paths
    return members, notes, extras


def _created(extras):
    """!
    @brief The creation time of a package: kept from the package that is saved again, so that a save of an unchanged project writes the same bytes.
    @param extras PackageExtras.
    @return str: UTC timestamp `YYYY-MM-DDTHH:MM:SSZ`.
    """
    if re.fullmatch(r"(19[89]\d|2\d{3})-\d\d-\d\dT\d\d:\d\d:\d\dZ", extras.created or ""):
        try:
            datetime.strptime(extras.created, "%Y-%m-%dT%H:%M:%SZ")
            return extras.created
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_bytes(members, extras):
    """!
    @brief The manifest.json for a set of members.
    @param members dict name -> bytes.
    @param extras PackageExtras (the unknown manifest keys are written back; `created` is kept, see `_created`).
    @return bytes.
    """
    entries = []
    for n, b in members.items():
        e = {"name": n, "size": len(b), "sha256": _sha(b)}
        if n.startswith(SOURCES_DIR):
            e.update(extras.source_meta.get(n, {"kind": "other", "function": ""}))
        entries.append(e)
    m = {"package_format": PACKAGE_FORMAT, "writer": f"pcbthermal {__version__}", "created": _created(extras), "members": entries}
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
    extras.created = _created(extras)
    manifest = _manifest_bytes(members, extras)
    data = package_bytes(manifest, members, extras.created)
    try:
        # The program never writes a package that it would refuse to read (a file far more compressible than any real one, a project above the limits)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _validate(zf)
        _check_project_cost(members[PROJECT_MEMBER])
        if len(members[PROJECT_MEMBER]) > MAX_PROJECT_BYTES:
            raise ProjectFormatError(f"{PROJECT_MEMBER} is {len(members[PROJECT_MEMBER])} bytes (limit {MAX_PROJECT_BYTES})")
        for name, blob in members.items():
            if len(blob) > _limit_for(name):
                raise ProjectFormatError(f"member {name!r} is {len(blob)} bytes (limit {_limit_for(name)})")
    except ProjectFormatError as exc:
        raise ProjectFormatError(f"the package cannot be written, it would not be readable: {exc}") from exc
    target = os.path.realpath(os.fspath(path))
    backup = None
    if os.path.exists(target) and not _is_package_or_missing(target):
        backup = _backup_path(target)                 # A JSON (or unreadable) file is replaced by a package: keep it
        shutil.copy2(target, backup)

    try:
        # The whole ZIP is built first, so that also the in-place write of a read-only folder is a single write of finished bytes
        _write_atomic(target, lambda fh: fh.write(data), binary=True)
    except BaseException:
        if backup:                                    # The old file was not replaced: its copy is not needed (review: each failed attempt left one more .bak)
            try:
                os.unlink(backup)
            except OSError:
                pass
        raise
    extras.writer = f"pcbthermal {__version__}"
    extras.is_package = True
    extras._hashes = {n: _sha(b) for n, b in members.items()}
    project.package = extras
    return backup, notes


def package_bytes(manifest, members, created):
    """!
    @brief The bytes of a package ZIP: deterministic (every member dated by the package's creation time, fixed permissions), so equal content gives equal bytes.
    @param manifest Bytes of manifest.json.
    @param members dict name -> bytes, in write order.
    @param created Creation time `YYYY-MM-DDTHH:MM:SSZ`.
    @return bytes.
    """
    when = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").timetuple()[:6]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, blob in [(MANIFEST, manifest)] + list(members.items()):
            info = zipfile.ZipInfo(name, date_time=when)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, blob, compresslevel=6)
    return buf.getvalue()


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


PRIVACY_HEAD_BYTES = 8192                           # Bytes of each stored file looked at by privacy_hints (the header and comments of a Gerber file sit at its top)
_PRIVACY_RULES = (
    ("a user folder path", re.compile(rb"(?:/Users/|/home/|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])[^\s*%\\/]{1,64}")),
    ("a network path", re.compile(rb"\\\\[A-Za-z0-9_.-]{1,64}\\")),
    ("an e-mail address", re.compile(rb"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){1,4}")),
    ("a user, author or computer name", re.compile(rb"(?i)\b(?:user(?:\s?name)?|author|login|computer|host(?:name)?|designer)\s{0,3}[:=]")),
)


def privacy_hints(sources, limit=PRIVACY_HEAD_BYTES):
    """!
    @brief Which stored source files carry text that may identify a person or a machine, by a cheap scan of their first bytes.
    @details Only the KIND of text found is returned, never the text itself (the rule of the CAD profiles: a banner can carry paths and user and computer names, and the
             program does not show or store them). Every pattern is bounded, so the scan is linear in the bytes looked at. A file without such text is not proven clean:
             the scan reads only the first `limit` bytes and knows only these patterns.
    @param sources dict member name -> bytes (`PackageExtras.sources`).
    @param limit Bytes of each file looked at.
    @return list of (file name, list of kinds), only for the files with a hint, in member order.
    """
    out = []
    for member in sorted(sources):
        head = bytes(sources[member][:limit])
        kinds = [label for label, rx in _PRIVACY_RULES if rx.search(head)]
        if kinds:
            out.append((member.rsplit("/", 1)[-1], kinds))
    return out


def attach_sources(project, files, set_name=None, replace=True):
    """!
    @brief Remember the source files of an import so that a package can store them.
    @details A project holds one import, so `replace=True` (a new import, a re-import by Replace or Update) drops EVERY stored set before the new files are kept (review: it
             dropped only the set of the new name, so a re-import from a folder of another name left the old set beside the new one, and `extract_sources` took the first set
             by name, possibly the stale one). `replace=False` (Add files) adds the files to the stored set when there is one.
    @param project The Project.
    @param files Iterable of (file name, bytes, kind, function[, origin]): the original name (a ZIP member with its folders), the ORIGINAL bytes, one of KINDS, the role
                 the import gave the file and the container it came from (one of ORIGINS, default "folder").
    @param set_name Name of the set (None: the stored set when adding to one, else the first import record's name, or "board").
    @param replace True: the stored files are replaced by these; False: these are added to them.
    @return int: number of files attached.
    """
    extras = getattr(project, "package", None) or PackageExtras()
    if replace:
        extras.sources, extras.source_meta = {}, {}
    if set_name is None:
        stored = sorted(extras.gerber_sets())
        set_name = stored[0] if stored and not replace else ((project.imports[0].name if project.imports else "") or "board")
    set_name = _safe_file_name(set_name).replace(" ", "_")[:60] or "board"
    taken = list(extras.sources)
    n = 0
    for item in files:
        name, blob, kind, function = item[:4]
        origin = item[4] if len(item) > 4 and item[4] in ORIGINS else "folder"
        member = _unique(f"{SOURCES_DIR}{set_name}/{_safe_file_name(name)}", taken)
        taken.append(member)
        extras.sources[member] = bytes(blob)
        # The original name (a ZIP member keeps its folders) and the container let a re-import read the same names, so the hashes and the pairing of the record hold
        extras.source_meta[member] = {"kind": kind if kind in KINDS else "other", "function": str(function), "original": str(name), "origin": origin}
        n += 1
    project.package = extras
    return n
