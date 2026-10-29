"""!
@file study_edge_cases.py
@brief Q6: the edge cases of the zone union: zones partly or wholly outside the board, boards with an outline, degenerate and self-intersecting polygons, vias and a metal block on split copper, the heat capacity and time constant, and the input checks.
@details Question answered: does the per-point union behave on the situations around the ordinary case, and does it agree with the one-zone drawing of the same copper where it must?
         Every comparison is "the copper drawn as pieces" against "the same copper drawn as one zone" (the second has no seam, so it is the exact answer for any rule that is a union of the copper), in the old rule (ZONE_RULE=max_cell on the
         variant; the FDM of `develop` differs, see study_cases.py) and in the per-point union (max_point). Peak rises (K) of the five models, 1 mm cells, unless said.
         Run from the repository root: .venv/bin/python research/zone-union/scripts/study_edge_cases.py ; writes out/study_edge_cases.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np

import variant
from paths import OUT

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def run_models(p, cell=1.0):
    """!
    @brief Peak rise of every model; errors are reported by name.
    @param p Problem.
    @param cell Cell (mm).
    @return dict.
    """
    from pcbthermal import SolverOptions, simulate
    out = {}
    for m in MODELS:
        try:
            out[m] = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - p.board.ambient
        except Exception as e:                                       # reported, not hidden
            out[m] = f"{type(e).__name__}"
    return out


def winding_inside(px, py, poly):
    """!
    @brief Points inside a polygon under the non-zero winding rule (the rule of PostScript and SVG; the program uses even-odd).
    @param px x of the points.
    @param py y of the points.
    @param poly Polygon (n, 2).
    @return numpy.ndarray of bool.
    """
    wn = np.zeros(px.shape, dtype=int)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cross = (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)
        up = (y0 <= py) & (y1 > py) & (cross > 0)
        down = (y0 > py) & (y1 <= py) & (cross < 0)
        wn += up.astype(int) - down.astype(int)
    return wn != 0


def fmt(d):
    """!
    @brief One line of numbers.
    @param d dict model -> value.
    @return str.
    """
    return " ".join(f"{d[m]:9.3f}" if isinstance(d[m], float) else f"{str(d[m])[:9]:>9s}" for m in MODELS)


def main():
    """!
    @brief Run every edge case and print the tables.
    @return None.
    """
    variant.use()
    import cases
    from cases import rect
    from pcbthermal import fvm
    from pcbthermal.checks import check_problem
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s, flush=True)
        lines.append(s)

    def compare(title, pieces, whole, cell=1.0, tweak=None):
        """!
        @brief Peak rises of a board drawn as pieces and as one piece, old rule and union.
        @param title Case title.
        @param pieces Function p -> None adding the zones of the pieces.
        @param whole Function p -> None adding the one-zone drawing.
        @param cell Cell (mm).
        @param tweak Optional function p -> None applied to both problems (outline, vias, ...).
        @return None.
        """
        res = {}
        for name, f in (("pieces", pieces), ("whole", whole)):
            p = cases.new_problem()
            if tweak:
                tweak(p)
            f(p)
            for rule in ("max_cell", "max_point"):
                variant.set_rule(rule)
                res[(name, rule)] = run_models(p, cell)
        out(f"\n{title}   (peak rise K; models {', '.join(MODELS)})")
        out(f"  {'one zone (reference of the pieces)':44s}" + fmt(res[("whole", "max_point")]))
        out(f"  {'pieces, old rule':44s}" + fmt(res[("pieces", "max_cell")]))
        out(f"  {'pieces, per-point union':44s}" + fmt(res[("pieces", "max_point")]))
        diff = {m: (res[("pieces", "max_point")][m] - res[("whole", "max_point")][m]) if isinstance(res[("pieces", "max_point")][m], float) and isinstance(res[("whole", "max_point")][m], float) else "-" for m in MODELS}
        out(f"  {'union minus one zone (K)':44s}" + fmt(diff))

    out("1. Zones partly or wholly outside the board (20 x 20 mm board; the zones are cut at x = 10.37 mm)")
    compare("   both pieces reach 5 mm beyond the board",
            lambda p: (p.add_zone(1, rect=(-5, -5, 10.37, 25)), p.add_zone(1, rect=(10.37, -5, 25, 25))),
            lambda p: p.add_zone(1, rect=(-5, -5, 25, 25)))
    compare("   a third zone entirely outside the board",
            lambda p: (p.add_zone(1, rect=(0, 0, 10.37, 20)), p.add_zone(1, rect=(10.37, 0, 20, 20)), p.add_zone(1, rect=(30, 30, 40, 40))),
            lambda p: p.add_zone(1, rect=(0, 0, 20, 20)))

    out("\n2. A board with an outline (T of 20 x 20 mm: bar 8 mm high on top, stem 6 mm wide), the copper cut at x = 10.37 mm through the stem and the bar")
    T = np.array([[0, 12], [20, 12], [20, 20], [0, 20], [0, 12], [7, 12], [7, 0], [13, 0], [13, 12]], dtype=float)
    Tout = np.array([[0, 12], [7, 12], [7, 0], [13, 0], [13, 12], [20, 12], [20, 20], [0, 20]], dtype=float) * 1e-3

    def with_outline(p):
        """!
        @brief Give the problem the T outline and a heater in the stem.
        @param p Problem.
        @return None.
        """
        p.board.outline = Tout
        p.heaters.clear()
        p.add_heater(1, 1.0, rect=(8, 4, 12, 8))
    compare("   T board",
            lambda p: (p.add_zone(1, rect=(0, 0, 10.37, 20)), p.add_zone(1, rect=(10.37, 0, 20, 20))),
            lambda p: p.add_zone(1, rect=(0, 0, 20, 20)), tweak=with_outline)

    out("\n3. Degenerate and self-intersecting polygons (area of the cell field on a 20 x 20 grid of 1 mm cells, in cells; program rule = even-odd)")
    import zone_rules as zr
    nx = ny = 20
    shapes = {
        "zero area (three collinear points)": np.array([[2, 2], [8, 2], [14, 2]], dtype=float) * 1e-3,
        "degenerate triangle (two coincident vertices)": np.array([[2, 2], [2, 2], [8, 8]], dtype=float) * 1e-3,
        "bow tie (two triangles joined at a crossing)": np.array([[1, 1], [10, 10], [10, 1], [1, 10]], dtype=float) * 1e-3,
        "pentagram (self-intersecting star)": np.array([[10 + 9 * np.sin(np.radians(144 * k)), 10 + 9 * np.cos(np.radians(144 * k))] for k in range(5)]) * 1e-3,
    }
    out(f"  {'polygon':58s}{'even-odd (program)':>20s}{'non-zero winding':>18s}")
    for name, poly in shapes.items():
        z = type("Z", (), {"polygon": poly, "fill": 1.0, "layer": 0})
        try:
            f = zr.combine([z], 1, nx, ny, 1e-3, 1e-3, 4, "max_point")[0].sum()
        except Exception as e:
            f = float("nan")
            name += f"  [{type(e).__name__}]"
        sub = (np.arange(4) + 0.5) / 4
        gx, gy = np.meshgrid(((np.arange(nx)[:, None] + sub).ravel()) * 1e-3, ((np.arange(ny)[:, None] + sub).ravel()) * 1e-3)
        nz = winding_inside(gx.ravel(), gy.ravel(), poly).mean() * nx * ny
        out(f"  {name:58s}{f:20.2f}{nz:18.2f}")
    out("  (the Gerber specification forbids self-intersecting contours, 2.6; the program has no check for them: README 7.3)")

    out("\n4. Vias and a metal block on split copper (two-layer board, via array under the part, aluminium block 2 mm thick on the top copper; cut at x = 10.37 mm on both layers)")

    def with_via_block(p):
        """!
        @brief Add a via array and a block over the part.
        @param p Problem.
        @return None.
        """
        p.add_via_array(rect=(8.5, 8.5, 11.5, 11.5), nx=3, ny=3, diameter=0.3)
        p.add_heatsink(1, 10.0, rect=(5, 5, 15, 15), thickness_mm=2.0)
    lay2 = lambda p: None
    res = {}
    for name in ("pieces", "whole"):
        for rule in ("max_cell", "max_point"):
            p = cases.new_problem(layers=2)
            with_via_block(p)
            if name == "pieces":
                for k in (1, 2):
                    p.add_zone(k, rect=(0, 0, 10.37, 20))
                    p.add_zone(k, rect=(10.37, 0, 20, 20))
            else:
                for k in (1, 2):
                    p.add_zone(k, rect=(0, 0, 20, 20))
            variant.set_rule(rule)
            res[(name, rule)] = run_models(p)
    out(f"  {'one zone per layer':44s}" + fmt(res[("whole", "max_point")]))
    out(f"  {'pieces, old rule':44s}" + fmt(res[("pieces", "max_cell")]))
    out(f"  {'pieces, per-point union':44s}" + fmt(res[("pieces", "max_point")]))

    out("\n5. Heat capacity and time constant of the FVM network (1 mm cells; the copper of 40 abutting strips of 0.5 mm against one zone)")
    for name, zs in (("one zone", None), ("40 strips", True)):
        for rule in ("max_cell", "max_point"):
            if name == "one zone" and rule == "max_cell":
                continue
            p = cases.new_problem()
            if zs:
                for j in range(40):
                    p.add_zone(1, rect=(0.5 * j, 0, 0.5 * (j + 1), 20))
            else:
                p.add_zone(1, rect=(0, 0, 20, 20))
            variant.set_rule(rule)
            net = fvm.Network(p, 20, 20, assemble=False)
            out(f"  {name:10s} {rule:10s}  total heat capacity {net.C.sum():9.4f} J/K   time constant {fvm.board_time_constant(net):8.3f} s   mean copper fill {net.fill.mean():.4f}")

    out("\n6. Input checks (check_problem, 1 mm cells) on the same copper: the strips drawn under the heater")
    for rule in ("max_cell", "max_point"):
        p = cases.new_problem()
        for j in range(40):
            p.add_zone(1, rect=(0.5 * j, 0, 0.5 * (j + 1), 20))
        variant.set_rule(rule)
        w = [str(x) for x in check_problem(p, 1.0)]
        out(f"  {rule:10s} warnings: {w if w else 'none'}")
    p = cases.new_problem()
    p.add_zone(1, rect=(0, 0, 20, 20))
    variant.set_rule("max_point")
    w = [str(x) for x in check_problem(p, 1.0)]
    out(f"  {'one zone':10s} warnings: {w if w else 'none'}")
    (OUT / "study_edge_cases.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
