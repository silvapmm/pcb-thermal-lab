#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file project.py
@brief Project files: a Problem plus its SolverOptions and free-form viewer metadata.

A project is the native JSON structure with two extra keys: "solver" (SolverOptions) and
"view" (anything the GUI wants to remember, such as the background image and its scale).
Plain native files and legacy editor files are read as well.
"""

import json
from dataclasses import dataclass, field

from . import __version__
from .api import SolverOptions
from .model import Problem, problem_from_dict, problem_from_legacy, problem_to_dict

PROJECT_SUFFIX = ".pcbt.json"


@dataclass
class Project:
    """!
    @brief Everything needed to reopen a session.
    """
    problem: Problem
    options: SolverOptions = field(default_factory=SolverOptions)
    view: dict = field(default_factory=dict)         # Viewer state: background image, zoom, ...


def project_to_dict(project):
    """!
    @brief Serialise a Project.
    @param project A Project.
    @return JSON-ready dict.
    """
    d = problem_to_dict(project.problem)
    d["solver"] = project.options.to_dict()
    d["view"] = project.view
    d["format"] = "pcbthermal-project-1"
    d["app_version"] = __version__                  # Version that wrote the file (informational)
    return d


def project_from_dict(data, validate=True):
    """!
    @brief Read a Project from a dict (native, project or legacy editor structure).
    @param data Parsed JSON.
    @param validate If False, accept a transiently inconsistent problem (undo snapshots).
    @return Project.
    """
    problem = problem_from_legacy(data) if "pcb_params" in data else problem_from_dict(data, validate)
    return Project(problem=problem, options=SolverOptions.from_dict(data.get("solver")),
                   view=dict(data.get("view", {})))


def load_project(path):
    """!
    @brief Load a project file.
    @param path File path.
    @return Project.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return project_from_dict(json.load(fh))


def save_project(path, project):
    """!
    @brief Save a project file.
    @param path File path.
    @param project The Project.
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project_to_dict(project), fh, indent=2)
