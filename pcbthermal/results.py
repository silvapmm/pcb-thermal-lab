"""!
@file results.py
@brief Result containers shared by the three solvers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class SteadyResult:
    """!
    @brief Steady-state solution of one model.
    @details Temperatures are in degC. T is None for models that do not resolve a field.
    """
    model: str                                   # "fvm", "lumped" or "analytic"
    ambient: float                               # Ambient temperature (degC)
    power_in: float                              # Total injected power (W)
    t_max: float                                 # Maximum temperature (degC)
    t_min: float                                 # Minimum temperature (degC)
    t_mean: float                                # Area-weighted mean temperature (degC)
    layer_mean: List[float]                      # Mean temperature of every layer (degC)
    t_max_location: Optional[tuple] = None       # (layer, x_m, y_m) of the hottest cell
    T: Optional[np.ndarray] = None               # Field of shape (layers, ny, nx), degC
    dx: float = 0.0                              # Cell size along x (m)
    dy: float = 0.0                              # Cell size along y (m)
    power_out: Dict[str, float] = field(default_factory=dict)  # Heat leaving by path (W)
    residual: float = 0.0                        # Relative residual of the linear system
    extras: Dict[str, float] = field(default_factory=dict)     # Model specific numbers
    arrays: Dict[str, np.ndarray] = field(default_factory=dict)  # Model specific profiles for plots
    warnings: List[str] = field(default_factory=list)          # Validity warnings for the user
    grid: str = "cells"                          # "cells": T holds cell values; "nodes": T holds values at grid points (FDM)

    def coords(self):
        """!
        @brief Positions of the samples of T along x and y.
        @return Tuple (xs, ys) in metres: cell centres for a cell field, grid points (starting at 0) for a node field.
        """
        ny, nx = self.T.shape[1:]
        off = 0.0 if self.grid == "nodes" else 0.5
        return (np.arange(nx) + off) * self.dx, (np.arange(ny) + off) * self.dy

    @property
    def delta_t(self):
        """!
        @brief Maximum temperature rise above ambient.
        @return Rise in kelvin.
        """
        return self.t_max - self.ambient

    @property
    def r_theta(self):
        """!
        @brief Thermal resistance from the hottest point to ambient.
        @return Resistance in K/W (0 if no power is injected).
        """
        return self.delta_t / self.power_in if self.power_in > 0 else 0.0

    @property
    def balance_error(self):
        """!
        @brief Relative energy-balance error, (power out - power in) / power in.
        @return Dimensionless error (0 means perfectly conservative).
        """
        if self.power_in <= 0 or not self.power_out:
            return 0.0
        return (sum(self.power_out.values()) - self.power_in) / self.power_in

    def summary(self):
        """!
        @brief Flat dictionary of the main numbers, ready for JSON or a table.
        @return Dict of floats and strings.
        """
        s = {
            "model": self.model,
            "power_in_w": self.power_in,
            "t_max_c": self.t_max,
            "t_mean_c": self.t_mean,
            "t_min_c": self.t_min,
            "delta_t_k": self.delta_t,
            "r_theta_k_per_w": self.r_theta,
            "energy_balance_error": self.balance_error,
            "residual": self.residual,
        }
        for i, t in enumerate(self.layer_mean):
            s[f"layer{i + 1}_mean_c"] = t
        for k, v in self.power_out.items():
            s[f"power_out_{k}_w"] = v
        s.update(self.extras)
        return s


@dataclass
class TransientResult:
    """!
    @brief Time history of a transient FVM run.
    """
    times: np.ndarray                            # Output times (s)
    t_max: np.ndarray                            # Maximum temperature at every output time (degC)
    t_mean: np.ndarray                           # Mean temperature at every output time (degC)
    frames: np.ndarray                           # Fields, shape (n_out, layers, ny, nx), degC
    steady_t_max: float                          # Steady-state maximum for reference (degC)
    ambient: float                               # Ambient temperature (degC)
    grid: str = "cells"                          # "cells" or "nodes": what the frames hold (nodes for the finite-difference model)

    def time_constant(self):
        """!
        @brief Time at which the maximum temperature rise reaches 63.2 % of the steady rise.
        @return Time in seconds, or nan if the run is too short to reach it.
        """
        target = self.ambient + 0.632 * (self.steady_t_max - self.ambient)
        above = np.where(self.t_max >= target)[0]
        if len(above) == 0 or above[0] == 0:
            return float("nan")
        k = above[0]
        # Linear interpolation between the two bracketing samples
        t0, t1 = self.times[k - 1], self.times[k]
        y0, y1 = self.t_max[k - 1], self.t_max[k]
        return float(t0 + (target - y0) / (y1 - y0) * (t1 - t0))
