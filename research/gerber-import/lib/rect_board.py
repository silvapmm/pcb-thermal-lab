#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rect_board.py
@brief A simple test board made only of squares and rectangles (one copper layer, 40 x 30 mm), for comparing the models of the program on geometry that needs no interpretation.
@details Features (mm, y up): a 10 x 10 square pad under the heater, a 2 mm wide rectangular track to an 8 x 8 square pad, a floating 6 x 6 square (no connection), a 0.5 mm thin rectangle along the bottom edge and a 12 x 4 rectangle.
         `rects(shift)` moves every feature by `shift` mm in x and y: 0 puts all the edges on the 1 mm cells of the thermal grid (the program's own zone fill is exact there), 0.4 puts them between the cell edges.
         The same rectangles feed the program as zones (native path) and the 0.1 mm mask (import path); the heater is a 6 x 6 mm block of 1 W at the centre of the large pad.
"""

import numpy as np

W, H = 40.0, 30.0
HEATER = (7.0, 12.0, 13.0, 18.0)                         # x0, y0, x1, y1 before the shift (inside the 10 x 10 pad)


def rects(shift=0.0):
    """!
    @brief The copper rectangles of the board.
    @param shift Offset added to x and y of every feature (mm).
    @return list of (x0, y0, x1, y1) in mm.
    """
    base = [(5.0, 10.0, 15.0, 20.0),            # large square pad under the heater
            (15.0, 14.0, 28.0, 16.0),           # 2 mm track
            (28.0, 11.0, 36.0, 19.0),           # 8 x 8 pad at the end of the track
            (20.0, 22.0, 26.0, 28.0),           # floating 6 x 6 square
            (2.0, 3.0, 38.0, 3.5),              # 0.5 mm thin rectangle
            (14.0, 5.0, 26.0, 9.0)]             # 12 x 4 rectangle
    return [(a + shift, b + shift, c + shift, d + shift) for a, b, c, d in base]


def heater(shift=0.0):
    """!
    @brief The heater block moved with the copper.
    @param shift Offset (mm).
    @return tuple (x0, y0, x1, y1).
    """
    return tuple(v + shift for v in HEATER)


def mask(shift=0.0, pix=0.1):
    """!
    @brief The copper mask of the board.
    @param shift Offset (mm).
    @param pix Pixel (mm).
    @return numpy.ndarray Boolean mask, rows from the bottom (y up).
    """
    m = np.zeros((int(round(H / pix)), int(round(W / pix))), bool)
    for x0, y0, x1, y1 in rects(shift):
        m[int(round(y0 / pix)):int(round(y1 / pix)), int(round(x0 / pix)):int(round(x1 / pix))] = True
    return m
