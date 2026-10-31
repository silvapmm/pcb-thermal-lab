#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_image_cost.py
@brief Two checks of the pre-written decision rule for the image of the edge: the cost of the edge term per via (against the 1 ms limit) and the size of the code (against 60 lines).
@details The time is measured only to compare with the limit (best of 20 repeats of 200 vias on a footprint at each cell); it is not a result of the study. The code size counts
         the lines of code (no blank lines, comments or docstrings) of the functions that the image adds to the program: `edge_image.a_cont`, `centres`, `mirror`, `image_energy`,
         `log_image_distance`, `well_correction`, `well_conductance_image` and `edge_patch.walls_for`. Run from the repository root.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import ast
import math
import time
from pathlib import Path

import edge_image as ei
import viakernel as vk

NAMES = {"edge_image.py": ("a_cont", "centres", "mirror", "image_energy", "log_image_distance", "well_correction", "well_conductance_image"), "edge_patch.py": ("walls_for",)}


def code_lines(path, names):
    """!
    @brief Lines of code (no blanks, comments or docstrings) of the named functions.
    @param path Source file.
    @param names Function names.
    @return dict name -> lines.
    """
    src = Path(path).read_text()
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            body = node.body[1:]                                             # every function starts with its docstring
            lines = set()
            for st in body:
                for n in ast.walk(st):
                    if hasattr(n, "lineno"):
                        lines.add(n.lineno)
            out[node.name] = len(lines)
    return out


def main():
    """!
    @brief Print the cost per via and the code size.
    @return None.
    """
    here = Path(__file__).resolve().parents[1] / "lib"
    total = 0
    for f, names in NAMES.items():
        c = code_lines(here / f, names)
        total += sum(c.values())
        print(f, c)
    print("code lines of the image:", total)
    for cell in (1.0, 0.5, 0.25, 0.125):
        dx = cell * 1e-3
        rv = 0.15e-3
        best = 1e9
        for _ in range(20):
            t0 = time.perf_counter()
            for k in range(200):
                w = vk.disc_target_weights(0.0097 + 1e-6 * k, 0.005, rv, math.exp(-0.25) * rv, dx, 0.0)
                ei.well_correction(w, (0.0097, 0.005), rv, dx, 0.0, [("x", 0.01)])
            best = min(best, (time.perf_counter() - t0) / 200)
        w = vk.disc_target_weights(0.0097, 0.005, rv, math.exp(-0.25) * rv, dx, 0.0)
        t0 = time.perf_counter()
        for _ in range(200):
            ei.well_correction(w, (0.0097, 0.005), rv, dx, 0.0, [("x", 0.01)])
        only = (time.perf_counter() - t0) / 200
        print(f"cell {cell:g} mm: footprint {len(w)} cells; footprint + edge term below 1 ms: {best < 1e-3}; edge term alone below 1 ms: {only < 1e-3}")


if __name__ == "__main__":
    main()
