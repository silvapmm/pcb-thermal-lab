"""!
@file study_sampling.py
@brief Q4: how many sub-samples per cell side the per-point union needs, and how the error depends on the cell size and on where the zone edges fall.
@details Question answered: is the 4 x 4 lattice of the program enough? The union of two zones that tile the board has no edge of its own (the answer is full copper for any lattice), so the sampling
         only matters at the true edges of the copper. The test board is therefore cut by a clearance (gap) of 0.25 mm between two zones, along a line at 0, 15, 30 or 45 degrees whose position is
         scanned over one cell. Two measures against the same board sampled with 64 x 64 points per cell (area to 1/4096): (1) the cell fill field (maximum and mean absolute error, and the error of
         the total copper area in cell units), (2) the FVM peak rise (relative to the rise), for s = 2, 3, 4, 8, 16 and cells of 0.5, 1.0 and 2.0 mm. The 64-point value is the converged
         program; its distance from the independent solver on the resolved copper is a separate small table (reference at 0.125 mm). The error of the old rule (max per cell) is added to (2).
         Run from the repository root: .venv/bin/python research/zone-union/scripts/study_sampling.py ; writes out/study_sampling.json and out/study_sampling.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import os

import numpy as np

import variant
from paths import OUT

SAMPLES = (2, 3, 4, 8, 16)
ANGLES = (0, 15, 30, 45)
CELLS = (0.5, 1.0, 2.0)
GAP = 0.25                                           # Clearance between the two zones (mm)
N_OFFSETS = 4                                        # Positions of the gap over one cell


def zones_of(cases, ang, off):
    """!
    @brief The two zones of a board cut by the gap.
    @param cases The cases module.
    @param ang Angle of the gap line (degrees).
    @param off Position of the gap centre (mm).
    @return list of two zone-like objects in metres.
    """
    a, b = cases.split_board_gap(ang, off, GAP)
    return [type("Z", (), {"polygon": q * 1e-3, "fill": 1.0, "layer": 0}) for q in (a, b)]


def fill_error(zr, cases, cell):
    """!
    @brief Errors of the cell fill for every sample count, worst over the angles and positions.
    @param zr The zone_rules module.
    @param cases The cases module.
    @param cell Cell size (mm).
    @return dict samples -> (max abs fill error, mean abs fill error, copper area error in cells).
    """
    n = int(round(20.0 / cell))
    dx = 20e-3 / n
    offs = np.arange(N_OFFSETS) * cell / N_OFFSETS + 0.037                # not on a grid line, scanned over one cell
    worst = {s: [0.0, 0.0, 0.0] for s in SAMPLES}
    for ang in ANGLES:
        for off in offs:
            zs = zones_of(cases, ang, off)
            g = zr.combine(zs, 1, n, n, dx, dx, 64, "max_point")[0]
            for s in SAMPLES:
                f = zr.combine(zs, 1, n, n, dx, dx, s, "max_point")[0]
                w = worst[s]
                w[0] = max(w[0], float(np.abs(f - g).max()))
                w[1] = max(w[1], float(np.abs(f - g).mean()))
                w[2] = max(w[2], abs(float(f.sum() - g.sum())))
    return {s: tuple(v) for s, v in worst.items()}


def peak_error(cases, cell):
    """!
    @brief FVM peak-rise error for every sample count against the 64-point value, worst over the angles and positions; and the old rule against the same value.
    @param cases The cases module.
    @param cell Cell size (mm).
    @return tuple (dict samples -> worst error in % of the rise, worst error of the old rule in %).
    """
    from pcbthermal import SolverOptions, simulate
    offs = np.arange(N_OFFSETS) * cell / N_OFFSETS + 0.037
    res = {s: 0.0 for s in SAMPLES}
    old = 0.0
    for ang in ANGLES:
        for off in offs:
            a, b = cases.split_board_gap(ang, off, GAP)
            p = cases.new_problem()
            p.add_zone(1, polygon=a.tolist())
            p.add_zone(1, polygon=b.tolist())

            def run(rule, s):
                """!
                @brief FVM peak rise under a rule and a sample count.
                @param rule Zone rule.
                @param s Sub-samples per cell side.
                @return float Rise in K.
                """
                variant.set_rule(rule)
                os.environ["ZONE_SAMPLES"] = str(s)
                return simulate(p, SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].t_max - 25.0

            ref = run("max_point", 64)
            for s in SAMPLES:
                res[s] = max(res[s], abs(run("max_point", s) - ref) / ref * 100.0)
            old = max(old, abs(run("max_cell", 64) - ref) / ref * 100.0)
    os.environ.pop("ZONE_SAMPLES", None)
    return res, old


def reference_check(cases):
    """!
    @brief The 64-point program value against the independent solver on the resolved copper (0.125 mm), for gaps at 0 and 30 degrees.
    @param cases The cases module.
    @return list of (angle, offset, program FVM rise at 1 mm cells with 64 points, reference, error %).
    """
    import reference
    from pcbthermal import SolverOptions, simulate
    rows = []
    for ang, off in ((0, 0.25), (0, 0.5), (30, 0.37), (45, 0.62)):
        a, b = cases.split_board_gap(ang, off, GAP)
        p = cases.new_problem()
        p.add_zone(1, polygon=a.tolist())
        p.add_zone(1, polygon=b.tolist())
        variant.set_rule("max_point")
        os.environ["ZONE_SAMPLES"] = "64"
        prog = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max - 25.0
        os.environ.pop("ZONE_SAMPLES", None)
        r = reference.reference_rise(p, {0: [a * 1e-3, b * 1e-3]}, 0.125, n_lam=2)["max"]
        rows.append((ang, off, prog, r, 100 * (prog / r - 1)))
    return rows


def main():
    """!
    @brief Run the study and print the tables.
    @return None.
    """
    variant.use()
    import cases
    import zone_rules as zr
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s, flush=True)
        lines.append(s)

    result = {"fill": {}, "peak": {}, "peak_old": {}}
    out(f"Two zones separated by a clearance of {GAP} mm; fill error against 64 x 64 points per cell, worst over 4 angles x {N_OFFSETS} positions")
    out(f"{'cell':>6s}{'s':>4s}{'max |dfill|':>14s}{'mean |dfill|':>14s}{'copper area error (cells)':>28s}")
    for cell in CELLS:
        fe = fill_error(zr, cases, cell)
        result["fill"][str(cell)] = {str(s): v for s, v in fe.items()}
        for s, (a, b, c) in fe.items():
            out(f"{cell:6.1f}{s:4d}{a:14.4f}{b:14.5f}{c:28.4f}")
    out("\nFVM peak rise: error (% of the rise) against the 64-point value, worst over the same positions")
    out(f"{'cell':>6s}" + "".join(f"{'s=' + str(s):>10s}" for s in SAMPLES) + f"{'old rule':>12s}")
    for cell in CELLS:
        pe, po = peak_error(cases, cell)
        result["peak"][str(cell)] = {str(s): v for s, v in pe.items()}
        result["peak_old"][str(cell)] = po
        out(f"{cell:6.1f}" + "".join(f"{pe[s]:10.4f}" for s in SAMPLES) + f"{po:12.3f}")
    out("\nThe 64-point FVM (0.5 mm cells) against the independent solver on the resolved copper (0.125 mm cells)")
    out(f"{'angle':>6s}{'position':>10s}{'program K':>11s}{'reference K':>13s}{'error %':>9s}")
    result["reference"] = []
    for ang, off, prog, r, e in reference_check(cases):
        out(f"{ang:6d}{off:10.2f}{prog:11.3f}{r:13.3f}{e:9.2f}")
        result["reference"].append([ang, off, prog, r, e])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "study_sampling.json").write_text(json.dumps(result, indent=1))
    (OUT / "study_sampling.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
