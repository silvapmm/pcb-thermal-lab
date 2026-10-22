"""!
@file inverse.py
@brief Power of a part from a measured temperature: the board model run backwards.

@details The temperature of a board point is, for constant heat transfer coefficients, proportional to the power of the part (the problem is linear),
         (with other heaters on the board it is affine in the power of the part), so the power that reproduces a measurement follows from two runs:
             P = P_run (T_measured - T(0)) / (T(P_run) - T(0)),  T(0) the temperature with only the other heaters.
         With computed coefficients (convection that grows with temperature) the relation is not linear and a secant iteration on the power is used.
         What is measured has to be a temperature the model has: the hottest board point under the part, its mean, the board temperature in the ring
         0.5 to 1.5 mm around it (the point where the JEDEC definition of psi_JB takes the board temperature) or the junction (needs theta).
         The result is only as good as the board in the model (copper, vias, stack-up, heat transfer) and as the thermocouple (a probe that touches the board
         cools it a little and reads a few kelvin low on a small part): see docs/models.md section 6.
"""

import copy

from .analysis import heater_stats
from .api import SolverOptions, _run_model

POINTS = ("max", "mean", "ring", "junction")


def _temperature(problem, name, options, index, point, power):
    """!
    @brief Temperature of the measured point with the part at a given power.
    @param problem A Problem (it is not modified).
    @param name Model name.
    @param options SolverOptions.
    @param index Index of the heater.
    @param point One of POINTS.
    @param power Power in watts given to the heater (the other heaters keep theirs).
    @return Temperature in degC.
    """
    pr = copy.deepcopy(problem)
    pr.heaters[index].power = power
    pr.heaters[index].profile = None
    if pr.board.h_mode == "computed":
        from .api import _solve_computed_h
        res = _solve_computed_h(pr, name, options)[0]
    else:
        res = _run_model(pr, name, options)
    row = heater_stats(res, pr)[index]
    key = {"max": "t_max", "mean": "t_mean", "ring": "t_ring", "junction": "t_junction"}[point]
    if row[key] is None:
        raise ValueError({"ring": "the grid is too coarse to have a ring around the part: use a smaller cell size",
                          "junction": "the part has no junction-to-pad resistance theta: enter it first"}[point])
    return row[key]


def power_from_temperature(problem, index, measured_c, point="ring", ambient_c=None, model="fvm", cell_mm=1.0, tolerance=1e-4, max_iter=20):
    """!
    @brief Power of one heater that makes the model reproduce a measured temperature.
    @param problem A Problem with the board drawn as it is in reality.
    @param index 0-based index of the heater (the part).
    @param measured_c Measured temperature in degC at `point`.
    @param point "max" (hottest board point under the footprint), "mean" (mean under it), "ring" (board 0.5 to 1.5 mm around it) or "junction" (needs theta).
    @param ambient_c Ambient temperature of the measurement in degC (default: the ambient of the board).
    @param model Model key used for the runs (fvm by default).
    @param cell_mm Cell size in millimetres.
    @param tolerance Relative tolerance on the temperature rise of the check run.
    @param max_iter Largest number of secant iterations (with constant coefficients none is needed).
    @return Dict: power_w, temperature_c (of the check run), rise_k (measured minus ambient), runs (number of model runs), linear (True if the affine estimate already matched).
    @throws ValueError If the heater index, the point or the ambient is wrong, the measured temperature is not above the ambient, or the model has no such point.
    """
    if not 0 <= index < len(problem.heaters):
        raise ValueError("heater index out of range")
    if point not in POINTS:
        raise ValueError(f"point must be one of {POINTS}")
    pr = copy.deepcopy(problem)
    if ambient_c is not None:
        pr.board.ambient = float(ambient_c)
    pr.validate()
    amb = pr.board.ambient
    rise = float(measured_c) - amb
    if rise <= 0:
        raise ValueError("the measured temperature must be above the ambient temperature")
    options = SolverOptions(models=(model,), cell_mm=cell_mm)
    p0 = max(pr.heaters[index].power, 1.0)
    # Other heaters keep their power, so the point is affine in the power of the part: T = T(0) + P (T(p0) - T(0)) / p0
    t_zero = _temperature(pr, model, options, index, point, 0.0)
    t0 = _temperature(pr, model, options, index, point, p0)
    runs = 2
    if t0 - t_zero <= 0:
        raise ValueError("the model shows no temperature rise at the measured point: is the part near the point and on the board?")
    if t_zero >= amb + rise:
        raise ValueError("the measured temperature is not higher than what the other heaters alone give at that point")
    p1 = p0 * (amb + rise - t_zero) / (t0 - t_zero)   # Exact when the coefficients are constant
    t1 = _temperature(pr, model, options, index, point, p1)
    runs += 1
    linear = abs(t1 - amb - rise) <= tolerance * rise
    pa, ta, pb, tb = p0, t0, p1, t1
    for _ in range(max_iter):
        if abs(tb - amb - rise) <= tolerance * rise:
            break
        # Secant step on (power, temperature)
        slope = (tb - ta) / (pb - pa) if pb != pa else (tb - t_zero) / pb
        pa, ta = pb, tb
        pb = max(pb + (amb + rise - tb) / slope, 1e-9)
        tb = _temperature(pr, model, options, index, point, pb)
        runs += 1
    return {"power_w": pb, "temperature_c": tb, "rise_k": rise, "runs": runs, "linear": bool(linear)}


def power_from_theta(t_junction_c, t_reference_c, theta_k_per_w):
    """!
    @brief Power from the datasheet relation Tj = T_ref + theta P, for a known junction temperature (a sense diode or the part's own sensor).
    @param t_junction_c Junction temperature in degC.
    @param t_reference_c Temperature of the reference point in degC: the board 1 mm from the part for psi_JB, the top of the case for psi_JT.
    @param theta_k_per_w The characterisation parameter or resistance in K/W (psi_JB, psi_JT or theta_JB).
    @return Power in watts.
    @throws ValueError If the parameter is not positive or the junction is not hotter than the reference.
    """
    if theta_k_per_w <= 0:
        raise ValueError("the thermal parameter must be positive")
    if t_junction_c <= t_reference_c:
        raise ValueError("the junction must be hotter than the reference point")
    return (t_junction_c - t_reference_c) / theta_k_per_w
