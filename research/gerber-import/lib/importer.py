#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file importer.py
@brief The import of a Gerber set: the files to the board box, a mask per copper layer (binary and coverage), the plated holes matched to pads and nets, and the warnings; NumPy only, nothing of the program is needed.
@details Phase 1 of the Gerber research. `import_board` takes the files of a set (copper layers from the top, an optional outline, drill files), finds the board box, draws every copper layer as a mask (binary, or coverage by sub-sampling),
         reads the plated holes and matches them to pads and nets (`nets.hole_report`). What is done with the masks (conductances, the program's `Problem`, solving) is phase 2 (`research/gerber-models/lib/faces.py`).
         Limits: a rectangular box from the outline or the copper, plated holes as positions and diameters, the layer order given by the caller.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import native_gerber as ng
import nets
import readers


@dataclass
class ImportedBoard:
    """!@brief What was understood from a Gerber set: the box, the copper layers (top first) with their masks, the plated holes with their pads and nets, and the warnings."""
    box: tuple                                  # (x0, y0, x1, y1) in mm, in the file coordinates, padded to whole cells
    pix: float                                  # mm, pixel of the masks
    cell: float                                 # mm, cell of the thermal grid the box was padded to
    layers: list = field(default_factory=list)  # dicts: name, layer (native_gerber.Layer), binary (bool, rows from the top), coverage (float, rows from the top)
    holes: list = field(default_factory=list)   # dicts of nets.hole_report plus x, y in board coordinates (mm)
    warnings: list = field(default_factory=list)

    @property
    def width(self):
        """!@brief Board width. @return Width (mm)."""
        return self.box[2] - self.box[0]

    @property
    def height(self):
        """!@brief Board height. @return Height (mm)."""
        return self.box[3] - self.box[1]


def roles_of_downloaded(name):
    """!
    @brief The roles of a board downloaded by scripts/fetch_boards.py.
    @param name Board key (for example "storm").
    @return Dict with "copper" (paths from the top), "outline" (path or None) and "drills" (list of paths).
    """
    f = readers.board_files(name)
    copper = [f[k] for k in ("F", "L2", "L3", "L4", "L5", "B") if k in f]
    return {"copper": copper, "outline": f.get("edge"), "drills": [f["drill"]] if "drill" in f else []}


def import_board(roles, pix=0.1, cell=1.0, supersample=4, box=None):
    """!
    @brief Read a Gerber set and draw its copper layers.
    @param roles Dict with "copper" (paths from the top layer down), optional "outline" (path) and "drills" (list of paths).
    @param pix Pixel of the masks (mm); the cell must be a whole number of pixels.
    @param cell Cell of the thermal grid (mm); the box is padded up to whole cells (the padding is bare laminate).
    @param supersample Sub-pixels per side of the coverage mask.
    @param box Optional (x0, y0, x1, y1) in mm overriding the box taken from the outline or the copper.
    @return ImportedBoard.
    @throws ValueError If the cell is not a whole number of pixels or no box can be found.
    """
    n = cell / pix
    if abs(n - round(n)) > 1e-9:
        raise ValueError("the cell must be a whole number of pixels")
    layers = [(Path(p).stem, ng.Layer(Path(p).read_text(errors="replace"))) for p in roles["copper"]]
    if box is None:
        edge = roles.get("outline")
        box = None
        for p in ([edge] if edge else []) + list(roles["copper"]):
            b = ng.layer_bbox(p)
            if b and b[2] - b[0] > 1 and b[3] - b[1] > 1:
                box = b
                break
        if box is None:
            raise ValueError("no usable board box")
    x0, y0, x1, y1 = box
    w, h = math.ceil((x1 - x0) / cell - 1e-9) * cell, math.ceil((y1 - y0) / cell - 1e-9) * cell
    ib = ImportedBoard(box=(x0, y0, x0 + w, y0 + h), pix=pix, cell=cell)
    for name, layer in layers:
        cv = ng.Canvas(x0, y0 + h, w, h, pix)
        layer.draw(cv)
        ib.layers.append({"name": name, "layer": layer, "binary": cv.mask.copy(), "coverage": ng.render_coverage(layer, x0, y0 + h, w, h, pix, supersample)})
        thin = [min(v for v in ap.p[:2] if v > 0) for ap in layer.apertures.values() if ap.kind in "CRO" and any(v > 0 for v in ap.p[:2])]
        if thin and min(thin) < 2 * pix:
            ib.warnings.append(f"{name}: the thinnest aperture is {min(thin):.3f} mm, under two pixels ({2 * pix:.2f} mm): coverage masks keep its area, binary masks may lose it")
    holes = []
    for p in roles.get("drills", []):
        holes += ng.read_drill(p)
    plated = [h for h in holes if h[3] is not False]
    if any(h[3] is None for h in plated):
        ib.warnings.append("some holes do not say whether they are plated: counted as plated")
    rep = nets.hole_report(plated, [(nm, ly) for nm, ly in layers])
    for r in rep:
        r["bx"], r["by"] = r["x"] - x0, r["y"] - y0
        if 0.0 <= r["bx"] <= w and 0.0 <= r["by"] <= h:
            ib.holes.append(r)
    return ib
