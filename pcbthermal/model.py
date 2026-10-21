"""!
@file model.py
@brief Data model of the PCB thermal problem and JSON readers.

The model is the single description shared by the three solvers (FVM, lumped network and
analytic). Everything inside the dataclasses is in SI units (m, W, K, W/mK, W/m2K, J/kgK,
kg/m3). The JSON files use millimetres and 1-based layer numbers (layer 1 = top), which is
what the graphical editor shows.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import copy
import json
import math
import os

import numpy as np

from .geometry import coverage_fraction, polygon_area, polygon_is_simple


@dataclass
class Materials:
    """!
    @brief Thermal properties of the two materials of the stack-up.
    @details Defaults are typical values: copper 385 W/mK; FR-4 0.3 W/mK through the thickness
             and about 0.9 W/mK in the plane (glass weave), 1850 kg/m3 and 900 J/kgK.
    """
    k_copper: float = 385.0           # Copper conductivity (W/mK)
    rho_copper: float = 8960.0        # Copper density (kg/m3)
    cp_copper: float = 385.0          # Copper specific heat (J/kgK)
    k_fr4_through: float = 0.3        # FR-4 conductivity across the thickness (W/mK)
    k_fr4_inplane: float = 0.9        # FR-4 conductivity along the plane (W/mK)
    rho_fr4: float = 1850.0           # FR-4 density (kg/m3)
    cp_fr4: float = 900.0             # FR-4 specific heat (J/kgK)


@dataclass
class Dielectric:
    """!
    @brief One dielectric layer (core or prepreg) between two adjacent copper layers, for the advanced stack-up.
    @details The properties are those of the material in the thickness direction (k_through) and along the plane (k_inplane).
    """
    thickness: float = 0.3e-3         # Thickness (m)
    name: str = "FR-4 (standard)"     # Material label (a DIELECTRICS entry or free text)
    k_through: float = 0.3            # Conductivity across the thickness (W/mK)
    k_inplane: float = 0.9            # Conductivity along the plane (W/mK)
    rho: float = 1850.0               # Density (kg/m3)
    cp: float = 900.0                 # Specific heat (J/kgK)


# Typical dielectric materials, (label, k_through W/mK, k_inplane W/mK, rho kg/m3, cp J/kgK). Indicative values, always editable
DIELECTRICS = (
    ("FR-4 (standard)", 0.3, 0.9, 1850.0, 900.0),
    ("FR-4 high Tg / filled", 0.4, 1.0, 1900.0, 900.0),
    ("Polyimide (flex)", 0.15, 0.15, 1420.0, 1090.0),
    ("PTFE ceramic (RO4350B type)", 0.69, 0.69, 1860.0, 830.0),
    ("Metal-core dielectric (2 W/mK)", 2.0, 2.0, 2300.0, 900.0),
    ("Alumina ceramic (96 %)", 24.0, 24.0, 3750.0, 800.0),
    ("Aluminium nitride", 170.0, 170.0, 3260.0, 740.0),
)


STACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stackups.json")   # Typical stack-ups by layer count (editable)
_STACKUP_CACHE = {}


def load_stackup_templates(path=None):
    """!
    @brief The typical stack-up templates read from the JSON file (cached).
    @param path File path (default: the file shipped with the package, `pcbthermal/data/stackups.json`).
    @return Dict with the keys description, notes, sources and templates ({"2": {...}, "4": {...}, ...}).
    @throws ValueError If the file is not a valid template file.
    """
    path = path or STACKUP_FILE
    stamp = (path, os.path.getmtime(path))
    if _STACKUP_CACHE.get("stamp") != stamp:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if "templates" not in data or not isinstance(data["templates"], dict):
            raise ValueError(f"{path}: no 'templates' table")
        for key, t in data["templates"].items():
            n = int(key)
            if len(t.get("copper_um", [])) != n or (t.get("mode") == "advanced" and len(t.get("dielectrics", [])) != n - 1):
                raise ValueError(f"{path}: template {key} needs {n} copper layers and {n - 1} dielectrics")
        _STACKUP_CACHE.update(stamp=stamp, data=data)
    return _STACKUP_CACHE["data"]


def stackup_template(layers, path=None):
    """!
    @brief The typical stack-up for a number of copper layers.
    @details The entry of the JSON file for that count; for a count that is not listed (3, 5, 7, ...) a generic one: 35 um outer copper, 15.2 um inner copper
             and equal gaps that bring the board to the total thickness of the largest listed template with fewer layers.
    @param layers Number of copper layers.
    @param path Template file (default: the shipped one).
    @return Dict with name, mode ("simple" or "advanced"), copper_um (list), dielectrics (list of dicts kind, thickness_um, material) and total_thickness_um.
    """
    data = load_stackup_templates(path)["templates"]
    t = data.get(str(layers))
    if t is not None:
        out = copy.deepcopy(t)
        out.setdefault("mode", "advanced")
        out["total_thickness_um"] = out.get("total_thickness_um", sum(out["copper_um"]) + sum(d["thickness_um"] for d in out["dielectrics"]))
        return out
    below = max((int(k) for k in data if int(k) < layers), default=min(int(k) for k in data))
    ref = stackup_template(below, path)
    copper = [35.0] + [15.2] * max(layers - 2, 0) + [35.0] if layers > 1 else [35.0]
    gap = (ref["total_thickness_um"] - sum(copper)) / (layers - 1) if layers > 1 else 0.0
    return {"name": f"{layers} layers, {ref['total_thickness_um'] / 1000:g} mm (generic: equal gaps)", "mode": "advanced" if layers > 1 else "simple",
            "copper_um": copper, "total_thickness_um": ref["total_thickness_um"],
            "dielectrics": [{"kind": "dielectric", "thickness_um": gap, "material": "FR-4 (standard)"} for _ in range(layers - 1)]}


@dataclass
class Board:
    """!
    @brief Geometry, stack-up and boundary conditions of the board (SI units).
    """
    width: float = 0.1                          # Board width along x (m)
    height: float = 0.1                         # Board height along y (m)
    thickness: float = 1.6e-3                   # Total board thickness (m)
    layers: int = 2                             # Number of copper layers (layer 0 = top)
    copper_thickness: List[float] = field(default_factory=lambda: [35e-6, 35e-6])  # Per layer (m)
    ambient: float = 25.0                       # Ambient temperature (degC)
    h_top: float = 10.0                         # Top surface coefficient, convection+radiation (W/m2K)
    h_bottom: float = 15.0                      # Bottom surface coefficient (W/m2K)
    h_side: Optional[float] = 10.0              # Edge coefficient (W/m2K); None = insulated edges
    via_plating: float = 25e-6                  # Plating thickness of the via barrel (m)
    h_mode: str = "manual"                      # "manual": h_top and h_bottom as typed; "computed": from correlations
    emissivity_top: float = 0.9                 # Emissivity of the top face (computed mode; solder mask about 0.9)
    emissivity_bottom: float = 0.9              # Emissivity of the bottom face (computed mode)
    air_speed: float = 0.0                      # Air speed along the board in m/s (computed mode; 0 = natural convection)
    orientation: str = "horizontal"             # "horizontal" (top face up), "horizontal_down" (top face down) or "vertical" (computed mode)
    h_calibration: float = 1.0                  # Multiplier of the computed convection (fit to a measurement)
    materials: Materials = field(default_factory=Materials)
    dielectrics: Optional[List[Dielectric]] = None   # Advanced stack-up: one per gap (layers - 1); None = simple, equal gaps of `materials`
    outline: Optional[np.ndarray] = field(default=None, compare=False)   # Board outline (n, 2) in metres inside the width x height box; None = the whole rectangle

    def apply_template(self, path=None):
        """!
        @brief Load the typical stack-up of the current number of layers (copper and dielectrics, or total thickness and copper for a simple board).
        @details Advanced board: copper thickness per layer, one dielectric per gap with the thickness and material of the template (the properties of the
                 material come from DIELECTRICS), total thickness = their sum. Simple board: total thickness of the template and the outer copper thickness on every layer.
        @param path Template file (default: the shipped one).
        @return The template dict used (its name tells which stack-up was loaded).
        """
        t = stackup_template(self.layers, path)
        if self.dielectrics is None or t["mode"] == "simple":
            if self.dielectrics is not None:
                self.dielectrics = None                  # A single layer has no gaps to describe
            self.thickness = t["total_thickness_um"] * 1e-6
            self.copper_thickness = [t["copper_um"][0] * 1e-6] * self.layers
            return t
        self.copper_thickness = [c * 1e-6 for c in t["copper_um"]]
        self.dielectrics = []
        for d in t["dielectrics"]:
            preset = next((p for p in DIELECTRICS if p[0] == d.get("material")), DIELECTRICS[0])
            self.dielectrics.append(Dielectric(d["thickness_um"] * 1e-6, preset[0], preset[1], preset[2], preset[3], preset[4]))
        self.thickness = self.total_thickness()
        return t

    def has_outline(self):
        """!
        @brief True when the board is not the full rectangle (an outline polygon is set).
        @return bool.
        """
        return self.outline is not None

    def cover(self, nx, ny, dx, dy, samples=4, minimum=0.01):
        """!
        @brief Fraction of every grid cell that lies on the board.
        @details All ones for a rectangular board; otherwise the coverage of the outline polygon. Cells with less than `minimum` are taken as off the board.
        @param nx Number of cells along x.
        @param ny Number of cells along y.
        @param dx Cell width in metres.
        @param dy Cell height in metres.
        @param samples Sub-samples per cell side.
        @param minimum Smallest coverage kept.
        @return Array (ny, nx) with values in [0, 1].
        """
        if self.outline is None:
            return np.ones((ny, nx))
        c = coverage_fraction(self.outline, nx, ny, dx, dy, samples)
        return np.where(c >= minimum, c, 0.0)

    def board_area(self):
        """!
        @brief Area of the board.
        @return Area in square metres (the polygon area with an outline, width x height otherwise).
        """
        return polygon_area(self.outline) if self.outline is not None else self.width * self.height

    def is_advanced(self):
        """!
        @brief True when the dielectrics are described one by one (advanced stack-up).
        @return bool.
        """
        return self.dielectrics is not None

    def total_thickness(self):
        """!
        @brief Total board thickness: the typed one in simple mode, copper plus dielectrics in advanced mode.
        @return Thickness in metres.
        """
        if self.dielectrics is None:
            return self.thickness
        return float(sum(self.copper_thickness) + sum(d.thickness for d in self.dielectrics))

    def make_advanced(self):
        """!
        @brief Switch to the advanced stack-up with dielectrics equal to the current simple ones (the same board, now editable per gap).
        """
        if self.dielectrics is None and self.layers > 1:
            m = self.materials
            gap = self.dielectric_thickness()
            self.dielectrics = [Dielectric(gap, "FR-4 (standard)", m.k_fr4_through, m.k_fr4_inplane, m.rho_fr4, m.cp_fr4) for _ in range(self.layers - 1)]
        elif self.dielectrics is None:
            self.dielectrics = []
        self.thickness = self.total_thickness()

    def make_simple(self):
        """!
        @brief Return to the simple stack-up: equal gaps that share the total thickness, FR-4 of `materials`.
        """
        self.thickness = self.total_thickness()
        self.dielectrics = None

    def gap_thicknesses(self):
        """!
        @brief Thickness of every dielectric gap, top to bottom.
        @return Array of length layers - 1 in metres.
        """
        if self.dielectrics is not None:
            return np.array([d.thickness for d in self.dielectrics], dtype=float)
        return np.full(max(self.layers - 1, 0), self.dielectric_thickness())

    def gap_properties(self):
        """!
        @brief Properties of every dielectric gap, top to bottom.
        @return Tuple of arrays (k_through, k_inplane, rho_cp) of length layers - 1; rho_cp in J/m3K.
        """
        n = max(self.layers - 1, 0)
        if self.dielectrics is not None:
            return (np.array([d.k_through for d in self.dielectrics], dtype=float), np.array([d.k_inplane for d in self.dielectrics], dtype=float),
                    np.array([d.rho * d.cp for d in self.dielectrics], dtype=float))
        m = self.materials
        return np.full(n, m.k_fr4_through), np.full(n, m.k_fr4_inplane), np.full(n, m.rho_fr4 * m.cp_fr4)

    def slab_thicknesses(self):
        """!
        @brief Thickness represented by every layer node: copper plus the part of the dielectric around it.
        @details Simple stack-up: the total thickness shared equally among the layers (the original model). Advanced: the copper plus half of each
                 adjacent gap, so the slabs add up to the total thickness.
        @return Array of length layers in metres.
        """
        L = self.layers
        if self.dielectrics is None:
            return np.full(L, self.thickness / L)
        d = self.gap_thicknesses()
        half = np.zeros(L)
        half[:-1] += d / 2.0
        half[1:] += d / 2.0
        return np.asarray(self.copper_thickness, dtype=float) + half

    def layer_laminate(self):
        """!
        @brief In-plane conductivity and volumetric heat capacity of the dielectric part of every layer node.
        @details The thickness-weighted mean of the two adjacent gaps (the single gap for the outer layers); the plain FR-4 values in simple mode.
        @return Tuple of arrays (k_inplane in W/mK, rho_cp in J/m3K), each of length layers.
        """
        L = self.layers
        k_ip, rho_cp = np.full(L, self.materials.k_fr4_inplane), np.full(L, self.materials.rho_fr4 * self.materials.cp_fr4)
        if self.dielectrics is None or L < 2:
            return k_ip, rho_cp
        d = self.gap_thicknesses()
        _, gk, gc = self.gap_properties()
        for l in range(L):
            gaps = [g for g in (l - 1, l) if 0 <= g < L - 1]
            w = np.array([d[g] for g in gaps])
            if w.sum() > 0:
                k_ip[l] = float(np.dot(w, [gk[g] for g in gaps]) / w.sum())
                rho_cp[l] = float(np.dot(w, [gc[g] for g in gaps]) / w.sum())
        return k_ip, rho_cp

    def dielectric_thickness(self):
        """!
        @brief Thickness of one dielectric layer between two adjacent copper layers.
        @return Thickness in metres (0 for a single-layer board).
        """
        if self.layers < 2:
            return 0.0
        if self.dielectrics is not None:
            return float(np.mean([d.thickness for d in self.dielectrics]))       # Mean of the gaps; use gap_thicknesses() for each one
        # Board thickness minus all copper, shared by the (layers - 1) dielectric gaps
        return (self.thickness - sum(self.copper_thickness)) / (self.layers - 1)

    def validate(self):
        """!
        @brief Check that the stack-up is physically meaningful.
        @throws ValueError If a dimension or property is not positive or the copper does not fit.
        """
        if self.layers < 1:
            raise ValueError("layers must be >= 1")
        if len(self.copper_thickness) != self.layers:
            raise ValueError("copper_thickness must have one value per layer")
        if min(self.width, self.height, self.total_thickness()) <= 0:
            raise ValueError("board dimensions must be positive")
        if self.dielectrics is not None:
            if len(self.dielectrics) != max(self.layers - 1, 0):
                raise ValueError("the advanced stack-up needs one dielectric per gap between copper layers")
            for d in self.dielectrics:
                if d.thickness <= 0 or d.k_through <= 0 or d.k_inplane <= 0 or d.rho <= 0 or d.cp <= 0:
                    raise ValueError("every dielectric needs a positive thickness, conductivities, density and specific heat")
            if min(self.copper_thickness) <= 0:
                raise ValueError("copper thickness must be positive")
        elif self.layers > 1 and self.dielectric_thickness() <= 0:
            raise ValueError("the copper layers do not fit inside the board thickness")
        if self.outline is not None:
            o = np.asarray(self.outline, dtype=float)
            if o.ndim != 2 or o.shape[1] != 2 or len(o) < 3:
                raise ValueError("the board outline needs at least three vertices")
            tol = 1e-9
            if o.min() < -tol or o[:, 0].max() > self.width + tol or o[:, 1].max() > self.height + tol:
                raise ValueError("the board outline must lie inside the width x height box")
            if polygon_area(o) <= 0 or not polygon_is_simple(o):
                raise ValueError("the board outline must be a simple polygon with a positive area")
        if self.h_top < 0 or self.h_bottom < 0:
            raise ValueError("heat transfer coefficients must be >= 0")
        if self.h_mode not in ("manual", "computed"):
            raise ValueError("h_mode must be 'manual' or 'computed'")
        if self.orientation not in ("horizontal", "horizontal_down", "vertical"):
            raise ValueError("orientation must be 'horizontal', 'horizontal_down' or 'vertical'")
        if not (0.0 <= self.emissivity_top <= 1.0 and 0.0 <= self.emissivity_bottom <= 1.0):
            raise ValueError("emissivity must be between 0 and 1")
        if self.air_speed < 0 or self.h_calibration <= 0:
            raise ValueError("air speed must be >= 0 and the calibration multiplier > 0")
        if self.h_mode == "manual" and self.h_top + self.h_bottom <= 0 and not self.h_side:
            raise ValueError("the board has no path to ambient (all coefficients are zero)")


@dataclass
class Zone:
    """!
    @brief Copper area on one layer.
    """
    layer: int                                  # 0-based layer index
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    fill: float = 1.0                           # Copper fill fraction inside the polygon (0..1)
    name: str = ""                              # Optional label shown in reports and the GUI


@dataclass
class SquareWave:
    """!
    @brief Power of a heater as a square wave: on-state power for a fraction of every period.
    @details The wave starts with the on-state at t = 0 of every period. The average power
             p_off + duty * (p_on - p_off) is what the steady-state models use by default.
    """
    p_on: float                                 # Power while on (W)
    period: float                               # Period (s)
    duty: float                                 # Fraction of the period spent on (0..1]
    p_off: float = 0.0                          # Power while off (W)

    def average(self):
        """!
        @brief Mean power over one period.
        @return Power in watts.
        """
        return self.p_off + self.duty * (self.p_on - self.p_off)

    def on_time(self):
        """!
        @brief Duration of the on-state in every period.
        @return Time in seconds.
        """
        return self.duty * self.period

    def off_time(self):
        """!
        @brief Duration of the off-state in every period.
        @return Time in seconds.
        """
        return (1.0 - self.duty) * self.period

    kind = "square"                             # Shape name used in files and reports
    repeat = True                               # A square wave repeats forever

    def peak(self):
        """!
        @brief Highest power of the wave.
        @return Power in watts.
        """
        return self.p_on

    def initial_power(self):
        """!
        @brief Power that defines the start state "steady state of the average": the average of a repeating wave.
        @return Power in watts.
        """
        return self.average()

    def shortest_feature(self):
        """!
        @brief Shortest constant-power stretch (limits the time step).
        @return Time in seconds.
        """
        return min(self.on_time(), self.off_time()) if self.off_time() > 0 else self.on_time()

    def intervals(self):
        """!
        @brief The constant-power stretches of one period.
        @return List of tuples (start s, end s, power W) covering [0, period].
        """
        if self.duty >= 1.0 or self.p_on == self.p_off:
            return [(0.0, self.period, self.average())]
        return [(0.0, self.on_time(), self.p_on), (self.on_time(), self.period, self.p_off)]

    def as_table(self):
        """!
        @brief The same wave as a TableProfile (used to export it to CSV).
        @return TableProfile.
        """
        iv = self.intervals()
        return TableProfile([a for a, _, _ in iv] + [iv[-1][1]], [p for _, _, p in iv], True)

    def validate(self):
        """!
        @brief Check the parameters.
        @throws ValueError If the period or duty are out of range or the powers are negative or inverted.
        """
        if not self.period > 0:
            raise ValueError("the period of a square wave must be positive")
        if not 0.0 < self.duty <= 1.0:
            raise ValueError("the duty cycle must be in (0, 1]")
        if self.p_on < 0 or self.p_off < 0 or self.p_off > self.p_on:
            raise ValueError("powers must satisfy 0 <= P_off <= P_on")

    def cumulative(self, t):
        """!
        @brief Energy delivered from t = 0 to t (exact, piecewise linear in t).
        @param t Time or array of times in seconds (>= 0).
        @return Energy in joules, same shape as t.
        """
        t = np.asarray(t, dtype=float)
        k = np.floor(t / self.period)
        r = t - k * self.period
        return self.p_off * t + (self.p_on - self.p_off) * (k * self.on_time() + np.minimum(r, self.on_time()))

    def mean_power(self, t0, t1):
        """!
        @brief Mean power over the interval [t0, t1], exact even when an edge falls inside it.
        @param t0 Start time(s) in seconds.
        @param t1 End time(s) in seconds (> t0).
        @return Mean power in watts (array if the inputs are arrays).
        """
        return (self.cumulative(t1) - self.cumulative(t0)) / (np.asarray(t1, dtype=float) - t0)


@dataclass
class TableProfile:
    """!
    @brief Power of a heater as a table of constant-power stretches (from a CSV file or typed).
    @details times has n + 1 increasing values starting at 0 and powers has n values: the power is powers[i] from
             times[i] to times[i + 1]. With repeat the table repeats every times[-1] seconds (a periodic load);
             without it the profile runs once and the last power is held afterwards (a mission or start-up profile).
    """
    times: List[float]                          # Breakpoints (s), n + 1 values, times[0] = 0
    powers: List[float]                         # Power of each stretch (W), n values
    repeat: bool = True                         # Repeat every times[-1] s, or run once and hold the last power

    kind = "table"                              # Shape name used in files and reports

    @property
    def period(self):
        """!
        @brief Length of the table (the period when it repeats).
        @return Time in seconds.
        """
        return float(self.times[-1])

    def intervals(self):
        """!
        @brief The constant-power stretches.
        @return List of tuples (start s, end s, power W).
        """
        return [(float(self.times[i]), float(self.times[i + 1]), float(self.powers[i])) for i in range(len(self.powers))]

    def average(self):
        """!
        @brief Time-weighted mean power over the table.
        @return Power in watts.
        """
        t, p = np.asarray(self.times, float), np.asarray(self.powers, float)
        return float(np.sum(p * np.diff(t)) / (t[-1] - t[0]))

    def peak(self):
        """!
        @brief Highest power of the table.
        @return Power in watts.
        """
        return float(np.max(self.powers))

    def initial_power(self):
        """!
        @brief Power that defines the start state "steady state of the average": the average if it repeats, the first power if not.
        @return Power in watts.
        """
        return self.average() if self.repeat else float(self.powers[0])

    def shortest_feature(self):
        """!
        @brief Shortest constant-power stretch (limits the time step).
        @return Time in seconds.
        """
        return float(np.min(np.diff(np.asarray(self.times, float))))

    def as_table(self):
        """!
        @brief Itself (so any profile can be exported with as_table()).
        @return This TableProfile.
        """
        return self

    def validate(self):
        """!
        @brief Check the table.
        @throws ValueError If it has fewer than one stretch, does not start at 0, is not increasing, has negative powers
                or too many rows.
        """
        t, p = np.asarray(self.times, float), np.asarray(self.powers, float)
        if len(t) != len(p) + 1 or len(p) < 1:
            raise ValueError("a power table needs at least one stretch: n powers and n + 1 times")
        if len(p) > 200000:
            raise ValueError("a power table is limited to 200,000 stretches")
        if t[0] != 0.0:
            raise ValueError("the first time of a power table must be 0")
        if np.any(np.diff(t) <= 0):
            raise ValueError("the times of a power table must be strictly increasing")
        if np.any(p < 0) or not np.all(np.isfinite(p)):
            raise ValueError("the powers of a power table must be finite and not negative")

    def cumulative(self, t):
        """!
        @brief Energy delivered from t = 0 to t (exact).
        @param t Time or array of times in seconds (>= 0).
        @return Energy in joules, same shape as t.
        """
        tt = np.asarray(self.times, float)
        pp = np.asarray(self.powers, float)
        edges = np.concatenate([[0.0], np.cumsum(pp * np.diff(tt))])              # Energy at every breakpoint
        length, total = tt[-1], edges[-1]
        t = np.asarray(t, dtype=float)

        def inside(x):
            # Energy inside one pass of the table at time x in [0, length]
            i = np.clip(np.searchsorted(tt, x, side="right") - 1, 0, len(pp) - 1)
            return edges[i] + pp[i] * (x - tt[i])

        if self.repeat:
            k = np.floor(t / length)
            return k * total + inside(t - k * length)
        return np.where(t <= length, inside(np.minimum(t, length)), total + pp[-1] * (t - length))

    def mean_power(self, t0, t1):
        """!
        @brief Mean power over [t0, t1], exact even when a breakpoint falls inside it.
        @param t0 Start time(s) in seconds.
        @param t1 End time(s) in seconds (> t0).
        @return Mean power in watts.
        """
        return (self.cumulative(t1) - self.cumulative(t0)) / (np.asarray(t1, dtype=float) - t0)


@dataclass
class Heater:
    """!
    @brief Heat source spread uniformly over a polygon on one layer.
    """
    layer: int                                  # 0-based layer index
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    power: float                                # Dissipated power (W)
    name: str = ""                              # Optional label (for example the component name)
    theta: float = 0.0                          # Junction-to-pad resistance (K/W), worst case: all the power enters the board; 0 = plain source
    profile: Optional[object] = None            # SquareWave or TableProfile; None = constant power
    tj_max: float = 0.0                         # Maximum junction temperature (degC); 0 = no limit
    psi_jb: float = 0.0                         # Junction-to-board characterisation parameter (K/W) for the ring-temperature estimate; 0 = not used
    power_tc: float = 0.0                       # Temperature coefficient of the power (1/K): P = P0 (1 + tc (Tj - 25 degC)); 0 = constant power
    theta_jc_top: float = 0.0                   # Junction-to-case (top) resistance (K/W) of the top path; used only with theta_sa
    theta_sa: float = 0.0                       # Heatsink-to-ambient resistance (K/W) on top of the package; 0 = no top path (worst case)
    interface: float = 0.0                      # Interface between package top and heatsink (K cm2/W, over the footprint area); 0 = perfect contact

    def top_resistance(self):
        """!
        @brief Total resistance of the top path, junction to ambient.
        @details theta_jc_top + interface / footprint area + theta_sa, in series; the path exists only for a part with a junction
                 resistance theta and a heatsink resistance theta_sa.
        @return Resistance in K/W, or 0.0 when the heater has no top path.
        """
        if self.theta <= 0 or self.theta_sa <= 0:
            return 0.0
        area_cm2 = max(self.area() * 1e4, 1e-9)
        return self.theta_jc_top + self.interface / area_cm2 + self.theta_sa

    def average_power(self):
        """!
        @brief Mean power: the profile average, or the constant power.
        @return Power in watts.
        """
        return self.profile.average() if self.profile else self.power

    def peak_power(self):
        """!
        @brief Highest power: the on-state of the profile, or the constant power.
        @return Power in watts.
        """
        return self.profile.peak() if self.profile else self.power

    def initial_power(self):
        """!
        @brief Power whose steady state is the default start of a time simulation.
        @return The average power of a repeating profile, the first power of a one-shot profile, the constant power otherwise.
        """
        return self.profile.initial_power() if self.profile else self.power

    def set_profile(self, profile):
        """!
        @brief Attach a power profile; `power` is kept equal to its average so steady models need no change.
        @param profile A SquareWave, a TableProfile or None (constant power).
        """
        self.profile = profile
        if profile is not None:
            self.power = profile.average()

    def area(self):
        """!
        @brief Footprint area.
        @return Area in square metres.
        """
        return polygon_area(self.polygon)


@dataclass
class Via:
    """!
    @brief Plated through via connecting all layers.
    """
    x: float                                    # X position (m)
    y: float                                    # Y position (m)
    diameter: float                             # Finished hole diameter (m)
    filled: bool = False                        # True for a copper-filled via (solid rod)
    name: str = ""                              # Optional label

    def copper_area(self, plating):
        """!
        @brief Copper cross-section of the via.
        @param plating Barrel plating thickness in metres (ignored for a filled via).
        @return Area in square metres: annulus for a hollow barrel, full disc if filled.
        """
        r = self.diameter / 2.0
        if self.filled:
            return math.pi * r * r
        # Hollow barrel: outer disc minus the empty core (the plating cannot exceed the radius)
        r_in = max(r - plating, 0.0)
        return math.pi * (r * r - r_in * r_in)


# Metals for heatsinks and spreaders: (name, conductivity W/mK, volumetric heat capacity rho*cp J/m3K). Aluminium, copper, brass and stainless from
# the Ferrotec material table (204, 386, 111 and 13.8 W/mK; densities 2.71, 8.96, 8.49 and 8.01 g/cm3), carbon steel 54 W/mK from the Engineering
# ToolBox table (its heat capacity is a textbook value). The user can always type other numbers.
METALS = (("Aluminium", 204.0, 2.44e6), ("Copper", 386.0, 3.45e6), ("Brass", 111.0, 2.91e6), ("Carbon steel", 54.0, 3.85e6),
          ("Stainless steel 304", 14.4, 3.69e6))

# Interface materials between the board (or a package) and a metal: (name, conductivity W/mK, thickness mm). Assumed typical values inside the ranges
# found in the literature (grease 7-20 um at best and 1-5 W/mK in practice, gap pads 1-6 W/mK and 0.5-1.2 mm); the resistance per area is t/k. Measured totals
# (ASTM D5470, Electronics Cooling 2014): Arctic Silver 5 paste 0.31 K cm2/W at 23.5 um, a ceramic paste 0.41, a 1.6 mm gap pad 12; so k here is an apparent value that includes the two contact resistances.
INTERFACES = (("Thermal paste, good (measured 0.3 K·cm²/W)", 1.5, 0.05), ("Paste, typical default (2 W/mK, 100 µm)", 2.0, 0.10),
              ("Soft gap pad (3 W/mK, 0.5 mm)", 3.0, 0.5), ("Gap pad (1 W/mK, 0.5 mm)", 1.0, 0.5), ("Hard gap pad (1 W/mK, 1 mm)", 1.0, 1.0))


# Typical junction-to-pad resistances by package family, K/W: indicative ranges from web summaries of vendor notes, NOT from a datasheet (QFN 2-10,
# power QFN 1-5, DFN 5-15, D2PAK 0.5-1, TO-220 1-2, SOT-223 junction to tab about 15; the SMA diode 20 is the SS12 datasheet value; the 0603 resistor
# is derived from a 0.1 W rating at 70 degC and a 170 degC limit). To be replaced by the datasheet value whenever there is one.
PACKAGE_THETA = (("QFN / exposed pad", 5.0), ("Power QFN", 3.0), ("DFN", 10.0), ("D2PAK / TO-263", 0.75), ("TO-220", 1.5),
                 ("SOT-223 (junction to tab)", 15.0), ("SMA / SMB / SMC diode (junction to terminal)", 20.0), ("Chip resistor 0603 (derived from its rating)", 1000.0))


@dataclass
class Heatsink:
    """!
    @brief Extra cooling over a polygon of an outer surface: a plain coefficient, or a metal block attached to the board.
    @details With thickness 0 the heatsink only adds h_extra to the board face inside the polygon. With a thickness it is a **metal
             block** pressed on the face through an interface (a gap pad or paste): the heat flows from the board copper into the
             block only where the block overlaps copper (the intersection of the planes), spreads sideways in the metal, is stored
             in its mass and leaves through the block's exposed surface with the coefficient of the board face plus h_extra.
    """
    layer: int                                  # 0-based layer index (must be 0 or layers-1)
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    h_extra: float                              # Added coefficient (W/m2K)
    name: str = ""                              # Optional label
    thickness: float = 0.0                      # Metal block thickness (m); 0 = a plain coefficient, no block
    k: float = 204.0                            # Conductivity of the block (W/mK); aluminium 204, copper 386
    rho_cp: float = 2.44e6                      # Volumetric heat capacity of the block (J/m3K); aluminium 2.44e6, copper 3.45e6
    contact_r: float = 5.0e-4                   # Interface resistance between the board and the block (m2K/W): pad thickness / k

    def is_block(self):
        """!
        @brief True if the heatsink is a metal block (it has a thickness).
        @return Boolean.
        """
        return self.thickness > 0.0


@dataclass
class Problem:
    """!
    @brief Complete thermal problem: board plus its elements.
    """
    board: Board
    zones: List[Zone] = field(default_factory=list)
    heaters: List[Heater] = field(default_factory=list)
    vias: List[Via] = field(default_factory=list)
    heatsinks: List[Heatsink] = field(default_factory=list)
    name: str = "board"

    def total_power(self):
        """!
        @brief Sum of all heater powers (the average for heaters with a profile).
        @return Power in watts.
        """
        return float(sum(h.power for h in self.heaters))

    def has_profiles(self):
        """!
        @brief True if at least one heater has a power profile.
        @return bool.
        """
        return any(h.profile is not None for h in self.heaters)

    def steady_copy(self, mode="average"):
        """!
        @brief Copy of the problem whose heater powers are the ones the steady-state models should use.
        @param mode "average" (mean power of every profile) or "peak" (on-state power, a worst-case bound).
        @return A new Problem; profiles are kept on the copy.
        @throws ValueError If the mode is unknown.
        """
        if mode not in ("average", "peak"):
            raise ValueError("steady power mode must be 'average' or 'peak'")
        p = copy.deepcopy(self)
        for h in p.heaters:
            h.power = h.peak_power() if mode == "peak" else h.average_power()
        return p

    def validate(self):
        """!
        @brief Validate the board and the element references.
        @throws ValueError On a bad layer index, negative power or heatsink on an inner layer.
        """
        self.board.validate()
        n = self.board.layers
        for e in list(self.zones) + list(self.heaters) + list(self.heatsinks):
            if not 0 <= e.layer < n:
                raise ValueError(f"element on layer {e.layer + 1} but the board has {n} layers")
        for h in self.heaters:
            if h.power < 0:
                raise ValueError("heater power must be >= 0")
            if h.theta < 0 or h.tj_max < 0 or h.psi_jb < 0 or not -0.05 <= h.power_tc <= 0.05:
                raise ValueError("a heater needs theta, tj_max and psi_jb >= 0 and a power temperature coefficient between -5 and 5 %/K")
            if h.theta_jc_top < 0 or h.theta_sa < 0 or h.interface < 0:
                raise ValueError("theta_jc_top, theta_sa and the interface resistance must be >= 0")
            if h.profile is not None:
                h.profile.validate()
        for s in self.heatsinks:
            if s.layer not in (0, n - 1):
                raise ValueError("a heatsink must be on the top or the bottom layer")
            if s.thickness < 0 or s.k <= 0 or s.rho_cp <= 0 or s.contact_r < 0 or s.h_extra < 0:
                raise ValueError("a heatsink needs h_extra, thickness and contact resistance >= 0 and k, heat capacity > 0")

    # ---------------------------------------------------------------- builder API (mm, layer 1 = top)
    @classmethod
    def new(cls, width_mm=100.0, height_mm=100.0, layers=2, thickness_mm=1.6, copper_um=35.0,
            name="board", **board_options):
        """!
        @brief Create an empty board using millimetres and micrometres.
        @param width_mm Board width in mm.
        @param height_mm Board height in mm.
        @param layers Number of copper layers.
        @param thickness_mm Total thickness in mm.
        @param copper_um Copper thickness per layer in micrometres.
        @param name Project name.
        @param board_options Any other Board field (ambient, h_top, h_bottom, h_side, via_plating, materials).
        @return A new Problem without elements.
        """
        board = Board(width=width_mm / 1000.0, height=height_mm / 1000.0,
                      thickness=thickness_mm / 1000.0, layers=layers,
                      copper_thickness=[copper_um * 1e-6] * layers, **board_options)
        return cls(board=board, name=name)

    @staticmethod
    def _shape_m(rect, polygon):
        """!
        @brief Convert a rectangle (x0, y0, x1, y1) or a polygon, both in mm, to a metre polygon.
        @param rect Tuple (x0, y0, x1, y1) in mm or None.
        @param polygon List of [x, y] in mm or None.
        @return Array (n, 2) in metres.
        @throws ValueError If neither or both shapes are given.
        """
        if (rect is None) == (polygon is None):
            raise ValueError("give exactly one of rect=(x0, y0, x1, y1) or polygon=[[x, y], ...]")
        if rect is not None:
            x0, y0, x1, y1 = rect
            polygon = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
        return np.asarray(polygon, dtype=float) / 1000.0

    def add_zone(self, layer, rect=None, polygon=None, fill=1.0, name=""):
        """!
        @brief Add a copper zone (layer 1 = top, geometry in mm).
        @param layer 1-based layer number.
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param polygon Polygon [[x, y], ...] in mm.
        @param fill Copper fill fraction (0..1).
        @param name Optional label.
        @return self, so calls can be chained.
        """
        self.zones.append(Zone(layer - 1, self._shape_m(rect, polygon), fill, name))
        return self

    def add_full_copper(self, layers=None, fill=1.0):
        """!
        @brief Add a full-board copper plane on the given layers.
        @param layers Iterable of 1-based layers (default: all layers).
        @param fill Copper fill fraction.
        @return self.
        """
        w, h = self.board.width * 1000.0, self.board.height * 1000.0
        for l in (layers if layers is not None else range(1, self.board.layers + 1)):
            self.add_zone(l, rect=(0, 0, w, h), fill=fill, name=f"plane L{l}")
        return self

    def add_heater(self, layer, power, rect=None, polygon=None, name="", theta=0.0, profile=None, tj_max=0.0, psi_jb=0.0, power_tc=0.0,
                   theta_jc_top=0.0, theta_sa=0.0, interface=0.0):
        """!
        @brief Add a heat source (layer 1 = top, geometry in mm, power in W).
        @param layer 1-based layer number.
        @param power Dissipated power in watts.
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param polygon Polygon [[x, y], ...] in mm.
        @param name Optional label (for example the component).
        @param theta Junction-to-pad resistance in K/W (the datasheet's junction-to-bottom, junction-to-terminal or junction-to-case number
               of a power part; adds the junction temperature to the report, worst case: all the power enters the board).
        @param profile Optional SquareWave; the heater power is then its average and `power` is ignored.
        @param tj_max Maximum junction temperature in degC (0 = none): the report gives the margin and the power limit.
        @param psi_jb Junction-to-board characterisation parameter in K/W (0 = none): the report adds Tj = ring temperature + psi P.
        @param power_tc Temperature coefficient of the power in 1/K (0 = constant); P = P0 (1 + tc (Tj - 25 degC)) is solved with the board.
        @param theta_jc_top Junction-to-case (top) resistance in K/W of the top path (used only with theta_sa).
        @param theta_sa Resistance in K/W from the heatsink on top of the package to the ambient (0 = no top path: all the power enters the board).
        @param interface Interface between package and heatsink in K cm2/W, divided by the footprint area (0 = perfect contact).
        @return self.
        """
        h = Heater(layer - 1, self._shape_m(rect, polygon), float(power), name, theta, None, float(tj_max), float(psi_jb), float(power_tc),
                   float(theta_jc_top), float(theta_sa), float(interface))
        h.set_profile(profile)
        self.heaters.append(h)
        return self

    def set_outline(self, polygon):
        """!
        @brief Give the board a non-rectangular outline (None restores the full rectangle).
        @details The polygon lies inside the width x height box of the board (the bounding box is NOT changed); the area outside it is not board: no
                 copper, no heat, no heat loss. The FVM, FDM and 3D solid solve any outline; the lumped and analytic models need a rectangle.
        @param polygon List of [x, y] in mm, or None.
        @return self.
        """
        self.board.outline = None if polygon is None else np.asarray(polygon, dtype=float) / 1000.0
        return self

    def add_via(self, x, y, diameter=0.3, filled=False, name=""):
        """!
        @brief Add one via (mm).
        @param x X position in mm.
        @param y Y position in mm.
        @param diameter Finished hole diameter in mm.
        @param filled True for a copper-filled via.
        @param name Optional label.
        @return self.
        """
        self.vias.append(Via(x / 1000.0, y / 1000.0, diameter / 1000.0, filled, name))
        return self

    def add_via_array(self, rect, nx, ny, diameter=0.3, filled=False):
        """!
        @brief Add a regular nx x ny array of vias, centred in a rectangle.
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param nx Vias along x.
        @param ny Vias along y.
        @param diameter Finished hole diameter in mm.
        @param filled True for copper-filled vias.
        @return self.
        """
        x0, y0, x1, y1 = rect
        # Vias sit at the centres of an nx x ny grid of equal cells, so the array is symmetric in the rectangle
        for i in range(nx):
            for j in range(ny):
                self.add_via(x0 + (i + 0.5) * (x1 - x0) / nx, y0 + (j + 0.5) * (y1 - y0) / ny, diameter, filled)
        return self

    def add_heatsink(self, layer, h_extra, rect=None, polygon=None, name="", thickness_mm=0.0, k=204.0, rho_cp=2.44e6,
                 contact_r=5.0e-4):
        """!
        @brief Add a heatsink: extra heat transfer coefficient on an outer surface, optionally a metal block (mm, W/m2K).
        @param layer 1 (top) or the last layer (bottom).
        @param h_extra Added coefficient in W/m2K (for a block: extra over the coefficient of the board face).
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param polygon Polygon [[x, y], ...] in mm.
        @param name Optional label.
        @param thickness_mm Thickness of the metal block in mm (0 = no block, only the coefficient).
        @param k Conductivity of the block in W/mK.
        @param rho_cp Volumetric heat capacity of the block in J/m3K.
        @param contact_r Interface resistance in m2K/W (pad thickness divided by its conductivity).
        @return self.
        """
        self.heatsinks.append(Heatsink(layer - 1, self._shape_m(rect, polygon), float(h_extra), name, thickness_mm / 1000.0,
                               float(k), float(rho_cp), float(contact_r)))
        return self


# --------------------------------------------------------------------------- JSON readers

def _poly_mm(points):
    """!
    @brief Convert a polygon in millimetres to a metre array.
    @param points List of [x_mm, y_mm].
    @return Array of shape (n, 2) in metres.
    """
    return np.asarray(points, dtype=float) / 1000.0


def problem_from_dict(data, validate=True):
    """!
    @brief Build a Problem from the native JSON structure (millimetres, 1-based layers).
    @param data Dict with the keys board, zones, heaters, vias and heatsinks (older files call the last one "sinks", still accepted).
    @param validate If False, skip the consistency check (used to restore undo snapshots).
    @return A Problem (validated unless validate is False).
    """
    b = data["board"]
    layers = int(b.get("layers", 2))
    cu = b.get("copper_thickness_mm", 0.035)
    # Accept a single value or a list with one value per layer
    cu_list = [float(c) / 1000.0 for c in (cu if isinstance(cu, list) else [cu] * layers)]
    mat = Materials(
        k_copper=b.get("k_copper", 385.0),
        k_fr4_through=b.get("k_fr4_through", 0.3),
        k_fr4_inplane=b.get("k_fr4_inplane", 0.9),
        rho_copper=b.get("rho_copper", 8960.0),
        cp_copper=b.get("cp_copper", 385.0),
        rho_fr4=b.get("rho_fr4", 1850.0),
        cp_fr4=b.get("cp_fr4", 900.0),
    )
    board = Board(
        width=b["width_mm"] / 1000.0,
        height=b["height_mm"] / 1000.0,
        thickness=b.get("thickness_mm", 1.6) / 1000.0,
        layers=layers,
        copper_thickness=cu_list,
        ambient=b.get("ambient_c", 25.0),
        h_top=b.get("h_top", 10.0),
        h_bottom=b.get("h_bottom", 15.0),
        h_side=b.get("h_side", 10.0),
        via_plating=b.get("via_plating_mm", 0.025) / 1000.0,
        h_mode=b.get("h_mode", "manual"),
        emissivity_top=b.get("emissivity_top", 0.9),
        emissivity_bottom=b.get("emissivity_bottom", 0.9),
        air_speed=b.get("air_speed_m_per_s", 0.0),
        orientation=b.get("orientation", "horizontal"),
        h_calibration=b.get("h_calibration", 1.0),
        materials=mat,
        outline=_poly_mm(b["outline_mm"]) if b.get("outline_mm") else None,
        dielectrics=[Dielectric(float(d["thickness_mm"]) / 1000.0, d.get("name", "FR-4 (standard)"), float(d.get("k_through", 0.3)),
                                float(d.get("k_inplane", 0.9)), float(d.get("rho", 1850.0)), float(d.get("cp", 900.0)))
                     for d in b["dielectrics"]] if "dielectrics" in b else None,
    )
    prob = Problem(board=board, name=data.get("name", "board"))
    for z in data.get("zones", []):
        prob.zones.append(Zone(z["layer"] - 1, _poly_mm(z["polygon_mm"]), z.get("fill", 1.0), z.get("name", "")))
    for h in data.get("heaters", []):
        # "theta_jb_k_per_w" is the key of files saved before the junction resistance was renamed
        heater = Heater(h["layer"] - 1, _poly_mm(h["polygon_mm"]), float(h["power_w"]), h.get("name", ""),
                        float(h.get("theta_k_per_w", h.get("theta_jb_k_per_w", 0.0))), None, float(h.get("tj_max_c", 0.0)),
                        float(h.get("psi_jb_k_per_w", 0.0)), float(h.get("power_tc_per_k", 0.0)),
                        float(h.get("theta_jc_top_k_per_w", 0.0)), float(h.get("theta_sa_k_per_w", 0.0)), float(h.get("interface_kcm2_per_w", 0.0)))
        if "profile" in h:
            heater.set_profile(_profile_from_dict(h["profile"]))
        prob.heaters.append(heater)
    for v in data.get("vias", []):
        prob.vias.append(Via(v["x_mm"] / 1000.0, v["y_mm"] / 1000.0,
                             v.get("diameter_mm", 0.3) / 1000.0, v.get("filled", False), v.get("name", "")))
    for s in data.get("heatsinks", data.get("sinks", [])):    # "sinks" is the key of files saved before the rename
        prob.heatsinks.append(Heatsink(s["layer"] - 1, _poly_mm(s["polygon_mm"]), float(s["h_extra"]), s.get("name", ""),
                               float(s.get("thickness_mm", 0.0)) / 1000.0, float(s.get("k_w_per_mk", 204.0)),
                               float(s.get("rho_cp_j_per_m3k", 2.44e6)), float(s.get("contact_r_m2k_per_w", 5.0e-4))))
    if validate:
        prob.validate()
    return prob


def problem_from_legacy(json_config):
    """!
    @brief Build a Problem from the json_config used by the original graphical editor.
    @details The editor stores element points in canvas pixels; they are mapped to millimetres
             with pcb_corners and the y axis is flipped so y = 0 is the bottom edge. The legacy
             convection_h_global becomes the edge coefficient.
    @param json_config Dict with pcb_params and elements.
    @return A validated Problem.
    """
    p = json_config["pcb_params"]
    w, h = p["width"], p["height"]
    (x0, y0), (x1, y1) = p.get("pcb_corners", [[0, 0], [w, h]])
    layers = int(p["layers"])

    def to_m(pt):
        # Pixel -> millimetre with the y axis inverted, then millimetre -> metre
        mx = (pt[0] - x0) / (x1 - x0) * w
        my = h - (pt[1] - y0) / (y1 - y0) * h
        return [mx / 1000.0, my / 1000.0]

    board = Board(
        width=w / 1000.0, height=h / 1000.0, thickness=p["thickness"] / 1000.0, layers=layers,
        copper_thickness=[p["copper_thickness"] / 1000.0] * layers,
        ambient=p["ambient_temp_global"],
        h_top=p["convection_h_top"], h_bottom=p["convection_h_bottom"],
        h_side=p["convection_h_global"] if str(p.get("boundary_mode", "Convective")).lower() == "convective" else None,
        materials=Materials(k_copper=p["copper_conductivity"], k_fr4_through=p["fr4_conductivity"],
                            k_fr4_inplane=p["fr4_conductivity"] * 3.0),
    )
    prob = Problem(board=board, name="legacy")
    for e in json_config.get("elements", []):
        pts = np.asarray([to_m(q) for q in e["points"]])
        layer = int(e.get("layer", 1)) - 1
        t = e["type"]
        if t == "Zone":
            prob.zones.append(Zone(layer, pts))
        elif t == "Heater":
            prob.heaters.append(Heater(layer, pts, float(e["power"])))
        elif t == "Sink":
            prob.heatsinks.append(Heatsink(layer, pts, float(e["htc_extra"])))
        elif t == "Via":
            prob.vias.append(Via(pts[0][0], pts[0][1], e["diameter"] / 1000.0))
    prob.validate()
    return prob


def load_problem(path):
    """!
    @brief Load a problem from a JSON file in either the native or the legacy format.
    @param path Path of the JSON file.
    @return A validated Problem.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # The legacy editor format is recognised by its pcb_params key
    if "pcb_params" in data:
        return problem_from_legacy(data)
    return problem_from_dict(data)


def reference_problem(power=5.0, layers=2, heater_mm=20.0, full_copper=True):
    """!
    @brief The reference board used by the documentation and the tests.
    @details 100 x 100 mm, 1.6 mm, 35 um copper on every layer, a square heater in the centre
             of the top layer and full copper planes.
    @param power Heater power in watts.
    @param layers Number of copper layers.
    @param heater_mm Heater side length in millimetres.
    @param full_copper If True, every layer has a full-board copper plane.
    @return A validated Problem.
    """
    data = {
        "name": "reference",
        "board": {"width_mm": 100, "height_mm": 100, "thickness_mm": 1.6, "layers": layers,
                  "copper_thickness_mm": 0.035},
        "heaters": [{"layer": 1, "power_w": power, "polygon_mm": [
            [50 - heater_mm / 2, 50 - heater_mm / 2], [50 + heater_mm / 2, 50 - heater_mm / 2],
            [50 + heater_mm / 2, 50 + heater_mm / 2], [50 - heater_mm / 2, 50 + heater_mm / 2]]}],
    }
    if full_copper:
        data["zones"] = [{"layer": l + 1, "polygon_mm": [[0, 0], [100, 0], [100, 100], [0, 100]]}
                         for l in range(layers)]
    return problem_from_dict(data)


def _profile_to_dict(profile):
    """!
    @brief Serialise a power profile.
    @param profile SquareWave or TableProfile.
    @return Dict with a "type" key.
    """
    if profile.kind == "table":
        return {"type": "table", "times_s": [float(x) for x in profile.times],
                "power_w": [float(x) for x in profile.powers], "repeat": bool(profile.repeat)}
    return {"type": "square", "p_on_w": profile.p_on, "p_off_w": profile.p_off, "period_s": profile.period,
            "duty": profile.duty}


def _profile_from_dict(w):
    """!
    @brief Read a power profile (files without "type" are square waves, as written by version 2.1.0).
    @param w Dict from _profile_to_dict.
    @return SquareWave or TableProfile.
    """
    if w.get("type") == "table":
        return TableProfile([float(x) for x in w["times_s"]], [float(x) for x in w["power_w"]], bool(w.get("repeat", True)))
    return SquareWave(float(w["p_on_w"]), float(w["period_s"]), float(w["duty"]), float(w.get("p_off_w", 0.0)))


def problem_to_dict(prob):
    """!
    @brief Serialise a Problem to the native JSON structure (millimetres, 1-based layers).
    @param prob A Problem.
    @return Dict that problem_from_dict reads back to an equivalent problem.
    """
    b = prob.board
    m = b.materials

    def poly(p):
        return (np.asarray(p) * 1000.0).round(6).tolist()

    return {
        "name": prob.name,
        "board": {
            "width_mm": b.width * 1000.0, "height_mm": b.height * 1000.0,
            "thickness_mm": b.total_thickness() * 1000.0, "layers": b.layers,
            "copper_thickness_mm": [c * 1000.0 for c in b.copper_thickness],
            "ambient_c": b.ambient, "h_top": b.h_top, "h_bottom": b.h_bottom, "h_side": b.h_side,
            "via_plating_mm": b.via_plating * 1000.0,
            "h_mode": b.h_mode, "emissivity_top": b.emissivity_top, "emissivity_bottom": b.emissivity_bottom,
            "air_speed_m_per_s": b.air_speed, "orientation": b.orientation, "h_calibration": b.h_calibration,
            "k_copper": m.k_copper, "k_fr4_through": m.k_fr4_through, "k_fr4_inplane": m.k_fr4_inplane,
            "rho_copper": m.rho_copper, "cp_copper": m.cp_copper, "rho_fr4": m.rho_fr4, "cp_fr4": m.cp_fr4,
            **({"outline_mm": poly(b.outline)} if b.outline is not None else {}),
            **({"dielectrics": [{"thickness_mm": d.thickness * 1000.0, "name": d.name, "k_through": d.k_through, "k_inplane": d.k_inplane,
                                 "rho": d.rho, "cp": d.cp} for d in b.dielectrics]} if b.dielectrics is not None else {}),
        },
        "zones": [{"layer": z.layer + 1, "polygon_mm": poly(z.polygon), "fill": z.fill, "name": z.name}
                  for z in prob.zones],
        "heaters": [dict({"layer": h.layer + 1, "power_w": h.power, "polygon_mm": poly(h.polygon), "name": h.name,
                          "theta_k_per_w": h.theta},
                         **({"tj_max_c": h.tj_max} if h.tj_max else {}), **({"psi_jb_k_per_w": h.psi_jb} if h.psi_jb else {}),
                         **({"power_tc_per_k": h.power_tc} if h.power_tc else {}),
                         **({"theta_jc_top_k_per_w": h.theta_jc_top} if h.theta_jc_top else {}),
                         **({"theta_sa_k_per_w": h.theta_sa} if h.theta_sa else {}),
                         **({"interface_kcm2_per_w": h.interface} if h.interface else {}),
                         **({"profile": _profile_to_dict(h.profile)} if h.profile else {})) for h in prob.heaters],
        "vias": [{"x_mm": v.x * 1000.0, "y_mm": v.y * 1000.0, "diameter_mm": v.diameter * 1000.0,
                  "filled": v.filled, "name": v.name} for v in prob.vias],
        "heatsinks": [dict({"layer": s.layer + 1, "polygon_mm": poly(s.polygon), "h_extra": s.h_extra, "name": s.name},
                       **({"thickness_mm": s.thickness * 1000.0, "k_w_per_mk": s.k, "rho_cp_j_per_m3k": s.rho_cp,
                           "contact_r_m2k_per_w": s.contact_r} if s.is_block() else {})) for s in prob.heatsinks],
    }
