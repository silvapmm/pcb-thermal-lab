#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boardrun.py
@brief Runs of the program's own network on imported real boards (all copper layers, vias, the laminate rule of 2.4.5): the import of a window or a whole board, the heater, and the read-outs.
@details Built on research/gerber-models/lib/faces.py (the import path of the earlier research, which hands the program's `fvm.Network` the face conductances of the imported copper) and
         research/gerber-import/lib/importer.py (the masks). Nothing in pcbthermal/ is changed. The program's Problem is made by `faces.to_problem` (size, layers, one Via per plated hole, one heater);
         the heater here may be a rectangle or a polygon (a paste group). Conventions as in faces.py: board coordinates start at the corner of the (padded) box, rows of the fields are from the bottom.
"""

import numpy as np

import faces as im
import registry


def import_window(key, box, pix, cell, supersample=4):
    """!
    @brief Import a window (or the whole board) of a downloaded board.
    @param key Board key of registry.BOARDS.
    @param box Window (x0, y0, x1, y1) in mm in the file coordinates, or None for the board box.
    @param pix Pixel of the masks (mm).
    @param cell Cell of the thermal grid (mm), a whole number of pixels.
    @param supersample Sub-pixels per side of the coverage mask.
    @return faces.ImportedBoard.
    """
    r = registry.roles(key)
    return im.import_board({"copper": r["copper"], "outline": r["outline"], "drills": r["drills"]}, pix=pix, cell=cell, supersample=supersample, box=box)


def make_problem(ib, centre, size_mm=6.0, power=1.0, layer=1, polygon=None, h_face=10.0, rect=None):
    """!
    @brief The program's Problem for an imported board with one heater.
    @param ib Imported board.
    @param centre (x, y) of the heater centre in board coordinates (mm).
    @param size_mm Side of the square heater (mm); ignored when a polygon or a rectangle is given.
    @param power Heat (W).
    @param layer Layer of the heater (1 = top).
    @param polygon Optional array (k, 2) of the heater outline in board coordinates (mm).
    @param h_face Heat transfer coefficient of both faces (W/m2K).
    @param rect Optional rectangle (x0, y0, x1, y1) of the heater in board coordinates (mm).
    @return pcbthermal.Problem.
    """
    p = im.to_problem(ib, {"layer": layer, "x": centre[0], "y": centre[1], "size": size_mm, "power": power}, h_face=h_face)
    if polygon is not None or rect is not None:
        # replace the square heater by the polygon or the rectangle (the same power)
        p.heaters.clear()
        if polygon is not None:
            p.add_heater(layer, power, polygon=[tuple(v) for v in np.asarray(polygon, float)])
        else:
            p.add_heater(layer, power, rect=tuple(rect))
    return p


def heater_stats(field, grid_mm, centre, size_mm, layer=0):
    """!
    @brief Mean and maximum rise of the heater block on a field.
    @param field Array (layers, rows, cols), rows from the bottom.
    @param grid_mm Size of the grid of the field (mm): the cell or the pixel.
    @param centre (x, y) of the heater centre (board coordinates, mm).
    @param size_mm Heater side (mm).
    @param layer Layer index (0 = top).
    @return tuple (mean K, max K) over the cells whose centres fall in the block (at least one cell is always used).
    """
    s = size_mm / 2.0
    i0, i1 = int(np.floor((centre[1] - s) / grid_mm + 0.5)), int(np.floor((centre[1] + s) / grid_mm + 0.5))
    j0, j1 = int(np.floor((centre[0] - s) / grid_mm + 0.5)), int(np.floor((centre[0] + s) / grid_mm + 0.5))
    blk = field[layer, i0:max(i1, i0 + 1), j0:max(j1, j0 + 1)]
    return float(blk.mean()), float(blk.max())


def program_runs(ib, problem, centre, size_mm, kinds=("fine", "today", "flow", "lambda"), mask_kind="coverage"):
    """!
    @brief The heater read-outs of the runs of the earlier research on one imported board.
    @details "fine": the program's network on the pixel grid with the sheet of every pixel (the reference; the rule off, the sheet holds the laminate); "today": the program as it is (one zone per cell
             with the copper fraction as fill, laminate rule on); "flow": the flow-based faces from the mask; "lambda": the lambda 0.5 faces. The cell size is that of the import.
    @param ib Imported board.
    @param problem Problem made by make_problem.
    @param centre Heater centre (board coordinates, mm).
    @param size_mm Heater side (mm).
    @param kinds Which runs to make.
    @param mask_kind "coverage" or "binary" mask for every run.
    @return dict kind -> (mean K, max K) of the heater block on the top layer, plus "board_max" -> K of the hottest cell of the cell runs.
    """
    out = {}
    sheets = None
    for k in kinds:
        if k == "fine":
            out[k] = heater_stats(im.solve_fine(ib, problem, mask_kind), ib.pix, centre, size_mm)
        elif k == "today":
            f = im.solve_today(ib, problem, mask_kind)
            out[k] = heater_stats(f, ib.cell, centre, size_mm)
            out["board_max_today"] = float(f.max())
        elif k in ("flow", "lambda"):
            if sheets is None:
                sheets = im.layer_sheets(ib, problem, mask_kind)
            f = im.solve_faces(ib, problem, im.layer_faces(sheets, ib, problem, k))
            out[k] = heater_stats(f, ib.cell, centre, size_mm)
            out["board_max_" + k] = float(f.max())
    return out


def set_capacity(net, problem, coverage_layers, n):
    """!
    @brief Give a network of imported copper the heat capacity of its copper.
    @details The face-conductance network of research/gerber-models has no zones, so the program computes its capacity as bare laminate (no copper: the program's C = f rho_cu cp_cu t_cu + laminate part,
             with f from the zones). For a steady solve this does not matter; for a transient it does. The capacity is arithmetic (right as it is: heat capacity adds), per cell from the coverage mask.
    @param net A fvm.Network (or faces.FaceNetwork) of the imported board, built with assemble=False.
    @param problem The Problem of the net.
    @param coverage_layers List of coverage arrays (rows from the TOP of the board, as in ImportedBoard.layers), one per copper layer, top first.
    @param n Pixels per cell side (1 for a network on the pixel grid).
    @return None (net.C is replaced in place).
    @throws ValueError If the board has laminate nodes of a one-layer board (not supported here).
    """
    import conduction as cd
    b = problem.board
    if len(coverage_layers) != b.layers or b.layers < 2:
        raise ValueError("set_capacity needs a board of two or more copper layers with one mask per layer")
    m = b.materials
    slab = np.asarray(b.slab_thicknesses())
    _, rho_cp = b.layer_laminate()
    tc = np.asarray(b.copper_thickness)
    cell = net.dx * net.dy * net.cover
    for l, cov in enumerate(coverage_layers):
        f = cd.cell_blocks(np.asarray(cov, float)[::-1], n).mean(axis=(2, 3))        # rows from the bottom, like the network
        net.C[l] = (f * m.rho_copper * m.cp_copper * tc[l] + (slab[l] - f * tc[l]) * rho_cp[l]) * cell


def percent(a, b):
    """!
    @brief Percent difference of a from b.
    @param a Value.
    @param b Reference.
    @return float 100 (a / b - 1).
    """
    return 100.0 * (a / b - 1.0)
