"""!
@file scenarios.py
@brief Boundary-limited conduction scenarios (fixed-temperature posts or border, little or no convection), the regime in which smeared conductivity fails most (Sampson, Electronics Cooling 2017).
@details A single copper sheet on laminate as in conduction.py, now with cells held at 0 K rise ("posts" or a border) and an optional loss through the two faces. The reference is the
         mask solved pixel by pixel; the candidates are the mappings of conduction.py on 1 mm cells (or any n x n pixel cell). All conductances are sheet conductances in W/K.
         Scenarios: `stripes` (copper stripes in the middle of a laminate board, posts either along or across the stripes) and `window` (a real window with its whole border held at 0 K).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import conduction as cd


def solve_general(gx, gy, cell_mm, power_map, h_face, fixed):
    """!
    @brief Steady temperature rise of a sheet with fixed cells and an optional loss through both faces.
    @param gx Conductances between horizontal neighbours (ny, nx - 1), W/K.
    @param gy Conductances between vertical neighbours (ny - 1, nx), W/K.
    @param cell_mm Cell size (mm), for the loss through the faces.
    @param power_map Heat per cell (ny, nx), W.
    @param h_face Heat transfer coefficient of each face (W/m2K); 0 means no convection.
    @param fixed Boolean array (ny, nx): cells held at zero rise (posts).
    @return numpy.ndarray (ny, nx) temperature rise (K).
    """
    ny, nx = gx.shape[0], gy.shape[1]
    n = ny * nx
    idx = np.arange(n).reshape(ny, nx)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    g = np.concatenate([gx.ravel(), gy.ravel()])
    diag = np.bincount(a, g, n) + np.bincount(b, g, n) + 2 * h_face * (cell_mm * 1e-3) ** 2
    K = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n)).tocsr() + sp.diags(diag)
    free = ~fixed.ravel()
    T = np.zeros(n)
    rhs = power_map.ravel()[free]
    T[free] = spla.spsolve(K.tocsc()[free][:, free].tocsc(), rhs)
    return T.reshape(ny, nx)


def pixel_reference(S, pix_mm, power_px, h_face, fixed_px):
    """!
    @brief The resolved solution: the mask solved pixel by pixel.
    @param S Pixel sheet conductances (ny, nx).
    @param pix_mm Pixel size (mm).
    @param power_px Heat per pixel (W).
    @param h_face Face heat transfer coefficient (W/m2K).
    @param fixed_px Boolean array of fixed pixels.
    @return Temperature rise per pixel (K).
    """
    return solve_general(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), pix_mm, power_px, h_face, fixed_px)


def coarse_faces(S, n, a=None, b=None):
    """!
    @brief The face conductances of every mapping on cells of n x n pixels.
    @param S Pixel sheet conductances (a pixel may be a mix of copper and laminate, for a coverage mask).
    @param n Pixels per cell side (even).
    @param a Sheet conductance of copper (default: the largest value of S).
    @param b Sheet conductance of the laminate (default: the smallest value of S).
    @return Dict name -> (gx, gy).
    """
    a = float(S.max()) if a is None else a
    b = float(S.min()) if b is None else b
    blk = cd.cell_blocks(S, n)
    f = ((blk - b) / (a - b)).mean(axis=(2, 3))                      # copper fraction of the cell (exact for a binary mask, area-weighted for a coverage mask)
    out = {}
    out["fill fraction (today)"] = cd.faces_from_cells(*([cd.map_power(f, 1.0, a, b)] * 2))
    out["geometric mean"] = cd.faces_from_cells(*([cd.map_power(f, 0.0, a, b)] * 2))
    lx, ly, ux, uy = cd.map_bounds(blk)
    out["tile method (low bound)"] = cd.faces_from_cells(lx, ly)
    sx, sy = cd.map_lambda(blk, 0.5)
    out["lambda 0.5"] = cd.faces_from_cells(sx, sy)
    out["flow-based faces"] = cd.dual_faces(S, n, 0)
    out["flow-based, margin 20 %"] = cd.dual_faces(S, n, max(int(round(0.2 * n)), 1))      # the window is widened by 20 % of a cell on each side so heat can spread sideways
    return out


def compare(S, pix_mm, n, power_px, fixed_px, h_face, heater, a=None, b=None, reference=None):
    """!
    @brief Reference and every mapping on one scenario; error of the mean rise over the heater block.
    @param S Pixel sheet conductances.
    @param pix_mm Pixel size (mm).
    @param n Pixels per cell side.
    @param power_px Heat per pixel (W).
    @param fixed_px Fixed pixels (cells are fixed when all their pixels are).
    @param h_face Face coefficient (W/m2K).
    @param heater Tuple (y0, y1, x0, x1) in pixels (multiples of n).
    @param a Copper sheet conductance for the mappings (default: the largest value of S).
    @param b Laminate sheet conductance for the mappings (default: the smallest value of S).
    @param reference Optional ready reference as (field, pixel size mm) on a finer grid whose pixels tile the same board; None solves S itself.
    @return Tuple (reference mean rise K, dict name -> error % of the mean rise, dict name -> error % of the maximum rise).
    """
    y0, y1, x0, x1 = heater
    if reference is None:
        ref = pixel_reference(S, pix_mm, power_px, h_face, fixed_px)
        ref_mean, ref_max = ref[y0:y1, x0:x1].mean(), ref[y0:y1, x0:x1].max()
    else:
        field, rpix = reference                                      # a finer solution of the same board: average its pixels over the heater block
        k = int(round(pix_mm / rpix))
        ref_mean, ref_max = field[y0 * k:y1 * k, x0 * k:x1 * k].mean(), field[y0 * k:y1 * k, x0 * k:x1 * k].max()
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power_px[:cy * n, :cx * n].reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed_px, n).mean(axis=(2, 3)) >= 0.5                        # a cell is held when at least half of its pixels are
    em, ex = {}, {}
    for name, (gx, gy) in coarse_faces(S, n, a, b).items():
        T = solve_general(gx, gy, pix_mm * n, pw, h_face, fx)
        blk = T[y0 // n:y1 // n, x0 // n:x1 // n]
        em[name] = 100 * (blk.mean() / ref_mean - 1)
        ex[name] = 100 * (blk.max() / ref_max - 1)
    return ref_mean, em, ex


def stripes(pix_mm=0.1, size_mm=36.0, across=True, copper_mm=24.0, stripe_px=5, pitch_px=10):
    """!
    @brief A laminate board with a block of copper stripes (running along x) in the middle, posts held at 0 K (3 mm deep, 6 mm wide), a heater at the centre. The posts are clear of the copper only when the block leaves room for them (copper_mm <= size_mm - 6, the default 24 mm leaves 3 mm of laminate); a 34 mm block runs under them.
    @param pix_mm Pixel size (mm).
    @param size_mm Board side (mm).
    @param across True: posts at the top and bottom edges (the heat crosses the stripes); False: posts at the left and right edges (the heat runs along them).
    @param copper_mm Side of the square block of stripes (mm).
    @param stripe_px Stripe width in pixels.
    @param pitch_px Stripe pitch in pixels.
    @return Tuple (S pixel conductances, power per pixel, fixed pixels, heater block (y0, y1, x0, x1)).
    """
    n = int(round(size_mm / pix_mm))
    mask = np.zeros((n, n), bool)
    c0, c1 = (n - int(copper_mm / pix_mm)) // 2, (n + int(copper_mm / pix_mm)) // 2
    for r in range(c0, c1):
        if (r - c0) % pitch_px < stripe_px:
            mask[r, c0:c1] = True
    fixed = np.zeros((n, n), bool)
    post = int(round(3.0 / pix_mm))                           # 3 mm wide posts at the middle of two opposite edges
    mid = n // 2
    if across:
        fixed[:post, mid - post:mid + post] = True
        fixed[-post:, mid - post:mid + post] = True
    else:
        fixed[mid - post:mid + post, :post] = True
        fixed[mid - post:mid + post, -post:] = True
    h0, h1 = mid - int(3.0 / pix_mm), mid + int(3.0 / pix_mm)
    power = np.zeros((n, n))
    power[h0:h1, h0:h1] = 1.0 / ((h1 - h0) ** 2)
    return cd.sheet_of(mask), power, fixed, (h0, h1, h0, h1)


def window_scenario(mask, pix_mm=0.1, border_mm=1.0):
    """!
    @brief A real window with its whole border (a ring of the given width) held at 0 K and 1 W in the 6 x 6 mm heater block of the studies.
    @param mask Boolean copper mask (rows from the top) of a 36 x 36 mm window.
    @param pix_mm Pixel size (mm).
    @param border_mm Width of the held ring (mm).
    @return Tuple (S, power per pixel, fixed pixels, heater block).
    """
    n = mask.shape[0]
    fixed = np.zeros((n, n), bool)
    w = int(round(border_mm / pix_mm))
    fixed[:w, :] = fixed[-w:, :] = fixed[:, :w] = fixed[:, -w:] = True
    h0, h1 = int(12.0 / pix_mm), int(18.0 / pix_mm)
    y0, y1 = n - h1, n - h0                                    # the heater block of the studies is at 12 to 18 mm from the bottom
    power = np.zeros((n, n))
    power[y0:y1, h0:h1] = 1.0 / ((y1 - y0) * (h1 - h0))
    return cd.sheet_of(mask), power, fixed, (y0, y1, h0, h1)


def box_scenario(shape, pix_mm, heater_mm, border_mm=1.0, heater_origin_mm=None):
    """!
    @brief Border held at 0 K and 1 W in a square block, on a board of any size.
    @param shape Tuple (rows, cols) of pixels.
    @param pix_mm Pixel size (mm).
    @param heater_mm Side of the square heater (mm).
    @param border_mm Width of the held ring (mm).
    @param heater_origin_mm Tuple (row mm from the top, column mm from the left) of the heater's corner; default: centred.
    @return Tuple (power per pixel, fixed pixels, heater block (y0, y1, x0, x1) in pixels).
    """
    ny, nx = shape
    fixed = np.zeros(shape, bool)
    w = int(round(border_mm / pix_mm))
    fixed[:w, :] = fixed[-w:, :] = fixed[:, :w] = fixed[:, -w:] = True
    h = int(round(heater_mm / pix_mm))
    if heater_origin_mm is None:
        y0, x0 = (ny - h) // 2, (nx - h) // 2
    else:
        y0, x0 = int(round(heater_origin_mm[0] / pix_mm)), int(round(heater_origin_mm[1] / pix_mm))
    power = np.zeros(shape)
    power[y0:y0 + h, x0:x0 + h] = 1.0 / (h * h)
    return power, fixed, (y0, y0 + h, x0, x0 + h)
