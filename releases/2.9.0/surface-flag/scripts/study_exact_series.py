#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_exact_series.py
@brief A second, exact reference for the surface flag: the cosine series of a plate under a uniform source, for rectangles, strips and non-rectangular parts.

@details Question (review of fix/surface-flag-narrow-part): does the table of study_flag_rule.py hold against a reference that shares nothing with the 3D finite volumes, what
         threshold of t/a would the exact solution set for a square and for an infinite strip, does the long side of a rectangle enter, and does the rule of
         thickness.source_width catch the overshoot of an L, a U, a rotated strip, a disc and a square with a thin tab?
         Method: a W x W plate (50 mm), thickness t, conductivity k, top insulated except a uniform flux q on the source, film h = 400 W/m2K below, adiabatic edges. The field is
         the double cosine series T = sum c_mn cos(l_m x) cos(l_n y) Z_mn(z) with Z = cosh(l z) + (h / k l) sinh(l z), l = sqrt(l_m^2 + l_n^2), exact for this problem; the
         surface, the column mean (mean of Z over the thickness) and the bottom value of every mode are written with tanh and sech so that no term overflows. Rectangles: the
         coefficients are exact (integrals of the cosines), 1500 and 3000 modes a side. Strips: the 1D series of a band across the whole plate, 200000 modes. Other shapes: the
         source is rasterized at 0.025 mm and its coefficients are the exact cell integrals (DCT times a sinc), 2000 modes a side. TRUE term = surface minus column mean; the
         PARABOLA is thickness.offsets with the exact fluxes (q in on top, h T_bottom out below); the ratio is read at the source centre (rectangles) or as the hottest surface
         minus the hottest column over the part (other shapes). A ratio above 1.07 is an overshoot (the 7 % quoted for the parabola).
         Usage: .venv/bin/python releases/2.9.0/surface-flag/scripts/study_exact_series.py   (about 15 s, under 1 GB)
"""

import os
import sys

import numpy as np
from scipy.fft import dct, dctn

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from pcbthermal import thickness                               # noqa: E402
from pcbthermal.geometry import points_in_polygon, polygon_area  # noqa: E402

W = 50e-3                                                      # plate side in m
H = 400.0                                                      # bottom film in W/m2K
TOL = 0.07                                                     # tolerance of the parabola quoted up to t/a 0.5


def kernels(lam, t, k, h=H):
    """!
    @brief Surface, column-mean and bottom amplitude of one cosine mode per unit flux coefficient.
    @param lam Wavenumbers in 1/m (array; 0 is the uniform mode).
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param h Bottom film in W/m2K.
    @return Tuple (surface, mean, bottom) of arrays in K per W/m2.
    """
    lam = np.asarray(lam, dtype=float)
    s, m, b = np.empty_like(lam), np.empty_like(lam), np.empty_like(lam)
    z = lam == 0.0
    # Uniform mode: a column, T = (q / h) (1 + h z / k)
    s[z], m[z], b[z] = (1 + h * t / k) / h, (1 + h * t / (2 * k)) / h, 1.0 / h
    l = lam[~z]
    beta = h / (k * l)
    th = np.tanh(l * t)
    sech = 2.0 * np.exp(-l * t) / (1.0 + np.exp(-2.0 * l * t))
    den = k * l * (th + beta)                                  # k Z'(t) / cosh(l t)
    s[~z] = (1.0 + beta * th) / den
    m[~z] = (th + beta * (1.0 - sech)) / (l * t) / den
    b[~z] = sech / den
    return s, m, b


def coef1d(x1, x2, n_modes):
    """!
    @brief Cosine coefficients of the indicator of [x1, x2] on [0, W].
    @param x1 Start in m.
    @param x2 End in m.
    @param n_modes Number of modes.
    @return Tuple (wavenumbers in 1/m, coefficients).
    """
    lam = np.arange(n_modes) * np.pi / W
    c = np.empty(n_modes)
    c[0] = (x2 - x1) / W
    c[1:] = 2.0 * (np.sin(lam[1:] * x2) - np.sin(lam[1:] * x1)) / lam[1:] / W
    return lam, c


def rect_ratio(t, k, b, c, n_modes=2000):
    """!
    @brief Parabola over true term at the centre of a centred rectangle b x c (exact coefficients).
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param b Side along y in m.
    @param c Side along x in m.
    @param n_modes Modes a side.
    @return float ratio.
    """
    m = W / 2
    lx, cx = coef1d(m - c / 2, m + c / 2, n_modes)
    ly, cy = coef1d(m - b / 2, m + b / 2, n_modes)
    s, mn, bt = kernels(np.sqrt(lx[None, :] ** 2 + ly[:, None] ** 2).ravel(), t, k)
    w = ((cy * np.cos(ly * m))[:, None] * (cx * np.cos(lx * m))[None, :]).ravel()
    true = w @ s - w @ mn
    return t * (2.0 + H * (w @ bt)) / (6.0 * k) / true


def strip_ratio(t, k, b, n_modes=200000):
    """!
    @brief Parabola over true term at the centre of a band of width b across the whole plate (the limit c >> b, a 1D problem).
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param b Band width in m.
    @param n_modes Number of modes.
    @return float ratio.
    """
    m = W / 2
    ly, cy = coef1d(m - b / 2, m + b / 2, n_modes)
    s, mn, bt = kernels(ly, t, k)
    w = cy * np.cos(ly * m)
    return t * (2.0 + H * (w @ bt)) / (6.0 * k) / (w @ s - w @ mn)


def shape_ratio(poly, t, k, n=2000):
    """!
    @brief Parabola over true term for any polygon: hottest surface minus hottest column over the part, from the series of the rasterized source.
    @param poly Vertices (m, 2) in m.
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param n Raster cells and modes a side.
    @return float ratio.
    """
    dx = W / n
    xc = (np.arange(n) + 0.5) * dx
    X, Y = np.meshgrid(xc, xc)
    mask = points_in_polygon(X.ravel(), Y.ravel(), np.asarray(poly)).reshape(n, n).astype(float)
    lam = np.arange(n) * np.pi / W
    sinc = np.ones(n)
    sinc[1:] = np.sin(lam[1:] * dx / 2) / (lam[1:] * dx / 2)
    fac = np.where(lam == 0, 1.0, 2.0) * dx / W * sinc     # exact integral of each cosine over each cell
    coef = dctn(mask, type=2, norm=None) / 4.0 * fac[:, None] * fac[None, :]
    s, mn, bt = (a.reshape(n, n) for a in kernels(np.sqrt(lam[:, None] ** 2 + lam[None, :] ** 2).ravel(), t, k))

    def back(kern):
        """!
        @brief The field at the cell centres from the mode amplitudes (inverse cosine transform).
        @param kern Amplitude per unit coefficient, (n, n).
        @return Field (n, n) in K per W/m2.
        """
        v = coef * kern
        v[1:, :] /= 2.0
        v[:, 1:] /= 2.0
        return dct(dct(v, type=3, axis=0, norm=None), type=3, axis=1, norm=None)

    ts, tm, tb = back(s), back(mn), back(bt)
    par = tm + t * (2.0 * mask + H * tb) / (6.0 * k)
    inside = mask > 0
    return (par[inside].max() - tm[inside].max()) / (ts[inside].max() - tm[inside].max())


def main():
    """!
    @brief Print the four tables: the cases of study_flag_rule.py, the strip and the square against t/a, the aspect ratio, and the non-rectangular parts.
    """
    print("1. The 19 rectangles of study_flag_rule.py (k W/mK, t mm, b x c mm): exact parabola/true at 1500 and 3000 modes")
    cases = [(385, 1, 2, 20), (385, 1, 2, 10), (385, 1, 5, 10), (385, 1, 10, 10),
             (385, 2, 2, 20), (385, 2, 2, 10), (385, 2, 2, 40), (385, 2, 3, 10), (385, 2, 4, 20), (385, 2, 5, 10), (385, 2, 5, 20), (385, 2, 10, 10), (385, 2, 10, 20), (385, 2, 20, 20),
             (385, 3, 5, 10), (385, 3, 4, 20), (150, 2, 2, 20), (150, 2, 5, 10), (150, 2, 10, 10)]
    for k, t, b, c in cases:
        r1 = rect_ratio(t * 1e-3, float(k), b * 1e-3, c * 1e-3, 1500)
        r2 = rect_ratio(t * 1e-3, float(k), b * 1e-3, c * 1e-3, 3000)
        print(f"   {k:3d} | {t} | {b:2d} x {c:2d} | t/b {t / b:.2f} | {r1:.4f} {r2:.4f} | overshoot {r2 > 1 + TOL} | flag {t / b > thickness.UPPER_RATIO}")
    t, k = 2e-3, 385.0
    print("2. Ratio against t/a (t 2 mm, k 385): infinite strip of width a, square of side a")
    for ta in (0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 1.0, 1.5, 2.0):
        print(f"   t/a {ta:.2f} | strip {strip_ratio(t, k, t / ta):.4f} | square {rect_ratio(t, k, t / ta, t / ta):.4f}")
    print("3. Aspect c/b at t/b = 1 and 0.5 (t 2 mm)")
    for cb in (1, 1.5, 2, 3, 5, 10, 20):
        print(f"   c/b {cb:4} | t/b 1: {rect_ratio(t, k, 2e-3, 2e-3 * cb):.4f} | t/b 0.5: {rect_ratio(t, k, 4e-3, 4e-3 * cb):.4f}")
    print("4. Other shapes on 2 mm, k 385 (hottest surface minus hottest column over the part)")
    m = W / 2
    x0 = y0 = m - 10e-3
    shapes = []
    for w in (2e-3, 3e-3, 4e-3):
        shapes.append((f"L arms {w * 1e3:.0f} x 20 mm", [(x0, y0), (x0 + 20e-3, y0), (x0 + 20e-3, y0 + w), (x0 + w, y0 + w), (x0 + w, y0 + 20e-3), (x0, y0 + 20e-3)]))
    w = 2e-3
    shapes.append(("U arms 2 x 20 mm", [(x0, y0), (x0 + 20e-3, y0), (x0 + 20e-3, y0 + 20e-3), (x0 + 20e-3 - w, y0 + 20e-3), (x0 + 20e-3 - w, y0 + w),
                                         (x0 + w, y0 + w), (x0 + w, y0 + 20e-3), (x0, y0 + 20e-3)]))
    for deg in (45, 17):
        th = np.radians(deg)
        rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        shapes.append((f"strip 2 x 20 mm at {deg} deg", np.array([(-10e-3, -1e-3), (10e-3, -1e-3), (10e-3, 1e-3), (-10e-3, 1e-3)]) @ rot.T + m))
    for d in (4e-3, 3e-3):
        shapes.append((f"disc d {d * 1e3:.0f} mm", m + d / 2 * np.array([(np.cos(a), np.sin(a)) for a in np.linspace(0, 2 * np.pi, 129)[:-1]])))
    shapes.append(("10 x 10 mm square + 1 x 4 mm tab", [(m - 5e-3, m - 5e-3), (m + 5e-3, m - 5e-3), (m + 5e-3, m - 0.5e-3), (m + 9e-3, m - 0.5e-3), (m + 9e-3, m + 0.5e-3),
                                                        (m + 5e-3, m + 0.5e-3), (m + 5e-3, m + 5e-3), (m - 5e-3, m + 5e-3)]))
    for name, poly in shapes:
        poly = np.asarray(poly, dtype=float)
        root_a = np.sqrt(polygon_area(poly))
        a = thickness.source_width(poly)
        r = shape_ratio(poly, t, k)
        print(f"   {name:32s} | t/sqrt(A) {t / root_a:.2f} | t/a {t / a:.2f} (a = source_width {a * 1e3:.2f} mm) | ratio {r:.3f} | overshoot {r > 1 + TOL} | flag {t / a > thickness.UPPER_RATIO}")
    print("5. The program (FVM, 0.5 mm cells, 10 W) against the series on the same plate: hottest surface and hottest column under the part, rise in K")
    for name, poly in (shapes[0], shapes[4]):
        print(f"   {name:32s} | {program_vs_series(np.asarray(poly, dtype=float), t, k)}")


def program_vs_series(poly, t, k, power=10.0, cell_mm=0.5):
    """!
    @brief Solve the same plate with the program's FVM and compare its surface and column read-outs and its flag with the exact series.
    @param poly Vertices (m, 2) in m.
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param power Source power in W.
    @param cell_mm FVM cell in mm.
    @return str one line of the table.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.model import Materials
    # The plate of tests/test_thickness.plate: full copper of thickness t on a laminate of 0.01 % of t, top insulated, film H below, adiabatic edges
    p = Problem.new(W * 1e3, W * 1e3, layers=1, thickness_mm=1.0001 * t * 1e3, copper_um=t * 1e6, ambient=25.0, h_top=1e-6, h_bottom=H, h_side=None,
                    materials=Materials(k_copper=k))
    p.add_full_copper()
    p.add_heater(1, power, polygon=(poly * 1e3).tolist(), name="S")
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=cell_mm)).results["fvm"]
    surf, col = r.extras["t_max_surface_top"] - 25.0, float(np.nanmax(r.T[0])) - 25.0
    # The series per unit flux, scaled by q = P / A
    n = 2000
    dx = W / n
    xc = (np.arange(n) + 0.5) * dx
    X, Y = np.meshgrid(xc, xc)
    mask = points_in_polygon(X.ravel(), Y.ravel(), poly).reshape(n, n).astype(float)
    lam = np.arange(n) * np.pi / W
    sinc = np.ones(n)
    sinc[1:] = np.sin(lam[1:] * dx / 2) / (lam[1:] * dx / 2)
    fac = np.where(lam == 0, 1.0, 2.0) * dx / W * sinc
    coef = dctn(mask, type=2, norm=None) / 4.0 * fac[:, None] * fac[None, :]
    s, mn, _ = (a.reshape(n, n) for a in kernels(np.sqrt(lam[:, None] ** 2 + lam[None, :] ** 2).ravel(), t, k))
    q = power / polygon_area(poly)
    fields = []
    for kern in (s, mn):
        v = coef * kern
        v[1:, :] /= 2.0
        v[:, 1:] /= 2.0
        fields.append(q * dct(dct(v, type=3, axis=0, norm=None), type=3, axis=1, norm=None))
    inside = mask > 0
    es, ec = fields[0][inside].max(), fields[1][inside].max()
    return (f"program surface {surf:.3f} column {col:.3f} term {surf - col:.3f} | series surface {es:.3f} column {ec:.3f} term {es - ec:.3f} | "
            f"term ratio {(surf - col) / (es - ec):.2f} | flag {bool(r.arrays['T_surface_flag'][0].any())}")


if __name__ == "__main__":
    main()
