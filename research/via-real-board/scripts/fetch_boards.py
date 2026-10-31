#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fetch_boards.py
@brief Fetch (if missing) the two third-party boards used by study S2 into the git-ignored data folder of gerber-import, and say where they are and what licence they carry.
@details Nothing is copied into this folder. The Allegro board has no stated licence: only numbers (counts, diameters, temperatures) may be quoted from it, never a picture of it.
         The Stormduino is MIT: its figures may be committed. Needs the network the first time. Run: `.venv/bin/python research/via-real-board/scripts/fetch_boards.py`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import paths
import real_board as rbd


def main():
    """!
    @brief Fetch the boards and print the folder, the licence and the hole counts.
    @return None.
    """
    print("data folder:", paths.gerber_data())
    for name, spec in rbd.BOARDS.items():
        rbd.fetch(name)
        holes, w, h = rbd.holes_of(name)
        print(f"{name}: {len(holes)} plated holes, {w:.1f} x {h:.1f} mm, {spec['layers']} copper layers, licence: {spec['licence']} ({spec['origin']})")


if __name__ == "__main__":
    main()
