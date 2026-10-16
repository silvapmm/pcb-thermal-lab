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

import numpy as np

from .geometry import polygon_area


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
    materials: Materials = field(default_factory=Materials)

    def dielectric_thickness(self):
        """!
        @brief Thickness of one dielectric layer between two adjacent copper layers.
        @return Thickness in metres (0 for a single-layer board).
        """
        if self.layers < 2:
            return 0.0
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
        if min(self.width, self.height, self.thickness) <= 0:
            raise ValueError("board dimensions must be positive")
        if self.layers > 1 and self.dielectric_thickness() <= 0:
            raise ValueError("the copper layers do not fit inside the board thickness")
        if self.h_top < 0 or self.h_bottom < 0:
            raise ValueError("heat transfer coefficients must be >= 0")
        if self.h_top + self.h_bottom <= 0 and not self.h_side:
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
class Heater:
    """!
    @brief Heat source spread uniformly over a polygon on one layer.
    """
    layer: int                                  # 0-based layer index
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    power: float                                # Dissipated power (W)
    name: str = ""                              # Optional label (for example the component name)
    theta_jb: float = 0.0                       # Junction-to-board resistance (K/W); 0 = not used
    profile: Optional["SquareWave"] = None      # Power versus time; None = constant power

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
        return self.profile.p_on if self.profile else self.power

    def set_profile(self, profile):
        """!
        @brief Attach a power profile; `power` is kept equal to its average so steady models need no change.
        @param profile A SquareWave or None (constant power).
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


@dataclass
class Sink:
    """!
    @brief Extra heat transfer coefficient over a polygon of an outer surface.
    """
    layer: int                                  # 0-based layer index (must be 0 or layers-1)
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    h_extra: float                              # Added coefficient (W/m2K)
    name: str = ""                              # Optional label


@dataclass
class Problem:
    """!
    @brief Complete thermal problem: board plus its elements.
    """
    board: Board
    zones: List[Zone] = field(default_factory=list)
    heaters: List[Heater] = field(default_factory=list)
    vias: List[Via] = field(default_factory=list)
    sinks: List[Sink] = field(default_factory=list)
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
        @throws ValueError On a bad layer index, negative power or sink on an inner layer.
        """
        self.board.validate()
        n = self.board.layers
        for e in list(self.zones) + list(self.heaters) + list(self.sinks):
            if not 0 <= e.layer < n:
                raise ValueError(f"element on layer {e.layer + 1} but the board has {n} layers")
        for h in self.heaters:
            if h.power < 0:
                raise ValueError("heater power must be >= 0")
            if h.profile is not None:
                h.profile.validate()
        for s in self.sinks:
            if s.layer not in (0, n - 1):
                raise ValueError("a sink must be on the top or the bottom layer")

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

    def add_heater(self, layer, power, rect=None, polygon=None, name="", theta_jb=0.0, profile=None):
        """!
        @brief Add a heat source (layer 1 = top, geometry in mm, power in W).
        @param layer 1-based layer number.
        @param power Dissipated power in watts.
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param polygon Polygon [[x, y], ...] in mm.
        @param name Optional label (for example the component).
        @param theta_jb Junction-to-board resistance in K/W (adds a junction temperature to the report).
        @param profile Optional SquareWave; the heater power is then its average and `power` is ignored.
        @return self.
        """
        h = Heater(layer - 1, self._shape_m(rect, polygon), float(power), name, theta_jb)
        h.set_profile(profile)
        self.heaters.append(h)
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

    def add_sink(self, layer, h_extra, rect=None, polygon=None, name=""):
        """!
        @brief Add a sink: extra heat transfer coefficient on an outer surface (mm, W/m2K).
        @param layer 1 (top) or the last layer (bottom).
        @param h_extra Added coefficient in W/m2K.
        @param rect Rectangle (x0, y0, x1, y1) in mm.
        @param polygon Polygon [[x, y], ...] in mm.
        @param name Optional label.
        @return self.
        """
        self.sinks.append(Sink(layer - 1, self._shape_m(rect, polygon), float(h_extra), name))
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
    @param data Dict with the keys board, zones, heaters, vias and sinks.
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
        materials=mat,
    )
    prob = Problem(board=board, name=data.get("name", "board"))
    for z in data.get("zones", []):
        prob.zones.append(Zone(z["layer"] - 1, _poly_mm(z["polygon_mm"]), z.get("fill", 1.0), z.get("name", "")))
    for h in data.get("heaters", []):
        heater = Heater(h["layer"] - 1, _poly_mm(h["polygon_mm"]), float(h["power_w"]),
                        h.get("name", ""), float(h.get("theta_jb_k_per_w", 0.0)))
        if "profile" in h:
            w = h["profile"]
            heater.set_profile(SquareWave(float(w["p_on_w"]), float(w["period_s"]), float(w["duty"]),
                                          float(w.get("p_off_w", 0.0))))
        prob.heaters.append(heater)
    for v in data.get("vias", []):
        prob.vias.append(Via(v["x_mm"] / 1000.0, v["y_mm"] / 1000.0,
                             v.get("diameter_mm", 0.3) / 1000.0, v.get("filled", False), v.get("name", "")))
    for s in data.get("sinks", []):
        prob.sinks.append(Sink(s["layer"] - 1, _poly_mm(s["polygon_mm"]), float(s["h_extra"]), s.get("name", "")))
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
            prob.sinks.append(Sink(layer, pts, float(e["htc_extra"])))
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
            "thickness_mm": b.thickness * 1000.0, "layers": b.layers,
            "copper_thickness_mm": [c * 1000.0 for c in b.copper_thickness],
            "ambient_c": b.ambient, "h_top": b.h_top, "h_bottom": b.h_bottom, "h_side": b.h_side,
            "via_plating_mm": b.via_plating * 1000.0,
            "k_copper": m.k_copper, "k_fr4_through": m.k_fr4_through, "k_fr4_inplane": m.k_fr4_inplane,
            "rho_copper": m.rho_copper, "cp_copper": m.cp_copper, "rho_fr4": m.rho_fr4, "cp_fr4": m.cp_fr4,
        },
        "zones": [{"layer": z.layer + 1, "polygon_mm": poly(z.polygon), "fill": z.fill, "name": z.name}
                  for z in prob.zones],
        "heaters": [dict({"layer": h.layer + 1, "power_w": h.power, "polygon_mm": poly(h.polygon), "name": h.name,
                          "theta_jb_k_per_w": h.theta_jb},
                         **({"profile": {"p_on_w": h.profile.p_on, "p_off_w": h.profile.p_off,
                                         "period_s": h.profile.period, "duty": h.profile.duty}}
                            if h.profile else {})) for h in prob.heaters],
        "vias": [{"x_mm": v.x * 1000.0, "y_mm": v.y * 1000.0, "diameter_mm": v.diameter * 1000.0,
                  "filled": v.filled, "name": v.name} for v in prob.vias],
        "sinks": [{"layer": s.layer + 1, "polygon_mm": poly(s.polygon), "h_extra": s.h_extra, "name": s.name}
                  for s in prob.sinks],
    }
