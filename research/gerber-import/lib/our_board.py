"""!
@file our_board.py
@brief A small board of our own design for figures and tests: an IC in the middle, eight signal nets that leave it radially and run round it on circular arcs to test points, and a ground net (exposed pad with thermal vias, a spoke and a ring with vias).
@details The board is written as Gerber text (RS-274X with X2 attributes: file function, aperture functions, net names) and as an Excellon drill file (plated holes with the X2 file function), so every feature of the reader can be tested on a board that belongs to this repository and has no licence issue.
         Geometry (mm, board 40 x 40, IC at the centre (20, 20)): the exposed pad is 2.4 x 2.4; eight 0.8 x 0.35 pads of the IC stand at 2.3 mm from the centre at the polar angles 22.5 + 45 k degrees;
         net S(k+1) leaves its pad radially at that angle, runs on a circle of radius R_k = 13.5 - 1.0 k round the IC counter-clockwise through an angle that keeps it clear of the radial tracks of the
         inner nets and of the ground spoke at 0 degrees (at most 150 degrees, ending at 346 degrees at the latest) and ends in a 0.8 mm test point with a 0.4 mm plated hole. Tracks are 0.2 mm. Ground:
         the exposed pad with four 0.8 mm via pads (0.3 mm holes), a 0.8 mm spoke along 0 degrees to a 0.8 mm ring of radius 18.5 mm with four 1.0 mm via pads (0.3 mm holes) at 45 + 90 k degrees.
         Used by tests/test_our_board_bench.py and make_figures.py (figure 1), and by the other two Gerber folders. Run `.venv/bin/python research/gerber-import/lib/our_board.py` (from the repository root) to write the files to data/synthetic/.
"""

import math
from pathlib import Path

SIZE = 40.0                       # mm, board side
CX = CY = 20.0                    # mm, IC centre
TRACK = 0.2                       # mm, signal track width
N_SIG = 8
R_FIRST, R_STEP = 13.5, 1.0       # mm, circle radii R_k = R_FIRST - R_STEP k
IC_R = 2.3                        # mm, polar distance of the IC pads from the centre
RING_R, RING_W = 18.5, 0.8        # mm, ground ring
ARC_MAX, END_LIMIT = 150.0, 346.0  # degrees
from paths import DATA

OUT = DATA / "synthetic"


def theta(k):
    """!
    @brief Polar angle of the pad and of the radial track of signal net k.
    @param k Net index 0..7.
    @return Angle in degrees.
    """
    return 22.5 + 45.0 * k


def radius(k):
    """!
    @brief Radius of the circle of signal net k.
    @param k Net index 0..7.
    @return Radius (mm).
    """
    return R_FIRST - R_STEP * k


def sweep(k):
    """!
    @brief Angle swept by the arc of signal net k.
    @param k Net index 0..7.
    @return Angle in degrees.
    """
    return min(ARC_MAX, END_LIMIT - theta(k))


def polar(r, deg):
    """!
    @brief Board position of a polar point round the IC.
    @param r Radius (mm).
    @param deg Angle (degrees).
    @return Tuple (x, y) in mm.
    """
    return CX + r * math.cos(math.radians(deg)), CY + r * math.sin(math.radians(deg))


def net_name(k):
    """!
    @brief Name of signal net k.
    @param k Net index 0..7.
    @return "S1" to "S8".
    """
    return f"S{k + 1}"


def end_point(k):
    """!
    @brief Position of the test point at the end of signal net k.
    @param k Net index 0..7.
    @return Tuple (x, y) in mm.
    """
    return polar(radius(k), theta(k) + sweep(k))


def ic_pad(k):
    """!
    @brief Position of the IC pad of signal net k.
    @param k Net index 0..7.
    @return Tuple (x, y) in mm.
    """
    return polar(IC_R, theta(k))


def squares(k):
    """!
    @brief Hand estimate of the number of squares of track between the IC pad and the test point of net k (the 0.4 mm of track under each pad is left out).
    @param k Net index 0..7.
    @return Number of squares (length / width).
    """
    length = (radius(k) - IC_R - 0.4) + (radius(k) * math.radians(sweep(k)) - 0.4)
    return length / TRACK


def gerber_text():
    """!
    @brief The copper layer as Gerber text with X2 attributes.
    @return String.
    """
    def c(v):
        """!@brief A length in mm as the integer of a 4.6 coordinate. @param v Length (mm). @return String of digits."""
        return str(int(round(v * 1e6)))

    def at(x, y, code):
        """!@brief A coordinate block. @param x X (mm). @param y Y (mm). @param code D code. @return String."""
        return f"X{c(x)}Y{c(y)}D0{code}*\n"

    t = "G04 our own board: IC with circular tracks (research/gerber-import/lib/our_board.py)*\n%TF.FileFunction,Copper,L1,Top*%\n%TF.FilePolarity,Positive*%\n%FSLAX46Y46*%\n%MOMM*%\nG75*\n"
    t += "%TA.AperFunction,Conductor*%\n%ADD10C,0.2*%\n%ADD11C,0.8*%\n%TD.AperFunction*%\n"
    t += "%TA.AperFunction,SMDPad,CuDef*%\n%ADD12R,0.8X0.35*%\n%ADD13R,0.35X0.8*%\n%ADD14R,2.4X2.4*%\n%TD.AperFunction*%\n"
    t += "%TA.AperFunction,ViaPad*%\n%ADD15C,0.8*%\n%ADD16C,1.0*%\n%TD.AperFunction*%\n"
    t += "%TA.AperFunction,ComponentPad*%\n%ADD17C,0.8*%\n%TD.AperFunction*%\n"
    for k in range(N_SIG):
        t += f"%TO.N,{net_name(k)}*%\n"
        px, py = ic_pad(k)
        t += ("D12*\n" if abs(math.cos(math.radians(theta(k)))) > abs(math.sin(math.radians(theta(k)))) else "D13*\n") + at(px, py, 3)
        t += "D10*\n" + at(px, py, 2)
        sx, sy = polar(radius(k), theta(k))
        t += at(sx, sy, 1)                                                           # radial track out to the circle
        ex, ey = end_point(k)
        t += f"G03*\nX{c(ex)}Y{c(ey)}I{c(CX - sx)}J{c(CY - sy)}D01*\nG01*\n"          # counter-clockwise arc about the IC
        t += "D17*\n" + at(ex, ey, 3) + "%TD*%\n"
    t += "%TO.N,GND*%\nD14*\n" + at(CX, CY, 3)
    t += "D15*\n" + "".join(at(CX + dx, CY + dy, 3) for dx in (-0.6, 0.6) for dy in (-0.6, 0.6))
    t += "D11*\n" + at(CX + 1.2, CY, 2) + at(CX + RING_R, CY, 1)                      # spoke along 0 degrees to the ring
    for q in range(4):                                                               # the ring in four quarter arcs
        a0, a1 = 90.0 * q, 90.0 * (q + 1)
        x0, y0 = polar(RING_R, a0)
        x1, y1 = polar(RING_R, a1)
        t += at(x0, y0, 2) + f"G03*\nX{c(x1)}Y{c(y1)}I{c(CX - x0)}J{c(CY - y0)}D01*\nG01*\n"
    t += "D16*\n" + "".join(at(*polar(RING_R, 45.0 + 90.0 * q), 3) for q in range(4)) + "%TD*%\nM02*\n"
    return t


def holes():
    """!
    @brief The plated holes as tuples (x, y, diameter) in mm: four thermal vias in the exposed pad, four vias on the ring, eight test-point holes.
    @return List of tuples.
    """
    out = [(CX + dx, CY + dy, 0.3) for dx in (-0.6, 0.6) for dy in (-0.6, 0.6)]
    out += [(*polar(RING_R, 45.0 + 90.0 * q), 0.3) for q in range(4)]
    out += [(*end_point(k), 0.4) for k in range(N_SIG)]
    return out


def drill_text():
    """!
    @brief The plated holes as an Excellon file with the X2 file function in a comment.
    @return String.
    """
    t = "M48\n; #@! TF.FileFunction,Plated,1,1,PTH\nMETRIC\nT1C0.300\nT2C0.400\n%\nG90\nG05\n"
    for tool, d in ((1, 0.3), (2, 0.4)):
        t += f"T{tool}\n" + "".join(f"X{x:.4f}Y{y:.4f}\n" for x, y, dd in holes() if abs(dd - d) < 1e-9)
    return t + "T0\nM30\n"


def write(folder=OUT):
    """!
    @brief Write the Gerber and the drill file.
    @param folder Destination folder.
    @return Tuple (Gerber path, drill path).
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    g, d = folder / "our_board_F_Cu.gbr", folder / "our_board_PTH.drl"
    g.write_text(gerber_text())
    d.write_text(drill_text())
    return g, d


if __name__ == "__main__":
    print(*write())
