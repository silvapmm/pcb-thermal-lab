#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file project.py
@brief Project files: a Problem plus its SolverOptions and free-form viewer metadata.

A project is the native JSON structure with two extra keys: "solver" (SolverOptions) and
"view" (anything the GUI wants to remember, such as the background image and its scale).
Plain native files and legacy editor files are read as well.

Format 2 (`pcbthermal-project-2`) is written only when the project holds imported boards (`Project.imports`). It NESTS the whole format 1
project under a "project" key next to an "imports" list, so that the released 2.4.x readers, which read data["board"] first, raise KeyError('board')
and report "Cannot open file" instead of opening the file, dropping the imports and saving it back as format 1. A project without imports
stays format 1, byte-identical to earlier versions. A file of a newer format than this program knows is refused with the writer's version.
Keys of a format 2 file that this version does not know (at the top level and inside the import records) are kept and written back, so that a
later 2.x that adds a field does not lose it through this version. A save is atomic (temporary file and rename) and keeps a `.bak` copy of
the old file whenever it changes the format of the file on disk.
"""

import json
import os
import re
import shutil
import tempfile
import copy
import errno
from dataclasses import dataclass, field

from . import __version__
from .api import SolverOptions
from .copper import has_mask
from .fileschema import ProjectFormatError, describe, guard
from .model import ImportRecord, Problem, problem_from_dict, problem_from_legacy, problem_to_dict

PROJECT_SUFFIX = ".pcbt.json"
FORMAT_1 = "pcbthermal-project-1"
FORMAT_2 = "pcbthermal-project-2"
KNOWN_FORMATS = (1, 2)                              # Format numbers this program reads
FORMAT_2_KEYS = ("format", "app_version", "project", "imports")   # Top-level keys of format 2 that this version reads


@dataclass
class Project:
    """!
    @brief Everything needed to reopen a session.
    """
    problem: Problem
    options: SolverOptions = field(default_factory=SolverOptions)
    view: dict = field(default_factory=dict)         # Viewer state: background image, zoom, ...
    imports: list = field(default_factory=list)      # ImportRecord list; non-empty makes the file format 2
    extra: dict = field(default_factory=dict)        # Top-level keys of a format 2 file this version does not know, written back unchanged
    package: object = field(default=None, compare=False, repr=False)   # package.PackageExtras of a project that came from (or is saved as) a `.pcbtz`; never in the JSON

    def run_problem(self):
        """!
        @brief The Problem to hand to the models: the project's problem with the imported copper of its first import record that holds masks.
        @details The native problem JSON carries no copper masks (they live in the import records, format 2); `project_from_dict` calls this, so a loaded project's problem
                 already reads its copper, and a program that edits the records calls it again. The copy is shallow (the elements and the packed masks are shared, nothing is
                 duplicated); a project without imported copper returns its own problem, and a problem that holds copper but no record keeps it.
        @return Problem.
        """
        for rec in self.imports:
            c = rec.copper
            if c is not None and any(has_mask(e) for e in c.layers):
                q = copy.copy(self.problem)
                q.imported = c
                return q
        return self.problem


def project_to_dict(project):
    """!
    @brief Serialise a Project.
    @details Format 1 (the project dict) when there are no imports; otherwise format 2, which nests that dict under "project" and writes back
             the top-level keys of a format 2 file that this version did not know (`Project.extra`).
    @param project A Project.
    @return JSON-ready dict.
    """
    d = problem_to_dict(project.problem)
    d["solver"] = project.options.to_dict()
    d["view"] = project.view
    d["format"] = FORMAT_1
    d["app_version"] = __version__                  # Version that wrote the file (informational)
    imports = list(project.imports)
    own = getattr(project.problem, "imported", None)
    if own is not None and any(has_mask(e) for e in own.layers) and not any(r.copper is not None and any(has_mask(e) for e in r.copper.layers) for r in imports):
        # The problem holds imported copper that no record carries (a problem made by ImportedBoard.to_problem and saved as it is): the native problem JSON has
        # no place for the masks, so without a record they were dropped and the file reopened as a bare board. Write them in a record of their own
        imports.append(ImportRecord(name="imported copper", copper=own))
    if not imports:
        return d
    out = {"format": FORMAT_2, "app_version": __version__, "project": d, "imports": [r.to_dict() for r in imports]}
    for key, value in project.extra.items():        # Forward compatibility: what a later 2.x added survives a save by this version
        out.setdefault(key, copy.deepcopy(value))
    return out


def format_number(data):
    """!
    @brief The format number of a parsed project file.
    @param data Parsed JSON.
    @return int: 1 for a file with no "format" key (plain native or legacy) or format 1, 2 for format 2.
    @throws ProjectFormatError If the format is newer than this program knows or is not a project format; the message names the writer's version.
    """
    if not isinstance(data, dict):                  # A JSON list or a bare value: not a project (a traceback otherwise)
        raise ProjectFormatError("this file is not a PCB Thermal Lab project (its JSON is not an object)")
    fmt = data.get("format")
    if fmt is None:
        return 1
    m = re.fullmatch(r"pcbthermal-project-(\d+)", str(fmt))
    if not m or int(m.group(1)) < 1:                # Format 0 does not exist: it is not "newer", it is unknown
        raise ProjectFormatError(f"unknown project format {fmt!r}")
    n = int(m.group(1))
    if n not in KNOWN_FORMATS:
        writer = data.get("app_version")
        who = f"PCB Thermal Lab {writer}" if writer else "a newer version of PCB Thermal Lab"
        raise ProjectFormatError(f"this project file is format {n}, written by {who}; this program ({__version__}) reads formats 1 and 2 only. "
                                 "Open it with that version or a later one.")
    return n


def project_from_dict(data, validate=True):
    """!
    @brief Read a Project from a dict (native, project or legacy editor structure; format 1 or 2).
    @param data Parsed JSON.
    @param validate If False, accept a transiently inconsistent problem (undo snapshots).
    @return Project.
    @throws ProjectFormatError For a newer format, a JSON that is not an object, or a format 2 file without its "project" section or with a
            malformed "imports" section.
    """
    imports, extra = [], {}
    if format_number(data) == 2:
        if not isinstance(data.get("project"), dict):
            raise ProjectFormatError("format 2 project file without its \"project\" section")
        raw = data.get("imports", [])
        if not isinstance(raw, list):
            raise ProjectFormatError("format 2 project file whose \"imports\" section is not a list")
        imports = []
        for i, r in enumerate(raw):                 # A hand-edited or damaged record: a message that names it, not a traceback
            with guard(f"imports[{i}]"):
                if not isinstance(r, dict):
                    raise ProjectFormatError(f"imports[{i}]: expected an object, got {describe(r)}")
                imports.append(ImportRecord.from_dict(r))
        with guard("unknown top-level keys"):       # Kept for a later version; a copy of values nested hundreds of levels deep raises RecursionError
            extra = {k: copy.deepcopy(v) for k, v in data.items() if k not in FORMAT_2_KEYS}
        data = data["project"]
    if "pcb_params" in data:
        with guard("legacy editor file"):
            problem = problem_from_legacy(data)
    else:
        problem = problem_from_dict(data, validate)
    if data.get("solver") is not None and not isinstance(data["solver"], dict):
        raise ProjectFormatError(f"solver: expected an object, got {describe(data['solver'])}")
    if data.get("view") is not None and not isinstance(data["view"], dict):
        raise ProjectFormatError(f"view: expected an object, got {describe(data['view'])}")
    with guard("solver"):
        options = SolverOptions.from_dict(data.get("solver"))
    project = Project(problem=problem, options=options, view=dict(data.get("view") or {}), imports=imports, extra=extra)
    project.problem = project.run_problem()          # The masks live in the import records; the models read them from the problem (shares the packed text)
    return project


def load_project(path):
    """!
    @brief Load a project file: a `.pcbt.json` (or legacy editor JSON), or a `.pcbtz` package, found by its content.
    @param path File path.
    @return Project (with `package` set for a package).
    @throws ProjectFormatError For a file of a format this program does not know, or a file that is not valid JSON.
    """
    # Every reader of a project (the commands `transient` and `convergence`, `model.load_problem`, the API) goes through here, so a package is read wherever a
    # project is (review: only the commands that called `package.load_any` read one; the others said "not UTF-8 text"); imported here, package imports this module
    from . import package
    if package.is_package(path):
        return package.load_package(path)
    return project_from_dict(read_project_json(path))


def read_project_json(path):
    """!
    @brief Parse a project file as JSON, turning a damaged file into a clear message.
    @param path File path.
    @return The parsed JSON.
    @throws ProjectFormatError If the file is not valid JSON (the message gives the line and column).
    """
    with open(path, "rb") as fh:
        return loads_project_json(fh.read())


def loads_project_json(raw):
    """!
    @brief Parse the bytes of a project JSON, turning a damaged file into a clear message (shared by `.pcbt.json` files and the project member of a package).
    @param raw Bytes of the file.
    @return The parsed JSON.
    @throws ProjectFormatError If the bytes are not valid UTF-8 JSON (the message gives the line and column).
    """
    try:
        # Text mode of the old reader: a UTF-8 file with a byte order mark was never accepted, so none is skipped here either
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectFormatError(f"this file is not valid JSON ({exc}); it may be damaged or not a project file") from exc
    except UnicodeDecodeError as exc:          # Bytes that are not UTF-8 (a binary or damaged file)
        raise ProjectFormatError(f"this file is not UTF-8 text ({exc.reason} at byte {exc.start}); it may be damaged or not a project file") from exc
    except ValueError as exc:                  # A number of more than 4300 digits: Python refuses to read it
        raise ProjectFormatError(f"this file holds a value that cannot be read ({exc}); it may be damaged or not a project file") from exc
    except RecursionError as exc:              # Lists or objects nested thousands of levels deep: no project is like that
        raise ProjectFormatError("this file is nested too deeply to be a project (lists or objects inside each other thousands of times)") from exc


def _file_format(path):
    """!
    @brief The format string of an existing file, without raising.
    @param path File path.
    @return str: FORMAT_2 for a format 2 file, FORMAT_1 for any other readable project, "" for a missing, unreadable or non-JSON file.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    return FORMAT_2 if str(data.get("format")) == FORMAT_2 else FORMAT_1


def _backup_path(path):
    """!
    @brief The first free backup name next to a file: `<path>.bak`, then `<path>.bak2`, `<path>.bak3`, ...
    @param path File path.
    @return str, a name that does not exist yet (an older backup is never overwritten).
    """
    candidate, n = f"{path}.bak", 2
    while os.path.lexists(candidate):
        candidate, n = f"{path}.bak{n}", n + 1
    return candidate


def _umask():
    """!
    @brief The process umask (read by setting and restoring it), for the permissions of a new file.
    @return int.
    """
    mask = os.umask(0)
    os.umask(mask)
    return mask


def _write_text_atomic(path, text):
    """!
    @brief Write a text file atomically (see `_write_atomic`).
    @param path Target path (a symbolic link is resolved, so the link stays and its target is replaced).
    @param text File content.
    @throws PermissionError If the existing file is read-only (it is not replaced behind the user's back).
    """
    _write_atomic(path, lambda fh: fh.write(text), binary=False)


def _write_atomic(path, write, binary):
    """!
    @brief Write a file so that a crash or an error during the write never leaves a truncated file in place of the old one.
    @details The content goes to a temporary file in the same folder, is flushed to the disk and then renamed over the target (`os.replace`,
             atomic on POSIX and on Windows NTFS). The permission bits of an existing file are kept; a new file gets the usual permissions
             (0666 minus the umask). When the folder does not allow a new file (a writable file in a read-only folder) the file is written in
             place, as the earlier versions did; the content is already built, so only an input/output error can interrupt it.
    @param path Target path (a symbolic link is resolved, so the link stays and its target is replaced).
    @param write Function(file object) that writes the whole content.
    @param binary True for a binary file (a package), False for UTF-8 text (a project JSON, with the line ends of earlier versions).
    @throws PermissionError If the existing file is read-only (it is not replaced behind the user's back).
    """
    if os.path.exists(path) and not os.access(path, os.W_OK):
        raise PermissionError(errno.EACCES, "the file is read-only", path)
    folder = os.path.dirname(os.path.abspath(path))
    try:
        fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=folder)
    except OSError:
        with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as fh:
            write(fh)
        return
    try:
        with os.fdopen(fd, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as fh:   # Text mode as before, so the line ends are those of earlier versions
            write(fh)
            fh.flush()
            os.fsync(fh.fileno())
        if os.path.exists(path):
            shutil.copymode(path, tmp)
        else:
            os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_project(path, project):
    """!
    @brief Save a project file.
    @details The project is serialised first (a value that cannot be written fails before the file is touched) and written atomically, so
             the old file stays whole if the save is interrupted. When the save changes the format of an existing file (format 1 to 2, the
             first save of a project with imports over an older file; or format 2 to 1, a project without imports over a file with imports),
             the old file is first copied to `<path>.bak` (or `.bak2`, `.bak3`, ... when that name is taken: an older backup is never
             overwritten); an existing file that is not a readable project is copied too. A project without imports is written exactly as
             before (format 1, same text).
    @param path File path.
    @param project The Project.
    @return str or None: the path of the backup copy made by this save, None when none was needed.
    @throws ValueError If the project holds a non-finite number (nothing is written).
    """
    try:
        # allow_nan=False: Python would write Infinity or NaN, which is not JSON and which this program then refuses to read, so the project would be lost
        text = json.dumps(project_to_dict(project), indent=2, allow_nan=False)
    except ValueError as exc:
        raise ValueError(f"the project cannot be saved because it holds a value that is not a finite number ({exc}); the file on disk was not touched") from exc
    target = os.path.realpath(os.fspath(path))
    backup = None
    new = FORMAT_2 if project.imports else FORMAT_1
    if os.path.exists(target) and _file_format(target) != new:   # Also an unreadable or non-JSON file: its content is unknown, keep it
        backup = _backup_path(target)
        shutil.copy2(target, backup)
    _write_text_atomic(target, text)
    return backup
