#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_references.py
@brief Do the two prototypes (joule.py, pdn.py) agree with references that do not share their assumptions? Closed forms of a strip, an L bend and a ring sector, the hand counts of the
       nets of figures 2 and 3 with the pixel refined, an exact network composition, a current split of known answer, the electro-thermal loop against its closed form, and the cell sum.
@details Written by the review of this folder (README section "Review"). NumPy and SciPy only (no gerbonara): every geometry is built here or by the independent reader.
         1. Closed forms: a straight strip (Rs L / W), an L bend of equal legs (each corner square counts 0.559 squares, a classical conformal-map result) and a ring sector with the current
            running round it (R = Rs theta / ln(ro / ri)), with the four-point and the nine-point stencils and finer pixels.
         2. The net VIN of figure 2 (hand count 70 squares, 67 without the track under the end pads) and the arc net S1 of figure 3 (229 squares) with the pixel refined to 0.0125 mm, on a
            lattice shifted by 0.3 pixel so that no track edge falls on a pixel centre.
         3. pdn.py against the series circuit composed from joule.solve_net (R_A + R_link + R_B), the power of the terminal ties, two parallel strips sharing a current in the ratio of
            their widths, and a sink on a piece with no source.
         4. The electro-thermal loop: a track at one uniform temperature T = Ta + Rth I^2 R(T), solved by plain fixed point through joule.solve_net with rho(T), against the closed form
            T* = (Ta + K R20 (1 - 20 alpha)) / (1 - alpha K R20), K = Rth I^2; it converges with ratio alpha K R20 and has no solution (runaway) when alpha Rth I^2 R20 >= 1.
         5. joule.to_cells on a map whose size is not a multiple of the cell.
         Run: .venv/bin/python research/gerber-nets/scripts/study_references.py (from the repository root; about a minute).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-nets in order)

import math

import numpy as np
from scipy import ndimage

import joule
import native_gerber as ng
import our_board as ob
import pdn
from make_figures import synthetic_nets_gerber
from nets import disc, net_pads

RS20 = joule.RHO_CU_20C / 35e-6                     # ohm per square, 35 um copper at 20 C
SHIFT = 0.3                                         # lattice offset in pixels: no edge on a multiple of 0.0125 mm falls on a pixel centre


def strip_and_bend(w_px):
    """!
    @brief A straight strip and an L bend of width w_px pixels against their closed forms (four-point stencil, where both are axis-aligned).
    @param w_px Track width in pixels.
    @return Tuple (strip ratio, bend squares measured, bend squares expected).
    """
    L = 10 * w_px
    m = np.ones((w_px, L), bool)
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[:, -1] = True
    r = joule.solve_net(m, 1.0, s, k, 1.0)[0]
    strip = r / ((L - 1) / w_px)                                    # terminal pixel centres are L - 1 pixels apart
    n = w_px + 5 * w_px                                             # corner square plus a leg of five squares each way
    m = np.zeros((n, n), bool)
    m[:w_px, :] = True                                              # horizontal leg (with the corner square)
    m[:, :w_px] = True                                              # vertical leg
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:w_px, -1] = True; k[-1, :w_px] = True
    rb = joule.solve_net(m, 1.0, s, k, 1.0)[0]
    leg = (n - 1 - w_px + 0.5) / w_px                               # from the terminal pixel centre to the corner square edge, in squares
    return strip, rb, 2 * leg + 0.559


def ring_sector(pix, stencil, ri=1.0, ro=3.0, deg=90.0):
    """!
    @brief A ring sector with the current running round it, R = Rs theta / ln(ro / ri) (exact), against the solver; terminals are the pixels just beyond the two radial edges.
    @param pix Pixel size (mm).
    @param stencil "4" or "9".
    @param ri Inner radius (mm).
    @param ro Outer radius (mm).
    @param deg Angle of the sector (degrees); the terminal strips sit outside it.
    @return Ratio of the solved resistance to the exact one.
    """
    n = int(math.ceil((ro + 0.5) / pix)) + 2
    c = (np.arange(-n, n) + SHIFT) * pix
    X, Y = np.meshgrid(c, c)
    rr = np.hypot(X, Y)
    th = np.degrees(np.arctan2(Y, X))
    ring = (rr >= ri) & (rr <= ro)
    sector = ring & (th >= 0) & (th <= deg)
    # Equipotential terminals: a strip of 3 pixels on each side, just outside the radial edges (a bus bar along each radial edge)
    band = 3 * pix
    src = ring & (th < 0) & (Y > -band) & (X > 0)
    snk = ring & (th > deg) & (np.abs(X * math.sin(math.radians(deg)) - Y * math.cos(math.radians(deg))) < band) & (X * math.cos(math.radians(deg)) + Y * math.sin(math.radians(deg)) > 0)
    mask = sector | src | snk
    r = joule.solve_net(mask, 1.0, src, snk, 1.0, stencil=stencil)[0]
    return r / (math.radians(deg) / math.log(ro / ri))


def net_resistance(text, net, pix, stencil="4", shift=SHIFT, yshift=None):
    """!
    @brief Resistance of one net between its two farthest pads (disc terminals of 0.25 mm), drawn on a lattice shifted by SHIFT pixels.
    @param text Gerber text.
    @param net Net name.
    @param pix Pixel size (mm).
    @param stencil "4" or "9".
    @param shift Lattice offset in pixels (0 puts pixel centres on the odd multiples of half a pixel, where the edges of the 0.25 mm neck of VIN fall at 0.05 mm).
    @param yshift Offset in y when it differs from shift (0.5 with shift 0 is the lattice of make_figures.fig_nets).
    @return Tuple (resistance in ohm at 35 um copper, power at 1 A in W).
    """
    layer = ng.Layer(text)
    bb = layer.bbox()
    x_left = (math.floor((bb[0] - 0.3) / pix) - shift) * pix
    y_top = (math.ceil((bb[3] + 0.3) / pix) + (shift if yshift is None else yshift)) * pix
    cv = ng.Canvas(x_left, y_top, bb[2] + 0.3 - x_left, y_top - (bb[1] - 0.3), pix)
    layer.draw(cv, [net])
    pa = np.array(net_pads(layer, net))
    d = np.hypot(pa[:, None, 0] - pa[None, :, 0], pa[:, None, 1] - pa[None, :, 1])
    i, j = np.unravel_index(d.argmax(), d.shape)
    src = disc(cv.mask.shape, cv, pa[i][0], pa[i][1], 0.25) & cv.mask
    snk = disc(cv.mask.shape, cv, pa[j][0], pa[j][1], 0.25) & cv.mask
    r, _, q = joule.solve_net(cv.mask, RS20, src, snk, 1.0, stencil=stencil)
    return r, q.sum()


def network_checks():
    """!
    @brief pdn.py against an exact series composition, the power of the ties, a current split of known answer and a sink with no source.
    @return None (prints).
    """
    import study_pdn_links as spl
    mask, r, t = spl.scenario()
    rs = spl.RS
    # The two pieces solved alone with equipotential terminals (joule.py, no ties, no link): the series circuit gives the load voltage
    ra = joule.solve_net(mask, rs, t["vin"], t["out_pad"], 1.0)[0]
    rb = joule.solve_net(mask, rs, t["rect_a"], t["load"], 1.0)[0]
    v_series = 5.0 - 1.5 * (ra + 0.1 + rb)
    v_pdn = float(np.nanmean(r["V"][t["load"]]))
    print(f"  pdn load voltage {v_pdn:.6f} V; series circuit 5 - 1.5 (R_A {ra * 1e3:.4f} + 100 + R_B {rb * 1e3:.4f} mohm) = {v_series:.6f} V; difference {(v_pdn - v_series) * 1e6:+.2f} uV")
    print(f"  copper heat pdn {r['p_copper'] * 1e3:.4f} mW, series 1.5^2 (R_A + R_B) = {2.25 * (ra + rb) * 1e3:.4f} mW")
    bal = r["p_source"] - r["p_copper"] - r["p_links"] - r["p_sinks"]
    print(f"  balance source - copper - link - load = {bal * 1e3:+.6f} mW of {r['p_source'] * 1e3:.3f} mW ({bal / r['p_source']:+.1e} of the power)")
    # Two separate strips of widths 4 and 8 pixels between two common terminals: the current divides as the widths (exact for pixel strips)
    m = np.zeros((14, 40), bool)
    m[0:4, :] = True; m[6:14, :] = True
    a = np.zeros_like(m); b = np.zeros_like(m)
    a[:, 0] = True; b[:, -1] = True
    res = pdn.solve(m, 0.01, {"a": a, "b": b}, [("vsource", "a", 1.0), ("isink", "b", 3.0)])
    q = res["q"]
    r1, r2 = 0.01 * 39 / 4, 0.01 * 39 / 8
    i1, i2 = math.sqrt(q[0:4].sum() / r1), math.sqrt(q[6:14].sum() / r2)
    print(f"  current split of two strips 4 and 8 px wide at 3 A: {i1:.6f} A and {i2:.6f} A (exact 1 and 2 A)")
    # A sink on a piece with no voltage source: the current has no way in
    m = np.zeros((4, 30), bool)
    m[:, 0:12] = True; m[:, 16:30] = True
    t2 = {"vin": np.zeros_like(m), "load": np.zeros_like(m), "far": np.zeros_like(m)}
    t2["vin"][:, 0] = True; t2["load"][:, 11] = True; t2["far"][:, 29] = True
    try:
        res = pdn.solve(m, 0.01, t2, [("vsource", "vin", 5.0), ("isink", "far", 1.0)])
        print(f"  a 1 A sink on a piece with no source: no error; p_source {res['p_source']:.3g} W, p_sinks {res['p_sinks']:.3g} W (the current is lost)")
    except ValueError as exc:
        print(f"  a 1 A sink on a piece with no source is refused: {exc}")


def electro_thermal(rth, amps, ta=25.0, tol=1e-9, max_iter=10000):
    """!
    @brief The electro-thermal loop on a 0.2 mm x 20 mm track (100 squares) at one uniform temperature: plain fixed point through joule.solve_net against the closed form.
    @param rth Thermal resistance from the track to the ambient (K/W), a lumped stand-in for the thermal model.
    @param amps Current (A).
    @param ta Ambient temperature (degrees C).
    @param tol Stop when the temperature changes by less than this (K).
    @param max_iter Iteration cap.
    @return Tuple (alpha Rth I^2 R20, closed-form T or None at runaway, fixed-point T or None, iterations).
    """
    m = np.ones((4, 401), bool)                                     # 4 px across, 400 px between terminal centres: 100 squares
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[:, -1] = True
    r20 = joule.solve_net(m, RS20, s, k, amps)[0]
    a = joule.ALPHA_CU
    kk = rth * amps ** 2
    slope = a * kk * r20
    exact = (ta + kk * r20 * (1 - 20 * a)) / (1 - slope) if slope < 1 else None
    temp = ta
    for it in range(1, max_iter + 1):
        r = joule.solve_net(m, joule.resistivity(temp) / 35e-6, s, k, amps)[0]
        new = ta + kk * r
        if new > 1500.0:
            return slope, exact, None, it
        if abs(new - temp) < tol:
            return slope, exact, new, it
        temp = new
    return slope, exact, None, max_iter


def main():
    """!
    @brief Run every check and print the numbers quoted in README section "Review".
    @return None.
    """
    print("1. closed forms (four-point stencil on axis-aligned copper)")
    for w in (4, 10, 20):
        s, rb, eb = strip_and_bend(w)
        print(f"  width {w:2d} px: strip R / (Rs (L-1)/W) = {s:.6f}; L bend {rb:.4f} squares against {eb:.4f} (legs + 0.559 corner): {100 * (rb / eb - 1):+.2f} %")
    print("  ring sector ri 1, ro 3 mm, 90 degrees, R = Rs theta / ln(ro/ri) = 1.4298 Rs (the centre-line count would say 1.5708 Rs)")
    for pix in (0.1, 0.05, 0.025):
        print(f"    pixel {pix:5.3f} mm ({2 / pix:.0f} px across): four-point {ring_sector(pix, '4'):.4f}, nine-point {ring_sector(pix, '9'):.4f} of the exact R")
    print("\n2. the nets of figures 2 and 3 with the pixel refined (lattice shifted by 0.3 px: no edge on a pixel centre)")
    text = text_vin = synthetic_nets_gerber()
    for pix in (0.05, 0.025, 0.0125):
        r4, p4 = net_resistance(text, "VIN", pix)
        r9, _ = net_resistance(text, "VIN", pix, "9")
        print(f"  VIN, pixel {pix:6.4f} mm: R {r4 * 1e3:.2f} mohm (I2R at 1 A {p4 * 1e3:.2f} mW), nine-point {r9 * 1e3:.2f}; hand count 70 squares {70 * RS20 * 1e3:.2f}, 67 squares {67 * RS20 * 1e3:.2f} mohm")
    r0, _ = net_resistance(text, "VIN", 0.05, shift=0.0)
    print(f"  VIN, pixel 0.05 mm on a lattice whose pixel centres fall on the edges of the neck (a tie): R {r0 * 1e3:.2f} mohm")
    print("  VIN on the lattice of figure 2 (make_figures.fig_nets, tie-free only at 0.05 mm): " + ", ".join(f"{net_resistance(text_vin, 'VIN', p, shift=0.0, yshift=0.5)[0] * 1e3:.2f} mohm at {p} mm" for p in (0.05, 0.025, 0.0125)))
    sq = ob.squares(0)
    text = ob.gerber_text()
    for pix in (0.05, 0.025, 0.0125):
        r4, _ = net_resistance(text, "S1", pix)
        r9, _ = net_resistance(text, "S1", pix, "9")
        print(f"  S1, pixel {pix:6.4f} mm ({0.2 / pix:.0f} px across): R {r4 * 1e3:.1f} mohm ({100 * (r4 / (sq * RS20) - 1):+.1f} %), nine-point {r9 * 1e3:.1f} ({100 * (r9 / (sq * RS20) - 1):+.1f} %); hand count {sq:.1f} squares = {sq * RS20 * 1e3:.1f} mohm")
    print("\n3. pdn.py against an exact network")
    network_checks()
    print("\n4. electro-thermal loop on a 0.2 x 20 mm track (100 squares, 48 mohm at 20 C), lumped Rth, constant current")
    for rth, amps in ((50.0, 1.0), (50.0, 5.0), (100.0, 5.0), (100.0, 6.5), (100.0, 7.5)):
        slope, exact, fp, it = electro_thermal(rth, amps)
        ex = f"{exact:.4f} C" if exact is not None else "none (runaway)"
        got = f"{fp:.4f} C in {it} iterations" if fp is not None else f"no fixed point (stopped after {it} iterations)"
        print(f"  Rth {rth:5.0f} K/W, I {amps:3.1f} A: alpha Rth I^2 R20 = {slope:.3f}; closed form {ex}; fixed point {got}")
    print("  runaway current of this track: I = 1 / sqrt(alpha Rth R20) = " + ", ".join(f"{1 / math.sqrt(joule.ALPHA_CU * rth * 100 * RS20):.2f} A at {rth:.0f} K/W" for rth in (50.0, 100.0)))
    print("\n5. joule.to_cells on a map whose size is not a multiple of the cell")
    q = np.ones((7, 9))
    print(f"  7 x 9 pixels of 1 W in cells of 2 x 2: {joule.to_cells(q, 2).shape} cells, total {joule.to_cells(q, 2).sum():.1f} W of {q.sum():.1f} W")


if __name__ == "__main__":
    main()
