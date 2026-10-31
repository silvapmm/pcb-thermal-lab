#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_gerber_spec_examples.py
@brief F6, topic 15: three examples printed in the Ucamco Gerber Layer Format Specification, revision 2026.05, run through the project's independent reader and compared with the area that follows from the coordinates.
@details Example "Two square boxes" (section 2.11, pages 25 and 26): two 5 x 5 mm squares drawn with a 0.01 mm circular aperture; the stroke area of a closed convex path of side a with a round
stroke of radius r is A + P r + pi r^2 - (a - 2 r)^2 per box. Examples of section 4.10.4.8 (pages 112 and 113): "two disjunct areas" (a 10 x 10 mm square plus a diamond of diagonal 8 mm outside it, 132 mm2) and
"region with hole" (the square with the same diamond cut out of it, 68 mm2). The reader is research/gerber-import/lib/native_gerber.py (it imports nothing of the program).
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_gerber_spec_examples.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research", "gerber-import", "lib"))
import native_gerber as ng  # noqa: E402

BOXES = """G04 Ucamco ex. 1: Two square boxes*
%MOMM*%
%FSLAX26Y26*%
%TF.Part,Other,example*%
%LPD*%
%ADD10C,0.010*%
D10*
X0Y0D02*
G01*
X5000000Y0D01*
Y5000000D01*
X0D01*
Y0D01*
X6000000D02*
X11000000D01*
Y5000000D01*
X6000000D01*
Y0D01*
M02*
"""

DISJUNCT = """G04 Example contour: two disjunct areas*
%FSLAX26Y26*%
%MOMM*%
G36*
X0Y5000000D02*
G01*
Y10000000D01*
X10000000D01*
Y0D01*
X0D01*
Y5000000D01*
X-1000000D01*
X-5000000Y1000000D01*
X-9000000Y5000000D01*
X-5000000Y9000000D01*
X-1000000Y5000000D01*
X0D01*
G37*
M02*
"""

HOLE = """G04 Example contour: Region with hole*
%FSLAX26Y26*%
%MOMM*%
G36*
X0Y5000000D02*
G01*
Y10000000D01*
X10000000D01*
Y0D01*
X0D01*
Y5000000D01*
X1000000D01*
X5000000Y1000000D01*
X9000000Y5000000D01*
X5000000Y9000000D01*
X1000000Y5000000D01*
X0D01*
G37*
M02*
"""


def area(text, x_left, y_top, w, h, pix=0.02):
    """!
    @brief Copper area of a Gerber text by the reader's coverage image.
    @param text Gerber file content.
    @param x_left Left edge of the window (mm).
    @param y_top Top edge of the window (mm).
    @param w Window width (mm).
    @param h Window height (mm).
    @param pix Pixel size (mm).
    @return float Area in mm2.
    """
    cov = ng.render_coverage(text, x_left, y_top, w, h, pix, supersample=4)
    return float(cov.sum() * pix * pix)


def main():
    """!
    @brief Print the three comparisons.
    @return None.
    """
    a, r = 5.0, 0.005
    box = a * a + 4 * a * r + math.pi * r * r - (a - 2 * r) ** 2
    got = area(BOXES, -0.5, 5.5, 12.0, 6.0, 0.01)
    print("Two square boxes: expected %.5f mm2 (two rings of the round stroke), reader %.5f mm2 (%.2f %%)" % (2 * box, got, 100 * (got / (2 * box) - 1)))
    got = area(DISJUNCT, -10.0, 11.0, 22.0, 12.0)
    print("Two disjunct areas: expected 132 mm2, reader %.3f mm2 (%.2f %%)" % (got, 100 * (got / 132 - 1)))
    got = area(HOLE, -1.0, 11.0, 12.0, 12.0)
    print("Region with hole: expected 68 mm2, reader %.3f mm2 (%.2f %%)" % (got, 100 * (got / 68 - 1)))


if __name__ == "__main__":
    main()
