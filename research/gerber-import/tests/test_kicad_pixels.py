"""!
@file test_kicad_pixels.py
@brief The nets of the Stormduino's own `.kicad_pcb`, drawn on the pixel grid, against the copper the independent reader draws from its Gerbers (README 4.46).
@details Needs the downloaded board (scripts/fetch_boards.py); skipped when it is missing. Small synthetic objects check the rasteriser itself without the board.
"""

import numpy as np
import pytest

import study_kicad_pixels as kp
from paths import DATA


class FakeGrid(kp.Grid):
    """!
    @brief A grid of 0.1 mm pixels over a 10 x 10 mm window for the tests of the rasteriser, without an imported board.
    """

    def __init__(self):
        """!
        @brief Build the grid.
        @return None.
        """
        self.rows = self.cols = 100
        self.pix = 0.1
        self.x = (np.arange(100) + 0.5) * 0.1
        self.y = (np.arange(100) + 0.5) * 0.1


def test_track_pad_and_stadium_cover_the_right_area():
    """!@brief A track of 1 mm width and 5 mm length with round ends covers its exact area (5 + pi/4 mm2) and a circular pad pi r2, within a pixel of perimeter. @return None."""
    g = FakeGrid()
    rs, cs, m = kp.segment_mask(g, (2.0, 5.0), (7.0, 5.0), 1.0)
    assert abs(m.sum() * 0.01 - (5.0 + np.pi / 4)) < 0.15
    rs, cs, m = kp.pad_mask(g, {"p": (5.0, 5.0), "size": (2.0, 2.0), "shape": "circle", "angle": 0.0})
    assert abs(m.sum() * 0.01 - np.pi) < 0.1
    rs, cs, m = kp.pad_mask(g, {"p": (5.0, 5.0), "size": (3.0, 1.0), "shape": "oval", "angle": 90.0})
    assert abs(m.sum() * 0.01 - (2.0 + np.pi / 4)) < 0.1                   # a stadium of 3 x 1 mm
    ys, xs = np.where(m)
    assert (ys.max() - ys.min()) > (xs.max() - xs.min())                    # turned by 90 degrees: taller than wide


def test_cad_copper_is_on_gerber_copper_on_the_stormduino():
    """!@brief Every pixel the CAD file draws is Gerber copper (under 0.01 % of them are not) and the Gerber copper the CAD file does not explain, farther than one pixel from any CAD object, is under 0.3 % of the layer. @return None."""
    kicad = DATA / "storm" / "stormduino.kicad_pcb"
    if not kicad.exists():
        pytest.skip("the Stormduino files are not downloaded (scripts/fetch_boards.py)")
    import importer as im
    import kicad_pcb
    from scipy import ndimage
    ib = im.import_board(im.roles_of_downloaded("storm"), pix=0.1, cell=1.0)
    grid = kp.Grid(ib)
    net, kind = kp.rasterise(grid, kicad_pcb.read(kicad))
    for li in range(2):
        g, k = ib.layers[li]["binary"], kind[li] > 0
        assert (k & ~g).sum() < 1e-4 * k.sum()
        far = g & ~k & ~ndimage.binary_dilation(k, iterations=1)
        assert far.sum() < 0.003 * g.sum()
