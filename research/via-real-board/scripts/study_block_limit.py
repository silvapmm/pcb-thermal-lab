#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_block_limit.py
@brief S2, where the block SOR breaks: footprints that overlap merge into one block, and the dense inverse of a block has (unknowns of the block)^2 entries. Counts only, no solve.
@details An n x n array of 0.3 mm vias at a pitch p on a board that holds it, four planes, cell c; the network is assembled with the recommended treatment and `matrix_stats.block_structure`
         reports the number of blocks after merging, the largest block (unknowns), the memory the dense inverses would need (8 bytes per entry) and the colours. Pitches from 1.5 mm
         (footprints apart) to 0.5 mm (a continuous via field). Nothing is inverted, so the run is light; the inverse memory is the figure that matters.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_block_limit.py`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import logging

import matrix_stats as ms
import real_board as rbd


def main():
    """!
    @brief Print the block structure against the pitch of the array and the cell.
    @return None.
    """
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    print("| array | pitch (mm) | cell (mm) | unknowns | blocks | largest block (unknowns) | dense inverses (MB) | colours |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
    for n in (20, 40):
        for pitch in (1.5, 1.0, 0.8, 0.6):
            for cell in (1.0, 0.5):
                holes, w, h = rbd.via_array_pitch(n, pitch, margin_mm=5.0)
                p = rbd.problem_from_holes(holes, w, h, layers=4, center=(w / 2, h / 2))
                net = ms.build(p, cell, "mw", board_only=True, image=False)
                b = ms.block_structure(net)
                print(f"| {n} x {n} | {pitch:g} | {cell:g} | {net.K.shape[0]:,} | {b['blocks']} | {b['largest_block']:,} | {b['inverse_bytes'] / 1e6:,.0f} | {b['colours']} |", flush=True)


if __name__ == "__main__":
    main()
