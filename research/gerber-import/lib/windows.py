#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file windows.py
@brief Cut 36 x 36 mm windows (0.1 mm pixels, centre-sampled copper) out of the downloaded boards for the mapping studies.
@details Six random windows per board whose 6 x 6 mm heater block (at 12..18 mm from the window corner, so that 0.6, 1.0 and 2.0 mm cells all tile it)
         has between 15 % and 90 % of copper and whose window has at least 15 % of copper. The seed is fixed: the same boards give the same windows.
         The reader is the independent NumPy one by default (readers.py); GERBER_READER=shapely uses gerbonara and shapely.
"""

import sys
from pathlib import Path

import numpy as np

import readers

PIX = 0.1                    # mm
WIN = 36.0                   # mm, window side
HEATER = (12.0, 18.0)        # mm, heater block inside the window (both directions)
BOARDS = ["storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz"]
from paths import OUT
FILE = OUT / f"windows_{readers.READER}.npz"          # one cache per reader


def build(per_board=6, seed=7):
    """!
    @brief Build the windows and save them to out/windows.npz.
    @param per_board Windows per board.
    @param seed Seed of the random generator.
    @return Tuple (masks array (K, 360, 360) of bool, list of tuples (board, x_left, y_bottom, window copper fraction, heater copper fraction)).
    """
    rng = np.random.default_rng(seed)
    masks, meta = [], []
    n = int(round(WIN / PIX))
    h0, h1 = int(HEATER[0] / PIX), int(HEATER[1] / PIX)
    for b in BOARDS:
        files = readers.board_files(b)
        x0, y0, x1, y1 = readers.box(files.get("edge"), files["F"])
        got = tries = 0
        while got < per_board and tries < 400:
            tries += 1
            ox, oy = rng.uniform(x0, x1 - WIN), rng.uniform(y0, y1 - WIN)
            m = readers.render(files["F"], ox, oy + WIN, WIN, WIN, PIX)
            hb = m[h0:h1, h0:h1]
            if 0.15 <= hb.mean() <= 0.9 and m.mean() >= 0.15:
                masks.append(m)
                meta.append((b, round(ox, 1), round(oy, 1), round(float(m.mean()), 3), round(float(hb.mean()), 3)))
                got += 1
        print(f"{b}: {got} windows in {tries} tries", flush=True)
    OUT.mkdir(exist_ok=True)
    np.savez_compressed(FILE, masks=np.array(masks), meta=np.array(meta, dtype=object))
    return np.array(masks), meta


def load():
    """!
    @brief Windows from out/windows.npz (built on first use).
    @return Tuple (masks, meta) as returned by build().
    """
    if not FILE.exists():
        return build()
    d = np.load(FILE, allow_pickle=True)
    return d["masks"], [tuple(m) for m in d["meta"]]


if __name__ == "__main__":
    masks, meta = build()
    print(len(masks), "windows; mean copper fraction", round(float(np.mean([m[3] for m in meta])), 3))
