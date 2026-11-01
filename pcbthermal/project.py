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
"""

import json
import os
import re
import shutil
from dataclasses import dataclass, field

from . import __version__
from .api import SolverOptions
from .model import ImportRecord, Problem, problem_from_dict, problem_from_legacy, problem_to_dict

PROJECT_SUFFIX = ".pcbt.json"
FORMAT_1 = "pcbthermal-project-1"
FORMAT_2 = "pcbthermal-project-2"
KNOWN_FORMATS = (1, 2)                              # Format numbers this program reads


class ProjectFormatError(ValueError):
    """!
    @brief A project file that this program must not open (a format newer than it knows, or a malformed format 2 file).
    """


@dataclass
class Project:
    """!
    @brief Everything needed to reopen a session.
    """
    problem: Problem
    options: SolverOptions = field(default_factory=SolverOptions)
    view: dict = field(default_factory=dict)         # Viewer state: background image, zoom, ...
    imports: list = field(default_factory=list)      # ImportRecord list; non-empty makes the file format 2


def project_to_dict(project):
    """!
    @brief Serialise a Project.
    @details Format 1 (the project dict) when there are no imports; otherwise format 2, which nests that dict under "project".
    @param project A Project.
    @return JSON-ready dict.
    """
    d = problem_to_dict(project.problem)
    d["solver"] = project.options.to_dict()
    d["view"] = project.view
    d["format"] = FORMAT_1
    d["app_version"] = __version__                  # Version that wrote the file (informational)
    if not project.imports:
        return d
    return {"format": FORMAT_2, "app_version": __version__, "project": d, "imports": [r.to_dict() for r in project.imports]}


def format_number(data):
    """!
    @brief The format number of a parsed project file.
    @param data Parsed JSON.
    @return int: 1 for a file with no "format" key (plain native or legacy) or format 1, 2 for format 2.
    @throws ProjectFormatError If the format is newer than this program knows or is not a project format; the message names the writer's version.
    """
    fmt = data.get("format")
    if fmt is None:
        return 1
    m = re.fullmatch(r"pcbthermal-project-(\d+)", str(fmt))
    if not m:
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
    @throws ProjectFormatError For a newer format or a format 2 file without its "project" key.
    """
    imports = []
    if format_number(data) == 2:
        if not isinstance(data.get("project"), dict):
            raise ProjectFormatError("format 2 project file without its \"project\" section")
        imports = [ImportRecord.from_dict(r) for r in data.get("imports", [])]
        data = data["project"]
    problem = problem_from_legacy(data) if "pcb_params" in data else problem_from_dict(data, validate)
    return Project(problem=problem, options=SolverOptions.from_dict(data.get("solver")),
                   view=dict(data.get("view", {})), imports=imports)


def load_project(path):
    """!
    @brief Load a project file.
    @param path File path.
    @return Project.
    @throws ProjectFormatError For a file of a format this program does not know.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return project_from_dict(json.load(fh))


def _is_format_2_file(path):
    """!
    @brief Whether an existing file is already a format 2 project.
    @param path File path.
    @return bool (False for a missing, unreadable or format 1 file).
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return str(json.load(fh).get("format")) == FORMAT_2
    except (OSError, ValueError, AttributeError):
        return False


def save_project(path, project):
    """!
    @brief Save a project file.
    @details Before a project with imports overwrites an existing file that is not format 2 yet, that file is copied to `<path>.bak`
             (once: the next saves find a format 2 file). A project without imports is written exactly as before (format 1).
    @param path File path.
    @param project The Project.
    """
    if project.imports and os.path.exists(path) and not _is_format_2_file(path):
        shutil.copy2(path, str(path) + ".bak")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project_to_dict(project), fh, indent=2)
