#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_vias_stats.py
@brief S2, first look at the boards: how many plated holes, which diameters, how close, how they meet the grid (no solver).
@details For the Allegro board, the Stormduino and the own via field: counts, diameter histogram, mean nearest-neighbour distance, and for cells of 2, 1, 0.5, 0.25 mm the share of
         cells with a via, the largest number of vias in one cell, the share of occupied cells that are shared, and the number of via pairs whose footprints overlap (centres closer
         than the mean diameter plus two cells). These are the numbers that decide the fill-in of the matrix and the size of the blocks of the block SOR. Statistics only.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_real_vias_stats.py`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import real_board as rbd


def boards():
    """!
    @brief The three hole sets of S2.
    @return list of (name, holes, width, height); a board whose files are missing is skipped with a message.
    """
    out = []
    for name in rbd.BOARDS:
        try:
            out.append((name,) + rbd.holes_of(name))
        except FileNotFoundError as e:
            print("skipped:", e)
    out.append(("own 10x10", *rbd.own_via_field(10)))
    out.append(("own 30x30", *rbd.own_via_field(30)))
    return out


def main():
    """!
    @brief Print the statistics table.
    @return None.
    """
    print("| board | holes | board (mm) | diameters (mm: count) | nearest neighbour (mm) | cell (mm) | cells with via | max vias per cell | shared cells | overlapping pairs |")
    print("| :-- | --: | :-- | :-- | --: | --: | --: | --: | --: | --: |")
    for name, holes, w, h in boards():
        for cell in (2.0, 1.0, 0.5, 0.25):
            s = rbd.hole_statistics(holes, cell, w, h)
            dia = ", ".join(f"{k:g}: {v}" for k, v in sorted(s["diameters"].items()))
            print(f"| {name} | {s['n']} | {w:.1f} x {h:.1f} | {dia} | {s['nearest_mean']:.2f} | {cell:g} | {s['cells_with_via']} of {s['cells']} | {s['max_per_cell']} | "
                  f"{100 * s['share_cells_shared']:.0f} % | {s['pairs_closer_than']} |")


if __name__ == "__main__":
    main()
