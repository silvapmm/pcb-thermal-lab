#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file compare.py
@brief The Difference view: the field of (model - reference) of two steady results, read on the same definition, and what is documented about how big it should be.
@details Display only: no solver is run and no number of any model moves. A difference between two models must not be a difference of definition, so both
         fields are read with the SAME read-out (the column mean of a layer, or the surface of the outer copper) and mixing two read-outs is refused. Models on
         different grids (a cell field and a node field, or two cell sizes) are resampled onto the grid of the reference by bilinear interpolation on the sample
         positions (`resample`), exact for a linear field; the note says so. No GUI imports here: the module is tested without a window.
         The expected-agreement statements (`expected_agreement`) are numbers taken from the tables of `docs/validation.md` sections 1 and 2 (the hottest point
         of 20 scenarios against the FVM, which the Lumped and Analytic constants were fitted to); a pair without a documented measurement says nothing.
"""

from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .results import SteadyResult, model_label

COLUMN = "column"                # Read-out: the mean of the layer's column (the headline of every model)
SURFACE = "surface"              # Read-out: the outer face of the outer copper (FVM, FDM and FEM results)
# Value of the field below which a difference is called zero (K); a model compared with itself gives exactly 0, a float round-off of two solves does not matter
ZERO_K = 1e-9


class DifferenceError(ValueError):
    """!
    @brief The two results cannot be compared like for like (a definition would be mixed, or a model has no field of that read-out).
    """


@dataclass
class Sample:
    """!
    @brief One field of a result with the name of its read-out and the positions of its samples.
    """
    values: np.ndarray                       # Array (ny, nx), degC
    readout: str                             # "column" or "surface"
    xs: np.ndarray                           # Sample positions along x, metres
    ys: np.ndarray                           # Sample positions along y, metres
    dx: float                                # Spacing along x, metres
    dy: float                                # Spacing along y, metres


@dataclass
class DifferenceField:
    """!
    @brief The difference (model - reference) on the grid of the reference, with its statistics.
    @details Every statistic is over the finite samples (a board with an outline has NaN off the board).
    """
    model: str                               # Key of the minuend
    reference: str                           # Key of the subtrahend
    readout: str                             # "column" or "surface": the same for both
    layer: int                               # 0-based layer drawn (the layer of the outer face for the surface)
    values: np.ndarray                       # Array (ny, nx), K
    dx: float                                # Spacing of the reference grid along x, metres
    dy: float                                # Spacing of the reference grid along y, metres
    resampled: bool                          # True when the model field was interpolated onto the reference grid
    face: int = 0                            # 0 top or 1 bottom: the face of the surface read-out
    maximum: float = 0.0                     # Largest difference, K
    minimum: float = 0.0                     # Smallest (most negative) difference, K
    where_max: Tuple[float, float] = (0.0, 0.0)   # (x, y) in mm of the largest difference
    where_min: Tuple[float, float] = (0.0, 0.0)   # (x, y) in mm of the smallest difference
    mean: float = 0.0                        # Mean difference over the samples, K
    rms: float = 0.0                         # Root mean square difference, K
    limit: float = 0.0                       # Half range of the symmetric colour scale, K
    peak_k: float = 0.0                      # Tmax(model) - Tmax(reference), K (the hottest points, not the field)
    peak_pct: float = 0.0                    # The same as a share of the rise of the reference, percent
    notes: List[str] = dc_field(default_factory=list)   # Short sentences the view shows (interpolation, outline, ...)


def default_reference(results, model):
    """!
    @brief The reference a Difference view starts with: the FVM, else the first other model that has a field.
    @param results dict key -> SteadyResult of the simulation.
    @param model Key of the model shown (never returned).
    @return Key, or None when no other model has a field.
    """
    usable = [k for k, r in results.items() if r.T is not None and k != model]
    if "fvm" in usable:
        return "fvm"
    return usable[0] if usable else None


def _layer_of_face(problem, face):
    """!
    @brief The layer that owns an outer face.
    @param problem The Problem.
    @param face 0 for the top face, 1 for the bottom face.
    @return 0-based layer index.
    """
    return 0 if face == 0 else problem.board.layers - 1


def sample(result, readout=COLUMN, layer=0, face=0):
    """!
    @brief The field of a result under one read-out, with its sample positions.
    @param result A SteadyResult.
    @param readout "column" (the layer mean) or "surface" (the outer face of the copper).
    @param layer 0-based layer of the column read-out.
    @param face 0 top or 1 bottom, for the surface read-out.
    @return Sample.
    @throws DifferenceError If the result has no field, or no field of that read-out (the message names the model).
    """
    name = model_label(result.model)
    if result.T is None:
        raise DifferenceError(f"{name} has no temperature field")
    if readout == COLUMN:
        if not 0 <= layer < result.T.shape[0]:
            raise DifferenceError(f"{name} has no layer {layer + 1}")
        vals = result.T[layer]
    elif readout == SURFACE:
        surf = result.arrays.get("T_surface")
        if surf is None or not np.isfinite(surf[face]).any():
            raise DifferenceError(f"{name} has no surface read-out")
        vals = surf[face]
    else:
        raise DifferenceError(f"unknown read-out {readout!r}")
    xs, ys = result.coords()
    return Sample(np.asarray(vals, float), readout, xs, ys, result.dx, result.dy)


def resample(values, xs, ys, xs_to, ys_to):
    """!
    @brief Bilinear interpolation of a field on a rectangular grid of samples onto another grid.
    @details Linear between the sample positions and linearly extended in the half cell between the outer samples and the board edge (so the result is exact for a
             linear field everywhere on the board). NaN samples (off the outline) make the NaN spread to the neighbouring points.
    @param values Array (ny, nx).
    @param xs Sample positions along x, metres.
    @param ys Sample positions along y, metres.
    @param xs_to Positions to read along x, metres.
    @param ys_to Positions to read along y, metres.
    @return Array (len(ys_to), len(xs_to)).
    """
    interp = RegularGridInterpolator((ys, xs), values, method="linear", bounds_error=False, fill_value=None)
    Y, X = np.meshgrid(ys_to, xs_to, indexing="ij")
    return interp(np.stack([Y.ravel(), X.ravel()], axis=-1)).reshape(Y.shape)


def _same_grid(a, b):
    """!
    @brief Tell whether two samples sit on the same positions.
    @param a Sample.
    @param b Sample.
    @return True when the shapes and the positions agree to a millionth of a cell.
    """
    return (a.values.shape == b.values.shape and np.allclose(a.xs, b.xs, atol=1e-6 * a.dx, rtol=0) and np.allclose(a.ys, b.ys, atol=1e-6 * a.dy, rtol=0))


def subtract(model_sample, reference_sample):
    """!
    @brief model - reference on the grid of the reference, refusing two different read-outs.
    @param model_sample Sample of the model.
    @param reference_sample Sample of the reference.
    @return Tuple (array in K on the reference grid, True when the model was interpolated).
    @throws DifferenceError If the read-outs differ: that would be a difference of definition, not of models.
    """
    if model_sample.readout != reference_sample.readout:
        raise DifferenceError(f"the read-outs differ ({model_sample.readout} against {reference_sample.readout}): a difference of definition, not of models")
    if _same_grid(model_sample, reference_sample):
        return model_sample.values - reference_sample.values, False
    moved = resample(model_sample.values, model_sample.xs, model_sample.ys, reference_sample.xs, reference_sample.ys)
    return moved - reference_sample.values, True


def unavailable_reason(model_result, reference_result, problem, readout=COLUMN, layer=0, face=0):
    """!
    @brief Why a difference between two results cannot be shown (None when it can).
    @param model_result SteadyResult of the model shown.
    @param reference_result SteadyResult of the reference.
    @param problem The Problem.
    @param readout "column" or "surface".
    @param layer 0-based layer of the column read-out.
    @param face 0 top or 1 bottom (surface read-out).
    @return A sentence, or None.
    """
    if model_result is reference_result:
        return "the model and the reference are the same"
    for r in (model_result, reference_result):
        # The Lumped and Analytic solve an outline board on a rectangle of the same area and stretch the field back: a point of it is not a point of the real board
        if r.T is not None and r.equivalent_scale is not None and problem.board.has_outline():
            return f"{model_label(r.model)} solved this outline board on a rectangle of the same area: its field is stretched, not a field of the board"
    try:
        sample(model_result, readout, layer, face)
        sample(reference_result, readout, layer, face)
    except DifferenceError as e:
        return str(e)
    return None


def difference_field(model_result, reference_result, problem, readout=COLUMN, layer=0, face=0):
    """!
    @brief The Difference view's data: model - reference of one read-out, with maximum, minimum and where, mean, RMS and the symmetric colour limit.
    @param model_result SteadyResult of the model shown (the minuend).
    @param reference_result SteadyResult of the reference (the subtrahend); its grid is the grid of the result.
    @param problem The Problem (the board size and outline, for the notes).
    @param readout "column" or "surface": the same for both models.
    @param layer 0-based layer of the column read-out (ignored for the surface, which takes the layer of its face).
    @param face 0 top or 1 bottom (surface read-out).
    @return DifferenceField.
    @throws DifferenceError If the pair cannot be compared (`unavailable_reason`).
    """
    why = unavailable_reason(model_result, reference_result, problem, readout, layer, face)
    if why is not None:
        raise DifferenceError(why)
    if readout == SURFACE:
        layer = _layer_of_face(problem, face)
    a = sample(model_result, readout, layer, face)
    b = sample(reference_result, readout, layer, face)
    diff, moved = subtract(a, b)
    ok = np.isfinite(diff)
    if not ok.any():
        raise DifferenceError("the two fields have no sample in common")
    warm = np.where(ok, diff, -np.inf)
    cold = np.where(ok, diff, np.inf)
    jM, iM = np.unravel_index(int(np.argmax(warm)), diff.shape)
    jm, im = np.unravel_index(int(np.argmin(cold)), diff.shape)
    dx, dy = reference_result.dx, reference_result.dy
    off_x, off_y = b.xs[iM] * 1000.0, b.ys[jM] * 1000.0
    out = DifferenceField(model=model_result.model, reference=reference_result.model, readout=readout, layer=layer, values=diff, dx=dx, dy=dy, resampled=moved, face=face)
    out.maximum, out.minimum = float(diff[jM, iM]), float(diff[jm, im])
    out.where_max, out.where_min = (float(off_x), float(off_y)), (float(b.xs[im] * 1000.0), float(b.ys[jm] * 1000.0))
    out.mean, out.rms = float(np.mean(diff[ok])), float(np.sqrt(np.mean(diff[ok] ** 2)))
    out.limit = max(abs(out.maximum), abs(out.minimum), 1e-3)           # A floor, so that a zero field still has a scale
    out.peak_k = float(model_result.t_max - reference_result.t_max)
    rise = max(reference_result.t_max - reference_result.ambient, 1e-9)
    out.peak_pct = 100.0 * out.peak_k / rise
    if moved:
        out.notes.append(f"{model_label(model_result.model)} was interpolated onto the {model_label(reference_result.model)} grid (bilinear between sample positions)")
    return out


def readout_name(readout, layer, face=0):
    """!
    @brief The words that name a read-out in a title.
    @param readout "column" or "surface".
    @param layer 0-based layer (column).
    @param face 0 top or 1 bottom (surface).
    @return For example "layer 1, column mean" or "surface (top)".
    """
    if readout == SURFACE:
        return f"surface ({'top' if face == 0 else 'bottom'})"
    return f"layer {layer + 1}, column mean"


# What is documented about the size of the difference between two models. Every row: (model, reference) -> (what, evidence). The numbers are those of the
# 20 scenarios of docs/validation.md section 2 (hottest point, share of the rise above ambient, the FVM as reference); tests/test_compare.py recomputes them
# from that table, so a number here that the table does not hold fails. Pairs that are not here have no documented measurement and say nothing (the FEM waits
# for the comparison campaign of 2.9.0).
@dataclass(frozen=True)
class Tip:
    """!
    @brief One documented statement about the expected size of a difference.
    """
    text: str            # The sentence the view shows
    evidence: str        # Where it comes from (a section of docs/validation.md)
    lo: float            # Lowest value of the range quoted, percent of the rise
    hi: float            # Highest value of the range quoted, percent of the rise
    n: int               # Scenarios of the range
    n_all: int           # Scenarios of the table
    outliers: Tuple[Tuple[str, float], ...]   # (scenario, percent) that the range leaves out


EXPECTED = {
    ("fdm", "fvm"): Tip("FDM: the hottest point is 0.5 % of the rise below the FVM or closer in {n} of {n_all} scenarios",
                        "section 2", -0.5, 0.0, 19, 20, (("a copper edge across the heater", -1.3),)),
    ("analytic", "fvm"): Tip("Analytic: a series with local corrections; the hottest point is {lo:+.1f} to {hi:+.1f} % of the rise from the FVM in {n} of {n_all} scenarios (-1.1 % on the example board)",
                             "sections 1 and 2", -1.8, 0.3, 18, 20, (("a copper island around the heater", -5.1), ("a copper edge across the heater", -27.9))),
    ("lumped", "fvm"): Tip("LPTN: the hottest point is {lo:+.1f} to {hi:+.1f} % of the rise from the FVM in {n} of {n_all} scenarios (+2.4 % on the example board)",
                           "sections 1 and 2", -5.4, 8.4, 19, 20, (("a copper edge across the heater", -27.9),)),
    ("solid3d", "fvm"): Tip("3D solid: the hottest point is {lo:+.1f} to {hi:+.1f} % of the rise from the FVM in {n} of {n_all} scenarios (a comparison model of the program, not an independent reference)",
                            "section 2", -0.3, 0.9, 20, 20, ()),
}


def expected_agreement(model, reference):
    """!
    @brief What the documents measured about the size of the difference of a pair of models (the confidence tip).
    @param model Key of the model shown.
    @param reference Key of the reference.
    @return List of sentences (empty when nothing is documented for the pair: then the view says nothing), the last one naming the evidence.
    """
    tip = EXPECTED.get((model, reference))
    if tip is None:
        return []
    body = tip.text.format(lo=tip.lo, hi=tip.hi, n=tip.n, n_all=tip.n_all)
    if tip.outliers:
        body += "; outside it: " + ", ".join(f"{what} {pct:+.1f} %" for what, pct in tip.outliers)
    return [body, f"The ranges are for the hottest point, not for every point of the map (docs/validation.md, {tip.evidence})"]
