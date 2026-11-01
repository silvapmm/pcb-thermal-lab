#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file synth.py
@brief Synthetic boards with known copper patterns (no Gerber, no holes) for the study of the copper mapping with the laminate rule: the simple boards that come before the real ones.
@details Each pattern is a boolean mask at the pixel; a board is a stack of such masks as the importer would give it (`faces.ImportedBoard`, masks with rows from the TOP).
"""

import numpy as np

import faces as im

SIDE_MM = 12.0
PIX_MM = 0.1
PATTERNS = ("stripes", "slot", "mesh", "relief", "islands", "diagonal")


def pattern(name, side=SIDE_MM, pix=PIX_MM):
    """!
    @brief A known copper pattern as a boolean mask (rows from the bottom).
    @param name One of "solid", "stripes", "slot", "mesh", "relief", "islands", "diagonal".
    @param side Side of the square window (mm).
    @param pix Pixel (mm).
    @return Boolean array (n, n), True = copper.
    @throws ValueError If the name is not known.
    """
    n = int(round(side / pix))
    c = (np.arange(n) + 0.5) * pix
    X, Y = np.meshgrid(c, c)
    if name == "solid":
        return np.ones((n, n), bool)
    if name == "stripes":                       # lines along x, pitch 0.9 mm, 0.4 mm wide (44 % copper), not a multiple of the cells
        return (Y % 0.9) < 0.4
    if name == "slot":                          # a plane with a 0.3 mm bare slot along y through the middle and another along x at one third: the heat has to go round
        return ~(((np.abs(X - side / 2) < 0.15) & (Y < side * 0.8)) | ((np.abs(Y - side / 3) < 0.15) & (X > side * 0.2)))
    if name == "mesh":                          # cross-hatch, pitch 1.1 mm, 0.35 mm wide
        return ((X % 1.1) < 0.35) | ((Y % 1.1) < 0.35)
    if name == "relief":                        # a plane with a pad of 6 mm held by 0.5 mm spokes inside a 0.4 mm clearance (thermal relief)
        pad = (np.abs(X - side / 2) < 3.0) & (np.abs(Y - side / 2) < 3.0)
        ring = (np.abs(X - side / 2) < 3.4) & (np.abs(Y - side / 2) < 3.4)
        spoke = (np.abs(X - side / 2) < 0.25) | (np.abs(Y - side / 2) < 0.25)
        return (~ring) | pad | (ring & ~pad & spoke)
    if name == "islands":                       # squares of 1.5 mm with 0.5 mm gaps, no copper path between them
        return ((X % 2.0) < 1.5) & ((Y % 2.0) < 1.5)
    if name == "diagonal":                      # lines at 45 degrees, pitch 1.2 mm along x, 0.45 mm wide
        return ((X + Y) % 1.2) < 0.45
    raise ValueError(f"unknown pattern {name!r}")


def synthetic_board(top, stack, cell, side=SIDE_MM, pix=PIX_MM):
    """!
    @brief An ImportedBoard with known copper (no Gerber, no holes).
    @param top Pattern name of the top layer.
    @param stack "2solid" (bottom solid), "2same" (bottom the same pattern shifted by half a pitch), "4" (inner 1 solid, inner 2 stripes across, bottom solid).
    @param cell Cell of the thermal grid (mm).
    @param side Side of the board (mm).
    @param pix Pixel (mm).
    @return faces.ImportedBoard (layers top first; masks "binary" and "coverage" rows from the TOP, as the importer gives them).
    @throws ValueError If the stack is not known.
    """
    t = pattern(top, side, pix)
    solid = pattern("solid", side, pix)
    if stack == "2solid":
        ms = [t, solid]
    elif stack == "2same":
        ms = [t, np.roll(np.roll(t, 5, axis=0), 5, axis=1)]
    elif stack == "4":
        ms = [t, solid, pattern("stripes", side, pix).T, solid]
    else:
        raise ValueError(f"unknown stack {stack!r}")
    layers = [{"name": f"L{i + 1}", "binary": m[::-1].copy(), "coverage": m[::-1].astype(float)} for i, m in enumerate(ms)]
    return im.ImportedBoard(box=(0.0, 0.0, side, side), pix=pix, cell=cell, layers=layers, holes=[], warnings=[])
