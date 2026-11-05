#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file synth_paste_board.py
@brief A synthetic board of our own (paste layers and placement files written here) for the figure that explains how the parts of an import are found.
@details Nothing here comes from a third-party design: the parts, their pads and their positions are invented, written as Gerber text (solder-paste regions with `TO.C`) and as a KiCad
         position report, and read back by the program's own parsers (`pcbthermal.gerber.parse_layer`, `pcbthermal.gerber.parts`). The footprint names follow the KiCad convention so that
         the envelope table of the program recognises them. Lengths in mm, angles in degrees (counter-clockwise).
         The top side holds a QFN with an exposed pad, a SOT-23 turned by 90 degrees, a 0402 capacitor 0.5 mm from one of its pins, two 0402 capacitors whose paste openings touch,
         more resistors and capacitors at 90, 180 and 270 degrees, and a pin-header connector that has no paste. The bottom side holds four parts.
"""

import math

#: Pitch (mm) of the QFN pads.
QFN_PITCH = 0.5


def _qfn_pads():
    """!
    @brief The paste openings of the QFN-20 (5 pads a side, pitch 0.5 mm, 0.7 x 0.3 mm each) and its exposed pad (a single 2.0 x 2.0 mm opening).
    @return list of (u, v, size_u, size_v) in mm, in the footprint frame.
    """
    pads = []
    for k in range(5):
        t = (k - 2) * QFN_PITCH
        pads += [(-2.2, t, 0.7, 0.3), (2.2, t, 0.7, 0.3), (t, -2.2, 0.3, 0.7), (t, 2.2, 0.3, 0.7)]
    pads.append((0.0, 0.0, 2.0, 2.0))
    return pads


#: Footprint name -> paste openings (centre u, centre v, size u, size v) in the footprint frame, mm.
PADS = {
    "QFN-20-1EP_4x4mm_P0.5mm_EP2.6x2.6mm": _qfn_pads(),
    "SOT-23": [(-1.1, 0.95, 1.0, 0.6), (-1.1, -0.95, 1.0, 0.6), (1.1, 0.0, 1.0, 0.6)],
    "R_0402_1005Metric": [(-0.5, 0.0, 0.5, 0.6), (0.5, 0.0, 0.5, 0.6)],
    "C_0402_1005Metric": [(-0.5, 0.0, 0.5, 0.6), (0.5, 0.0, 0.5, 0.6)],
    "R_0603_1608Metric": [(-0.775, 0.0, 0.9, 0.95), (0.775, 0.0, 0.9, 0.95)],
    "C_0603_1608Metric": [(-0.775, 0.0, 0.9, 0.95), (0.775, 0.0, 0.9, 0.95)],
    "PinHeader_1x04_P2.54mm_Vertical": [],               # a through-hole connector: no paste
}

#: The parts of the top side, as placed (true positions): ref, value, footprint, x (mm), y (mm), rotation (degrees).
TOP = [
    ("U1", "QFN-20", "QFN-20-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", 11.0, 12.0, 0.0),
    ("U2", "BC847", "SOT-23", 22.0, 14.0, 90.0),
    ("C1", "100n", "C_0402_1005Metric", 22.0, 11.6, 0.0),          # 0.5 mm from the lower pins of U2
    ("C2", "1u", "C_0402_1005Metric", 6.0, 4.0, 90.0),             # C2 and C3 stand side by side: their pads touch
    ("C3", "1u", "C_0402_1005Metric", 6.6, 4.0, 90.0),
    ("R1", "10k", "R_0402_1005Metric", 14.0, 4.0, 0.0),
    ("R2", "4k7", "R_0603_1608Metric", 19.0, 4.0, 180.0),
    ("R3", "1k", "R_0402_1005Metric", 27.0, 8.0, 90.0),
    ("C4", "10u", "C_0603_1608Metric", 27.0, 18.0, 270.0),
    ("J1", "Header", "PinHeader_1x04_P2.54mm_Vertical", 3.0, 19.0, 0.0),
]

#: The parts of the bottom side (true positions in the frame of the Gerber files).
BOTTOM = [
    ("U3", "BC857", "SOT-23", 10.0, 14.0, 0.0),
    ("C5", "100n", "C_0402_1005Metric", 20.0, 8.0, 90.0),
    ("R4", "2k2", "R_0603_1608Metric", 24.0, 16.0, 0.0),
    ("R5", "470", "R_0402_1005Metric", 6.0, 5.0, 0.0),
]

#: The shift (mm) of the placement file of the top side against the Gerber files (the file says the part is at its true position plus this).
SHIFT = (3.0, -2.0)


def pad_polygons(part, side="top"):
    """!
    @brief The paste openings of a part in the board frame.
    @param part Tuple (ref, value, footprint, x, y, rotation) with the true position in mm and the rotation in degrees.
    @param side "top" or "bottom": the footprint of a bottom part is mirrored (the local x changes sign) before the rotation, as in the Gerber X3 specification.
    @return list of polygons, each a list of four (x, y) corners in mm.
    """
    _, _, fp, x, y, rot = part
    a = math.radians(rot)
    c, s = math.cos(a), math.sin(a)
    out = []
    for u, v, w, h in PADS[fp]:
        if side == "bottom":
            u = -u
        corners = [(u - w / 2, v - h / 2), (u + w / 2, v - h / 2), (u + w / 2, v + h / 2), (u - w / 2, v + h / 2)]
        out.append([(x + cu * c - cv * s, y + cu * s + cv * c) for cu, cv in corners])
    return out


def paste_text(parts, side="top", refs=True):
    """!
    @brief Gerber text of a solder-paste layer: one region per opening, with the `TO.C` designator of the part when `refs` is True.
    @param parts List of part tuples.
    @param side "top" or "bottom".
    @param refs True: write `%TO.C,<ref>*%` before each region (and `%TD*%` after); False: the layer names no part.
    @return str, RS-274X in millimetres, 4.6 format.
    """
    def f(v):
        """!@brief A length as an integer of the 4.6 format. @param v Length in mm. @return str."""
        return str(int(round(v * 1e6)))

    t = f"%TF.FileFunction,Paste,{'Top' if side == 'top' else 'Bot'}*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
    for part in parts:
        for poly in pad_polygons(part, side):
            if refs:
                t += f"%TO.C,{part[0]}*%\n"
            t += "G36*\n" + f"X{f(poly[0][0])}Y{f(poly[0][1])}D02*\n" + "".join(f"X{f(x)}Y{f(y)}D01*\n" for x, y in poly[1:] + poly[:1]) + "G37*\n"
            if refs:
                t += "%TD*%\n"
    return t + "M02*\n"


def placement_text(top, bottom=(), shift=(0.0, 0.0), negate_bottom_x=False):
    """!
    @brief A KiCad position report of the parts, as a CAD tool would write it.
    @param top Top-side part tuples (true positions).
    @param bottom Bottom-side part tuples (true positions).
    @param shift (dx, dy) in mm added to the positions of the file (a different origin).
    @param negate_bottom_x True: the X of the bottom-side parts is written with the opposite sign (a KiCad export option), after the shift.
    @return str, the text of the `.pos` file.
    """
    rows = ["### Footprint positions - synthetic ###", "## Unit = mm, Angle = deg.", "## Side : All", "# Ref     Val       Package                           PosX       PosY       Rot  Side"]
    for side, group in (("top", top), ("bottom", bottom)):
        for ref, val, fp, x, y, rot in group:
            px, py = x + shift[0], y + shift[1]
            if side == "bottom" and negate_bottom_x:
                px = -px
            rows.append(f"{ref}  {val}  {fp}  {px:.4f}  {py:.4f}  {rot:.4f}  {side}")
    return "\n".join(rows + ["## End", ""])
