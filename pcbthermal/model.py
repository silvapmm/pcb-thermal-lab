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


@dataclass
class Heater:
    """!
    @brief Heat source spread uniformly over a polygon on one layer.
    """
    layer: int                                  # 0-based layer index
    polygon: np.ndarray                         # Vertices (n, 2) in metres
    power: float                                # Dissipated power (W)

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
        @brief Sum of all heater powers.
        @return Power in watts.
        """
        return float(sum(h.power for h in self.heaters))

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
        for s in self.sinks:
            if s.layer not in (0, n - 1):
                raise ValueError("a sink must be on the top or the bottom layer")


# --------------------------------------------------------------------------- JSON readers

def _poly_mm(points):
    """!
    @brief Convert a polygon in millimetres to a metre array.
    @param points List of [x_mm, y_mm].
    @return Array of shape (n, 2) in metres.
    """
    return np.asarray(points, dtype=float) / 1000.0


def problem_from_dict(data):
    """!
    @brief Build a Problem from the native JSON structure (millimetres, 1-based layers).
    @param data Dict with the keys board, zones, heaters, vias and sinks.
    @return A validated Problem.
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
        prob.zones.append(Zone(z["layer"] - 1, _poly_mm(z["polygon_mm"]), z.get("fill", 1.0)))
    for h in data.get("heaters", []):
        prob.heaters.append(Heater(h["layer"] - 1, _poly_mm(h["polygon_mm"]), float(h["power_w"])))
    for v in data.get("vias", []):
        prob.vias.append(Via(v["x_mm"] / 1000.0, v["y_mm"] / 1000.0,
                             v.get("diameter_mm", 0.3) / 1000.0, v.get("filled", False)))
    for s in data.get("sinks", []):
        prob.sinks.append(Sink(s["layer"] - 1, _poly_mm(s["polygon_mm"]), float(s["h_extra"])))
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
        "zones": [{"layer": z.layer + 1, "polygon_mm": poly(z.polygon), "fill": z.fill} for z in prob.zones],
        "heaters": [{"layer": h.layer + 1, "power_w": h.power, "polygon_mm": poly(h.polygon)} for h in prob.heaters],
        "vias": [{"x_mm": v.x * 1000.0, "y_mm": v.y * 1000.0, "diameter_mm": v.diameter * 1000.0,
                  "filled": v.filled} for v in prob.vias],
        "sinks": [{"layer": s.layer + 1, "polygon_mm": poly(s.polygon), "h_extra": s.h_extra} for s in prob.sinks],
    }
