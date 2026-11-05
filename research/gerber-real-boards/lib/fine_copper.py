#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fine_copper.py
@brief The fine-copper detector: how much of the copper of a layer is finer than the cell of the thermal grid, and the threshold at which the program should warn.
@details Copper finer than the cell (tracks and clearances narrower than the cell, hatching, thin fills) is what the mapping from the mask to the cell conductances can only approximate; the larger the share,
         the larger the difference between the cell model and the resolved pixel model (research/gerber-models README 4.4, 4.42). Two indicators, both from a copper coverage or binary mask at the pixel of the import:
         1. `partial_share`: the share of the copper area that lies in cells that are neither empty nor full (0.02 < fraction < 0.98): the cells where the arithmetic fill and the true conduction differ;
         2. `thin_share`: the share of the copper area that disappears when the copper is opened with a disc of the cell's half-width (copper whose local width is under the cell): the copper the cell grid cannot resolve.
         `calibrate` picks the threshold on an indicator from measured errors (scripts/study_fine_copper_warning.py). NumPy and SciPy only. No threshold is hard-coded here: the study sets it.
"""

import numpy as np
from scipy import ndimage


def cell_fractions(coverage, pix, cell):
    """!
    @brief The copper fraction of every cell.
    @param coverage Float array (rows, cols) with the copper fraction of each pixel (a boolean mask is accepted).
    @param pix Pixel (mm).
    @param cell Cell (mm); a whole number of pixels.
    @return numpy.ndarray (rows // n, cols // n) with the mean of each n x n block (the edge rows and columns that do not fill a cell are cut).
    @throws ValueError If the cell is not a whole number of pixels.
    """
    n = cell / pix
    if abs(n - round(n)) > 1e-6:
        raise ValueError("the cell must be a whole number of pixels")
    n = int(round(n))
    a = np.asarray(coverage, float)
    ny, nx = a.shape[0] // n, a.shape[1] // n
    return a[:ny * n, :nx * n].reshape(ny, n, nx, n).mean(axis=(1, 3))


def opened(binary, radius_px):
    """!
    @brief Morphological opening of a boolean mask with a disc, by distance transforms (fast for large radii).
    @param binary Boolean array.
    @param radius_px Radius of the disc in pixels (the copper narrower than twice this is lost).
    @return Boolean array: the copper that a disc of that radius fits into.
    """
    if radius_px <= 0 or not binary.any():
        return binary.copy()
    core = ndimage.distance_transform_edt(binary) > radius_px           # erosion: centres of discs that fit
    if not core.any():
        return np.zeros_like(binary)
    return ndimage.distance_transform_edt(~core) <= radius_px           # dilation: the copper those discs cover


def indicators(coverage, pix, cell):
    """!
    @brief The two fine-copper indicators of a layer for one cell size.
    @param coverage Float array (rows, cols), copper fraction per pixel (0 to 1); a boolean mask is accepted.
    @param pix Pixel (mm).
    @param cell Cell (mm), a whole number of pixels.
    @return dict with partial_share, thin_share (0 to 1; both 0 when the layer has no copper), copper_fraction (of the board), n_cells.
    """
    cov = np.asarray(coverage, float)
    total = cov.sum()
    f = cell_fractions(cov, pix, cell)
    if total <= 0:
        return {"partial_share": 0.0, "thin_share": 0.0, "copper_fraction": 0.0, "n_cells": int(f.size)}
    mixed = (f > 0.02) & (f < 0.98)
    partial = float((f * mixed).sum() / f.sum())
    binary = cov >= 0.5
    if binary.sum() == 0:
        thin = 1.0
    else:
        keep = opened(binary, max(int(round(cell / pix / 2.0)) - 0, 1))
        thin = float(1.0 - (keep & binary).sum() / binary.sum())
    return {"partial_share": partial, "thin_share": thin, "copper_fraction": float(total / cov.size), "n_cells": int(f.size)}


def fine_cells(coverage, pix, cell, min_thin=0.25):
    """!
    @brief The cells where fine copper is concentrated, for a map on screen.
    @param coverage Float array (rows, cols), copper fraction per pixel.
    @param pix Pixel (mm).
    @param cell Cell (mm).
    @param min_thin A cell is marked when at least this share of its copper is thinner than the cell.
    @return Boolean array (cell rows, cell cols), rows as in the mask.
    """
    cov = np.asarray(coverage, float)
    n = int(round(cell / pix))
    binary = cov >= 0.5
    thin_px = binary & ~opened(binary, max(n // 2, 1))
    ny, nx = cov.shape[0] // n, cov.shape[1] // n
    t = thin_px[:ny * n, :nx * n].reshape(ny, n, nx, n).sum(axis=(1, 3))
    c = binary[:ny * n, :nx * n].reshape(ny, n, nx, n).sum(axis=(1, 3))
    return (c > 0) & (t >= min_thin * np.maximum(c, 1))


def calibrate(indicator, error, err_limit=0.05, recall=0.9):
    """!
    @brief Choose the warning threshold of an indicator from measured errors of the cell model.
    @details The threshold is the indicator value that at least `recall` of the cases whose error exceeds `err_limit` reach or pass; the false-alarm rate is the share of the other cases that also reach it.
    @param indicator Array of indicator values, one per case.
    @param error Array of absolute relative errors of the cell model against the resolved model (0.05 = 5 %), same length.
    @param err_limit Error above which a case should be warned about.
    @param recall Share of the bad cases the threshold must catch.
    @return dict with threshold, recall (achieved), false_alarm (share of the good cases above the threshold), n_bad, n_good; threshold is nan when no case is bad.
    """
    x, e = np.asarray(indicator, float), np.asarray(error, float)
    bad = e > err_limit
    if not bad.any():
        return {"threshold": float("nan"), "recall": float("nan"), "false_alarm": float("nan"), "n_bad": 0, "n_good": int(len(x))}
    thr = float(np.quantile(x[bad], 1.0 - recall))
    good = ~bad
    fa = float((x[good] >= thr).mean()) if good.any() else float("nan")
    return {"threshold": thr, "recall": float((x[bad] >= thr).mean()), "false_alarm": fa, "n_bad": int(bad.sum()), "n_good": int(good.sum())}
