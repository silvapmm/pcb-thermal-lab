#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_forced_and_air_sources.py
@brief Do the program's air properties and its forced-convection law agree with Lienhard Table A.6 and with Yovanovich and Teertstra (2001)?

Question (README 9.1, plan study S0): (1) `convection.air_properties` against the three rows of Lienhard Table A.6 (book page 755) at 300, 350 and 400 K;
(2) `convection.h_forced` (laminar 0.664 Re^(1/2) Pr^(1/3) on the flow length) against the composite of Yovanovich and Teertstra (2001), eq 18,
Nu = (S*^n + (C Re^(1/2) Pr^(1/3))^n)^(1/n), with S* from eq 8 (S*_sqrtA = (1 + sqrt(L/W))^2 / sqrt(pi L/W), rewritten on L with S*_L = sqrt(L/W) S*_sqrtA),
n from eqs 24 and 25 (flow along the short side W: n = 1.42 - 0.28 log10(W/L), which is above 1.42 since W/L < 1; flow along the long side L: n = 1.42 - 0.45 log10(L/W))
and C = 0.742 (eq 17, linearised) or 0.664 (eq 12, the textbook value).  All on p 206 to 208 of the paper (PDF pages 2 to 4).
The paper's equations are transcribed here; eq 9 (L/W > 5) is not implemented (every case below has L/W <= 2).  The fit of n covers Re_L from 1 to 5000 (Table 2, p 208);
three of the five cases below (Re 6 079, 12 158 and 18 237) are past it, where the composite is its boundary-layer term.
Corrected by the review: the first version wrote eq 24 with log10(L/W) (sign of the logarithm reversed); no case below used that branch, so no printed number moved.

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_forced_and_air_sources.py   (about 1 s)
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import convection as cv  # noqa: E402

AMBIENT = 25.0                                              # degC
# Lienhard, A Heat Transfer Textbook, Table A.6 (p 755), air at 1 atm: T K, k W/mK, nu m2/s, Pr
LIENHARD_A6 = [(300, 0.0264, 1.575e-5, 0.707), (350, 0.0300, 2.069e-5, 0.702), (400, 0.0335, 2.613e-5, 0.699)]
# Forced cases: (flow length mm, width mm, speed m/s)
FORCED_CASES = [(100, 80, 0.2), (100, 80, 1.0), (100, 80, 3.0), (40, 30, 0.5), (200, 100, 1.0)]


def air_vs_table(rows=LIENHARD_A6):
    """!
    @brief Relative differences of the program's air properties from Lienhard Table A.6.
    @param rows  List of (T in K, k in W/mK, nu in m2/s, Pr) as printed.
    @return list of dict: T, dk, dnu, dpr (fractions, program/table - 1).
    """
    out = []
    for t_k, k, nu, pr in rows:
        p = cv.air_properties(t_k - 273.15)
        out.append(dict(T=t_k, dk=p["k"] / k - 1.0, dnu=p["nu"] / nu - 1.0, dpr=p["pr"] / pr - 1.0))
    return out


def yt_exponent(length, width):
    """!
    @brief Interpolation parameter n of Yovanovich and Teertstra (2001), eqs 24 and 25, for the flow along `length`.
    @param length  Flow length in m.
    @param width   Width across the flow in m.
    @return float n (dimensionless).
    """
    if length >= width:
        return 1.42 - 0.45 * math.log10(length / width)                         # eq 25: flow along the long side L, log10(L/W)
    return 1.42 - 0.28 * math.log10(length / width)                             # eq 24: flow along the short side W, log10(W/L) < 0


def yt_forced_h(length, width, speed, dt, c, ambient=AMBIENT):
    """!
    @brief Heat transfer coefficient of the Yovanovich-Teertstra (2001) composite, eq 18, for a plate with the flow along `length`.
    @param length  Flow length in m.
    @param width   Width across the flow in m.
    @param speed   Free-stream speed in m/s.
    @param dt      Surface minus ambient in K (air at the film temperature).
    @param c       Coefficient of the Re^(1/2) Pr^(1/3) term, 0.742 (eq 17) or 0.664 (eq 12).
    @param ambient Ambient in degC.
    @return float h in W/m2K.
    """
    p = cv.air_properties(ambient + dt / 2)
    lw = max(length, width) / min(length, width)
    s_sqrt_a = (1 + math.sqrt(lw)) ** 2 / math.sqrt(math.pi * lw)             # eq 8 (L/W <= 5)
    s_l = math.sqrt(length / width) * s_sqrt_a                                  # shape factor on the flow length
    n = yt_exponent(length, width)                                              # eqs 24 and 25
    re = speed * length / p["nu"]
    nu = (s_l ** n + (c * re ** 0.5 * p["pr"] ** (1 / 3)) ** n) ** (1 / n)
    return nu * p["k"] / length


def forced_vs_yt(cases=FORCED_CASES, dt=20.0):
    """!
    @brief The program's forced h against eq 18 with C = 0.742 and with C = 0.664.
    @param cases  List of (flow length mm, width mm, speed m/s).
    @param dt     Surface minus ambient in K.
    @return list of dict: case, re, h_prog, h_742, h_664, d_742, d_664 (fractions, program/YT - 1).
    """
    out = []
    for a, b, u in cases:
        h_prog = cv.h_forced(AMBIENT + dt, AMBIENT, u, a * 1e-3)
        p = cv.air_properties(AMBIENT + dt / 2)
        h742 = yt_forced_h(a * 1e-3, b * 1e-3, u, dt, 0.742)
        h664 = yt_forced_h(a * 1e-3, b * 1e-3, u, dt, 0.664)
        out.append(dict(case=(a, b, u), re=u * a * 1e-3 / p["nu"], h_prog=h_prog, h_742=h742, h_664=h664, d_742=h_prog / h742 - 1.0, d_664=h_prog / h664 - 1.0))
    return out


def main():
    """!
    @brief Print both tables.
    @return None.
    """
    print("1. air against Lienhard Table A.6 (program/table - 1)")
    for r in air_vs_table():
        print(f"  {r['T']} K  k {100 * r['dk']:+.1f} %  nu {100 * r['dnu']:+.1f} %  Pr {100 * r['dpr']:+.1f} %")
    print("2. forced convection, flow along the first side, dT 20 K: h program | YT eq 18 with 0.742 | with 0.664")
    for r in forced_vs_yt():
        a, b, u = r["case"]
        print(f"  {a}x{b} u {u}: Re {r['re']:.0f}  {r['h_prog']:.2f} | {r['h_742']:.2f} ({100 * r['d_742']:+.0f} %) | {r['h_664']:.2f} ({100 * r['d_664']:+.0f} %)")


if __name__ == "__main__":
    main()
