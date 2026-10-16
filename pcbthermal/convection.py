"""!
@file convection.py
@brief Heat transfer coefficient of the board faces from correlations: natural and forced convection plus radiation.
@details Used when the board cooling mode is "computed" (the user does not type h). All functions use SI units and
         temperatures in degC at the interface. Sources and limits: docs/models.md section 5.
"""

import math

SIGMA = 5.670374419e-8          # Stefan-Boltzmann constant (W/m2K4)
G = 9.80665                     # Gravity (m/s2)
P_ATM = 101325.0                # Air pressure (Pa)
R_AIR = 287.05                  # Specific gas constant of air (J/kgK)
CP_AIR = 1007.0                 # Specific heat of air (J/kgK), within 1 % between 250 and 450 K


def air_properties(t_film_c):
    """!
    @brief Properties of dry air at atmospheric pressure (Sutherland-type fits, valid about 250 to 450 K).
    @param t_film_c Film temperature in degC.
    @return Dict with k (W/mK), nu (m2/s), alpha (m2/s), pr and beta (1/K).
    """
    t = t_film_c + 273.15
    mu = 1.458e-6 * t ** 1.5 / (t + 110.4)                              # Dynamic viscosity (Pa s)
    k = 2.648e-3 * t ** 1.5 / (t + 245.4 * 10.0 ** (-12.0 / t))         # Conductivity (W/mK)
    rho = P_ATM / (R_AIR * t)
    return {"k": k, "nu": mu / rho, "alpha": k / (rho * CP_AIR), "pr": mu * CP_AIR / k, "beta": 1.0 / t}


def rayleigh(delta_t, length, props):
    """!
    @brief Rayleigh number of a heated surface.
    @param delta_t Temperature difference between surface and air in kelvin (absolute value is used).
    @param length Characteristic length in metres.
    @param props Air properties from air_properties().
    @return Dimensionless Ra.
    """
    return G * props["beta"] * abs(delta_t) * length ** 3 / (props["nu"] * props["alpha"])


def h_natural_horizontal(t_surface, t_ambient, length, facing_up):
    """!
    @brief Natural convection coefficient of a horizontal plate.
    @details Hot surface facing up: Nu = 0.54 Ra^(1/4) up to Ra = 1e7, then 0.15 Ra^(1/3); facing down: Nu = 0.27 Ra^(1/4).
             The characteristic length is area over perimeter. A cold surface swaps up and down.
    @param t_surface Mean surface temperature in degC.
    @param t_ambient Air temperature in degC.
    @param length Characteristic length A/P in metres.
    @param facing_up True if the surface faces up.
    @return Tuple (h in W/m2K, Rayleigh number).
    """
    dt = t_surface - t_ambient
    props = air_properties(0.5 * (t_surface + t_ambient))
    ra = rayleigh(max(abs(dt), 1e-3), length, props)
    up = facing_up if dt >= 0 else not facing_up               # Buoyancy reverses for a surface colder than the air
    if up:
        nu = 0.54 * ra ** 0.25 if ra <= 1e7 else 0.15 * ra ** (1.0 / 3.0)
    else:
        nu = 0.27 * ra ** 0.25
    return nu * props["k"] / length, ra


def h_natural_vertical(t_surface, t_ambient, height):
    """!
    @brief Natural convection coefficient of a vertical plate (Churchill and Chu, full Ra range).
    @details Nu = (0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27))^2.
    @param t_surface Mean surface temperature in degC.
    @param t_ambient Air temperature in degC.
    @param height Plate height in metres.
    @return Tuple (h in W/m2K, Rayleigh number).
    """
    props = air_properties(0.5 * (t_surface + t_ambient))
    ra = rayleigh(max(abs(t_surface - t_ambient), 1e-3), height, props)
    nu = (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1.0 + (0.492 / props["pr"]) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2
    return nu * props["k"] / height, ra


def h_forced(t_surface, t_ambient, speed, length):
    """!
    @brief Forced convection coefficient of a flat plate parallel to the flow.
    @details Laminar Nu = 0.664 Re^(1/2) Pr^(1/3); above Re = 5e5 the mixed form Nu = (0.037 Re^(4/5) - 871) Pr^(1/3).
    @param t_surface Mean surface temperature in degC.
    @param t_ambient Air temperature in degC.
    @param speed Free-stream air speed in m/s (0 gives 0).
    @param length Plate length along the flow in metres.
    @return h in W/m2K.
    """
    if speed <= 0.0:
        return 0.0
    props = air_properties(0.5 * (t_surface + t_ambient))
    re = speed * length / props["nu"]
    nu = 0.664 * math.sqrt(re) * props["pr"] ** (1.0 / 3.0) if re < 5e5 else (0.037 * re ** 0.8 - 871.0) * props["pr"] ** (1.0 / 3.0)
    return nu * props["k"] / length


def h_radiation(t_surface, t_ambient, emissivity):
    """!
    @brief Linearised radiation coefficient to surroundings at the air temperature.
    @details h_r = eps sigma (Ts^2 + Ta^2)(Ts + Ta) with absolute temperatures. A view factor of 1 to surroundings at the
             ambient temperature is assumed (an enclosure or other hot boards would reduce it).
    @param t_surface Mean surface temperature in degC.
    @param t_ambient Surroundings temperature in degC.
    @param emissivity Hemispherical emissivity, 0 to 1.
    @return h in W/m2K.
    """
    ts, ta = t_surface + 273.15, t_ambient + 273.15
    return emissivity * SIGMA * (ts * ts + ta * ta) * (ts + ta)


def board_h(board, t_top, t_bottom):
    """!
    @brief Heat transfer coefficients of the top and bottom faces of a board from its cooling settings.
    @details Natural and forced convection are blended as (h_n^3 + h_f^3)^(1/3) (Churchill's rule for mixed convection),
             the calibration multiplier scales the convection only, and radiation is added. Orientation "horizontal" has the
             top face looking up; "vertical" uses the plate correlation with the board height for both faces.
    @param board Board with h_mode, emissivity_top, emissivity_bottom, air_speed, orientation and h_calibration.
    @param t_top Mean temperature of the top face in degC.
    @param t_bottom Mean temperature of the bottom face in degC.
    @return Tuple (h_top, h_bottom, info) with W/m2K and a dict of the parts (convection, radiation, Rayleigh numbers).
    """
    ta = board.ambient
    area, perim = board.width * board.height, 2.0 * (board.width + board.height)
    length = area / perim
    info = {}
    out = []
    for name, ts, eps, up in (("top", t_top, board.emissivity_top, True), ("bottom", t_bottom, board.emissivity_bottom, False)):
        if board.orientation == "vertical":
            hn, ra = h_natural_vertical(ts, ta, board.height)
        else:
            hn, ra = h_natural_horizontal(ts, ta, length, up)
        hf = h_forced(ts, ta, board.air_speed, board.width)
        hc = board.h_calibration * (hn ** 3 + hf ** 3) ** (1.0 / 3.0)
        hr = h_radiation(ts, ta, eps)
        info[name] = {"convection": hc, "radiation": hr, "rayleigh": ra, "natural": hn, "forced": hf}
        out.append(hc + hr)
    return out[0], out[1], info
