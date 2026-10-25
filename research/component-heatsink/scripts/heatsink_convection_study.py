"""!
@file heatsink_convection_study.py
@brief A heatsink known only by its sink-to-ambient resistance: fixed value, natural-convection scaling with the temperature rise, and forced convection factors.

@details Natural convection of a finned heatsink: power W = beta * dT^1.25, so the resistance dT/W scales as dT^-0.25 (correction factor 1.257 at 30 K against the catalogue
         value at 75 K; Alpha Novatech and Infineon AN-1057 style catalogues). Forced convection: the volumetric performance C = R * V (cm3 K/W) is 500-800 in natural
         convection, 150-250 at 1 m/s, 80-150 at 2.5 m/s and 50-80 at 5 m/s (Electronics Cooling, "How to select a heat sink"), i.e. factors of about 0.31, 0.18 and 0.10 on the
         natural value. Chain: Rja = Rjc + Rcs + Rsa. The study keeps the board coefficients constant (as chain_study.py).
         Forced air: the factor multiplies the catalogue value and the result is held fixed (a forced-convection coefficient hardly depends on the
         temperature rise). An earlier version also applied the natural-convection scaling (dT_ref/dT)^0.25 to the forced values, which made them 1.8 to
         2.0 times too high at the small rises of forced air (6.8, 4.4 and 2.7 K/W instead of 3.7, 2.2 and 1.2 K/W); corrected in the review.

Usage: python research/component-heatsink/scripts/heatsink_convection_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import component_study as cs                                          # noqa: E402
import chain_study as ch                                              # noqa: E402

FORCED = {"natural": 1.0, "1 m/s": 0.31, "2.5 m/s": 0.18, "5 m/s": 0.10}      # Ratios of the volumetric performance 200/650, 115/650, 65/650
R_PASTE = 0.5                                                                  # Default paste, K cm2/W


def top_heatsink(part, h, power, theta_ref, scaling, dt_ref=75.0, factor=1.0):
    """!
    @brief Junction temperature with a top heatsink whose resistance may depend on its own temperature rise.
    @param part Entry of component_study.PARTS.
    @param h Board coefficients (top, bottom) in W/m2K.
    @param power Dissipated power in W.
    @param theta_ref Catalogue sink-to-ambient resistance in K/W at the reference rise (natural) or as given (fixed).
    @param scaling "fixed" or "natural" (resistance proportional to the rise to the power -0.25).
    @param dt_ref Reference temperature rise of the catalogue value in K.
    @param factor Forced-convection factor applied to the natural value.
    @return Tuple (Tj in degC, sink resistance used in K/W, heat share through the top).
    """
    p = dict(part)
    p["p"] = power
    area_cm2 = part["w"] * part["h"] / 100.0
    r_sa = theta_ref * factor
    for _ in range(100):
        r = ch.chain(p, h, part["th"], part["thtop"] + R_PASTE / area_cm2 + r_sa, None)
        if scaling == "fixed":
            break
        d_sink = r["top"] * power * r_sa                               # Rise of the heatsink over the ambient
        new = theta_ref * factor * (dt_ref / max(d_sink, 1.0)) ** 0.25
        if abs(new - r_sa) < 1e-4:
            break
        r_sa = new
    return r["tj"], r_sa, r["top"]


def main():
    """!
    @brief Print the tables.
    """
    part = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]
    h = cs.run(part, 25.0)["h"]
    print("MOSFET, top heatsink 12 K/W catalogue value at a 75 K rise, default paste; fixed resistance against natural-convection scaling (Tj in degC, sink resistance in K/W)")
    print("| Power [W] | fixed 12 K/W | natural scaling: Tj | sink R used | heat through the top |\n| --: | --: | --: | --: | --: |")
    for pw in (0.5, 1.0, 2.0, 3.0, 4.0):
        fx = top_heatsink(part, h, pw, 12.0, "fixed")
        nt = top_heatsink(part, h, pw, 12.0, "natural")
        print(f"| {pw:g} | {fx[0]:.1f} | {nt[0]:.1f} | {nt[1]:.1f} | {100 * nt[2]:.0f} % |", flush=True)
    print("\nSame heatsink (12 K/W natural at a 75 K rise, 2 W) in forced convection (factors of the volumetric performance on the catalogue value, held fixed; natural row scaled with the rise)")
    print("| Air | sink R used [K/W] | Tj [degC] | heat through the top |\n| :-- | --: | --: | --: |")
    for name, f in FORCED.items():
        # Natural convection scales with the rise; forced air is the catalogue value times the factor, not scaled with the rise
        tj, r, share = top_heatsink(part, h, 2.0, 12.0, "natural" if f == 1.0 else "fixed", factor=f)
        print(f"| {name} | {r:.1f} | {tj:.1f} | {100 * share:.0f} % |", flush=True)
    print("\nSize to resistance (volumetric performance 500-800 cm3 K/W natural): heatsink volume for a given resistance")
    print("| Volume [cm3] | natural R [K/W] | 1 m/s | 2.5 m/s | 5 m/s |\n| --: | --: | --: | --: | --: |")
    for v in (5, 10, 20, 50):
        print(f"| {v} | {500 / v:.0f} to {800 / v:.0f} | {150 / v:.0f} to {250 / v:.0f} | {80 / v:.1f} to {150 / v:.1f} | {50 / v:.1f} to {80 / v:.1f} |")


if __name__ == "__main__":
    main()
