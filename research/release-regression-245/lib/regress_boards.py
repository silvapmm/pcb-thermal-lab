#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file regress_boards.py
@brief The boards of the release regression: the three example files of the program, one derived example and thirteen small canonical boards, each built through the public builder API only.
@details The same builders are run on every revision, so they use only calls that exist in v2.4.4 and in the release candidate (`Problem.new`, `add_zone`, `add_full_copper`,
         `add_heater`, `add_via`, `add_via_array`, `add_heatsink`, `set_outline`, `load_problem`). The module imports the program lazily: the caller puts the program tree to
         test on `sys.path` first (see `regress_harness.use_program`). Dimensions are in mm in the builders (the builder API converts), SI in the program.

         Four boards have an independent reference (`REFERENCE_SPECS`): a laminate with the same conductivity in all directions, insulated sides, a square source on the top
         copper, which is what `research/solid3d-verification/lib/layered3d.py` solves. Their sources and pads sit on multiples of 2 mm, so that the heated area is the same at
         every cell size of the suite (a source edge between cell edges changes the heated area, and `round()` rounds halves to even).
"""

import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# Boards that the independent layered solver can represent (uniform conductivity per cell, insulated sides, one square source on the top copper).
REFERENCE_SPECS = {
    "plate_uniform": dict(size=60.0, layers=2, thickness=1.6, cu_um=35.0, pad=None, src=(26.0, 26.0, 34.0, 34.0), power=5.0, k_lam=0.3, k_cu=385.0, h_top=10.0, h_bottom=15.0, ambient=25.0),
    "plate_pad": dict(size=60.0, layers=2, thickness=1.6, cu_um=35.0, pad=(20.0, 20.0, 40.0, 40.0), src=(26.0, 26.0, 34.0, 34.0), power=5.0, k_lam=0.3, k_cu=385.0, h_top=10.0, h_bottom=15.0, ambient=25.0),
    "one_layer_full": dict(size=60.0, layers=1, thickness=1.6, cu_um=35.0, pad=None, src=(26.0, 26.0, 34.0, 34.0), power=1.0, k_lam=0.3, k_cu=385.0, h_top=10.0, h_bottom=15.0, ambient=25.0),
    "one_layer_pad": dict(size=60.0, layers=1, thickness=1.6, cu_um=35.0, pad=(20.0, 20.0, 40.0, 40.0), src=(26.0, 26.0, 34.0, 34.0), power=1.0, k_lam=0.3, k_cu=385.0, h_top=10.0, h_bottom=15.0, ambient=25.0),
}

# One line for each board: what it exercises (the README table repeats it).
DESCRIPTIONS = {
    "example_board": "examples/example_board.pcbt.json: 4 layers, partial top copper, 9 vias, two parts, a bottom heatsink",
    "profile_board": "examples/profile_board.pcbt.json: the example with a square-wave power profile (steady state at the average power)",
    "reference_board": "examples/reference_board.pcbt.json: 2 layers, one 20 mm part, full copper",
    "example_cut_to_T": "the example board cut to an inverted T (outline), both parts and the vias on the board",
    "plate_uniform": "60 x 60 mm, 2 layers full copper, one 8 mm source (independent reference)",
    "plate_pad": "plate_uniform with a 20 mm copper window on both layers and bare laminate around it (independent reference)",
    "plate_vias": "plate_uniform with a 4 x 4 array of 0.3 mm vias under the source",
    "plate_lone_via": "plate_uniform with one 0.3 mm via under the source (the point via)",
    "round_outline": "60 mm box, round outline of 56 mm diameter, 2 layers full copper, centred source",
    "t_outline": "80 x 60 mm box cut to a T, 2 layers full copper, a part in the stem",
    "two_layer_partial": "80 x 60 mm, 2 layers, top copper 40 x 30 mm, bottom copper at 70 % fill, one part",
    "one_layer_full": "60 x 60 mm, 1 layer, full copper, 8 mm part (independent reference)",
    "one_layer_pad": "60 x 60 mm, 1 layer, 20 mm pad, 8 mm part (independent reference)",
    "finned_block": "60 x 40 mm, 2 layers, a 3 mm aluminium block with plate fins on the bottom face under a part",
    "part_top_path": "50 x 50 mm, 2 layers, a component with theta, theta_jc_top and a heatsink on the package (top path) on a 14 mm pad",
    "hatched_copper": "60 x 60 mm, 2 layers, both layers hatched (fill 0.5 and 0.7), one part",
    "part_across_outline": "40 x 40 mm, outline edge at x = 37.3 mm (between the cell edges at 2, 1 and 0.5 mm), a part across the edge",
}

EXAMPLE_FILES = ("example_board", "profile_board", "reference_board")


def _new(width, height, layers, thickness, cu_um, name, **kw):
    """!
    @brief Problem.new, imported lazily so that the caller chooses which program tree is loaded.
    @param width Width in mm.
    @param height Height in mm.
    @param layers Copper layers.
    @param thickness Board thickness in mm.
    @param cu_um Copper thickness per layer in micrometres.
    @param name Project name.
    @param kw Board options (ambient, h_top, h_bottom, h_side, materials).
    @return A new Problem.
    """
    from pcbthermal import Problem
    return Problem.new(width, height, layers=layers, thickness_mm=thickness, copper_um=cu_um, name=name, **kw)


def _from_spec(name):
    """!
    @brief Build a reference-capable board from its specification.
    @param name Key of REFERENCE_SPECS.
    @return Problem with insulated sides, laminate of equal conductivity in all directions and one square source on layer 1.
    """
    from pcbthermal.model import Materials
    s = REFERENCE_SPECS[name]
    mat = Materials(k_copper=s["k_cu"], k_fr4_through=s["k_lam"], k_fr4_inplane=s["k_lam"])
    p = _new(s["size"], s["size"], s["layers"], s["thickness"], s["cu_um"], name, ambient=s["ambient"], h_top=s["h_top"], h_bottom=s["h_bottom"], h_side=None, materials=mat)
    if s["pad"] is None:
        p.add_full_copper()
    else:
        for layer in range(1, s["layers"] + 1):
            p.add_zone(layer, rect=s["pad"])                              # the same window on every layer: the laminate shows around it
    p.add_heater(1, s["power"], rect=s["src"], name="U")
    return p


def _circle(cx, cy, r, n=96):
    """!
    @brief Vertices of a regular polygon that approximates a circle.
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param r Radius in mm.
    @param n Number of vertices.
    @return List of [x, y] in mm.
    """
    return [[cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)] for i in range(n)]


def _plate_vias(name, lone):
    """!
    @brief plate_uniform (with the edge coefficient of the program defaults) and vias under the source.
    @param name Project name.
    @param lone True for one via at the centre, False for a 4 x 4 array.
    @return Problem.
    """
    p = _new(60, 60, 2, 1.6, 35.0, name, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.add_heater(1, 5.0, rect=(26, 26, 34, 34), name="U")
    if lone:
        p.add_via(30.0, 30.0, diameter=0.3)
    else:
        p.add_via_array((27, 27, 33, 33), 4, 4, diameter=0.3)
    return p


def _round_outline():
    """!
    @brief Round board of 56 mm diameter in a 60 mm box.
    @return Problem.
    """
    p = _new(60, 60, 2, 1.6, 35.0, "round_outline", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.set_outline(_circle(30.0, 30.0, 28.0))
    p.add_heater(1, 5.0, rect=(26, 26, 34, 34), name="U")
    return p


def _t_outline():
    """!
    @brief T-shaped board: a bar 80 x 20 mm on top of a stem 20 mm wide.
    @return Problem.
    """
    p = _new(80, 60, 2, 1.6, 35.0, "t_outline", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.set_outline([[0, 60], [0, 40], [30, 40], [30, 0], [50, 0], [50, 40], [80, 40], [80, 60]])
    p.add_heater(1, 4.0, rect=(34, 10, 46, 22), name="U")
    return p


def _two_layer_partial():
    """!
    @brief Two layers, a copper window on top and a 70 % hatch on the bottom.
    @return Problem.
    """
    p = _new(80, 60, 2, 1.6, 35.0, "two_layer_partial", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_zone(1, rect=(20, 15, 60, 45))
    p.add_zone(2, rect=(0, 0, 80, 60), fill=0.7)
    p.add_heater(1, 6.0, rect=(34, 24, 46, 36), name="U")
    return p


def _hatched():
    """!
    @brief Both layers hatched over the whole board.
    @return Problem.
    """
    p = _new(60, 60, 2, 1.6, 35.0, "hatched_copper", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_zone(1, rect=(0, 0, 60, 60), fill=0.5)
    p.add_zone(2, rect=(0, 0, 60, 60), fill=0.7)
    p.add_heater(1, 3.0, rect=(24, 24, 36, 36), name="U")
    return p


def _finned_block():
    """!
    @brief A finned aluminium block on the bottom face under a part on the top face.
    @return Problem.
    """
    p = _new(60, 40, 2, 1.6, 35.0, "finned_block", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.add_heater(1, 6.0, rect=(24, 14, 36, 26), name="U")
    p.add_heatsink(2, 0.0, rect=(8, 6, 52, 34), name="block", thickness_mm=3.0, k=204.0, rho_cp=2.44e6, contact_r=5.0e-4,
                   fin_height_mm=10.0, fin_thickness_mm=1.0, fin_pitch_mm=5.0)
    return p


def _top_path():
    """!
    @brief A component with a heatsink on the package, on a small pad over a full bottom plane.
    @return Problem.
    """
    p = _new(50, 50, 2, 1.6, 35.0, "part_top_path", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_zone(1, rect=(18, 18, 32, 32))
    p.add_zone(2, rect=(0, 0, 50, 50))
    p.add_heater(1, 3.0, rect=(22, 22, 28, 28), name="Q1", theta=2.0, tj_max=125.0, theta_jc_top=5.0, theta_sa=20.0, interface=0.5, role="component")
    return p


def _across_outline():
    """!
    @brief A part across an outline edge that lies between the cell edges of 2, 1 and 0.5 mm (x = 37.3 mm).
    @return Problem.
    """
    p = _new(40, 40, 2, 1.6, 35.0, "part_across_outline", h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.set_outline([[0, 0], [37.3, 0], [37.3, 40], [0, 40]])
    p.add_heater(1, 4.0, rect=(31, 16, 39, 24), name="U")
    return p


def load_example(name, examples_dir):
    """!
    @brief Load one example file with the program under test.
    @param name File stem, for example "example_board".
    @param examples_dir Folder with the `.pcbt.json` files (the same folder is given for every revision, so that all of them read the same input).
    @return Problem.
    """
    from pcbthermal.model import load_problem
    return load_problem(str(Path(examples_dir) / f"{name}.pcbt.json"))


def _example_cut_to_t(examples_dir):
    """!
    @brief The example board with an inverted-T outline.
    @param examples_dir Folder of the example files.
    @return Problem.
    """
    p = load_example("example_board", examples_dir)
    p.name = "example_cut_to_T"
    p.set_outline([[0, 0], [100, 0], [100, 42], [73, 42], [73, 80], [27, 80], [27, 42], [0, 42]])
    return p


def board_names():
    """!
    @brief All board names in the order of the reports.
    @return List of str.
    """
    return list(EXAMPLE_FILES) + ["example_cut_to_T", "plate_uniform", "plate_pad", "plate_vias", "plate_lone_via", "round_outline", "t_outline",
                                  "two_layer_partial", "one_layer_full", "one_layer_pad", "finned_block", "part_top_path", "hatched_copper", "part_across_outline"]


def build(name, examples_dir=None):
    """!
    @brief Build a board by name.
    @param name One of board_names().
    @param examples_dir Folder of the example files (default: `examples/` of this repository).
    @return A fresh Problem (the caller may modify it).
    @throws KeyError If the name is unknown.
    """
    ex = examples_dir or (REPO / "examples")
    if name in EXAMPLE_FILES:
        return load_example(name, ex)
    if name == "example_cut_to_T":
        return _example_cut_to_t(ex)
    if name in REFERENCE_SPECS:
        return _from_spec(name)
    table = {"plate_vias": lambda: _plate_vias(name, False), "plate_lone_via": lambda: _plate_vias(name, True), "round_outline": _round_outline,
             "t_outline": _t_outline, "two_layer_partial": _two_layer_partial, "hatched_copper": _hatched, "finned_block": _finned_block,
             "part_top_path": _top_path, "part_across_outline": _across_outline}
    return table[name]()


def features(problem):
    """!
    @brief Facts about a built problem that the classification tables use (no solver is run).
    @param problem A Problem.
    @return dict with layers, vias, outline, heaters, blocks, profiles, ambient and size_mm.
    """
    b = problem.board
    return {"layers": int(b.layers), "vias": len(problem.vias), "outline": bool(b.has_outline()), "heaters": len(problem.heaters),
            "blocks": sum(1 for h in problem.heatsinks if h.thickness > 0), "profiles": bool(problem.has_profiles()), "ambient": float(b.ambient),
            "size_mm": [round(b.width * 1000.0, 3), round(b.height * 1000.0, 3)]}
