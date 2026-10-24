"""!
@file inverse.py
@brief Power of a part from a measured temperature: the board model run backwards.

@details The temperature of a board point is, for constant heat transfer coefficients, proportional to the power of the part (the problem is linear),
         (with other heaters on the board it is affine in the power of the part), so the power that reproduces a measurement follows from two runs:
             P = P_run (T_measured - T(0)) / (T(P_run) - T(0)),  T(0) the temperature with only the other heaters.
         With computed coefficients (convection that grows with temperature) the relation is not linear and a secant iteration on the power is used.
         What is measured has to be a temperature the model has: the hottest board point under the part, its mean, the board temperature in the ring
         0.5 to 1.5 mm around it (the point where the JEDEC definition of psi_JB takes the board temperature), the junction (needs theta) or **the top of the package**
         (needs theta and the datasheet psi_JT: T_top = T_junction - psi_JT P, with T_junction = T_board,max + theta P, so T_top = T_board,max + (theta - psi_JT) P).
         Which board is drawn matters: the board temperature under the part is a function of the copper, the vias, the stack-up and the heat transfer, so the same top
         temperature gives different powers on different boards (research/power-calculator/scripts/power_from_top_study.py).
         The result is only as good as the board in the model (copper, vias, stack-up, heat transfer) and as the thermocouple (a probe that touches the board
         cools it a little and reads a few kelvin low on a small part): see docs/models.md section 6.
"""

import copy
import math

from . import defaults
from .analysis import heater_stats
from .api import SolverOptions, _run_model

POINTS = ("max", "mean", "ring", "junction", "top")


def _temperature(problem, name, options, index, point, power, psi_jt=0.0):
    """!
    @brief Temperature of the measured point with the part at a given power.
    @param problem A Problem (it is not modified).
    @param name Model name.
    @param options SolverOptions.
    @param index Index of the heater.
    @param point One of POINTS.
    @param power Power in watts given to the heater (the other heaters keep theirs).
    @param psi_jt Junction-to-top characterisation parameter in K/W (only for point "top").
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
    key = {"max": "t_max", "mean": "t_mean", "ring": "t_ring", "junction": "t_junction", "top": "t_junction"}[point]
    if row[key] is None:
        raise ValueError({"ring": "the grid is too coarse to have a ring around the part: use a smaller cell size",
                          "junction": "the part has no junction-to-pad resistance theta: enter it first",
                          "top": "the top of the package needs the junction-to-pad resistance theta of the part and the datasheet psi_JT: enter them first"}[point])
    if point == "top":
        return row[key] - psi_jt * power                      # The top of the case is psi_JT below the junction
    return row[key]


def point_temperatures(problem, name, options, index, power, psi_jt=0.0):
    """!
    @brief Every temperature of a part that the calculator can use, with the part at a given power.
    @param problem A Problem (it is not modified).
    @param name Model name.
    @param options SolverOptions.
    @param index Index of the heater.
    @param power Power in watts given to the heater.
    @param psi_jt Datasheet psi_JT in K/W to give the top of the package (needs theta).
    @return Dict with board_max, board_mean, ring (board 0.5 to 1.5 mm around the part), junction and top (None where the part has no theta, or psi_jt is 0) in degC.
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
    tj = row["t_junction"]
    return {"board_max": row["t_max"], "board_mean": row["t_mean"], "ring": row["t_ring"], "junction": tj,
            "top": (tj - psi_jt * power) if (tj is not None and psi_jt > 0) else None}


def power_from_temperature(problem, index, measured_c, point="ring", ambient_c=None, model="fvm", cell_mm=1.0, tolerance=1e-4, max_iter=20, psi_jt=0.0):
    """!
    @brief Power of one heater that makes the model reproduce a measured temperature.
    @param problem A Problem with the board drawn as it is in reality.
    @param index 0-based index of the heater (the part).
    @param measured_c Measured temperature in degC at `point`.
    @param point "max" (hottest board point under the footprint), "mean" (mean under it), "ring" (board 0.5 to 1.5 mm around it) or "junction" (needs theta) or "top" (top of the package: needs theta and psi_jt).
    @param ambient_c Ambient temperature of the measurement in degC (default: the ambient of the board).
    @param model Model key used for the runs (fvm by default).
    @param cell_mm Cell size in millimetres.
    @param tolerance Relative tolerance on the temperature rise of the check run.
    @param max_iter Largest number of secant iterations (with constant coefficients none is needed).
    @param psi_jt Datasheet junction-to-top parameter psi_JT in K/W, for point "top" (the temperature measured is that of the top of the case).
    @return Dict: power_w, temperature_c (of the check run), rise_k (measured minus ambient), runs (number of model runs), linear (True if the affine estimate already matched),
            at_power (point_temperatures at the power found) and resistance_k_per_w (rise per watt at the measured point: what the copper, vias, stack-up and heat transfer give).
    @throws ValueError If the heater index, the point or the ambient is wrong, the measured temperature is not above the ambient, or the model has no such point.
    """
    if not 0 <= index < len(problem.heaters):
        raise ValueError("heater index out of range")
    if point not in POINTS:
        raise ValueError(f"point must be one of {POINTS}")
    if point == "top" and psi_jt < 0:
        raise ValueError("psi_JT cannot be negative")
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
    t_zero = _temperature(pr, model, options, index, point, 0.0, psi_jt)
    t0 = _temperature(pr, model, options, index, point, p0, psi_jt)
    runs = 2
    if t0 - t_zero <= 0:
        raise ValueError("the model shows no temperature rise at the measured point: is the part near the point and on the board?")
    if t_zero >= amb + rise:
        raise ValueError("the measured temperature is not higher than what the other heaters alone give at that point")
    p1 = p0 * (amb + rise - t_zero) / (t0 - t_zero)   # Exact when the coefficients are constant
    t1 = _temperature(pr, model, options, index, point, p1, psi_jt)
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
        tb = _temperature(pr, model, options, index, point, pb, psi_jt)
        runs += 1
    state = point_temperatures(pr, model, options, index, pb, psi_jt)
    return {"power_w": pb, "temperature_c": tb, "rise_k": rise, "runs": runs + 1, "linear": bool(linear), "at_power": state,
            "resistance_k_per_w": rise / pb if pb > 0 else float("inf")}


DESIGN_LEVELS = ("none", "cad", "hand", "estimated")           # How the board was described: see power_band


def design_amounts(u):
    """!
    @brief The amplitudes of the design-uncertainty terms for the chosen confidence level.
    @details The defaults hold one amplitude per term at the level "estimated" (design_*_pct) and one multiplier per level (design_scale_*). The level "none" is zero by definition.
    @param u Uncertainty dict (the keys design_level, design_coverage_pct, design_weight_pct, design_planes_pct, design_vias_pct, design_scale_cad/hand/estimated).
    @return Dict coverage, weight, planes, vias as fractions (0 = the term is off).
    @throws ValueError If the level is not one of DESIGN_LEVELS.
    """
    level = u.get("design_level", "none")
    if level not in DESIGN_LEVELS:
        raise ValueError(f"design level must be one of {DESIGN_LEVELS}")
    scale = 0.0 if level == "none" else float(u[f"design_scale_{level}"])
    return {k: max(scale * float(u[f"design_{k}_pct"]) / 100.0, 0.0) for k in ("coverage", "weight", "planes", "vias")}


def pr_has(problem, attr):
    """!
    @brief Whether a Problem has any element of one kind (a term with nothing to change is skipped).
    @param problem Problem.
    @param attr Attribute name: "zones" or "vias".
    @return bool.
    """
    return len(getattr(problem, attr)) > 0


def _design_coverage(pr, f):
    """!
    @brief Scale the copper fill of every zone on an outer layer (a hatched pour drawn solid, or the other way round).
    @details The zones of the inner layers are left to the inner-planes term (_design_planes): moving them here too would count the same doubt twice in the root sum of squares.
             A board of one or two layers has only outer layers, so every zone is moved.
    @param pr Problem copy to change in place.
    @param f Multiplier of the fill (the result is limited to 1).
    """
    last = len(pr.board.copper_thickness) - 1                       # Index of the bottom layer (0 on a one-layer board)
    for z in pr.zones:
        if z.layer in (0, last):
            z.fill = min(max(z.fill * f, 0.0), 1.0)


def _design_weight(pr, f):
    """!
    @brief Scale the copper thickness of every layer (0.5 oz taken for 1 oz).
    @param pr Problem copy to change in place.
    @param f Multiplier of the thickness.
    """
    pr.board.copper_thickness = [t * f for t in pr.board.copper_thickness]


def _design_planes(pr, a, sign):
    """!
    @brief Doubt about the inner planes: thinner (less fill) on one side, undrawn planes or more fill on the other.
    @param pr Problem copy to change in place.
    @param a Amplitude as a fraction.
    @param sign -1 for the cool side (planes smaller than drawn), +1 for the other (planes larger, or present although not drawn).
    """
    import numpy as np
    from .model import Zone
    n = len(pr.board.copper_thickness)             # One thickness per copper layer
    for layer in range(1, n - 1):                                   # Inner layers only: the outer ones are drawn with their pads
        own = [z for z in pr.zones if z.layer == layer]
        if sign < 0:
            for z in own:
                z.fill = max(z.fill * (1.0 - a), 0.0)
        elif own:
            for z in own:
                z.fill = min(z.fill * (1.0 + a), 1.0)
        else:
            w, h = pr.board.width, pr.board.height                  # A plane that may exist but was not drawn: board-sized, at a fill of `a`
            pr.zones.append(Zone(layer=layer, polygon=np.array([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]), fill=min(a, 1.0), name="undrawn plane"))


def _design_vias(pr, f):
    """!
    @brief Scale the copper of the via barrels (their number or their plating).
    @param pr Problem copy to change in place.
    @param f Multiplier of the plating thickness.
    """
    pr.board.via_plating *= f


def power_band(problem, index, measured_c, point="ring", ambient_c=None, model="fvm", cell_mm=1.0, psi_jt=0.0, uncertainty=None, progress=None):
    """!
    @brief The power with its uncertainty band: nominal, best case (lowest plausible power) and worst case (highest plausible power).
    @details The nominal power is power_from_temperature. Then each source of doubt is moved alone to both ends of its uncertainty and the calculator is run again: the copper
             (thickness of every layer), the heat transfer (both face coefficients, or the convection multiplier when they are computed), theta and psi_JT (when the point uses
             them) and the reading itself. A source moves the power down on one side and up on the other; the deviations of the independent sources are combined as the
             root of the sum of squares, separately below and above the nominal value, which is how independent uncertainties are normally added (stacking all of them at once
             would give a range nobody has seen). More copper means a lower board resistance, so more watts for the same reading.
             **Design uncertainty** (levels cad / hand / estimated; "none" reproduces the band without it exactly): four more sources describe how well the drawn board matches the real
             one, each moved alone like the others: the copper coverage (fill of every zone of the outer layers), the copper weight (thickness of every layer, beyond the number uncertainty above),
             the inner planes (smaller than drawn, or present but not drawn: board-sized zones at a fill equal to the amplitude) and the via barrels (plating, standing for their
             number). The amplitude of each is its value at "estimated" times the multiplier of the level. The band without these terms does not cover a wrongly drawn board.
    @param problem A Problem with the board drawn as it is in reality.
    @param index 0-based index of the heater.
    @param measured_c Measured temperature in degC.
    @param point One of POINTS.
    @param ambient_c Ambient of the measurement in degC (default: the board's).
    @param model Model key.
    @param cell_mm Cell size in millimetres.
    @param psi_jt Datasheet psi_JT in K/W for the point "top".
    @param uncertainty Dict with copper_pct, h_pct, theta_pct, psi_jt_pct and reading_k, and the design keys design_level, design_coverage_pct, design_weight_pct, design_planes_pct,
                        design_vias_pct, design_scale_cad/hand/estimated (default: the "calculator" defaults of the program). Level "none" switches the design terms off.
    @param progress Optional callback progress(message, fraction).
    @return Dict: the keys of power_from_temperature plus best_w, worst_w, contributions (list of dicts factor, low_w, high_w) and uncertainty (the values used).
    """
    d = defaults.load()["calculator"]
    u = {"copper_pct": d["copper_uncertainty_pct"], "h_pct": d["h_uncertainty_pct"], "theta_pct": d["theta_uncertainty_pct"], "psi_jt_pct": d["psi_jt_uncertainty_pct"],
         "reading_k": d["reading_uncertainty_k"]}
    for k in ("design_level", "design_coverage_pct", "design_weight_pct", "design_planes_pct", "design_vias_pct", "design_scale_cad", "design_scale_hand", "design_scale_estimated"):
        if k in d:
            u[k] = d[k]
    u.update(uncertainty or {})
    design = design_amounts(u)
    base = power_from_temperature(problem, index, measured_c, point=point, ambient_c=ambient_c, model=model, cell_mm=cell_mm, psi_jt=psi_jt)
    p0 = base["power_w"]

    def scaled_copper(pr, f):
        pr.board.copper_thickness = [t * f for t in pr.board.copper_thickness]

    def scaled_h(pr, f):
        if pr.board.h_mode == "computed":
            pr.board.h_calibration *= f
        else:
            pr.board.h_top *= f
            pr.board.h_bottom *= f

    def scaled_theta(pr, f):
        pr.heaters[index].theta *= f

    factors = [("copper", u["copper_pct"] / 100.0, scaled_copper, "copper"), ("heat transfer", u["h_pct"] / 100.0, scaled_h, "h")]
    if point in ("junction", "top"):
        factors.append(("θ junction-pad", u["theta_pct"] / 100.0, scaled_theta, "theta"))
    if point == "top":
        factors.append(("ψJT", u["psi_jt_pct"] / 100.0, None, "psi"))
    factors.append(("reading", u["reading_k"], None, "reading"))
    # Design uncertainty: one-at-a-time like the others; a term with a zero amplitude (or without anything to change) is not run at all, so level "none" is the old band
    if design["coverage"] > 0 and any(z.layer in (0, len(problem.board.copper_thickness) - 1) for z in problem.zones):
        factors.append(("design: copper coverage", design["coverage"], _design_coverage, "design"))
    if design["weight"] > 0:
        factors.append(("design: copper weight", design["weight"], _design_weight, "design"))
    if design["planes"] > 0 and len(problem.board.copper_thickness) > 2:
        factors.append(("design: inner planes", design["planes"], None, "planes"))
    if design["vias"] > 0 and pr_has(problem, "vias"):
        factors.append(("design: vias", design["vias"], _design_vias, "design"))
    contributions, down, up = [], 0.0, 0.0
    for n, (name, amount, mutate, kind) in enumerate(factors):
        if progress:
            progress(f"Uncertainty: {name}", (n + 0.5) / (len(factors) + 1))
        powers = []
        for sign in (-1.0, 1.0):
            pr, meas, psi = copy.deepcopy(problem), float(measured_c), psi_jt
            if kind == "reading":
                meas += sign * amount
            elif kind == "psi":
                psi = psi_jt * (1.0 + sign * amount)
            elif kind == "planes":
                _design_planes(pr, amount, sign)
            else:
                mutate(pr, 1.0 + sign * amount)
            try:
                powers.append(power_from_temperature(pr, index, meas, point=point, ambient_c=ambient_c, model=model, cell_mm=cell_mm, psi_jt=psi)["power_w"])
            except ValueError:                                  # The reading falls outside what the changed board can explain: that end does not exist
                continue
        if not powers:
            continue
        lo, hi = min(powers + [p0]), max(powers + [p0])
        contributions.append({"factor": name, "low_w": lo, "high_w": hi, "design": name.startswith("design")})
        down += (p0 - lo) ** 2
        up += (hi - p0) ** 2
    out = dict(base)
    out.update(best_w=p0 - math.sqrt(down), worst_w=p0 + math.sqrt(up), contributions=contributions, uncertainty=u)
    return out


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
