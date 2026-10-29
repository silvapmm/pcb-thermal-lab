"""!
@file real_board.py
@brief A real board (the Stormduino, from its own KiCad file) drawn as program zones: every track, pad and zone fill becomes a solid zone polygon, the way an import of CAD polygons would hand them to the program.
@details Question answered: what does the way zones are combined do to a board whose copper is a crowd of overlapping and abutting polygons? A track meets a pad, parallel tracks share a cell,
         a zone fill surrounds both. The KiCad file is read with research/gerber-import/lib/kicad_pcb.py; the data is git-ignored and is found in this worktree or in the main checkout
         (research/gerber-import/data/storm, fetched by research/gerber-import/scripts/fetch_boards.py; nothing of it is stored in the repository).
         Tracks are rectangles with a 10-sided disc at each end (round caps), pads are rectangles, rounded rectangles (as rectangles), ovals (16-gon capsules) and circles (16-gon), zone fills are
         their filled polygons. Vias are left out (the program's vias are not zones). Coordinates: file x, y down -> board x, y up.
"""

import math
import sys
from pathlib import Path

import numpy as np

from paths import REPO

STORM = "research/gerber-import/data/storm/stormduino.kicad_pcb"


def find_file():
    """!
    @brief Locate the KiCad file of the Stormduino in this worktree or in the main checkout the worktree belongs to.
    @return Path of the file.
    @throws FileNotFoundError If the board was not fetched anywhere.
    """
    here = REPO / STORM
    if here.exists():
        return here
    # A worktree lives in <main>/.claude/worktrees/<name>: the main checkout holds the git-ignored data
    for parent in REPO.parents:
        cand = parent / STORM
        if cand.exists():
            return cand
    raise FileNotFoundError("Stormduino not fetched: run research/gerber-import/scripts/fetch_boards.py")


def read():
    """!
    @brief Read the board with the reader of the Gerber investigation.
    @return dict from kicad_pcb.read.
    """
    sys.path.insert(0, str(REPO / "research" / "gerber-import" / "lib"))
    import kicad_pcb
    return kicad_pcb.read(str(find_file()))


def disc(cx, cy, r, n=10):
    """!
    @brief Regular polygon approximating a disc.
    @param cx Centre x (mm).
    @param cy Centre y (mm).
    @param r Radius (mm).
    @param n Number of vertices.
    @return numpy.ndarray (n, 2).
    """
    a = 2 * math.pi * (np.arange(n) + 0.5) / n
    return np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a)])


def box(cx, cy, w, h, deg):
    """!
    @brief Rectangle rotated about its centre.
    @param cx Centre x (mm).
    @param cy Centre y (mm).
    @param w Width (mm).
    @param h Height (mm).
    @param deg Rotation in degrees (counter-clockwise, board axes).
    @return numpy.ndarray (4, 2).
    """
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return np.column_stack([cx + pts[:, 0] * c - pts[:, 1] * s, cy + pts[:, 0] * s + pts[:, 1] * c])


def capsule(cx, cy, w, h, deg, n=16):
    """!
    @brief Stadium (oval pad) as a polygon.
    @param cx Centre x (mm).
    @param cy Centre y (mm).
    @param w Width (mm).
    @param h Height (mm).
    @param deg Rotation in degrees.
    @param n Vertices per semicircle.
    @return numpy.ndarray.
    """
    r = min(w, h) / 2
    half = (max(w, h) - 2 * r) / 2
    t = np.linspace(-math.pi / 2, math.pi / 2, n)
    right = np.column_stack([half + r * np.cos(t), r * np.sin(t)])
    left = np.column_stack([-half - r * np.cos(t), -r * np.sin(t)])
    pts = np.vstack([right, left])
    if h > w:                                         # the long side is y
        pts = pts[:, ::-1] * [1, 1]
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.column_stack([cx + pts[:, 0] * c - pts[:, 1] * s, cy + pts[:, 0] * s + pts[:, 1] * c])


def objects(data):
    """!
    @brief All copper objects of the board as polygons in board millimetres (x right, y up), by layer (0 = F.Cu, 1 = B.Cu).
    @param data dict from kicad_pcb.read.
    @return tuple (dict layer -> list of polygons, (xmin, ymin, xmax, ymax) of the objects).
    """
    out = {0: [], 1: []}
    name = {"F.Cu": 0, "B.Cu": 1}
    for s in data["segments"]:
        if s["layer"] not in name:
            continue
        (x0, y0), (x1, y1) = s["a"], s["b"]
        y0, y1 = -y0, -y1
        L = math.hypot(x1 - x0, y1 - y0)
        k = name[s["layer"]]
        if L > 1e-9:
            out[k].append(box((x0 + x1) / 2, (y0 + y1) / 2, L, s["w"], math.degrees(math.atan2(y1 - y0, x1 - x0))))
        out[k].append(disc(x0, y0, s["w"] / 2))
        out[k].append(disc(x1, y1, s["w"] / 2))
    for p in data["pads"]:
        if p["kind"] == "np_thru_hole":
            continue
        layers = [name[l] for l in ("F.Cu", "B.Cu") if l in p["layers"] or "*.Cu" in p["layers"]]
        x, y = p["p"][0], -p["p"][1]
        w, h = p["size"]
        ang = -p["angle"]                              # file angles are clockwise (y down)
        for k in layers:
            if p["shape"] == "circle":
                out[k].append(disc(x, y, w / 2, 16))
            elif p["shape"] == "oval":
                out[k].append(capsule(x, y, w, h, ang))
            else:
                out[k].append(box(x, y, w, h, ang))
    for z in data["zones"]:
        if z["layer"] in name:
            for poly in z["filled"]:
                out[name[z["layer"]]].append(np.array([(x, -y) for x, y in poly]))
    allp = np.vstack([q for v in out.values() for q in v])
    return out, (allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())


def window(objs, x0, y0, size):
    """!
    @brief The objects that touch a square window, shifted so that the window starts at (0, 0).
    @param objs dict layer -> polygons from `objects`.
    @param x0 Left of the window (mm).
    @param y0 Bottom of the window (mm).
    @param size Side of the window (mm).
    @return dict layer -> list of polygons (mm) in window coordinates.
    """
    out = {}
    for k, polys in objs.items():
        keep = []
        for q in polys:
            if q[:, 0].max() < x0 or q[:, 0].min() > x0 + size or q[:, 1].max() < y0 or q[:, 1].min() > y0 + size:
                continue
            keep.append(q - [x0, y0])
        out[k] = keep
    return out
