#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_source_checks.py
@brief Do the formulas of the fin-channel study match the sources it could not open? Reproduces a published number of every source obtained in this folder.

@details Questions answered (the numbers printed here are the ones of README.md):
         A. Elenbaas (1942) parallel-plate data (Figure 11 of Yovanovich, Teertstra and Muzychka 2002, plot values) against the four correlations of the Waterloo review
            (equations 8, 20, 21, 22), the YTM composite (their equation 29) and the independent numerical channel of `research/fin-channel/lib/channel_bl.py`.
         B. Bar-Cohen, Iyengar and Kraus (2003): the array coefficient of its Figure 2 (52.4 W/m2K near 8 mm) and Figure 4 (198 W/m2K at s = t = 9 mm), the optimum spacing
            constant of its equation 17 (2.66) against the one recomputed from its equation 13 (2.7156), and the identity of its equation 13 with equation 21 of the review.
         C. Ostrach (1953) Table I against an independent solution of the similarity equations, and the Prandtl function of Churchill and Chu against both.
         D. Six measured short fin arrays on a horizontal base (ENCIT 2012, plot values) against the uniform coefficient the program gives its finned block (its fin
            ratio, imported from `pcbthermal.blocks`), the same coefficient on the real fins, and the correlations of Tari and Mehrtash (2013).
         Results go to `research/fin-channel-sources/out/source_checks.json` for `make_figures.py`.
Usage: .venv/bin/python research/fin-channel-sources/scripts/study_source_checks.py   (about 1 minute; the numerical channel takes most of it)
"""

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import sources as S                                                 # noqa: E402
import channel as ch                                                # noqa: E402
import channel_bl as bl                                             # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def rms_percent(a, b):
    """!
    @brief Root-mean-square of the relative difference (a - b) / b in percent.
    @param a Predicted values.
    @param b Reference values.
    @return Percent.
    """
    d = (np.asarray(a) - np.asarray(b)) / np.asarray(b)
    return 100.0 * float(np.sqrt(np.mean(d ** 2)))


def study_a(results):
    """!
    @brief A: Elenbaas data (plot) against the correlations.
    @param results Dict that receives the numbers.
    @return None.
    """
    ra, nu = S.elenbaas_data_from_fig11()
    names = {"Elenbaas (8)": ch.nu_elenbaas, "Churchill (20)": ch.nu_churchill, "Bar-Cohen-Rohsenow (21)": ch.nu_bcr, "Raithby-Hollands (22)": ch.nu_rh,
             "YTM (29, n=2)": S.ytm_parallel_plates_nu}
    print("A. Elenbaas (1942) parallel-plate data, plot values of Figure 11 of YTM (2002): %d points, Ra_b %.2g to %.2g" % (len(ra), ra.min(), ra.max()))
    rows = {}
    for key, f in names.items():
        pred = np.array([f(r) for r in ra])
        rows[key] = {"rms_percent": rms_percent(pred, nu), "mean_percent": 100.0 * float(np.mean((pred - nu) / nu)),
                     "rms_low": rms_percent(pred[ra < 100], nu[ra < 100]), "rms_high": rms_percent(pred[ra >= 100], nu[ra >= 100])}
        print("   %-26s rms %5.1f %%  mean %+5.1f %%   (Ra_b < 100: rms %4.1f %%, >= 100: %4.1f %%)" % (key, rows[key]["rms_percent"], rows[key]["mean_percent"],
                                                                                                         rows[key]["rms_low"], rows[key]["rms_high"]))
    # The independent numerical channel at the data's Rayleigh numbers (a subset: every 3rd point to keep the run short)
    idx = list(range(0, len(ra), 3))
    num = []
    for i in idx:
        num.append(bl.solve(float(ra[i]), n_y=100, n_x=300)["nu_b"])
    num = np.array(num)
    rows["numerical channel (Pr 0.71)"] = {"rms_percent": rms_percent(num, nu[idx]), "mean_percent": 100.0 * float(np.mean((num - nu[idx]) / nu[idx])), "n": len(idx)}
    print("   %-26s rms %5.1f %%  mean %+5.1f %%   (%d points)" % ("numerical channel", rows["numerical channel (Pr 0.71)"]["rms_percent"],
                                                                rows["numerical channel (Pr 0.71)"]["mean_percent"], len(idx)))
    # The two limits of the data: Ra_b <= 3: Nu / (Ra_b/24); Ra_b >= 1e3: Nu / Ra_b^(1/4)
    lo = ra < 3
    hi = ra > 2000
    print("   data / (Ra_b/24) for Ra_b < 3: mean %.3f (%d points); data / Ra_b^(1/4) for Ra_b > 2000: mean %.3f (%d points)" % (float(np.mean(nu[lo] / (ra[lo] / 24.0))), int(lo.sum()),
                                                                                                                        float(np.mean(nu[hi] / ra[hi] ** 0.25)), int(hi.sum())))
    # YTM equation 29 against equation 21 of the review over the whole range
    grid = np.logspace(-2, 6, 400)
    d = np.array([S.ytm_parallel_plates_nu(r) / ch.nu_bcr(r) - 1.0 for r in grid])
    print("   YTM eq. 29 against BCR eq. 21 (review), Ra_b 1e-2 to 1e6: %+.1f %% to %+.1f %%, at Ra_b 1: %+.1f %%, 100: %+.1f %%, 1e4: %+.1f %%" % (
        100 * d.min(), 100 * d.max(), 100 * (S.ytm_parallel_plates_nu(1.0) / ch.nu_bcr(1.0) - 1), 100 * (S.ytm_parallel_plates_nu(100.0) / ch.nu_bcr(100.0) - 1),
        100 * (S.ytm_parallel_plates_nu(1e4) / ch.nu_bcr(1e4) - 1)))
    results["A"] = {"ra": ra.tolist(), "nu": nu.tolist(), "rows": rows, "numerical_idx": idx, "numerical": num.tolist()}


def study_b(results):
    """!
    @brief B: the array of Bar-Cohen, Iyengar and Kraus (2003).
    @param results Dict that receives the numbers.
    @return None.
    """
    print("B. Bar-Cohen, Iyengar and Kraus (2003): 100 x 100 mm base, theta_b 25 K, k 200 W/mK, fins 45 mm high and 1 mm thick (Figure 2)")
    out = {"amb": {}}
    for amb in (20.0, 25.0, 45.0):
        so, ha = S.optimum_of_ha(25.0, 1e-3, 0.045, 0.1, 0.1, 200.0, amb)
        lm = S.bik_least_material(25.0, 9e-3, 0.1, 0.1, 200.0, amb)
        out["amb"][str(amb)] = {"s_opt_mm": so * 1e3, "ha_max": ha, "ha_s8": S.bik_array(25.0, 8e-3, 1e-3, 0.045, 0.1, 0.1, 200.0, amb)["ha"], "ha_lm": lm["ha"], "h_lm": lm["height"]}
        print("   ambient %2.0f degC: optimum spacing %.2f mm, h_a there %.2f W/m2K (paper: about 8 mm, 52.4); h_a(8 mm) %.2f; least-material s = t = 9 mm: H = %.0f mm, h_a = %.1f (paper: 198)" % (
            amb, so * 1e3, ha, out["amb"][str(amb)]["ha_s8"], lm["height"] * 1e3, lm["ha"]))
    # The paper's upper bound of 222 W/m2K "by extending the optimal plate-fin geometry to infinite height [24]" rests on reference 24 (not read) and is not reproduced here.
    # equation 17 against the optimum recomputed from equation 13
    p = ch.air(45.0 + 12.5)
    eta = S.bik_array(25.0, 8e-3, 1e-3, 0.045, 0.1, 0.1, 200.0, 45.0)["eta"]
    s17 = S.bik_s_opt_eq17(25.0, 0.1, eta, 45.0, 2.66)
    s27 = S.bik_s_opt_eq17(25.0, 0.1, eta, 45.0, 2.7156)
    k_c, ra_c, nu_c = ch.optimum_spacing_constants(ch.nu_bcr)
    print("   equation 17 coefficient 2.66 -> s_opt %.2f mm; with 2.7156 recomputed from equation 13: %.2f mm; coefficient from eq. 13 by maximising Nu / s^2: %.4f (Ra_b %.2f, Nu_b %.4f); paper: 2.66 and Nu 1.25 (text)" % (
        s17 * 1e3, s27 * 1e3, k_c, ra_c, nu_c))
    out["eq17"] = {"s17_mm": s17 * 1e3, "s2716_mm": s27 * 1e3, "k_eq13": k_c, "ra_opt": ra_c, "nu_opt": nu_c}
    # identity of equation 13 with equation 21 of the review
    grid = np.logspace(-1, 5, 61)
    diff = max(abs(S.bik_nu_fin(r) / ch.nu_bcr(r) - 1.0) for r in grid)
    print("   equation 13 of the paper against equation 21 of the review (Ra_b 0.1 to 1e5): largest relative difference %.2e (576 = 24^2; 2.873 against 0.59^-2 = %.4f)" % (diff, 0.59 ** -2))
    out["identity_eq13_eq21"] = diff
    # Elenbaas's own optimum (Ra_b about 50 for the Elenbaas formula; the paper says Nu = 1.25)
    k_e, ra_e, nu_e = ch.optimum_spacing_constants(ch.nu_elenbaas)
    print("   optimum of Nu_b / b^2 from the Elenbaas formula (eq. 8 of the review): K = %.4f, Ra_b %.1f, Nu_b %.4f (paper's text: Elenbaas optimum Nu 1.25)" % (k_e, ra_e, nu_e))
    out["elenbaas_opt"] = {"k": k_e, "ra": ra_e, "nu": nu_e}
    results["B"] = out


def study_c(results):
    """!
    @brief C: Ostrach (1953) Table I and the Churchill and Chu Prandtl function.
    @param results Dict that receives the numbers.
    @return None.
    """
    print("C. Ostrach (1953) Table I, -H'(0), against an independent collocation solution of the similarity equations")
    rows = []
    for pr, ref in S.OSTRACH_TABLE_I.items():
        v = S.ostrach_h0(pr)
        # the shooting is stiff for Pr > 2 and is run only for Pr <= 2 (nan otherwise)
        fpp, v_shoot = S.ostrach_h0_shooting(pr) if pr <= 2.0 else (S.ostrach_h0(pr, full=True)[0], float("nan"))
        fo = (4.0 / 3.0) * v / math.sqrt(2.0) / pr ** 0.25          # Nu_L = (4/3) Nu_x(L), Nu_x = -H'(0) (Gr_x/4)^(1/4)
        fc = S.churchill_prandtl_function(pr)
        rows.append({"pr": pr, "table": ref, "solver": v, "shooting": v_shoot, "fpp0": fpp, "f_ostrach": fo, "f_churchill": fc})
        print("   Pr %7.3f  table %.4f  collocation %.4f (%+.2f %%)  shooting %.4f  F''(0) %.4f   Nu_L / Ra_L^(1/4): similarity %.4f, Churchill-Chu term %.4f (%+.2f %%)" % (
            pr, ref, v, 100 * (v / ref - 1), v_shoot, fpp, fo, fc, 100 * (fc / fo - 1)))
    results["C"] = rows
    # also the known limits: Pr -> infinity 0.503 Pr^(1/4)/... is not read; skip
    big = S.ostrach_h0(1000.0)
    print("   Pr 1000 (not read from the table): -H'(0) = %.4f" % big)
    results["C_pr1000"] = big


def study_d(results):
    """!
    @brief D: six measured horizontal arrays against the program's uniform coefficient and the Tari-Mehrtash correlations.
    @param results Dict that receives the numbers.
    @return None.
    """
    print("D. Short fin arrays on a horizontal base, fins up, measured mean coefficient on the total wetted area (plot values, ENCIT 2012) against the program's uniform h")
    out = {}
    ratios_by_gap = {5.55: [], 14.35: []}
    for k, a in S.ENCIT_ARRAYS.items():
        rows = []
        for dt, hm in S.ENCIT_H_MEASURED[k]:
            u = S.uniform_h_array(a, dt)                                  # the program's fin ratio (W/p fins)
            u_act = S.uniform_h_array(a, dt, fins="actual")               # the same coefficient on the real fins
            t_up = S.tari_horizontal_up(a, dt)
            phi_l = S.uniform_h_array(a, dt, channel_length=a["l"] * 1e-3)
            phi_h = S.uniform_h_array(a, dt, channel_length=0.5 * a["l"] * 1e-3)
            phi_l_act = S.uniform_h_array(a, dt, channel_length=a["l"] * 1e-3, fins="actual")
            rows.append({"dt": dt, "h_meas": hm, "h_uniform": u["h_mean"], "h_uniform_actual": u_act["h_mean"], "h_face": u["h_face"], "eta": u["eta"], "tari_h": t_up["h"],
                         "tari_in_range": t_up["in_range"], "tari_down": S.tari_horizontal_down(a, dt), "phi_L": phi_l["phi"], "h_phi_L": phi_l["h_mean"],
                         "h_phi_L_actual": phi_l_act["h_mean"], "phi_L2": phi_h["phi"], "h_phi_L2": phi_h["h_mean"]})
            ratios_by_gap[a["s"]].append(u["h_mean"] / hm)
        out[k] = rows
        meas = np.array([r["h_meas"] for r in rows])
        uni = np.array([r["h_uniform"] for r in rows])
        tar = np.array([r["tari_h"] for r in rows])
        act = np.array([r["h_uniform_actual"] for r in rows])
        print("   array %d (S %5.2f mm, H %4.1f mm, %d points): measured %.1f to %.1f; program %.1f to %.1f (program / measured %.2f to %.2f); uniform h on the real fins %.2f to %.2f"
              " of measured; Tari-Mehrtash eq. 5 %.1f to %.1f (%.2f to %.2f of measured)" % (
                  k, a["s"], a["h"], len(rows), meas.min(), meas.max(), uni.min(), uni.max(), (uni / meas).min(), (uni / meas).max(), (act / meas).min(), (act / meas).max(),
                  tar.min(), tar.max(), (tar / meas).min(), (tar / meas).max()))
    for s, v in ratios_by_gap.items():
        rows = [r for k, a in S.ENCIT_ARRAYS.items() if a["s"] == s for r in out[k]]
        act = np.array([r["h_uniform_actual"] / r["h_meas"] for r in rows])
        print("   gap %5.2f mm: program / measured, mean %.2f (min %.2f, max %.2f, %d points); uniform h on the real fins / measured, mean %.2f (min %.2f, max %.2f)" % (
            s, np.mean(v), np.min(v), np.max(v), len(v), act.mean(), act.min(), act.max()))
    # The vertical-channel fraction phi of Proposal B used outside its orientation, with the channel length taken as the fin length L or as L/2 (the chimney of Harahap and McManus)
    for s in (5.55, 14.35):
        rows = [r for k, a in S.ENCIT_ARRAYS.items() if a["s"] == s for r in out[k]]
        meas = np.array([r["h_meas"] for r in rows])
        for key, label in (("h_phi_L", "phi with L = fin length"), ("h_phi_L2", "phi with L = half the fin length"), ("h_phi_L_actual", "phi, L = fin length, real fins")):
            pred = np.array([r[key] for r in rows])
            print("   gap %5.2f mm, %-34s: phi %.2f to %.2f, predicted / measured mean %.2f (min %.2f, max %.2f)" % (
                s, label, min(r["phi_L2" if key == "h_phi_L2" else "phi_L"] for r in rows), max(r["phi_L2" if key == "h_phi_L2" else "phi_L"] for r in rows),
                np.mean(pred / meas), np.min(pred / meas), np.max(pred / meas)))
    out["ratios"] = {str(s): v for s, v in ratios_by_gap.items()}
    # The same arrays rotated (what the program would be asked if the board is horizontal and the block is on the underside): downward correlation, program's face down
    results["D"] = out


def main():
    """!
    @brief Run the four studies and write the JSON.
    @return None.
    """
    results = {}
    study_a(results)
    study_b(results)
    study_c(results)
    study_d(results)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "source_checks.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("written", os.path.join(OUT, "source_checks.json"))


if __name__ == "__main__":
    main()
