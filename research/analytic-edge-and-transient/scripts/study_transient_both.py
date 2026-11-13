#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient_both.py
@brief Question B and C: the time to 63 % of the Analytic (and Lumped) step response on boards with vias, a heatsink and both, against the FVM at 1 mm.

@details For 10 boards (plain, vias alone, heatsink alone under the part and beside it, both, 2 and 4 layers, edge coefficient) the unit-step response of the part
         is computed by the FVM (fvm.step_responses at 1 mm, the reference), the Lumped, the Analytic as in the program and the Analytic with the calibration variants
         of lib/calib_variants.py. Printed: steady resistance, time to 63 %, the largest difference of the whole curve (in percent of the steady resistance) and
         the error of the time to 63 % against the FVM.
         Run from the repository root: .venv/bin/python research/analytic-edge-and-transient/scripts/study_transient_both.py [--variants current,program,two,two_max]
         [--local 16,24] [--cell 1.0] [--calibrate-on all|vias]  ("program" is the v2.5.1 one-factor calibration, frozen in lib/analytic_v251.py; "current" is the live 2.6.0 local modal system; the review's run: --variants program --local 16 --cell 0.5 --calibrate-on vias)
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards26 as B          # noqa: E402
import calib_variants as cv   # noqa: E402
import local_modal as LM      # noqa: E402


def boards():
    """!
    @brief The ten boards of the study.
    @return List of (name, Problem).
    """
    pl, wv, ws = B.plain, B.with_vias, B.with_sink
    return [("plain 2L", pl()), ("1 via", wv(pl(), 1)), ("vias 4x4", wv(pl())), ("sink under", ws(pl())), ("sink beside", ws(pl(), 100.0, "side")),
            ("vias+sink under", ws(wv(pl()))), ("vias+sink beside", ws(wv(pl()), 100.0, "side")), ("plain 4L", pl(4)),
            ("4L vias+sink under", ws(wv(pl(4)), 300.0)), ("2L h_side 50 vias+sink", ws(wv(pl(h_side=50.0))))]


def curve_err(t_ref, z_ref, r_ref, t, z, r):
    """!
    @brief Largest difference of the normalised curves over log-spaced times.
    @param t_ref Times of the reference.
    @param z_ref Reference response (K/W).
    @param r_ref Reference steady resistance.
    @param t Times of the model.
    @param z Model response.
    @param r Model steady resistance.
    @return float Percent of the reference steady resistance (absolute K/W difference, not normalised by the model's own resistance).
    """
    tt = np.geomspace(max(t_ref[0], t[0]) * 2, min(t_ref[-1], t[-1]), 60)
    a = np.interp(np.log(tt), np.log(t_ref), z_ref)
    b = np.interp(np.log(tt), np.log(t), z)
    return 100.0 * float(np.abs(a - b).max()) / r_ref


def square_peak(t, z, period, duty=0.5, cycles=12):
    """!
    @brief Largest rise (K per W of peak power) of a unit square wave by superposition of the step response, in the last cycle.
    @param t Times of the response in seconds.
    @param z Unit-step response in K/W.
    @param period Period in seconds.
    @param duty Duty cycle.
    @param cycles Number of cycles.
    @return Tuple (maximum, minimum) of the rise in the last cycle in K per W.
    """
    def zz(x):
        """!
        @brief Step response at x (0 before the step, last value after the last sample).
        @param x Array of times.
        @return Array.
        """
        x = np.asarray(x, dtype=float)
        out = np.interp(np.log(np.maximum(x, t[0])), np.log(t), z, right=z[-1])
        out = np.where(x < t[0], z[0] * x / t[0], out)       # linear below the first sample
        return np.where(x <= 0.0, 0.0, out)
    tt = np.linspace((cycles - 1) * period, cycles * period, 400)
    resp = np.zeros_like(tt)
    for k in range(cycles):
        resp += zz(tt - k * period) - zz(tt - (k + duty) * period)
    return float(resp.max()), float(resp.min())


def main(argv=None):
    """!
    @brief Run the study.
    @param argv Arguments.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="program,two,two_max")
    ap.add_argument("--local", default="16,24", help="K of the local modal prototype (empty: none)")
    ap.add_argument("--cell", type=float, default=1.0)
    ap.add_argument("--calibrate-on", default="all", choices=("all", "vias"), help="factor of the local system on the whole tile matrix or on the vias only (review)")
    args = ap.parse_args(argv)
    variants = args.variants.split(",")
    print(f"{'board':24s} {'model':16s} {'R K/W':>7s} {'t63 s':>8s} {'t63 err %':>9s} {'curve max %':>11s}   square wave peak/swing error % at T = t63/2 and 2 t63")
    for name, p in boards():
        t, z, r = B.step(p, "fvm", args.cell)
        ref63 = B.t63(t, z[:1], r[:1])[0]
        print(f"{name:24s} {'FVM':16s} {r[0]:7.3f} {ref63:8.2f}")
        per = (0.5 * ref63, 2.0 * ref63)
        refsq = [square_peak(t, z[0], pp) for pp in per]
        rows = [("lumped", None)] + [("analytic", v) for v in variants] + [("local", int(k)) for k in args.local.split(",") if k]
        for model, v in rows:
            if model == "local":
                ti, zi, ri, _ = LM.step_local(p, args.cell, 300, v, calibrate_on=args.calibrate_on)
                label = f"local K{v}" + ("" if args.calibrate_on == "all" else " vias")
            else:
                if v:
                    cv.install(v)
                ti, zi, ri = B.step(p, model, args.cell)
                label = model if v is None else f"analytic/{v}"
            t63 = B.t63(ti, zi[:1], ri[:1])[0]
            sq = [square_peak(ti, zi[0], pp) for pp in per]
            swing = " ".join(f"{100 * (a[0] / b[0] - 1):+5.1f}/{100 * ((a[0] - a[1]) / (b[0] - b[1]) - 1):+5.1f}" for a, b in zip(sq, refsq))
            print(f"{'':24s} {label:16s} {ri[0]:7.3f} {t63:8.2f} {100 * (t63 / ref63 - 1):+9.1f} {curve_err(t, z[0], r[0], ti, zi[0], ri[0]):11.1f}   {swing}", flush=True)
            cv.install("program")


if __name__ == "__main__":
    main()
