#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_grid_error_drawn_copper.py
@brief The grid error of the program's FVM with DRAWN copper (no import) at the cells 0.5, 1 and 2 mm, in the setting of the 24 mm windows of `study_program_cells.py`:
       how large is the overshoot that a 4 mm part two cells wide gets from the grid alone, with full copper, half-fill copper and no copper at all?
@details Answers the question of `docs/validation.md` 27.3: is the overshoot of the imported faces at a 2 mm cell (+7.2 to +9.6 %) the program's own grid error?
         Setting: 24 x 24 mm board, simple stack-up 1.6 mm, copper 35 micrometres, h = 10 W/m2K on both faces, adiabatic sides, heater 4 mm of 1 W at the centre of the
         top layer (edges on the lines of every cell), the heater mean of the top layer (cells whose centres lie in the heater block), the FVM at each cell against
         the same board at 0.25 mm (and 0.125 mm as the check of the reference). Copper: every layer a zone over the whole board with fill 1 or 0.5, or no zone (bare laminate).
         Run (repository root, about 20 s, peak resident size 2.5 GB, the bare boards with their laminate nodes at 0.125 mm): .venv/bin/python research/gerber-real-boards/scripts/study_grid_error_drawn_copper.py
         NOT verified: heaters other than a 4 mm square, other boards, copper patterns other than uniform (the imported windows are patterned: their spreading lies between).
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import numpy as np

from pcbthermal import fvm
from pcbthermal.model import Problem

SIDE, HEATER, THICK, H_FACE = 24.0, 4.0, 1.6, 10.0
CELLS = (0.5, 1.0, 2.0)


def board(layers, fill):
    """!
    @brief The 24 mm board with drawn copper.
    @param layers Number of copper layers.
    @param fill Fill of the zone drawn over the whole of every layer (None: no zone, bare laminate).
    @return Problem.
    """
    p = Problem.new(SIDE, SIDE, layers=layers, thickness_mm=THICK, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    c = SIDE / 2
    p.add_heater(1, 1.0, rect=(c - HEATER / 2, c - HEATER / 2, c + HEATER / 2, c + HEATER / 2))
    if fill is not None:
        for layer in range(1, layers + 1):
            p.add_zone(layer, rect=(0.0, 0.0, SIDE, SIDE), fill=fill)    # A zone over the whole board: uniform copper
    return p


def heater_mean(p, cell):
    """!
    @brief Mean rise of the top layer over the cells whose centres lie in the heater block (the metric of study_program_cells.py).
    @param p Problem.
    @param cell Cell in mm.
    @return float K.
    """
    n = int(round(SIDE / cell))
    theta = fvm.Network(p, n, n).solve_steady()[0]
    c = SIDE / 2
    x = (np.arange(n) + 0.5) * cell
    inside = (x > c - HEATER / 2) & (x < c + HEATER / 2)
    return float(theta[0][inside[:, None] & inside[None, :]].mean())


def main():
    """!
    @brief Print the grid error in percent of the heater rise for every copper case and layer count.
    @return None.
    """
    for layers in (2, 4):
        for name, fill in (("full copper", 1.0), ("half fill", 0.5), ("bare laminate", None)):
            p = board(layers, fill)
            ref = heater_mean(p, 0.25)
            check = 100.0 * (heater_mean(p, 0.125) / ref - 1.0)
            errors = "  ".join(f"{cell:g} mm {100.0 * (heater_mean(p, cell) / ref - 1.0):+.2f}" for cell in CELLS)
            print(f"L{layers} {name:13s} reference {ref:8.3f} K (0.125 mm {check:+.2f} %): {errors}", flush=True)


if __name__ == "__main__":
    main()
