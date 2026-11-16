#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_model_lists.py
@brief Every tuple, list, set or dict of the program that names the 3D solid also names the FEM, except the lists that are deliberately without it.

A model added to the program (the FEM was) is easy to miss in a hard-coded list; this test reads the source of the core and of the window and fails naming the
file, the line and the literal. The exceptions are listed below with the reason of each.
"""

import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["api.py", "cli.py", "memory.py", "checks.py", "results.py", "plots.py", "analysis.py", "defaults.py", "jobs.py"]
GUI = os.path.join(ROOT, "pcbthermal", "gui")

# (file, text of the literal) pairs that name the 3D solid and not the FEM on purpose; the key is a fragment of the literal's source
ALLOWED = {
    ("checks.py", '"layered"'): "the small-part rule is a rule of the cell footprint of the layered models and of the 3D solid's slabs; the FEM has its own check_fem (part below the mesh)",
    ("checks.py", '("fvm", "fdm", "solid3d")'): ("the via-at-the-edge warning is about the cut footprint of a via on the FVM/FDM cell grid; the FEM meshes the barrel as a hollow tube, or, without room for "
                                              "one, as a rod over the elements under the drill, and its outline is rectangular (a refused outline never reaches it)"),
    ("checks.py", '{"fdm", "solid3d"}'): "the same via-at-the-edge test: the models that do not take the FVM's mirror image",
}


def _literals(path):
    """!
    @brief The collection literals of a source file that contain the string "solid3d".
    @param path File path.
    @return List of (line, source segment, set of the string constants in the literal).
    """
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            consts = {e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        elif isinstance(node, ast.Dict):
            consts = {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        else:
            continue
        if "solid3d" in consts:
            found.append((node.lineno, ast.get_source_segment(src, node) or "", consts))
    return found


def test_every_list_that_names_the_3d_solid_names_the_fem():
    """!
    @brief Parse the model lists of the core and of the window and require "fem" next to "solid3d".
    """
    paths = [os.path.join(ROOT, "pcbthermal", f) for f in FILES] + [os.path.join(GUI, f) for f in sorted(os.listdir(GUI)) if f.endswith(".py")]
    missing = []
    for path in paths:
        if not os.path.exists(path):
            continue
        base = os.path.basename(path)
        for line, seg, consts in _literals(path):
            if "fem" in consts or any(b == base and frag in seg for (b, frag) in ALLOWED):
                continue
            missing.append(f"{base}:{line}: {seg[:110]}")
    assert not missing, "a model list names solid3d but not fem:\n" + "\n".join(missing)
