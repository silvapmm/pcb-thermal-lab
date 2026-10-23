"""!
@file study_angles.py
@brief Tracks that are not at 0 or 90 degrees: area, connectivity and electrical resistance of a thin track on the pixel grid, against the angle.
@details A track of 30 mm and width w is written with gerbonara (so no reader wrote it) at angles 0 to 90 degrees. For each angle, width and pixel size the independent reader draws it and
         the study reports (1) the copper area against the exact one, (2) whether the track is still one piece with 4-connected pixels (the connectivity of the conduction solvers; a one-pixel
         diagonal line has none) and (3) the resistance between the two ends from `joule.solve_net` against the ideal Rs L / w: the ratio shows the grid's anisotropy, which should not depend
         on the angle. Run (numpy, scipy, shapely and gerbonara needed): .venv/bin/python research/gerbers/scripts/study_angles.py (from the repository root)
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math
from pathlib import Path

import numpy as np
from scipy import ndimage

import joule
import make_synthetic as ms
import native_gerber as ng

LENGTH = 30.0                                  # mm
WIDTHS = (0.1, 0.15, 0.2, 0.3)
ANGLES = (0, 7.5, 15, 22.5, 30, 37.5, 45, 52.5, 60, 67.5, 75, 82.5, 90)
STENCILS = ("4", "9")
PIXELS = (0.1, 0.05, 0.025)
RS = 0.0005                                    # ohm per square (only the ratio matters)


def one(width, angle, pix):
    """!
    @brief One track: draw it with the independent reader and measure it.
    @param width Track width (mm).
    @param angle Angle to the X axis (degrees).
    @param pix Pixel size (mm).
    @return Tuple (area error %, connected pieces, dict stencil -> resistance ratio or None when the ends are not connected).
    """
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    x0, y0 = 1.0, 1.0
    obj, geom = ms.line(x0, y0, x0 + LENGTH * ca, y0 + LENGTH * sa, width)
    gf, _ = ms.build([(obj, geom, True)])
    path = ms.OUT / "angle_tmp.gbr"
    ms.OUT.mkdir(parents=True, exist_ok=True)
    gf.save(path)
    layer = ng.Layer(path.read_text())
    bb = layer.bbox()
    cv = ng.Canvas(bb[0] - 0.5, bb[3] + 0.5, bb[2] - bb[0] + 1.0, bb[3] - bb[1] + 1.0, pix)
    layer.draw(cv)
    mask = cv.mask
    err = 100 * (mask.sum() * pix * pix / geom.area - 1)
    lab, n = ndimage.label(mask)                               # 4-connected pieces
    r_ratio = {}
    # Terminals: pixels within one track width of each end centre, 0 to w/2 in from the end
    cx = cv.x0 + (np.arange(mask.shape[1]) + 0.5) * pix
    cy = cv.y0 - (np.arange(mask.shape[0]) + 0.5) * pix
    X, Y = np.meshgrid(cx, cy)
    d0 = np.hypot(X - x0, Y - y0)
    d1 = np.hypot(X - (x0 + LENGTH * ca), Y - (y0 + LENGTH * sa))
    # Use the end caps only (circle of radius w/2): the ideal length between the two cap centres is LENGTH
    src, snk = mask & (d0 <= width / 2), mask & (d1 <= width / 2)
    for st in STENCILS:
        try:
            r, _, _ = joule.solve_net(mask, RS, src, snk, 1.0, stencil=st)
            # Ideal: RS L / w between the cap centres; the caps add a small spreading term, the ratio is what matters
            r_ratio[st] = r / (RS * LENGTH / width)
        except ValueError:
            r_ratio[st] = None
    path.unlink()
    return err, n, r_ratio


def main():
    """!
    @brief Run the sweep and print one table per pixel size.
    @return None.
    """
    for pix in PIXELS:
        print(f"\npixel {pix} mm: area error % / pieces / R ratio with the 4-point and the 9-point stencil (R grid over ideal Rs L / w; '-' = ends not connected)")
        print(f"{'angle':>6s}" + "".join(f"{'w=' + str(w):>34s}" for w in WIDTHS))
        for a in ANGLES:
            row = f"{a:6.1f}"
            for w in WIDTHS:
                err, n, rr = one(w, a, pix)
                row += f"{err:+7.1f} {n:3d} " + "".join((f"{rr[st]:7.3f}" if rr[st] is not None else "      -") for st in STENCILS) + "  "
            print(row)


if __name__ == "__main__":
    main()
