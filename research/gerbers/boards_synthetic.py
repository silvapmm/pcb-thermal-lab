"""!
@file boards_synthetic.py
@brief Deterministic synthetic copper layouts written as Gerber text (round tracks and pads, a ground pour with clearance holes), used by the tests and the studies.
"""

import math

import numpy as np

HEAD = "%FSLAX36Y36*%\n%MOMM*%\n"


def mm(v):
    """!
    @brief A length in mm as the integer string of a 3.6 coordinate format.
    @param v Length (mm).
    @return String of digits.
    """
    return str(int(round(v * 1e6)))


def random_board_text(seed=11, tracks=110, pads=70, size=36.0, widths=(0.15, 0.2, 0.3, 0.5), pour=True, max_len=14.0, holes=20):
    """!
    @brief A Gerber text with random round tracks (any angle) and round pads, optionally with a ground pour on the left third with clearance holes.
    @param seed Random seed.
    @param tracks Number of tracks.
    @param pads Number of pads.
    @param size Board side (mm).
    @param widths Track widths to choose from (mm).
    @param pour True to add the pour.
    @param max_len Longest track (mm).
    @param holes Number of clearance holes in the pour.
    @return Gerber text.
    """
    rng = np.random.default_rng(seed)
    t = HEAD + "".join(f"%ADD{10 + i}C,{w}*%\n" for i, w in enumerate(widths)) + "".join(f"%ADD{20 + i}C,{d}*%\n" for i, d in enumerate((0.8, 1.2, 2.0)))
    if pour:
        third = size / 3.0
        t += "G36*\n" + f"X{mm(0)}Y{mm(0)}D02*\nX{mm(third)}Y{mm(0)}D01*\nX{mm(third)}Y{mm(size)}D01*\nX{mm(0)}Y{mm(size)}D01*\nX{mm(0)}Y{mm(0)}D01*\nG37*\n"
        t += "%LPC*%\n%ADD30C,1.0*%\nD30*\n" + "".join(f"X{mm(x)}Y{mm(y)}D03*\n" for x, y in rng.uniform(1, third - 1, (holes, 2))) + "%LPD*%\n"
    for _ in range(tracks):
        x, y = rng.uniform(1, size - 1, 2)
        a, ln = rng.uniform(0, 2 * math.pi), rng.uniform(2, max_len)
        x2, y2 = min(max(x + ln * math.cos(a), 0.5), size - 0.5), min(max(y + ln * math.sin(a), 0.5), size - 0.5)
        t += f"D{10 + int(rng.integers(len(widths)))}*\nX{mm(x)}Y{mm(y)}D02*\nX{mm(x2)}Y{mm(y2)}D01*\n"
    for _ in range(pads):
        x, y = rng.uniform(1, size - 1, 2)
        t += f"D{20 + int(rng.integers(3))}*\nX{mm(x)}Y{mm(y)}D03*\n"
    return t + "M02*\n"
