#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fileschema.py
@brief Type checks of a project file at the loading boundary: one clear exception that names the key path and the expected type.
@details A project file is user data (hand-edited, damaged, or written by another tool), so a value of the wrong type must not reach the constructors, where it
         would surface as a TypeError or a KeyError with a traceback. `check_problem_dict` walks the native problem structure once (a few microseconds per
         element) and raises ProjectFormatError for the first wrong value; `guard` turns whatever a constructor still raises on a value that passed the
         checks (a range that only the model knows) into the same exception, with the path of the section being read. No numeric limit of the physics is
         repeated here: ranges stay in `Problem.validate`.
"""

import math
import numbers

import numpy as np

# Keys of the native structure by the kind of value they must hold. "num" is a finite number (int or float, not a bool), "num?" a number or null
# (null has a meaning: `h_side` null is an insulated edge, which the program writes itself), "int" an integer-valued number, "str" a text,
# "bool" a boolean, "poly" a list of pairs of numbers, "numlist" a list of numbers.
BOARD_KEYS = {
    "width_mm": "num", "height_mm": "num", "thickness_mm": "num", "layers": "int", "ambient_c": "num", "h_top": "num", "h_bottom": "num", "h_side": "num?",
    "via_plating_mm": "num", "h_mode": "str", "emissivity_top": "num", "emissivity_bottom": "num", "air_speed_m_per_s": "num", "orientation": "str",
    "h_calibration": "num", "template_inner_oz": "num", "natural_form": "str", "k_copper": "num", "k_fr4_through": "num", "k_fr4_inplane": "num",
    "rho_copper": "num", "cp_copper": "num", "rho_fr4": "num", "cp_fr4": "num"}
DIELECTRIC_KEYS = {"thickness_mm": "num", "name": "str", "k_through": "num", "k_inplane": "num", "rho": "num", "cp": "num"}
ZONE_KEYS = {"layer": "int", "polygon_mm": "poly", "fill": "num", "name": "str"}
HEATER_KEYS = {
    "layer": "int", "polygon_mm": "poly", "power_w": "num", "name": "str", "theta_k_per_w": "num", "theta_jb_k_per_w": "num", "tj_max_c": "num",
    "psi_jb_k_per_w": "num", "power_tc_per_k": "num", "theta_jc_top_k_per_w": "num", "theta_sa_k_per_w": "num", "interface_kcm2_per_w": "num",
    "contact_area_mm2": "num", "pad_thickness_mm": "num", "pad_k_w_per_mk": "num", "role": "str", "base_interface_kcm2_per_w": "num",
    "base_pad_thickness_mm": "num", "base_pad_k_w_per_mk": "num", "family": "str", "heatsink": "str"}
VIA_KEYS = {"x_mm": "num", "y_mm": "num", "diameter_mm": "num", "filled": "bool", "name": "str", "fill_k_w_per_mk": "num", "fill": "str"}
HEATSINK_KEYS = {
    "layer": "int", "polygon_mm": "poly", "h_extra": "num", "name": "str", "thickness_mm": "num", "k_w_per_mk": "num", "rho_cp_j_per_m3k": "num",
    "contact_r_m2k_per_w": "num", "fin_height_mm": "num", "fin_thickness_mm": "num", "fin_pitch_mm": "num", "pad_thickness_mm": "num", "pad_k_w_per_mk": "num"}
SQUARE_KEYS = {"type": "str", "p_on_w": "num", "p_off_w": "num", "period_s": "num", "duty": "num"}
TABLE_KEYS = {"type": "str", "times_s": "numlist", "power_w": "numlist", "repeat": "bool"}
REQUIRED = {"board": ("width_mm", "height_mm"), "zones": ("layer", "polygon_mm"), "heaters": ("layer", "polygon_mm", "power_w"), "vias": ("x_mm", "y_mm"),
            "heatsinks": ("layer", "polygon_mm", "h_extra")}


class ProjectFormatError(ValueError):
    """!
    @brief A project file that this program must not open: a format newer than it knows, a malformed file, or a value of the wrong type.
    @details The message names the key path and what was expected, for example "zones[2].polygon_mm: expected a list of pairs of numbers, got a string".
    """


def describe(value):
    """!
    @brief The kind of a JSON value, in words, for a message.
    @param value Any parsed JSON value.
    @return str.
    """
    if value is None:
        return "null"
    if isinstance(value, (bool, np.bool_)):
        return "a boolean"
    if isinstance(value, numbers.Real):
        if _is_num(value):
            return "a number"
        return "a number too large" if isinstance(value, numbers.Integral) else "a non-finite number"   # An int beyond the float range, or NaN / Infinity
    if isinstance(value, str):
        return "a string"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return type(value).__name__


def _is_num(v):
    """!
    @brief True for a finite real number (a bool is not a number here).
    @details Any real counts, not only int and float: the undo snapshots of the window are read by the same code without going through JSON, so they can
             hold NumPy scalars (np.int64 is not an int, np.float32 not a float). An integer too large for a float (JSON has no limit on digits) is not
             finite here, instead of the OverflowError that math.isfinite would raise.
    @param v Value.
    @return bool.
    """
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:                               # An int beyond the float range
        return False


def check_value(path, value, kind):
    """!
    @brief Check one value against its kind.
    @param path Key path for the message.
    @param value The value.
    @param kind "num", "num?", "int", "str", "bool", "poly" or "numlist".
    @return None.
    @throws ProjectFormatError If the value is not of that kind.
    """
    ok = True
    if kind == "num":
        ok = _is_num(value)
        what = "a number"
    elif kind == "num?":
        ok = value is None or _is_num(value)
        what = "a number or null"
    elif kind == "int":
        ok = _is_num(value) and float(value).is_integer() and abs(value) < 1e9
        what = "an integer"
    elif kind == "str":
        ok = isinstance(value, str)
        what = "a string"
    elif kind == "bool":
        ok = isinstance(value, (bool, np.bool_))
        what = "true or false"
    elif kind == "numlist":
        ok = isinstance(value, list) and all(_is_num(x) for x in value)
        what = "a list of numbers"
    else:                                               # "poly"
        ok = isinstance(value, list) and all(isinstance(p, (list, tuple)) and len(p) == 2 and all(_is_num(x) for x in p) for p in value)
        what = "a list of pairs of numbers"
        if not ok and isinstance(value, list):          # Name the offending point, as the maintainer's example asks
            for i, p in enumerate(value):
                if not (isinstance(p, (list, tuple)) and len(p) == 2 and all(_is_num(x) for x in p)):
                    raise ProjectFormatError(f"{path}[{i}]: expected a pair of numbers, got {describe(p)}")
    if not ok:
        raise ProjectFormatError(f"{path}: expected {what}, got {describe(value)}")


def check_keys(path, obj, table, required=()):
    """!
    @brief Check the known keys of an object; unknown keys are left alone (forward compatibility).
    @param path Key path of the object.
    @param obj The value, which must be an object.
    @param table Map of key to kind.
    @param required Keys that must be present.
    @return None.
    @throws ProjectFormatError For a non-object, a missing required key or a wrong value.
    """
    if not isinstance(obj, dict):
        raise ProjectFormatError(f"{path}: expected an object, got {describe(obj)}")
    for key in required:
        if key not in obj:
            raise ProjectFormatError(f"{path}.{key}: required key is missing")
    for key, kind in table.items():
        if key in obj:
            check_value(f"{path}.{key}", obj[key], kind)


def _check_list(path, data, key, table, required, alt=None):
    """!
    @brief Check a list of objects under a top-level key.
    @param path Prefix (empty for the top level).
    @param data The dict that holds the list.
    @param key Key of the list.
    @param table Map of key to kind of one element.
    @param required Required keys of one element.
    @param alt Older name of the key (still accepted).
    @return None.
    """
    name = key if key in data or alt is None or alt not in data else alt
    items = data.get(name, [])
    if not isinstance(items, list):
        raise ProjectFormatError(f"{name}: expected a list, got {describe(items)}")
    for i, item in enumerate(items):
        check_keys(f"{name}[{i}]", item, table, required)
        if name == "heaters" and "profile" in item:
            prof = item["profile"]
            check_keys(f"{name}[{i}].profile", prof, TABLE_KEYS if isinstance(prof, dict) and prof.get("type") == "table" else SQUARE_KEYS,
                       ("times_s", "power_w") if isinstance(prof, dict) and prof.get("type") == "table" else ("p_on_w", "period_s", "duty"))


def check_problem_dict(data):
    """!
    @brief Check the native problem structure (board, zones, heaters, vias, heatsinks) before it is built.
    @param data Dict of the native structure.
    @return None.
    @throws ProjectFormatError For the first wrong value, naming its key path.
    """
    if not isinstance(data, dict):
        raise ProjectFormatError(f"expected an object, got {describe(data)}")
    if "name" in data:
        check_value("name", data["name"], "str")
    if "board" not in data:
        raise ProjectFormatError("board: required key is missing")
    b = data["board"]
    check_keys("board", b, BOARD_KEYS, REQUIRED["board"])
    if "copper_thickness_mm" in b:
        cu = b["copper_thickness_mm"]
        check_value("board.copper_thickness_mm", cu, "numlist" if isinstance(cu, list) else "num")
    if b.get("outline_mm"):
        check_value("board.outline_mm", b["outline_mm"], "poly")
    if "dielectrics" in b:
        dl = b["dielectrics"]
        if not isinstance(dl, list):
            raise ProjectFormatError(f"board.dielectrics: expected a list, got {describe(dl)}")
        for i, d in enumerate(dl):
            check_keys(f"board.dielectrics[{i}]", d, DIELECTRIC_KEYS, ("thickness_mm",))
    _check_list("", data, "zones", ZONE_KEYS, REQUIRED["zones"])
    _check_list("", data, "heaters", HEATER_KEYS, REQUIRED["heaters"])
    _check_list("", data, "vias", VIA_KEYS, REQUIRED["vias"])
    _check_list("", data, "heatsinks", HEATSINK_KEYS, REQUIRED["heatsinks"], alt="sinks")


class guard:
    """!
    @brief Context manager that turns any exception of a block of constructors into a ProjectFormatError naming the section.
    @details Used for what the type checks cannot know (a range, the content of an import record). A ProjectFormatError raised inside passes unchanged.
    """

    def __init__(self, section):
        """!
        @brief Name the section being read.
        @param section Key path for the message, for example "imports[0]" or "solver".
        @return None.
        """
        self.section = section

    def __enter__(self):
        """!
        @brief Enter the block.
        @return self.
        """
        return self

    def __exit__(self, kind, exc, tb):
        """!
        @brief Convert an exception of the block.
        @param kind Exception class or None.
        @param exc The exception.
        @param tb Traceback.
        @return False (the original exception passes) or never, because the new one is raised from it.
        """
        if exc is None or isinstance(exc, (ProjectFormatError, KeyboardInterrupt, SystemExit, MemoryError)):
            return False
        text = str(exc.args[0]) if isinstance(exc, KeyError) and exc.args else str(exc)
        kind_name = "missing key" if isinstance(exc, KeyError) else "malformed value"
        raise ProjectFormatError(f"{self.section}: {kind_name} ({text})") from exc
