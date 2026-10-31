#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s3_boards.py
@brief S3 on the boards of the program: the Jacobi radius of the program's own matrices, the estimates, the omega they give, and the sweeps and seconds of the program's SOR with each.
@details Question: is an estimate of rho_J cheap compared with the solve and robust on boards with vias, partial copper, outlines and many layers?
         Boards (simple first, then the example): bare plates of 1, 2, 4 and 6 layers; a 4-layer plate with a 5 x 5 via array (the program's point treatment: a pure stencil); partial
         copper; a round board (cells off the board pinned to the ambient); the example board of the program at 2 mm and 1 mm.
         For every board: rho_J by eigenvalues (reference), the Rayleigh bound and the closed form (no product), Lanczos 3, 5, 10, 20 steps, the power method on (I + J_s)/2 with 50
         and 200 steps; the omegas; sweeps and seconds of `Network.solve_sor` of the program at its own formula, Young's exact, Rayleigh, Lanczos 10, the adaptive estimate
         (`s3boards.adaptive_run`) and the measured best omega; the seconds of the direct solve and of each estimate.
         Part 2: the mean-potential via treatment (variant c' of research/sor-with-via-couplings): rho of the stencil part of K (what the colours iterate) and of the full K, the omega they
         give against the measured best omega of (c').
         Part 3: scaling of the cost of the estimate and of the sweeps with the grid (plate 2 layers, cells 40 to 160 per side).
Usage: python research/young-omega-tiles/scripts/study_s3_boards.py [--quick]   (from the repository root; --quick leaves out the 1 mm example and the best-omega scans). Results go to
       out/s3_boards.json.
"""

import math
import os
import sys
import time

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s3boards as sb                                                       # noqa: E402
import young as yg                                                          # noqa: E402

QUICK = "--quick" in sys.argv
RES = {}


def boards():
    """!
    @brief The boards of the study: (label, Problem, cell in mm).
    @return list.
    """
    out = [("plate 1 layer 40 mm", sb.plate(1, 40.0), 1.0), ("plate 2 layers 40 mm", sb.plate(2, 40.0), 1.0), ("plate 4 layers 40 mm", sb.plate(4, 40.0), 1.0),
           ("plate 6 layers 40 mm", sb.plate(6, 40.0), 1.0), ("plate 4 layers, forced air h=50", sb.plate(4, 40.0, h_top=50.0, h_bottom=50.0), 1.0),
           ("4 layers + 5x5 vias (point)", sb.plate(4, 40.0, vias=5, via_pitch_mm=1.5, fill_k=385.0), 0.5), ("partial copper 4 layers", sb.partial_copper(4, 40.0), 1.0),
           ("round board 40 mm", sb.round_board(2, 40.0), 1.0), ("example board 2 mm", sb.example_board(), 2.0)]
    if not QUICK:
        out.append(("example board 1 mm", sb.example_board(), 1.0))
    return out


def run_board(label, prob, cell):
    """!
    @brief All the measurements for one board.
    @param label Name.
    @param prob Problem.
    @param cell Cell in mm.
    @return dict.
    """
    net = sb.net_program(prob, cell)
    K = net.K
    N = K.shape[0]
    t_dir, _ = sb.direct_seconds(net)
    rho, t_ex = yg.timed(yg.rho_exact, K)
    rec = {"label": label, "cell": cell, "N": N, "nl": net.nl, "nx": net.nx, "ny": net.ny, "rho": rho, "t_direct": t_dir, "t_exact_eig": t_ex}
    est = {}
    (rq, p), t = yg.timed(yg.rho_rayleigh, K)
    est["Rayleigh"] = {"rho": rq, "products": p, "seconds": t}
    cf = yg.rho_closed_form(0.0, float(net.g_amb.sum()), diag_sum=float(K.diagonal().sum()))
    est["closed form"] = {"rho": cf, "products": 0, "seconds": 0.0}
    est["Rayleigh all nodes"] = {"rho": yg.rho_rayleigh(K, linked_only=False)[0], "products": 1, "seconds": 0.0}
    for k in (3, 5, 10, 20):
        (r, p, _h), t = yg.timed(yg.rho_lanczos, K, k)
        est[f"Lanczos {k}"] = {"rho": r, "products": p, "seconds": t}
    for m in (50, 200):
        (r, p), t = yg.timed(yg.rho_power, K, m)
        est[f"power {m}"] = {"rho": r, "products": p, "seconds": t}
    for v in est.values():
        v["omega"] = yg.omega_young(v["rho"])
        v["err_1mrho_pct"] = 100.0 * ((1.0 - v["rho"]) / (1.0 - rho) - 1.0)
    rec["estimates"] = est
    # Sweeps of the program's SOR at the candidate omegas
    sweeps = {}
    om = {"program": yg.omega_program(net.nx, net.ny), "Young exact": yg.omega_young(rho), "Rayleigh": est["Rayleigh"]["omega"], "Lanczos 10": est["Lanczos 10"]["omega"]}
    for name, w in om.items():
        r = sb.sweeps_program(net, w)
        sweeps[name] = {"omega": w, "iterations": r["iterations"], "converged": r["converged"], "seconds": r["seconds"]}
    t0 = time.perf_counter()
    ad = sb.adaptive_run(net)
    sweeps["adaptive"] = {"omega": ad["omegas"][-1], "omegas": ad["omegas"], "iterations": ad["iterations"], "converged": ad["converged"], "seconds": time.perf_counter() - t0}
    if not QUICK:
        wy = om["Young exact"]
        wb, itb, table = sb.best_omega(lambda w: sb.sweeps_program(net, w, max_iter=20000)["iterations"], max(om["program"], wy - 0.03), min(wy + 0.015, 1.995))
        sweeps["measured best"] = {"omega": wb, "iterations": itb}
        rec["omega_scan"] = table
    rec["sweeps"] = sweeps
    return rec


def part1():
    """!
    @brief The boards of the program with the program's point treatment of the vias.
    @return None.
    """
    print("## 1. Boards of the program (point treatment of the vias, pure stencil): rho_J, estimates, omega, sweeps\n")
    recs = [run_board(*b) for b in boards()]
    outio.table(["board", "cell mm", "N", "rho_J (eigenvalues)", "omega_opt", "program's omega", "direct solve s", "eigenvalues s"],
                [[r["label"], r["cell"], r["N"], f"{r['rho']:.6f}", f"{yg.omega_young(r['rho']):.4f}", f"{r['sweeps']['program']['omega']:.4f}", f"{r['t_direct']:.3f}", f"{r['t_exact_eig']:.2f}"]
                 for r in recs])
    names = ["Rayleigh", "Rayleigh all nodes", "closed form", "Lanczos 3", "Lanczos 5", "Lanczos 10", "Lanczos 20", "power 50", "power 200"]
    print("Relative error of 1 - rho_J of each estimate (positive = below the true radius = omega on the safe side); products with K in the last row of each estimate in section 3.\n")
    outio.table(["board"] + names, [[r["label"]] + [f"{r['estimates'][n]['err_1mrho_pct']:+.2f} %" for n in names] for r in recs])
    cols = ["program", "Young exact", "Rayleigh", "Lanczos 10", "adaptive"] + ([] if QUICK else ["measured best"])
    print("Sweeps of the program's SOR (tol 1e-9) and omega used:\n")
    outio.table(["board"] + cols, [[r["label"]] + [f"{r['sweeps'][c]['iterations']} @ {r['sweeps'][c]['omega']:.4f}" + ("" if r["sweeps"][c].get("converged", True) else " (no conv.)") for c in cols]
                                   for r in recs])
    print("Cost (seconds on this machine): direct solve, SOR with the program's omega, SOR with Young's, Rayleigh, Lanczos 10:\n")
    outio.table(["board", "direct", "SOR program omega", "SOR Young omega", "Rayleigh", "Lanczos 10", "Lanczos 10 in sweeps (2 products each)"],
                [[r["label"], f"{r['t_direct']:.3f}", f"{r['sweeps']['program']['seconds']:.2f}", f"{r['sweeps']['Young exact']['seconds']:.2f}", f"{r['estimates']['Rayleigh']['seconds']:.4f}",
                  f"{r['estimates']['Lanczos 10']['seconds']:.3f}", f"{r['estimates']['Lanczos 10']['products'] / 2:.0f}"] for r in recs])
    RES["part1"] = recs


def part2():
    """!
    @brief The mean-potential via treatment: omega of the stencil part against the measured best of the block SOR (c').
    @return None.
    """
    print("## 2. Mean-potential via couplings, block SOR (c'): omega from the stencil part of K\n")
    sb.load_libraries()
    import sorvia as sv
    rows, out = [], []
    cases = [("3 x 3 array, 0.5 mm", sb.plate(4, 21.0, vias=3, via_pitch_mm=3.5, fill_k=385.0, source_mm=10.0), 0.5),
             ("5 x 5 array pitch 1.2 mm, 0.5 mm", sb.plate(4, 30.0, vias=5, via_pitch_mm=1.2, fill_k=385.0, source_mm=6.0), 0.5)]
    if not QUICK:
        cases.append(("example board 1 mm", sb.example_board(), 1.0))
    for label, prob, cell in cases:
        net = sb.net_meanpot(prob, cell)
        K = net.K
        st = sv.stencil_parts(net)
        Kst = (sp.diags(K.diagonal()) + st["S"]).tocsr()                          # diagonal of K, stencil off-diagonals: what the colour sweeps iterate
        rho_st = yg.rho_exact(Kst)
        rho_full = yg.rho_exact(K)
        lz, p, _ = yg.rho_lanczos(Kst, 10)
        lzf, _p2, _ = yg.rho_lanczos(K, 10)
        rqf, _ = yg.rho_rayleigh(K)
        wy, wl = yg.omega_young(rho_st), yg.omega_young(lz)
        wp = yg.omega_program(net.nx, net.ny)
        # The full K has positive entries inside a footprint: its Jacobi matrix is not non-negative, Young's theory does not apply to it and the measured sweeps decide
        wf = yg.omega_young(rho_full)
        res = {w_name: sb.sweeps_block(net, w, max_iter=40000)["iterations"] for w_name, w in
               (("program", wp), ("Young stencil", wy), ("Lanczos 10 stencil", wl), ("Young full K", wf), ("Lanczos 10 full K", yg.omega_young(lzf)), ("Rayleigh full K", yg.omega_young(rqf)))}
        wb, itb, _t = sb.best_omega(lambda w: sb.sweeps_block(net, w, max_iter=20000)["iterations"], wp, 1.995)
        rows.append([label, K.shape[0], f"{rho_st:.6f}", f"{rho_full:.6f}", f"{lzf:.6f}", f"{rqf:.6f}", f"{wp:.4f} / {res['program']}", f"{wy:.4f} / {res['Young stencil']}", f"{wl:.4f} / {res['Lanczos 10 stencil']}",
                     f"{wf:.4f} / {res['Young full K']}", f"{yg.omega_young(lzf):.4f} / {res['Lanczos 10 full K']}", f"{yg.omega_young(rqf):.4f} / {res['Rayleigh full K']}", f"{wb:.4f} / {itb}"])
        out.append({"label": label, "N": K.shape[0], "rho_stencil": rho_st, "rho_full": rho_full, "rho_lanczos_full": lzf, "rho_rayleigh_full": rqf, "sweeps": res, "best": [wb, itb]})
    outio.table(["board", "N", "rho_J stencil part", "rho_J full K", "Lanczos 10 full K", "Rayleigh full K", "program: omega / sweeps", "Young (stencil)", "Lanczos 10 (stencil)", "Young (full K)",
                 "Lanczos 10 (full K)", "Rayleigh (full K)", "measured best (omega 1.5.. 1.995)"], rows)
    RES["part2"] = out


def part3():
    """!
    @brief Scaling with the grid: products of the estimate against sweeps of the solve (plate, 2 layers).
    @return None.
    """
    print("## 3. Scaling with the grid (2-layer plate, tol 1e-9)\n")
    rows, out = [], []
    sizes = (40, 80, 120) if QUICK else (40, 80, 120, 160)
    for n in sizes:
        prob = sb.plate(2, float(n))
        net = sb.net_program(prob, 1.0)
        rho = yg.rho_exact(net.K)
        w = yg.omega_young(rho)
        (r10, p10, _), t10 = yg.timed(yg.rho_lanczos, net.K, 10)
        (rq, _), trq = yg.timed(yg.rho_rayleigh, net.K)
        s_prog = sb.sweeps_program(net, None)
        s_y = sb.sweeps_program(net, w)
        t_dir, _ = sb.direct_seconds(net)
        rows.append([f"{n} x {n} x 2", net.K.shape[0], f"{rho:.7f}", f"{1 - rho:.2e}", f"{w:.4f}", s_prog["iterations"], s_y["iterations"], f"{s_prog['seconds'] / max(s_y['seconds'], 1e-9):.1f}",
                     f"{t10:.3f}", f"{trq:.4f}", f"{t_dir:.3f}", f"{s_y['seconds']:.2f}"])
        out.append({"n": n, "N": net.K.shape[0], "rho": rho, "sweeps_program": s_prog["iterations"], "sweeps_young": s_y["iterations"], "t_lanczos10": t10, "t_rq": trq, "t_direct": t_dir,
                    "t_sor_young": s_y["seconds"], "t_sor_program": s_prog["seconds"], "lanczos10": r10})
    outio.table(["grid", "N", "rho_J", "1 - rho_J", "omega_opt", "sweeps program omega", "sweeps Young", "time ratio", "Lanczos 10 s", "Rayleigh s", "direct s", "SOR Young s"], rows)
    RES["part3"] = out


def main():
    """!
    @brief Run the three parts and save.
    @return None.
    """
    sb.load_libraries()
    part1()
    part2()
    part3()
    print("saved", outio.save("s3_boards", RES))


if __name__ == "__main__":
    main()
