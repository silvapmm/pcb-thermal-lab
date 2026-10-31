#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s3_block_more.py
@brief S3 for the block SOR with the mean-potential via couplings, on more boards than the three of `study_s3_boards.py` part 2 (review): does the omega from the Rayleigh bound
       of the FULL K stay near the measured best and below it, and is the block SOR stable for every omega below 2?
@details The full K has positive entries inside a via footprint (the mean-potential coupling), so its Jacobi matrix is not non-negative and Young's theory does not hold; the
         block SOR (`sorvia.RB` with the via blocks solved exactly, the blocks coloured) is still a block SOR of a symmetric positive definite matrix, so it converges for every
         0 < omega < 2 (Ostrowski-Reich, block form: Saad 2003, section 4.2, read in `sor-with-via-couplings`); this study measures it. For every board: rho of the full K by
         eigenvalues (largest and smallest eigenvalue of J_s, because a matrix with positive off-diagonal entries can have its largest modulus at the negative end), the
         Rayleigh bound of the full K with the linked-node mask, the sweeps of the block SOR at the program's omega, at the Rayleigh omega, at Young's omega of the exact rho, the
         measured best, and the sweeps to the tolerance at omega 1.995 and 1.999 (stability).
Usage: python research/young-omega-tiles/scripts/study_s3_block_more.py [--quick]   (from the repository root; a few minutes). Results go to out/s3_block_more.json.
"""

import math
import os
import sys

import numpy as np
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s3boards as sb                                                       # noqa: E402
import young as yg                                                          # noqa: E402
from pcbthermal.model import Materials, Problem                            # noqa: E402

QUICK = "--quick" in sys.argv


def array_board(layers, side_mm, n, pitch_mm, source_mm, fill_k=385.0, offset_mm=0.0, h=10.0, round_board=False):
    """!
    @brief A square (or round) board, full copper on every layer, a source in the middle and an n x n via array, optionally shifted away from the source along x.
    @param layers Copper layers.
    @param side_mm Board side (or diameter) in mm.
    @param n Vias per side.
    @param pitch_mm Pitch in mm.
    @param source_mm Side of the source in mm.
    @param fill_k Via fill conductivity in W/mK.
    @param offset_mm Shift of the array along x in mm (0: under the source).
    @param h Film coefficient of both faces in W/m2K.
    @param round_board True: a round outline of diameter side_mm.
    @return Problem.
    """
    p = Problem.new(side_mm, side_mm, layers, 1.6, 35.0, h_top=h, h_bottom=h, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side_mm, side_mm))
    c = side_mm / 2
    p.add_heater(1, 1.0, rect=(c - source_mm / 2, c - source_mm / 2, c + source_mm / 2, c + source_mm / 2))
    hh = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            p.add_via(c + offset_mm + (i - hh) * pitch_mm, c + (j - hh) * pitch_mm, 0.3, fill_k=fill_k)
    if round_board:
        r = side_mm / 2
        p.set_outline([[c + r * math.cos(2 * math.pi * k / 72), c + r * math.sin(2 * math.pi * k / 72)] for k in range(72)])
    return p


def boards():
    """!
    @brief The boards: (label, Problem, cell mm).
    @return list.
    """
    out = [("lone via under the source, 2 layers", array_board(2, 20.0, 1, 1.0, 4.0), 0.5),
           ("2 x 2 pitch 2.0, 4 layers", array_board(4, 20.0, 2, 2.0, 5.0), 0.5),
           ("4 x 4 pitch 1.0, 4 layers", array_board(4, 20.0, 4, 1.0, 5.0), 0.5),
           ("3 x 3 pitch 2.5, 6 layers", array_board(6, 24.0, 3, 2.5, 8.0), 0.5),
           ("3 x 3 pitch 3.5, open barrels, 4 layers", array_board(4, 21.0, 3, 3.5, 10.0, fill_k=0.0), 0.5),
           ("3 x 3 pitch 2.0 beside the source (offset 6 mm), 2 layers", array_board(2, 24.0, 3, 2.0, 4.0, offset_mm=6.0), 0.5),
           ("round board 30 mm, 3 x 3 pitch 2.0, 2 layers", array_board(2, 30.0, 3, 2.0, 6.0, round_board=True), 0.5),
           ("forced air h = 50, 3 x 3 pitch 2.0, 4 layers", array_board(4, 20.0, 3, 2.0, 6.0, h=50.0), 0.5),
           ("example board 2 mm", sb.example_board(), 2.0)]
    return out[:3] if QUICK else out


def jacobi_extremes(K):
    """!
    @brief Largest and smallest eigenvalue of J_s = I - D^-1/2 K D^-1/2 (dense up to 3000 unknowns, ARPACK above).
    @param K Sparse symmetric positive definite matrix.
    @return Tuple (lambda_max, lambda_min).
    """
    mv, n, _sd, _c = yg.jacobi_symmetric(K)
    if n <= 3000:
        d = 1.0 / np.sqrt(K.diagonal())
        w = np.linalg.eigvalsh((K.multiply(d[:, None]).multiply(d[None, :])).toarray())
        return float(1.0 - w[0]), float(1.0 - w[-1])
    op = spla.LinearOperator((n, n), matvec=mv, dtype=float)
    hi = spla.eigsh(op, k=1, which="LA", tol=1e-12, ncv=60, return_eigenvectors=False)[0]
    lo = spla.eigsh(op, k=1, which="SA", tol=1e-8, ncv=60, return_eigenvectors=False)[0]
    return float(hi), float(lo)


def run(label, prob, cell):
    """!
    @brief All the measurements of one board.
    @param label Name.
    @param prob Problem.
    @param cell Cell in mm.
    @return dict.
    """
    net = sb.net_meanpot(prob, cell)
    K = net.K
    lmax, lmin = jacobi_extremes(K)
    rho = max(abs(lmax), abs(lmin))
    rq, _p = yg.rho_rayleigh(K)
    w_prog, w_ray = yg.omega_program(net.nx, net.ny), yg.omega_young(rq)
    w_young = yg.omega_young(min(rho, 1.0 - 1e-15))
    it = lambda w, m=60000: sb.sweeps_block(net, w, max_iter=m)["iterations"]      # noqa: E731
    rec = {"label": label, "N": K.shape[0], "lambda_max": lmax, "lambda_min": lmin, "rho": rho, "rho_rayleigh": rq, "omega_program": w_prog, "omega_rayleigh": w_ray,
           "omega_young": w_young, "sweeps_program": it(w_prog), "sweeps_rayleigh": it(w_ray), "sweeps_young": it(w_young)}
    wb, itb, _t = sb.best_omega(lambda w: it(w, 20000), max(w_prog, w_ray - 0.03), min(w_ray + 0.012, 1.998))
    # The best of the scan and of the three runs above (the sweep count is not smooth in omega: it is checked every 10 sweeps)
    cand = [(wb, itb), (w_prog, rec["sweeps_program"]), (w_ray, rec["sweeps_rayleigh"]), (w_young, rec["sweeps_young"])]
    rec["omega_best"], rec["sweeps_best"] = min(cand, key=lambda t: t[1])
    # Stability: sweeps to the tolerance at omegas close to 2 (the residual first grows, by up to ten times, then falls; it must converge, however slowly)
    for w in (1.995, 1.999):
        r = sb.sweeps_block(net, w, max_iter=60000)
        rec[f"sweeps_{w}"] = int(r["iterations"]) if r["converged"] else -1
        rec[f"peak_res_{w}"] = max(h[1] for h in r["history"]) if r["history"] else float("nan")
    print(f"{label}: done", flush=True)
    return rec


def main():
    """!
    @brief Run every board and print the table.
    @return None.
    """
    sb.load_libraries()
    recs = [run(*b) for b in boards()]
    print("\n## Block SOR (c') with the mean-potential via couplings: omega from the full K (omega / sweeps, tol 1e-9)\n")
    outio.table(["board", "N", "lambda_max J_s", "lambda_min J_s", "Rayleigh full K", "program", "Rayleigh (full K)", "Young (exact rho, full K)", "measured best",
                 "Rayleigh / best sweeps", "sweeps at 1.995 / 1.999 (-1: not converged in 60000)", "largest residual at 1.999"],
                [[r["label"], r["N"], f"{r['lambda_max']:.6f}", f"{r['lambda_min']:+.6f}", f"{r['rho_rayleigh']:.6f}", f"{r['omega_program']:.4f} / {r['sweeps_program']}",
                  f"{r['omega_rayleigh']:.4f} / {r['sweeps_rayleigh']}", f"{r['omega_young']:.4f} / {r['sweeps_young']}", f"{r['omega_best']:.4f} / {r['sweeps_best']}",
                  f"{r['sweeps_rayleigh'] / r['sweeps_best']:.2f}", f"{r['sweeps_1.995']} / {r['sweeps_1.999']}", f"{r['peak_res_1.999']:.1e}"] for r in recs])
    print("saved", outio.save("s3_block_more", recs))


if __name__ == "__main__":
    main()
