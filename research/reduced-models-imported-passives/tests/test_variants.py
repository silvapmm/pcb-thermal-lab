#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_variants.py
@brief Checks of lib/variants.py on a small synthetic imported board (no library board needed): the uniform and tile variants keep the mean copper of the mask, one heater is kept, the
       local measures read the mask. The RP2040 itself is used only when PCBT_REAL_BOARDS is set.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "lib"))

import variants as V  # noqa: E402
from pcbthermal import copper, model  # noqa: E402


def _board():
    """!
    @brief A 20 x 10 mm two-layer board with an imported top mask (left half copper, a 1 mm track to a 2 x 2 mm pad on the right) and a heater on the pad.
    @return Problem.
    """
    p = model.Problem.new(20, 10, layers=2)
    pix = 0.05
    rows, cols = int(10 / pix), int(20 / pix)
    ras = np.zeros((rows, cols), np.uint8)
    ras[:, :int(8 / pix)] = 255                              # plane
    ras[int(4.5 / pix):int(5.5 / pix), int(8 / pix):int(15 / pix)] = 255      # track
    ras[int(4 / pix):int(6 / pix), int(15 / pix):int(17 / pix)] = 255          # pad
    p.imported = copper.imported_from_rasters([ras], pix, names=["top"], indices=[0])
    p.add_heater(layer=1, rect=(15, 4, 17, 6), power=1.0, name="H1")
    return p, ras


def test_uniform_keeps_mean_fill():
    """!
    @brief The uniform variant has one zone per imported layer at the mean coverage of the mask.
    @return None.
    """
    p, ras = _board()
    u = V.variant(p, "uniform")
    assert u.imported is None and len(u.zones) == 1
    assert abs(u.zones[0].fill - ras.mean() / 255.0) < 1e-9


def test_tiles_keep_total_copper():
    """!
    @brief The tile variant keeps the copper area of the mask (sum of fill x tile area) within a pixel row.
    @return None.
    """
    p, ras = _board()
    t = V.variant(p, "tiles", 2.0)
    area = sum(z.fill * (z.polygon[:, 0].max() - z.polygon[:, 0].min()) * (z.polygon[:, 1].max() - z.polygon[:, 1].min()) for z in t.zones)
    assert abs(area / (ras.mean() / 255.0 * 20e-3 * 10e-3) - 1) < 0.01


def test_only_heater_and_measures():
    """!
    @brief only_heater keeps the named heater; the local measures see a pad fully on copper and the fill falling with the window.
    @return None.
    """
    p, _ = _board()
    q = V.only_heater(p, "H1")
    assert len(q.heaters) == 1 and V.only_heater(p, "none") is None
    m = V.local_measures(q, "H1", radii=(1.0, 5.0))
    assert m["under"] > 0.99 and m["fill_1"] > m["fill_5"]
    assert abs(m["side_mm"] - 2.0) < 1e-6


@pytest.mark.skipif("PCBT_REAL_BOARDS" not in os.environ, reason="library of boards not linked")
def test_rp2040_opens():
    """!
    @brief The RP2040 of the library opens with 27 heat sources.
    @return None.
    """
    _, prob = V.open_board("rp2040", 1.0)
    assert len(prob.heaters) == 27
