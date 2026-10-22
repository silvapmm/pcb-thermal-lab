"""!
@file defaults.py
@brief Defaults and material libraries, shipped in JSON and overridable by a user file.

@details Two files make the defaults of the program:
         * the **shipped** `pcbthermal/data/defaults.json`: the material libraries (via fills, metals, interface materials, dielectrics, package families), the properties of a
           new board, the defaults of new elements and the solver settings;
         * the **user** file `user_defaults.json` in the configuration folder (see user_dir): it holds only what the user changed. A library entry with the same `name` replaces
           the shipped one, a new name is added, the names in `removed` are hidden, and any other value replaces the shipped value. The stack-up templates have their own
           file, `stackups.json`, which the user can also put in the configuration folder (see stackup_file).
         The user file is read at start-up and whenever it changes; `diff_text()` and `has_user_file()` tell the application what is customised so it can say so.
         The folder is `PCBTHERMAL_CONFIG` if that environment variable is set, otherwise the usual per-user folder of the system. This module has no Qt and no import
         of the model, so the physics core and the command line can use it.
"""

import copy
import json
import os
import sys

SHIPPED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "defaults.json")
USER_NAME = "user_defaults.json"
STACKUP_NAME = "stackups.json"
LIBRARIES = ("via_fills", "metals", "interfaces", "dielectrics", "package_theta")      # Lists of entries keyed by "name"
_CACHE = {}


def user_dir():
    """!
    @brief The configuration folder of the user (not created).
    @return Path: $PCBTHERMAL_CONFIG, else ~/Library/Application Support/PCBThermalLab (macOS), %APPDATA%/PCBThermalLab (Windows) or ~/.config/pcbthermal-lab.
    """
    env = os.environ.get("PCBTHERMAL_CONFIG")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PCBThermalLab")
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PCBThermalLab")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")), "pcbthermal-lab")


def user_file():
    """!
    @brief Path of the user defaults file (it may not exist).
    @return Path.
    """
    return os.path.join(user_dir(), USER_NAME)


def stackup_file():
    """!
    @brief The stack-up template file in use: the user's `stackups.json` if it exists, otherwise the shipped one.
    @return Path.
    """
    mine = os.path.join(user_dir(), STACKUP_NAME)
    return mine if os.path.exists(mine) else os.path.join(os.path.dirname(SHIPPED_FILE), STACKUP_NAME)


def has_user_file():
    """!
    @brief True when a user defaults file exists.
    @return bool.
    """
    return os.path.exists(user_file())


def shipped():
    """!
    @brief The shipped defaults.
    @return Dict (a copy).
    """
    if "shipped" not in _CACHE:
        with open(SHIPPED_FILE, encoding="utf-8") as fh:
            _CACHE["shipped"] = json.load(fh)
    return copy.deepcopy(_CACHE["shipped"])


def user_overrides():
    """!
    @brief What the user file contains (an empty dict when there is none or when it cannot be read).
    @return Dict.
    """
    path = user_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _merge_library(base, over, removed):
    """!
    @brief Merge a library: entries of `over` replace those of `base` with the same name, new names are appended, `removed` names disappear.
    @param base List of dicts (shipped).
    @param over List of dicts (user).
    @param removed Names to hide.
    @return List of dicts.
    """
    out = [copy.deepcopy(e) for e in base if e["name"] not in removed]
    index = {e["name"]: i for i, e in enumerate(out)}
    for e in over:
        if e["name"] in index:
            out[index[e["name"]]] = copy.deepcopy(e)
        elif e["name"] not in removed:
            index[e["name"]] = len(out)
            out.append(copy.deepcopy(e))
    return out


def merged(overrides=None):
    """!
    @brief The shipped defaults with the user's changes applied.
    @param overrides The user dict (default: the user file).
    @return Dict.
    """
    data = shipped()
    over = user_overrides() if overrides is None else overrides
    removed = over.get("removed", {})
    for lib in LIBRARIES:
        if lib in over.get("libraries", {}) or lib in removed:
            data["libraries"][lib] = _merge_library(data["libraries"][lib], over.get("libraries", {}).get(lib, []), set(removed.get(lib, [])))
    for section in ("materials", "new_board", "new_elements", "solver"):
        data[section].update(over.get(section, {}))
    return data


def load():
    """!
    @brief The defaults in force (shipped plus user file), cached until the user file changes.
    @return Dict (a copy).
    """
    path = user_file()
    stamp = os.path.getmtime(path) if os.path.exists(path) else None
    if _CACHE.get("stamp", "none") != stamp or "merged" not in _CACHE:
        _CACHE["merged"] = merged()
        _CACHE["stamp"] = stamp
    return copy.deepcopy(_CACHE["merged"])


def value(section, key):
    """!
    @brief One scalar default.
    @param section "materials", "new_board", "new_elements" or "solver".
    @param key Name inside the section.
    @return The value.
    """
    return load()[section][key]


def library(name):
    """!
    @brief The entries of one library.
    @param name One of LIBRARIES.
    @return List of dicts.
    """
    return load()["libraries"][name]


def diff(full):
    """!
    @brief What differs between a full defaults dict and the shipped one, in the form of the user file.
    @param full A dict with the structure of the shipped file (libraries as full lists).
    @return Dict with libraries (changed or added entries), removed (names hidden per library) and the changed scalars of each section.
    """
    base = shipped()
    out = {}
    for lib in LIBRARIES:
        old = {e["name"]: e for e in base["libraries"][lib]}
        new = {e["name"]: e for e in full["libraries"][lib]}
        changed = [e for n, e in new.items() if old.get(n) != e]
        gone = [n for n in old if n not in new]
        if changed:
            out.setdefault("libraries", {})[lib] = changed
        if gone:
            out.setdefault("removed", {})[lib] = gone
    for section in ("materials", "new_board", "new_elements", "solver"):
        changed = {k: v for k, v in full[section].items() if base[section].get(k) != v}
        if changed:
            out[section] = changed
    return out


def save_user(full):
    """!
    @brief Write the user file with the differences between `full` and the shipped defaults (no file at all when there are none).
    @param full A dict with the structure of the shipped file.
    @return The dict written ({} when the file was removed).
    """
    changes = diff(full)
    path = user_file()
    if not changes:
        reset_user()
        return {}
    os.makedirs(user_dir(), exist_ok=True)
    changes = {"_comment": "Only what differs from the shipped defaults (pcbthermal/data/defaults.json). Delete this file to go back to the shipped values.", **changes}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(changes, fh, indent=2, ensure_ascii=False)
    _CACHE.pop("stamp", None)
    return changes


def reset_user():
    """!
    @brief Delete the user file (back to the shipped defaults).
    """
    path = user_file()
    if os.path.exists(path):
        os.remove(path)
    _CACHE.pop("stamp", None)


def diff_text():
    """!
    @brief A short sentence on what the user file changes, for the status bar and the About box.
    @return String: empty when nothing is customised.
    """
    over = user_overrides()
    if not over:
        return ""
    parts = []
    for lib, rows in over.get("libraries", {}).items():
        parts.append(f"{len(rows)} in {lib}")
    for lib, rows in over.get("removed", {}).items():
        parts.append(f"{len(rows)} removed from {lib}")
    for section in ("materials", "new_board", "new_elements", "solver"):
        if over.get(section):
            parts.append(f"{len(over[section])} in {section}")
    return ", ".join(parts)
