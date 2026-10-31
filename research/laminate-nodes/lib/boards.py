#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief The test boards of the investigation: one description (`Spec`) that gives both the program's Problem and the copper masks of the resolved reference, from the simplest board up.
@details Maintainer's rule: simple boards first. The set (README 1.1) is: a one-layer board with full copper, with a square pad, with a square window; two-layer boards of 0.2 to 3.2 mm
         laminate with a pad on the top, a window, a bare bottom; the typical 4- and 6-layer stack-ups of the program (`model.stackup_template`) with a window in the top copper or a pad;
         the hatched top copper (a fine grid of copper and laminate); a copper pad with its edge half a cell off the grid (the partial-cell cases); a pad and a part off the centre. A copper
         layer is described by a shape: ("full",), ("none",), ("pad", side_mm), ("window", side_mm) or ("rects", [(x0, y0, x1, y1), ...]) in mm with the origin at the board corner;
         ("hatch", pitch_mm, duty) is a fine grid of copper lines (reference only; the program sees the fill as `Zone.fill`). Everything is in mm at the interface and SI inside the program.
         The numbers of the board that both sides need (copper thickness, gaps, conductivities, films) are read from the Problem so that they cannot differ.
"""

from dataclasses import dataclass, field

import numpy as np

from pcbthermal import Problem
from pcbthermal import model as pmodel
from pcbthermal.model import Dielectric, Materials


@dataclass
class Spec:
    """!
    @brief One board of the set (lengths in mm).
    """
    name: str
    layers: int = 2
    stack: str = "simple"                       # "simple" (equal gaps) or "template" (the typical stack-up of the program for this layer count)
    thickness: float = 1.6                      # total thickness in mm (simple stack-up)
    cu_um: float = 35.0                         # copper thickness of a simple stack-up in um
    size: float = 30.0                          # square board side
    part: float = 6.0                           # side of the square part
    part_xy: tuple = None                       # lower-left corner of the part in mm (None: centred)
    power: float = 1.0
    shapes: list = None                         # one shape per layer (None: full copper everywhere)
    h_top: float = 10.0
    h_bottom: float = 10.0
    k_in: float = 0.9
    k_th: float = 0.3
    vias: tuple = ()                            # ((x_mm, y_mm), ...) program vias (default barrel); the reference gets the same copper area
    extra: dict = field(default_factory=dict)

    def shape(self, layer):
        """!
        @brief Shape of a layer.
        @param layer 0-based layer.
        @return tuple.
        """
        return ("full",) if self.shapes is None else self.shapes[layer]

    def symmetric(self):
        """!
        @brief True when the board and the part are symmetric about both mid-lines (a quadrant gives the same answer; the sides are insulated so the planes are exact).
        @return bool.
        """
        if self.part_xy is not None or self.vias:
            return False
        return all(s[0] in ("full", "none", "pad", "window") for s in (self.shapes or [("full",)] * self.layers))

    def part_rect(self):
        """!
        @brief Rectangle (x0, y0, x1, y1) in mm of the part.
        @return tuple.
        """
        if self.part_xy is None:
            c = self.size / 2
            return (c - self.part / 2, c - self.part / 2, c + self.part / 2, c + self.part / 2)
        x, y = self.part_xy
        return (x, y, x + self.part, y + self.part)


def centred(side, board):
    """!
    @brief A square centred on the board.
    @param side Side in mm.
    @param board Board side in mm.
    @return (x0, y0, x1, y1) in mm.
    """
    c = board / 2
    return (c - side / 2, c - side / 2, c + side / 2, c + side / 2)


def rects_of(shape, size):
    """!
    @brief Rectangles (mm) whose union is the copper of a shape, for the program's zones.
    @param shape A shape tuple.
    @param size Board side in mm.
    @return list of (x0, y0, x1, y1); [] for no copper.
    @throws ValueError For a shape the program cannot take as rectangles (hatch).
    """
    kind = shape[0]
    if kind == "full":
        return [(0, 0, size, size)]
    if kind == "none":
        return []
    if kind == "pad":
        return [centred(shape[1], size)]
    if kind == "rects":
        return list(shape[1])
    if kind == "window":
        x0, y0, x1, y1 = centred(shape[1], size)
        out = [(0, 0, size, y0), (0, y1, size, size), (0, y0, x0, y1), (x1, y0, size, y1)]
        return [r for r in out if r[2] > r[0] and r[3] > r[1]]
    raise ValueError(kind)


def problem(spec):
    """!
    @brief The program's Problem of a spec.
    @param spec A Spec.
    @return Problem.
    """
    mats = Materials(k_fr4_through=spec.k_th, k_fr4_inplane=spec.k_in)
    thick = spec.thickness
    t = None
    if spec.stack == "template" and spec.layers > 1:
        t = pmodel.stackup_template(spec.layers)
        thick = t["total_thickness_um"] / 1000.0
    p = Problem.new(spec.size, spec.size, spec.layers, thick, spec.cu_um, h_top=spec.h_top, h_bottom=spec.h_bottom, h_side=None, materials=mats)
    if t is not None:
        b = p.board
        b.copper_thickness = [c * 1e-6 for c in t["copper_um"]]
        b.dielectrics = [Dielectric(thickness=d["thickness_um"] * 1e-6, name=d["material"], k_through=spec.k_th, k_inplane=spec.k_in) for d in t["dielectrics"]]
        b.thickness = b.total_thickness()
    for layer in range(spec.layers):
        sh = spec.shape(layer)
        if sh[0] == "hatch":
            # The program sees a fine hatch only through the fill of a zone: duty cycle of a grid of lines of width duty * pitch in both directions
            duty = sh[2]
            p.add_zone(layer + 1, rect=(0, 0, spec.size, spec.size), fill=1.0 - (1.0 - duty) ** 2)
            continue
        for r in rects_of(sh, spec.size):
            p.add_zone(layer + 1, rect=r)
    p.add_heater(1, spec.power, rect=spec.part_rect())
    for (x, y) in spec.vias:
        p.add_via(x, y, 0.3)                    # the program's default barrel: diameter 0.3 mm, plating of the board
    return p


def raster(shape, nx, ny, dx_mm, size, x_lo=0.0, y_lo=0.0):
    """!
    @brief Copper fill of a shape on a grid of square cells (centre sampling; the edges of the shapes are meant to lie on cell edges).
    @param shape A shape tuple.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx_mm Cell size in mm.
    @param size Board side in mm.
    @param x_lo x of the left edge of the grid in mm (a quadrant starts at the centre).
    @param y_lo y of the bottom edge of the grid in mm.
    @return float array (ny, nx) in [0, 1].
    """
    xs = x_lo + (np.arange(nx) + 0.5) * dx_mm
    ys = y_lo + (np.arange(ny) + 0.5) * dx_mm
    X, Y = np.meshgrid(xs, ys)
    if shape[0] == "hatch":
        pitch, duty = shape[1], shape[2]
        line_x = ((X % pitch) / pitch) < duty
        line_y = ((Y % pitch) / pitch) < duty
        return (line_x | line_y).astype(float)
    m = np.zeros((ny, nx), dtype=bool)
    for r in rects_of(shape, size):
        m |= (X > r[0]) & (X < r[2]) & (Y > r[1]) & (Y < r[3])
    return m.astype(float)


def board_numbers(p):
    """!
    @brief The numbers of the board that the reference needs, read from the Problem.
    @param p A Problem.
    @return dict.
    """
    b = p.board
    m = b.materials
    d = {"layers": b.layers, "t_cu": [float(x) for x in b.copper_thickness], "k_cu": float(m.k_copper), "rcp_cu": float(m.rho_copper * m.cp_copper),
         "h_top": float(b.h_top), "h_bottom": float(b.h_bottom)}
    if b.layers == 1:
        d.update(gaps=[float(b.slab_thicknesses()[0] - b.copper_thickness[0])], kz=[float(m.k_fr4_through)], kxy=[float(m.k_fr4_inplane)], rcp=[float(m.rho_fr4 * m.cp_fr4)])
    else:
        kz, kxy, rcp = b.gap_properties()
        d.update(gaps=[float(x) for x in b.gap_thicknesses()], kz=[float(x) for x in kz], kxy=[float(x) for x in kxy], rcp=[float(x) for x in rcp])
    return d


# The set of the first runs (README 1.1). Names are the keys of the tables.
def simple_set():
    """!
    @brief The simple boards of the first runs: one-layer, two-layer and the typical stack-ups, with pads and windows.
    @return list of Spec.
    """
    out = []
    for side in (6, 10, 20):
        out.append(Spec(f"1L 1.6 mm pad {side}", layers=1, shapes=[("pad", side)]))
    out.append(Spec("1L 1.6 mm full", layers=1, shapes=[("full",)]))
    for side in (4, 8, 12):
        out.append(Spec(f"1L 1.6 mm window {side}", layers=1, shapes=[("window", side)]))
    for thick in (0.2, 0.4, 0.8, 1.6, 3.2):
        out.append(Spec(f"2L {thick} mm pad 10 bare bottom", layers=2, thickness=thick, shapes=[("pad", 10), ("none",)]))
        out.append(Spec(f"2L {thick} mm window 6", layers=2, thickness=thick, shapes=[("window", 6), ("full",)]))
    for side in (2, 4, 8, 12):
        out.append(Spec(f"2L 1.6 mm window {side}", layers=2, shapes=[("window", side), ("full",)]))
    out.append(Spec("2L 1.6 mm full (uniform)", layers=2))
    for n in (4, 6):
        out.append(Spec(f"{n}L typical window 6", layers=n, stack="template", shapes=[("window", 6)] + [("full",)] * (n - 1)))
        out.append(Spec(f"{n}L typical pad 10", layers=n, stack="template", shapes=[("pad", 10)] + [("full",)] * (n - 1)))
        out.append(Spec(f"{n}L typical full (uniform)", layers=n, stack="template"))
    return out
