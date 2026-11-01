#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s3_exact.py
@brief S3, exact cases first: how well the estimates of the Jacobi radius and of Young's omega work on matrices whose answer is known in closed form.
@details Question: is there a cheap estimate of rho_J? Here the answer is known, so the estimators are tested before any board of the program.
         Part A (textbook): the 5-point Poisson matrix (rho_J = cos(pi / (n + 1)), omega_opt = 2 / (1 + sin(pi / (n + 1))), Saad 2003 section 4.2.5 and Young): the eigenvalue
                 estimators and Young's relation against the dense spectral radius of the SOR matrix at several omega; the program's factor 2 / (1 + sin(pi / n)) is this optimum
                 with n instead of n + 1 (the same family: fixed edges), the measured sweeps of an independent red-black SOR.
         Part B (torus): periodic plate with a uniform loss, rho_J = 4 g / (4 g + a) exactly and the uniform vector is the exact eigenvector: the Rayleigh bound is exact.
         Part C (plate of the program's stencil, insulated edges, layers): exact rho_J (eigenvalues) against the Rayleigh bound, the closed form and Lanczos k = 2..20 for uniform
                 and non-uniform losses (cooling concentrated at an edge, in a patch, on one layer); error in 1 - rho (the quantity that sets omega) and in omega.
         Part D (sweeps against omega): the independent red-black SOR on a plate; sweeps at the program's omega, Young's omega and the omegas given by the estimates; the cost of
                 each estimate in products with K, in sweeps equivalent (a sweep is two products) and in seconds.
         Part E (the power method fails by symmetry): power iteration on J_s against on (I + J_s) / 2 and Lanczos on the same start.
Usage: python research/young-omega-tiles/scripts/study_s3_exact.py   (from the repository root; no board of the program is needed; minutes). Results go to out/s3_exact.json.
"""

import math
import os
import sys

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import young as yg                                                          # noqa: E402

RES = {}


def part_a():
    """!
    @brief Textbook Poisson matrix: rho_J, omega_opt, the SOR radius and the measured sweeps.
    @return None.
    """
    print("## A. Poisson 5-point matrix (fixed edges), the textbook case\n")
    rows, out = [], []
    for n in (6, 8, 10, 12):
        K = sp.csr_matrix(yg.poisson_matrix(n))
        rho = yg.rho_exact(K)
        w_opt = yg.omega_young(rho)
        # Dense spectral radius of the natural-order SOR matrix over a grid of omega: the minimum is Young's optimum, independent of the relation
        ws = np.linspace(1.0, 1.99, 100)
        rad = [yg.sor_iteration_radius(K, w) for w in ws]
        w_num = float(ws[int(np.argmin(rad))])
        rad_at_opt = yg.sor_iteration_radius(K, w_opt)
        rows.append([n, f"{math.cos(math.pi / (n + 1)):.6f}", f"{rho:.6f}", f"{w_opt:.4f}", f"{2 / (1 + math.sin(math.pi / (n + 1))):.4f}", f"{w_num:.2f}",
                     f"{rad_at_opt:.5f}", f"{w_opt - 1:.5f}", f"{2 / (1 + math.sin(math.pi / n)):.4f}"])
        out.append({"n": n, "rho_cos": math.cos(math.pi / (n + 1)), "rho_eig": rho, "omega_young": w_opt, "omega_scan": w_num, "rad_at_opt": rad_at_opt,
                    "omega_program_formula": 2 / (1 + math.sin(math.pi / n))})
    outio.table(["n", "cos(pi/(n+1))", "rho_J eigenvalues", "omega_opt (Young)", "2/(1+sin(pi/(n+1)))", "omega at min of dense SOR radius (step 0.01)", "SOR radius at omega_opt",
                 "omega_opt - 1", "program's formula (n)"], rows)
    # Young's relation against the dense SOR radius for several omega on one case
    K = sp.csr_matrix(yg.poisson_matrix(8))
    mu = yg.rho_exact(K)
    rows2 = []
    for w in (1.0, 1.2, 1.4, 1.5, yg.omega_young(mu), 1.7, 1.9):
        rows2.append([f"{w:.4f}", f"{yg.sor_iteration_radius(K, w):.6f}", f"{yg.rho_sor(w, mu):.6f}"])
    outio.table(["omega (n = 8)", "dense SOR radius", "Young's relation"], rows2)
    RES["A"] = out


def plate_cases():
    """!
    @brief The plates of parts C and D: label, matrix and the colouring.
    @return list of (label, K, colour, meta).
    """
    out = []
    for nl, n, gz, a in ((1, 40, 0.0, 0.002), (2, 40, 0.5, 0.002), (4, 40, 0.5, 0.002), (6, 40, 0.5, 0.002), (4, 80, 0.5, 0.0005), (2, 80, 0.5, 0.002)):
        K = yg.plate_matrix(nl, n, n, 1.0, 1.0, gz, a)
        out.append((f"{nl} layers, {n}x{n}, loss {a}", K, yg.parity_colour(nl, n, n), {"nl": nl, "n": n}))
    # Non-uniform losses: all at one edge, a central patch, one layer only
    n, nl = 40, 4
    g = np.zeros((nl, n, n))
    g[:, :, 0] = 0.05
    out.append(("edge-cooled (edge column only)", yg.plate_matrix(nl, n, n, 1.0, 1.0, 0.5, g), yg.parity_colour(nl, n, n), {"nl": nl, "n": n}))
    g = np.zeros((nl, n, n))
    g[-1, 15:25, 15:25] = 0.02
    out.append(("patch-cooled (heatsink-like patch)", yg.plate_matrix(nl, n, n, 1.0, 1.0, 0.5, g + 1e-5), yg.parity_colour(nl, n, n), {"nl": nl, "n": n}))
    g = np.zeros((nl, n, n))
    g[-1] = 0.004
    out.append(("one face only (bottom)", yg.plate_matrix(nl, n, n, 1.0, 1.0, 0.5, g), yg.parity_colour(nl, n, n), {"nl": nl, "n": n}))
    return out


def part_b():
    """!
    @brief The torus: exact rho_J and exact Rayleigh bound.
    @return None.
    """
    print("## B. Periodic plate with uniform loss: rho_J = 4 g / (4 g + a)\n")
    rows, out = [], []
    for nx, a in ((16, 0.1), (32, 0.01), (64, 0.001), (64, 0.0001)):
        K = yg.torus_matrix(nx, nx, 1.0, a)
        exact = 4.0 / (4.0 + a)
        rq, _ = yg.rho_rayleigh(K)
        lz, prod, _ = yg.rho_lanczos(K, 3)
        rows.append([f"{nx}x{nx}", a, f"{exact:.8f}", f"{yg.rho_exact(K):.8f}", f"{rq:.8f}", f"{lz:.8f}", f"{yg.omega_young(exact):.5f}", f"{yg.omega_young(rq):.5f}"])
        out.append({"n": nx, "a": a, "exact": exact, "eig": yg.rho_exact(K), "rq": rq, "lanczos3": lz})
    outio.table(["torus", "loss a", "4g/(4g+a)", "rho_J eigenvalues", "Rayleigh (1 product)", "Lanczos 3 steps", "omega_opt exact", "omega_opt from Rayleigh"], rows)
    RES["B"] = out


def part_c():
    """!
    @brief Plates of the program's stencil: exact against the estimates.
    @return None.
    """
    print("## C. Plates with the program's stencil: errors of the estimates of rho_J (relative error of 1 - rho, and omega)\n")
    rows, out = [], []
    ks = (2, 3, 5, 10, 20)
    for label, K, _col, _meta in plate_cases():
        rho = yg.rho_exact(K)
        row = {"case": label, "N": K.shape[0], "rho": rho, "omega": yg.omega_young(rho)}
        cells = [label, K.shape[0], f"{rho:.6f}", f"{yg.omega_young(rho):.4f}"]
        rq, _ = yg.rho_rayleigh(K)
        cells.append(f"{100 * ((1 - rq) / (1 - rho) - 1):+.2f} %")
        row["rq"] = rq
        for k in ks:
            r, _p, _h = yg.rho_lanczos(K, k)
            cells.append(f"{100 * ((1 - r) / (1 - rho) - 1):+.2f} %")
            row[f"lanczos{k}"] = r
        for m in (50, 200):
            r, _p = yg.rho_power(K, m)
            cells.append(f"{100 * ((1 - r) / (1 - rho) - 1):+.2f} %")
            row[f"power{m}"] = r
        rows.append(cells)
        out.append(row)
    outio.table(["plate", "N", "rho_J", "omega_opt", "Rayleigh"] + [f"Lanczos {k}" for k in ks] + ["power 50", "power 200"], rows)
    print("(entry = relative error of 1 - rho_J; positive = the estimate is below the true radius, i.e. omega below the optimum, the safe side)\n")
    RES["C"] = out


def part_d():
    """!
    @brief Sweeps against omega on plates and the cost of each estimate.
    @return None.
    """
    print("## D. Sweeps of an independent red-black SOR at the program's omega, Young's, and the estimates (tol 1e-9)\n")
    rows, out = [], []
    for label, K, col, meta in plate_cases():
        n = meta["n"]
        N = K.shape[0]
        b = np.zeros(N)
        b[N // 2 + n // 2] = 1.0
        rho = yg.rho_exact(K)
        (rq, _), t_rq = yg.timed(yg.rho_rayleigh, K)
        (lz, p_lz, _), t_lz = yg.timed(yg.rho_lanczos, K, 8)
        choices = {"program": yg.omega_program(n, n), "Young exact": yg.omega_young(rho), "Rayleigh": yg.omega_young(rq), "Lanczos 8": yg.omega_young(lz)}
        sweeps = {}
        for name, w in choices.items():
            _x, it, ok = yg.sor_rb_matrix(K, b, col, w, 1e-9, 30000)
            sweeps[name] = it if ok else None
        rows.append([label, f"{choices['program']:.4f}", f"{choices['Young exact']:.4f}", f"{choices['Rayleigh']:.4f}", f"{choices['Lanczos 8']:.4f}"] +
                    [sweeps[k] if sweeps[k] else "no conv." for k in choices] + [f"{t_rq * 1e3:.1f} / {t_lz * 1e3:.1f}"])
        out.append({"case": label, "omegas": choices, "sweeps": sweeps, "t_rq": t_rq, "t_lanczos8": t_lz, "products_lanczos8": p_lz})
    outio.table(["plate", "omega program", "omega Young", "omega Rayleigh", "omega Lanczos 8", "sweeps program", "sweeps Young", "sweeps Rayleigh", "sweeps Lanczos 8",
                 "ms: Rayleigh / Lanczos 8"], rows)
    RES["D"] = out
    # Curve sweeps against omega for one plate (figure data)
    label, K, col, meta = plate_cases()[2]
    n = meta["n"]
    N = K.shape[0]
    b = np.zeros(N)
    b[N // 2 + n // 2] = 1.0
    rho = yg.rho_exact(K)
    curve = []
    for w in np.linspace(1.5, 1.98, 25):
        _x, it, ok = yg.sor_rb_matrix(K, b, col, float(w), 1e-9, 30000)
        curve.append({"omega": float(w), "sweeps": it if ok else None, "predicted": yg.sweeps_predicted(float(w), rho)})
    RES["D_curve"] = {"case": label, "rho": rho, "omega_young": yg.omega_young(rho), "omega_program": yg.omega_program(n, n), "curve": curve}


def part_e():
    """!
    @brief The plain power method on J_s does not converge (symmetric spectrum); the shifted one and Lanczos do.
    @return None.
    """
    print("## E. Power method on J_s, on (I + J_s)/2, and Lanczos (4-layer plate 40x40; error of rho_J)\n")
    label, K, _c, _m = plate_cases()[2]
    rho = yg.rho_exact(K)
    mv, n, sd, cnt = yg.jacobi_symmetric(K)
    rng = np.random.default_rng(1)
    rows = []
    for m in (10, 50, 200, 800):
        x = rng.standard_normal(n)
        x /= np.linalg.norm(x)
        for _ in range(m):                                                    # plain power method on J_s: Rayleigh quotient of the iterate
            y = mv(x)
            x = y / np.linalg.norm(y)
        plain = float(x @ mv(x))
        sh, _ = yg.rho_power(K, m, start="random", seed=1)
        lz, _p, _h = yg.rho_lanczos(K, min(m, 60), start="random", seed=1)
        rows.append([m, f"{plain:+.6f}", f"{sh:.6f}", f"{lz:.6f}" if m <= 60 else "-"])
    print(f"exact rho_J = {rho:.6f} ({label})\n")
    outio.table(["products", "power on J_s (Rayleigh quotient, sign alternates)", "power on (I + J_s)/2", "Lanczos (random start, k = products)"], rows)
    RES["E"] = {"rho": rho, "rows": rows}


def main():
    """!
    @brief Run the parts and save the results.
    @return None.
    """
    for part in (part_a, part_b, part_c, part_d, part_e):
        part()
    print("saved", outio.save("s3_exact", RES))


if __name__ == "__main__":
    main()
