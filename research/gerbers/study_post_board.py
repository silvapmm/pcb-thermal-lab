"""!
@file study_post_board.py
@brief An analogue of the post-mounted board of Sampson (2017): a 100 x 124 mm board held at four corner posts, copper that does not reach the posts, 1 W, with and without convection.
@details The article's board (6 layers, k_vw = 38 W/m K, traces that stop short of the posts, 236 C against 9 C with smearing) cannot be rebuilt from the text: its trace bitmaps are figures.
         This is an analogue of the mechanism, as a single equivalent sheet: laminate 0.59 W/m K, 1.6 mm; a copper pixel is the six layers superposed (6 x 35 um of copper, sheet conductance
         0.59 * 1.6e-3 + 391 * 210e-6); the copper region is a plane perforated by clearance holes (0.9 mm on a 1.5 mm pitch, 73 % copper) that stops a keep-out distance short of each post. For several keep-out radii the
         reference (the bitmap solved pixel by pixel at 0.25 mm) is compared with (a) the naive smeared model, one conductivity over the whole board (the volume-weighted value of the bitmap, as the article's k_vw),
         (b) the fill fraction per cell (what the program does today with the imported copper), (c) the geometric mean, (d) lambda 0.5 and (e) the flow-based faces, on 2 mm and 1 mm cells.
         Run: python study_post_board.py (about 8 minutes)
"""

import numpy as np

import conduction as cd
import scenarios as sc

PIX = 0.25                                   # mm
W, H = 100.0, 124.0                          # mm (the article's board is 100 x 125; 124 tiles with 2 mm cells)
T_LAM = 1.6e-3                               # m
K_LAM = 0.59                                 # W/m K (the article's board conductivity)
S_B = K_LAM * T_LAM                          # laminate sheet conductance (W/K)
S_C = K_LAM * T_LAM + 391.0 * 6 * 35e-6      # a pixel with copper on all six layers (W/K)
POST_R = 2.5                                 # mm, radius of a post (held at 0 K)
POST_AT = 8.0                                # mm, distance of the post centres from the board edges
HEATER = 6.0                                 # mm, square at the board centre


def board(keepout_mm):
    """!
    @brief The bitmap of the analogue board.
    @param keepout_mm Distance from the edge of a post to the nearest copper (mm).
    @return Tuple (S pixel conductances, fixed pixels (posts), power per pixel, heater block (y0, y1, x0, x1)).
    """
    ny, nx = int(round(H / PIX)), int(round(W / PIX))
    y, x = (np.arange(ny) + 0.5) * PIX, (np.arange(nx) + 0.5) * PIX
    X, Y = np.meshgrid(x, y)
    plane = np.ones((ny, nx), bool)
    # Perforation: clearance holes of 0.9 mm on a 1.5 mm pitch (about 27 % of the area removed)
    fx, fy = (X % 1.5) - 0.75, (Y % 1.5) - 0.75
    plane &= (fx * fx + fy * fy) > (0.45 ** 2)
    plane &= (X > 2.0) & (X < W - 2.0) & (Y > 2.0) & (Y < H - 2.0)                     # copper stops 2 mm short of the board edge
    fixed = np.zeros((ny, nx), bool)
    for cx in (POST_AT, W - POST_AT):
        for cy in (POST_AT, H - POST_AT):
            d = np.hypot(X - cx, Y - cy)
            fixed |= d <= POST_R
            plane &= d > POST_R + keepout_mm                                            # no copper near the post
    S = np.where(plane, S_C, S_B)
    h = int(round(HEATER / PIX))
    y0, x0 = ((ny - h) // 2) // 8 * 8, ((nx - h) // 2) // 8 * 8                      # the heater block starts on a 2 mm cell boundary
    power = np.zeros((ny, nx))
    power[y0:y0 + h, x0:x0 + h] = 1.0 / (h * h)
    return S, fixed, power, (y0, y0 + h, x0, x0 + h)


def smeared(S, fixed, power, h_face):
    """!
    @brief The naive model: one conductivity over the whole board, the volume-weighted value of the bitmap (what the article calls k_vw).
    @param S Pixel sheet conductances.
    @param fixed Fixed pixels.
    @param power Heat per pixel.
    @param h_face Face coefficient (W/m2K).
    @return Temperature rise per pixel.
    """
    Su = np.full(S.shape, float(S.mean()))
    return sc.pixel_reference(Su, PIX, power, h_face, fixed)


def main():
    """!
    @brief Run the keep-out sweep and print the tables.
    @return None.
    """
    for h_face in (0.0, 10.0):
        print(f"\nconvection {h_face} W/m2K on each face; reference = the bitmap solved at {PIX} mm; max rise in the heater block, error of every model (%)")
        print(f"{'keep-out mm':>11s} {'volume-weighted k W/mK':>23s} {'reference K':>12s} {'smeared':>9s}" + "".join(f"{lab:>16s}" for lab in ("fill 2mm", "geom 2mm", "lam0.5 2mm", "flow 2mm", "fill 1mm", "flow 1mm")))
        for ko in (4.0, 8.0, 12.0, 16.0):
            S, fixed, power, (y0, y1, x0, x1) = board(ko)
            ref = sc.pixel_reference(S, PIX, power, h_face, fixed)
            rmax = ref[y0:y1, x0:x1].max()
            row = f"{ko:11.0f} {S.mean() / T_LAM:23.1f} {rmax:12.1f} {100 * (smeared(S, fixed, power, h_face)[y0:y1, x0:x1].max() / rmax - 1):+9.0f}"
            for n in (8, 4):
                _, _, ex = sc.compare(S, PIX, n, power, fixed, h_face, (y0, y1, x0, x1), a=S_C, b=S_B, reference=(ref, PIX))
                for key in (("fill fraction (today)", "geometric mean", "lambda 0.5", "flow-based faces") if n == 8 else ("fill fraction (today)", "flow-based faces")):
                    row += f"{ex[key]:+16.0f}"
            print(row)


if __name__ == "__main__":
    main()
