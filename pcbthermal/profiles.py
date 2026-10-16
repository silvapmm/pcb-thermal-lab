"""!
@file profiles.py
@brief Power profiles: average-or-resolve decision per heater and the time simulation of square-wave power.

@details A heater may carry a SquareWave profile. What the board does with it depends on how fast the wave is
compared with the board's own thermal response, so every heater gets a decision:

- **average**: the oscillation it causes is too small to matter; the heater is replaced by its average power
  (exact to within the oscillation, and instant),
- **resolved**: the wave is simulated in time.

The decision is arithmetic on the unit-step response Z_i(t) of every heater (degC per W at its own hottest
point). For a square wave of period T, on-time tp, swing dP = P_on - P_off, superposition of delayed steps gives
the periodic peak and valley:

    peak   = dP * sum_{m>=0} [Z(m T + tp) - Z(m T)]
    valley = dP * sum_{m>=1} [Z(m T) - Z(m T - tp)]

with the tail of both sums D * (Rth - Z(M T)) after M terms. The oscillation peak - valley is compared with a
threshold in degC. Several heaters share an error budget: heaters are sorted by oscillation and averaged, smallest
first, while the sum of their oscillations stays within the threshold, so the neglected oscillation anywhere on the
board is at most the threshold.

The resolved heaters are then simulated together with the averaged ones in one time-stepping run (the response is
linear). The power of a step is the exact mean of the wave over that step, so edges need not coincide with step
boundaries and no energy is lost.
"""

import math
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.interpolate import PchipInterpolator

from . import fvm


class ProfileError(ValueError):
    """!
    @brief The requested time simulation cannot be run as asked (too expensive or inconsistent); the message says what to change.
    """


@dataclass
class ProfileOptions:
    """!
    @brief Settings of the power-profile analysis and simulation.
    """
    threshold_c: float = 1.0                    # Oscillation (degC) that may be ignored in total
    initial: str = "average"                    # "average" (steady state of the average power) or "temperature"
    initial_c: Optional[float] = None           # Start temperature in degC when initial == "temperature"; None = ambient
    duration: str = "stable"                    # "stable" (until the cycle repeats), "cycles" or "time"
    cycles: int = 10                            # Windows to simulate when duration == "cycles"
    time_s: float = 60.0                        # Seconds to simulate when duration == "time"
    stable_c: float = 0.1                       # Peak change (degC) between windows that counts as stable
    max_windows: int = 60                       # Window limit for duration == "stable"
    max_steps: int = 200000                     # Refuse runs that need more time steps than this
    theta: float = 1.0                          # 1.0 implicit Euler, 0.5 Crank-Nicolson
    frames: int = 60                            # Frames of the last window kept for the animation

    def validate(self):
        """!
        @brief Check the values.
        @throws ValueError On an unknown mode or an out-of-range number.
        """
        if self.threshold_c < 0 or self.stable_c <= 0:
            raise ValueError("threshold_c must be >= 0 and stable_c > 0")
        if self.initial not in ("average", "temperature"):
            raise ValueError("initial must be 'average' or 'temperature'")
        if self.duration not in ("stable", "cycles", "time"):
            raise ValueError("duration must be 'stable', 'cycles' or 'time'")
        if self.cycles < 1 or self.time_s <= 0 or self.max_windows < 2 or self.max_steps < 100 or self.frames < 2:
            raise ValueError("cycles >= 1, time_s > 0, max_windows >= 2, max_steps >= 100 and frames >= 2 are required")
        if self.theta not in (0.5, 1.0):
            raise ValueError("theta must be 0.5 or 1.0")

    def to_dict(self):
        """!
        @brief JSON-ready dictionary.
        @return Dict of the options.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """!
        @brief Build validated options from a dictionary, ignoring unknown keys.
        @param data Dict as produced by to_dict (or None).
        @return ProfileOptions.
        """
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        o = cls(**known)
        o.validate()
        return o


@dataclass
class StepResponse:
    """!
    @brief Unit-step responses Z_i(t) of every heater at its own hottest point.
    """
    model: str                                  # Model that produced them
    times: np.ndarray                           # Sample times in s (increasing, without t = 0)
    z: np.ndarray                               # Responses (n_heaters, n_times) in degC/W
    rth: np.ndarray                             # Steady-state resistances (n_heaters,) in degC/W

    def z_at(self, i, t):
        """!
        @brief Response of heater i at any time(s): monotone cubic interpolation in log time, linear below the first
               sample (heat-capacity limited) and Rth above the last.
        @param i Heater index.
        @param t Time or array of times in seconds (values <= 0 give 0).
        @return Response in degC/W with the shape of t.
        """
        t = np.asarray(t, dtype=float)
        scalar = t.ndim == 0
        t = np.atleast_1d(t)
        if not hasattr(self, "_interp"):
            self._interp = {}
        if i not in self._interp:
            # The response is smooth and monotone: PCHIP on (log t, Z) keeps it monotone and accurate even though
            # superposition sums subtract nearly equal values
            self._interp[i] = PchipInterpolator(np.log(self.times), self.z[i])
        out = np.zeros_like(t)
        pos = t > 0
        tt = t[pos]
        vals = np.empty_like(tt)
        inside = (tt >= self.times[0]) & (tt <= self.times[-1])
        vals[inside] = self._interp[i](np.log(tt[inside]))
        below = tt < self.times[0]
        vals[below] = self.z[i, 0] * tt[below] / self.times[0]
        above = tt > self.times[-1]
        vals[above] = self.rth[i]
        out[pos] = vals
        return float(out[0]) if scalar else out


@dataclass
class HeaterDecision:
    """!
    @brief The decision for one heater and the numbers behind it.
    """
    index: int                                  # Heater index
    name: str                                   # Heater label
    kind: str                                   # "constant", "wave" (square) or "table"
    regime: str                                 # "constant", "average" or "resolved"
    average_power: float                        # Mean power (W)
    peak_power: float                           # On-state power (W)
    period: float                               # Period or table length (s); 0 for a constant heater
    duty: float                                 # Duty of a square wave; 1 for a constant heater; NaN for a table
    average_rise: float                         # Rise at its hottest point with the average power (degC)
    oscillation: float                          # Peak-to-peak oscillation at its hottest point (degC)
    periodic_peak_rise: float                   # Periodic-steady-state peak rise (degC)
    periodic_valley_rise: float                 # Periodic-steady-state valley rise (degC)
    repeat: bool = True                         # False for a one-shot table (always resolved)

    @property
    def oscillation_percent(self):
        """!
        @brief Oscillation as a percentage of the average rise (informational; the decision uses degC).
        @return Percentage.
        """
        return 100.0 * self.oscillation / self.average_rise if self.average_rise > 0 else 0.0


def step_response_fvm(problem, cell_mm=2.0):
    """!
    @brief Unit-step responses of every heater computed with the finite-volume model.
    @param problem A Problem with at least one heater.
    @param cell_mm Cell size in millimetres.
    @return StepResponse.
    """
    times, z, rth = fvm.step_responses(problem, cell_mm=cell_mm)
    return StepResponse("fvm", times, z, rth)


def _cumulative_response(resp, i, period, sigma, terms):
    """!
    @brief G(sigma) = sum over m >= 0 of [Z(sigma + m T) - Z(m T)], the response of the periodised impulse up to sigma.
    @details G(T) equals the steady resistance. The terms beyond the exact ones are added as sigma / T times what is left of
             the step response (the response is flat there), which is exact when T is much shorter than the time scale.
    @param resp StepResponse.
    @param i Heater index.
    @param period Period T in seconds.
    @param sigma Array of values in [0, T].
    @param terms Number of exact terms.
    @return Array like sigma, in degC/W.
    """
    sigma = np.atleast_1d(np.asarray(sigma, dtype=float))
    m = np.arange(terms)
    z0 = resp.z_at(i, m * period)                                         # Z(m T), shared by all sigma
    tail = resp.rth[i] - float(resp.z_at(i, terms * period))
    out = np.empty_like(sigma)
    # Evaluate in blocks to bound the memory of the (sigma x terms) array
    step = max(1, int(4e6 // terms))
    for lo in range(0, len(sigma), step):
        sg = sigma[lo:lo + step]
        zs = resp.z_at(i, sg[:, None] + m[None, :] * period)
        out[lo:lo + step] = np.sum(zs - z0[None, :], axis=1) + tail * sg / period
    return out


def wave_response(resp, i, profile, terms=3000):
    """!
    @brief Periodic-steady-state rise (peak and valley) of a heater's own hottest point under a repeating profile.
    @details With P(t) piecewise constant and periodic, T(u) = sum over the stretches j of P_j [G(s2) - G(s1)], where
             [s1, s2] is the part of the period whose impulse response falls on stretch j, and G is _cumulative_response.
             For a square wave this is the exact formula peak = P_off Rth + dP G(tp) of docs/roadmap.md 1.2. The extremes are
             searched at the breakpoints and at the middle of every stretch.
    @param resp StepResponse of the reference model.
    @param i Heater index.
    @param profile SquareWave or repeating TableProfile of that heater.
    @param terms Number of exact terms of the superposition sums.
    @return Tuple (peak_rise, valley_rise) in degC above ambient.
    """
    iv = profile.intervals()
    period = profile.period
    rth = resp.rth[i]
    powers = np.array([p for _, _, p in iv])
    if len(iv) == 1 or np.ptp(powers) == 0.0:
        return float(powers[0] * rth), float(powers[0] * rth)
    a = np.array([x for x, _, _ in iv])
    b = np.array([y for _, y, _ in iv])
    # Phases at which the temperature is evaluated: every breakpoint and every stretch middle
    u = np.unique(np.concatenate([a, 0.5 * (a + b)]))
    # Window of sigma (time since the impulse) that lands on stretch j at phase u, for the two wraps
    los, his = [], []
    for k in (0, 1):
        lo = np.clip(u[:, None] - b[None, :] + k * period, 0.0, period)
        hi = np.clip(u[:, None] - a[None, :] + k * period, 0.0, period)
        los.append(lo)
        his.append(hi)
    lo, hi = np.stack(los), np.stack(his)                                   # (2, n_u, n_int)
    needed = np.unique(np.concatenate([lo.ravel(), hi.ravel()]))
    exact_terms = int(min(terms, max(50, 3e6 // max(len(needed), 1))))
    if len(needed) > 1500:
        # Many different windows: interpolate G (smooth, monotone) from a grid that contains the extremes
        grid = np.unique(np.concatenate([np.geomspace(max(profile.shortest_feature() / 20.0, period * 1e-9), period, 600),
                                         np.linspace(0.0, period, 600), [0.0, period]]))
        g_grid = _cumulative_response(resp, i, period, grid, exact_terms)
        interp = PchipInterpolator(grid, g_grid)
        g_of = lambda x: interp(x)                                          # noqa: E731
    else:
        g_vals = _cumulative_response(resp, i, period, needed, exact_terms)
        g_of = lambda x: np.interp(x, needed, g_vals)                       # noqa: E731
    contrib = np.where(hi > lo, g_of(hi) - g_of(lo), 0.0)                   # (2, n_u, n_int)
    temp = contrib.sum(axis=0) @ powers                                     # (n_u,)
    return float(temp.max()), float(temp.min())


def once_response(resp, i, profile, n_points=400):
    """!
    @brief Rise of a heater's own hottest point during a one-shot profile, starting from the steady state of its first power.
    @param resp StepResponse of the reference model.
    @param i Heater index.
    @param profile A TableProfile that does not repeat.
    @param n_points Number of times at which the response is sampled (plus every breakpoint).
    @return Tuple (peak_rise, valley_rise) in degC above ambient over the profile length.
    """
    iv = profile.intervals()
    powers = np.array([p for _, _, p in iv])
    starts = np.array([a for a, _, _ in iv])
    t = np.unique(np.concatenate([np.linspace(0.0, profile.period, n_points), starts, [profile.period]]))
    dP = np.diff(np.concatenate([[powers[0]], powers]))                   # Steps of power at the start of each stretch
    temp = powers[0] * resp.rth[i] + np.zeros_like(t)
    for s, d in zip(starts, dP):
        if d != 0.0:
            temp = temp + d * resp.z_at(i, t - s)
    return float(temp.max()), float(temp.min())


def decide(problem, resp, threshold_c):
    """!
    @brief Decide, for every heater, whether its power wave is averaged or resolved in time.
    @param problem A Problem (heaters may carry profiles).
    @param resp StepResponse of the reference model, one row per heater.
    @param threshold_c Total oscillation (degC) that may be ignored.
    @return List of HeaterDecision, one per heater, in heater order.
    """
    out = []
    waves = []
    for i, h in enumerate(problem.heaters):
        avg = h.average_power()
        rise = avg * resp.rth[i]
        if h.profile is None:
            out.append(HeaterDecision(i, h.name or f"Heater {i + 1}", "constant", "constant", avg, avg, 0.0, 1.0,
                                      rise, 0.0, rise, rise))
            continue
        w = h.profile
        if w.repeat:
            pk, vl = wave_response(resp, i, w)
        else:
            pk, vl = once_response(resp, i, w)
        kind = "wave" if w.kind == "square" else "table"
        duty = w.duty if w.kind == "square" else float("nan")
        out.append(HeaterDecision(i, h.name or f"Heater {i + 1}", kind, "average" if w.repeat else "resolved", avg, w.peak(),
                                  w.period, duty, rise, max(pk - vl, 0.0), pk, vl, w.repeat))
        if w.repeat:
            waves.append(i)                                              # A one-shot profile never takes part in the budget
    # Error budget: average the heaters with the smallest oscillations while their sum stays within the threshold
    spent = 0.0
    for i in sorted(waves, key=lambda k: out[k].oscillation):
        if spent + out[i].oscillation <= threshold_c:
            spent += out[i].oscillation
        else:
            out[i].regime = "resolved"
    return out


@dataclass
class ProfileResult:
    """!
    @brief Outcome of the time simulation of one model.
    """
    model: str
    decisions: List[HeaterDecision]
    resolved: bool                              # False when every heater was averaged (no time stepping needed)
    ambient: float
    dx: float = 0.0
    dy: float = 0.0
    times: Optional[np.ndarray] = None          # Times of the last window (s)
    t_max: Optional[np.ndarray] = None          # Hottest temperature of the board at those times (degC)
    t_heaters: Optional[np.ndarray] = None      # Hottest temperature under every heater (n_heaters, n_times)
    frame_times: Optional[np.ndarray] = None    # Times of the stored frames (s)
    frames: Optional[np.ndarray] = None         # Fields (n_frames, layers, ny, nx) in degC
    peak_map: Optional[np.ndarray] = None       # Highest temperature reached at every cell in the last window (degC)
    history_t: Optional[np.ndarray] = None      # Whole run, decimated: times (s)
    history_max: Optional[np.ndarray] = None    # Whole run, decimated: hottest temperature (degC)
    window: float = 0.0                         # Length of one window (s)
    dt: float = 0.0                             # Time step (s)
    steps: int = 0                              # Steps taken
    windows: int = 0                            # Windows simulated
    converged: bool = False
    seconds: float = 0.0                        # Computing time
    initial_c: float = 0.0                      # Start temperature (degC); for "average" the mean field maximum
    steady_average_max: float = 0.0             # Steady maximum with every heater at its average power (degC)
    steady_peak_max: float = 0.0                # Steady maximum with every heater at its on-state power (degC)
    peak_location: Optional[tuple] = None       # (layer, x_m, y_m) of the hottest cell of the peak map
    warnings: List[str] = field(default_factory=list)

    @property
    def peak(self):
        """!
        @brief Highest temperature of the last window.
        @return Temperature in degC (the steady average maximum when nothing was resolved).
        """
        return float(self.t_max.max()) if self.t_max is not None else self.steady_average_max

    @property
    def minimum(self):
        """!
        @brief Lowest value of the hottest-point temperature in the last window.
        @return Temperature in degC.
        """
        return float(self.t_max.min()) if self.t_max is not None else self.steady_average_max

    @property
    def oscillation(self):
        """!
        @brief Peak-to-peak oscillation of the hottest-point temperature in the last window.
        @return Degrees Celsius.
        """
        return self.peak - self.minimum

    def time_above(self, limit_c):
        """!
        @brief Time spent above a temperature limit in the last window.
        @param limit_c Temperature limit in degC.
        @return Tuple (seconds, fraction of the window).
        """
        if self.t_max is None or len(self.times) == 0:
            return 0.0, 0.0
        frac = float(np.mean(self.t_max > limit_c))
        return frac * self.window, frac

    def summary(self):
        """!
        @brief Flat dictionary of the main numbers.
        @return Dict of floats, strings and booleans.
        """
        return {"model": self.model, "resolved": self.resolved, "peak_c": self.peak, "minimum_c": self.minimum,
                "oscillation_c": self.oscillation, "steady_average_c": self.steady_average_max,
                "steady_peak_c": self.steady_peak_max, "windows": self.windows, "steps": self.steps,
                "dt_s": self.dt, "window_s": self.window, "converged": self.converged, "seconds": self.seconds,
                "decisions": [{"heater": d.name, "regime": d.regime, "average_w": d.average_power,
                               "oscillation_c": d.oscillation, "oscillation_percent": d.oscillation_percent}
                              for d in self.decisions]}


def plan_run(problem, decisions, options):
    """!
    @brief Choose the window length, the time step and check that the run is affordable.
    @param problem A Problem.
    @param decisions Decisions from decide().
    @param options ProfileOptions.
    @return Dict with the resolved heater indices, window (s), steps per window, dt (s) and the estimated total steps.
    @throws ProfileError If the run needs more than options.max_steps steps.
    """
    res = [d.index for d in decisions if d.regime == "resolved"]
    if not res:
        return {"resolved": [], "window": 0.0, "n_per": 0, "dt": 0.0, "steps": 0, "once": False, "exact": True}
    waves = {i: problem.heaters[i].profile for i in res}
    repeating = [w.period for w in waves.values() if w.repeat]
    once = [w.period for w in waves.values() if not w.repeat]
    # The window is the period of the combined repeating signal (least common multiple); a one-shot profile fixes the length
    window, exact = _common_period(repeating) if repeating else (0.0, True)
    window = max([window] + once)
    shortest = min(w.shortest_feature() for w in waves.values())
    n_per = max(int(math.ceil(window / (shortest / 10.0))), 20)
    dt = window / n_per
    if once and options.duration != "time":
        steps = n_per                                                  # One pass of the profile
    elif options.duration == "cycles":
        steps = options.cycles * n_per
    elif options.duration == "time":
        steps = int(math.ceil(options.time_s / dt))
    else:
        steps = min(options.max_windows, 12) * n_per        # Typical need when starting from the average state
    if steps > options.max_steps:
        names = ", ".join(problem.heaters[i].name or f"heater {i + 1}" for i in res)
        raise ProfileError(
            f"the time simulation needs about {steps:,} steps (limit {options.max_steps:,}): the resolved heaters ({names}) "
            f"have a shortest stretch of {shortest:.3g} s and a window of {window:.3g} s. Raise the oscillation "
            "threshold so that the fastest heater is averaged, shorten the duration, or raise the step limit.")
    return {"resolved": res, "window": window, "n_per": n_per, "dt": dt, "steps": steps, "once": bool(once), "exact": exact}


def _common_period(periods, max_ratio=50.0):
    """!
    @brief Period of the sum of several repeating signals: the least common multiple of their periods.
    @details Periods are turned into fractions (denominator limit 100000); if the least common multiple is more than max_ratio
             times the longest period (or there is none), the longest period is used and the result is marked inexact.
    @param periods List of periods in seconds.
    @param max_ratio Largest accepted ratio between the common period and the longest period.
    @return Tuple (period in seconds, True if every period divides it).
    """
    from fractions import Fraction
    from math import gcd
    longest = max(periods)
    fr = [Fraction(p).limit_denominator(100000) for p in periods]
    den = 1
    for f in fr:
        den = den * f.denominator // gcd(den, f.denominator)
    nums = [int(f * den) for f in fr]
    lcm = 1
    for n in nums:
        lcm = lcm * n // gcd(lcm, n)
    common = lcm / den
    ok = all(abs(common / p - round(common / p)) < 1e-6 for p in periods)
    if not ok or common > max_ratio * longest:
        return longest, False
    return float(common), True


def run_windows(problem, decisions, options, adapter, model, progress=None):
    """!
    @brief Window-by-window time simulation shared by all models.
    @details The adapter knows how a model advances in time; this function owns the plan, the exact step-mean power,
             the convergence test (peak and minimum repeat between windows), the frames and the result assembly.
             Adapter interface: dx, dy, ambient, steady_average_max, steady_peak_max; begin(options) ->
             (state, initial_c); prepare(dt) (called after begin); advance(state, dt, powers) -> state; observe(state) -> (hottest, per-heater hottest);
             frame(state) -> field (layers, ny, nx) in degC; peak_values(state) -> flat array to maximise or None.
    @param problem A Problem (heater powers equal the averages).
    @param decisions Decisions from decide().
    @param options ProfileOptions.
    @param adapter Model adapter (see above).
    @param model Model name stored in the result.
    @param progress Optional callback progress(message, fraction).
    @return ProfileResult.
    @throws ProfileError If the run is too expensive for options.max_steps.
    """
    options.validate()
    t_begin = time.time()
    result = ProfileResult(model=model, decisions=decisions, resolved=False, ambient=adapter.ambient, dx=adapter.dx,
                           dy=adapter.dy, steady_average_max=adapter.steady_average_max,
                           steady_peak_max=adapter.steady_peak_max)
    plan = plan_run(problem, decisions, options)
    if not plan["resolved"]:
        result.initial_c, result.converged, result.seconds = adapter.steady_average_max, True, time.time() - t_begin
        return result
    res, window, n_per, dt = plan["resolved"], plan["window"], plan["n_per"], plan["dt"]
    nh = len(problem.heaters)
    waves = {i: problem.heaters[i].profile for i in res}
    p_avg = np.array([h.average_power() for h in problem.heaters])
    state, result.initial_c = adapter.begin(options)
    adapter.prepare(dt)
    if options.duration == "time":
        windows_max = int(math.ceil(plan["steps"] / n_per))
    elif plan["once"]:
        windows_max = 1                                                # One pass of a one-shot profile
    elif options.duration == "cycles":
        windows_max = options.cycles
    else:
        windows_max = min(options.max_windows, max(options.max_steps // n_per, 2))
    stride = max(n_per // options.frames, 1)
    history, total, prev_peak, prev_min, converged = [], 0, None, None, False
    for w in range(windows_max):
        t_start = (np.arange(n_per) + w * n_per) * dt
        P = np.tile(p_avg, (n_per, 1))
        for i in res:
            P[:, i] = waves[i].mean_power(t_start, t_start + dt)          # Exact mean power of every step
        gmax = np.empty(n_per)
        hmax = np.empty((nh, n_per))
        peak_map = None
        frames, frame_t = [], []
        for s in range(n_per):
            state = adapter.advance(state, dt, P[s])
            gmax[s], hmax[:, s] = adapter.observe(state)
            values = adapter.peak_values(state)
            if values is not None:
                peak_map = values.copy() if peak_map is None else np.maximum(peak_map, values, out=peak_map)
            if (s + 1) % stride == 0:
                frames.append(adapter.frame(state).astype(np.float32))
                frame_t.append((w * n_per + s + 1) * dt)
        total += n_per
        history.append(gmax)
        wp, wm = float(gmax.max()), float(gmax.min())
        if progress:
            progress(f"Window {w + 1}: peak {wp:.1f} °C", min((w + 1) / max(windows_max, 1), 0.99))
        if options.duration == "stable" and prev_peak is not None and \
                abs(wp - prev_peak) < options.stable_c and abs(wm - prev_min) < options.stable_c:
            converged = True
            break
        prev_peak, prev_min = wp, wm
    if plan["once"] and options.duration != "time":
        converged = True                                                 # A single pass has nothing to settle
    elif options.duration != "stable":
        converged = prev_peak is not None and w >= 1
    result.resolved = True
    result.window, result.dt, result.windows, result.steps, result.converged = window, dt, w + 1, total, converged
    result.times = (np.arange(1, n_per + 1) + w * n_per) * dt
    result.t_max, result.t_heaters = gmax, hmax
    result.frames, result.frame_times = np.asarray(frames), np.asarray(frame_t)
    result.peak_map = result.frames.max(axis=0) if peak_map is None else adapter.shape_field(peak_map)
    flat = np.concatenate(history)
    keep = max(len(flat) // 3000, 1)
    result.history_max, result.history_t = flat[::keep], (np.arange(1, len(flat) + 1) * dt)[::keep]
    l, i, j = np.unravel_index(int(np.argmax(result.peak_map)), result.peak_map.shape)
    result.peak_location = (int(l), (j + 0.5) * adapter.dx, (i + 0.5) * adapter.dy)
    if options.duration == "stable" and not converged and not plan["once"]:
        result.warnings.append(f"the cycle did not repeat within {w + 1} windows (a change below {options.stable_c} °C "
                               "was not reached); the last window is reported")
    if not plan["exact"]:
        result.warnings.append("the resolved periods have no common multiple within 50 times the longest one, so the combined "
                               "signal is not followed over its whole period; the peak is the highest value seen in the last window")
    if plan["once"]:
        result.warnings.append("a one-shot profile is simulated once from its start state; its last power is held after the end")
    result.warnings += list(getattr(adapter, "warnings", []))
    result.seconds = time.time() - t_begin
    if progress:
        progress("Time simulation done", 1.0)
    return result


class _FVMAdapter:
    """!
    @brief Adapter that advances the finite-volume model in time (see run_windows for the interface).
    """

    def __init__(self, problem, cell_mm):
        """!
        @param problem A Problem (heater powers equal the averages).
        @param cell_mm Cell size in millimetres.
        """
        b = problem.board
        self.ambient = b.ambient
        nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
        ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
        self.net = fvm.Network(problem, nx, ny)
        self.dx, self.dy = self.net.dx, self.net.dy
        self.p_avg = np.array([h.average_power() for h in problem.heaters])
        steady = spla.splu(self.net.K.tocsc())
        self.th_avg = steady.solve(self.net.Qw_matrix @ self.p_avg)
        p_init = np.array([h.initial_power() for h in problem.heaters])      # Start state: average, or first power of a one-shot
        self.th_init = self.th_avg if np.allclose(p_init, self.p_avg) else steady.solve(self.net.Qw_matrix @ p_init)
        th_peak = steady.solve(self.net.Qw_matrix @ np.array([h.peak_power() for h in problem.heaters]))
        self.steady_average_max = float(self.th_avg.max() + self.ambient)
        self.steady_peak_max = float(th_peak.max() + self.ambient)
        self.shape = (self.net.nl, self.net.ny, self.net.nx)

    def prepare(self, dt):
        """!
        @brief Factorise the step matrix for the time step.
        @param dt Time step in seconds.
        """
        self.dt = dt
        Cd, K = self.net.C.ravel(), self.net.K
        self.lu = spla.splu((sp.diags(Cd / dt) + self.theta * K).tocsc())
        self.B = (sp.diags(Cd / dt) - (1.0 - self.theta) * K).tocsr()

    def begin(self, options):
        """!
        @brief Initial state.
        @param options ProfileOptions.
        @return Tuple (state, reported initial temperature in degC).
        """
        self.theta = options.theta
        if options.initial == "average":
            return self.th_init.copy(), float(self.th_init.max() + self.ambient)
        t0 = self.ambient if options.initial_c is None else float(options.initial_c)
        return np.full_like(self.th_avg, t0 - self.ambient), t0

    def advance(self, x, dt, powers):
        """!
        @brief One implicit step.
        @param x State (rise above ambient, flat).
        @param dt Time step (s), equal to the prepared one.
        @param powers Power of every heater during the step (W).
        @return New state.
        """
        return self.lu.solve(self.B @ x + self.net.Qw_matrix @ powers)

    def observe(self, x):
        """!
        @brief Hottest temperature of the board and under every heater.
        @param x State.
        @return Tuple (hottest degC, array of per-heater hottest degC).
        """
        return float(x.max() + self.ambient), np.array([x[idx].max() for idx in self.net.footprints]) + self.ambient

    def frame(self, x):
        """!
        @brief Field in degC.
        @param x State.
        @return Array (layers, ny, nx).
        """
        return x.reshape(self.shape) + self.ambient

    def peak_values(self, x):
        """!
        @brief Values whose running maximum is the peak map.
        @param x State.
        @return Flat array in degC.
        """
        return x + self.ambient

    def shape_field(self, flat):
        """!
        @brief Reshape a flat field.
        @param flat Flat array.
        @return Array (layers, ny, nx).
        """
        return flat.reshape(self.shape)


def run_fvm(problem, decisions, options, cell_mm=1.0, progress=None):
    """!
    @brief Time simulation of a problem with power profiles using the finite-volume model.
    @param problem A Problem (heater powers equal the averages).
    @param decisions Decisions from decide().
    @param options ProfileOptions.
    @param cell_mm Cell size in millimetres.
    @param progress Optional callback progress(message, fraction).
    @return ProfileResult.
    @throws ProfileError If the run is too expensive for options.max_steps.
    """
    return run_windows(problem, decisions, options, _FVMAdapter(problem, cell_mm), "fvm", progress)
