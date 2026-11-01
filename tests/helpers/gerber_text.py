#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gerber_text.py
@brief Builders of small synthetic Gerber and Excellon files for the tests of pcbthermal.gerber (metric, 4.6 format, so every coordinate is exact to a nanometre).
@details The files are written by the test, with areas and positions that are known in closed form, so the reader is compared with geometry and not with itself.
"""


def num(v):
    """!
    @brief A coordinate in the 4.6 format (micrometre digits are plenty: 6 decimals).
    @param v Value in mm.
    @return str Integer text.
    """
    return str(int(round(v * 1e6)))


def header(extra=""):
    """!
    @brief The head of a metric 4.6 file.
    @param extra Extra extended commands (attributes, apertures) written after the format.
    @return str Gerber text.
    """
    return "%FSLAX46Y46*%\n%MOMM*%\n" + extra


def flash(x, y, d_code=10):
    """!
    @brief A flash block.
    @param x X (mm).
    @param y Y (mm).
    @param d_code Aperture number.
    @return str Gerber text.
    """
    return f"D{d_code}*\nX{num(x)}Y{num(y)}D03*\n"


def line(x0, y0, x1, y1, d_code=10):
    """!
    @brief A straight draw.
    @param x0 Start X (mm).
    @param y0 Start Y (mm).
    @param x1 End X (mm).
    @param y1 End Y (mm).
    @param d_code Aperture number.
    @return str Gerber text.
    """
    return f"D{d_code}*\nG01*\nX{num(x0)}Y{num(y0)}D02*\nX{num(x1)}Y{num(y1)}D01*\n"


def region(points):
    """!
    @brief A closed region.
    @param points List of (x, y) in mm (the contour is closed by the writer).
    @return str Gerber text.
    """
    out = "G36*\n"
    pts = list(points) + [points[0]]
    out += f"X{num(pts[0][0])}Y{num(pts[0][1])}D02*\nG01*\n"
    for x, y in pts[1:]:
        out += f"X{num(x)}Y{num(y)}D01*\n"
    return out + "G37*\n"


def end():
    """!
    @brief The end of file block.
    @return str Gerber text.
    """
    return "M02*\n"
