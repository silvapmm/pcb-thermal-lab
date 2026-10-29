"""!
@file study_fix_impact.py
@brief The measured impact of the two program changes proposed by the research: how the zones are combined, and the laminate under a single copper layer in the 3D solid.
@details Run once per variant of the program, with PYTHONPATH pointing at it, giving a tag: `max` (the program as it is), `additive` (np.minimum(fill + coverage, 1), the first idea), `union` (the maximum per sample point,
         geometry.zone_fill: overlap keeps the larger fill, abutting zones add up) and `union_lam` (union plus the laminate slab under a single copper layer in solid3d.py). Each run writes out/fix_impact_<tag>.json with the peak
         temperature of every model on: a board of 0.5 mm strips against one zone (abutting zones), two overlapping zones of fill 0.5 (overlap), the three example boards of the repository, and single-layer boards with the 3D solid.
         `--compare` prints the tables of the differences against the program as it is.
         Run: PYTHONPATH=<variant>:. .venv/bin/python research/gerber-models/scripts/study_fix_impact.py <tag>; then .venv/bin/python research/gerber-models/scripts/study_fix_impact.py --compare (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json
import sys

from paths import OUT, REPO

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def peaks(p, models=MODELS, cell=1.0):
    """!
    @brief Peak temperature rise of every model on a problem.
    @param p Problem.
    @param models Model keys.
    @param cell Cell (mm).
    @return dict model -> rise (K), or the error name.
    """
    from pcbthermal import SolverOptions, simulate
    out = {}
    for m in models:
        try:
            out[m] = round(simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - p.board.ambient, 3)
        except Exception as e:                                                # reported, not hidden
            out[m] = f"{type(e).__name__}"
    return out


def run(tag):
    """!
    @brief Run the cases for the program on the import path and save out/fix_impact_<tag>.json.
    @param tag Name of the variant.
    @return None.
    """
    from pcbthermal import Problem
    from pcbthermal.project import load_project
    res = {}

    def board(layers=1):
        """!
        @brief A 20 x 20 mm board with a 4 x 4 mm heater.
        @param layers Copper layers.
        @return Problem.
        """
        p = Problem.new(width_mm=20, height_mm=20, layers=layers, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=None)
        p.add_heater(1, 1.0, rect=(8, 8, 12, 12))
        return p

    p = board()
    p.add_zone(1, rect=(0, 0, 20, 20))
    res["one zone (reference of the strips)"] = peaks(p)
    p = board()
    for j in range(40):
        p.add_zone(1, rect=(0.5 * j, 0, 0.5 * (j + 1), 20))
    res["the same copper in 40 abutting strips"] = peaks(p)
    p = board()
    p.add_zone(1, rect=(0, 0, 20, 20), fill=0.5).add_zone(1, rect=(0, 0, 20, 20), fill=0.5)
    res["two overlapping zones of fill 0.5"] = peaks(p)
    p = board()
    p.add_zone(1, rect=(0, 0, 20, 20), fill=0.5)
    res["one zone of fill 0.5 (reference of the overlap)"] = peaks(p)
    p = board()
    p.add_zone(1, rect=(0, 0, 12, 20), fill=0.8).add_zone(1, rect=(8, 0, 20, 20), fill=0.4)
    res["partly overlapping zones, fills 0.8 and 0.4"] = peaks(p)
    for name in ("example_board", "profile_board", "reference_board"):
        pr = load_project(REPO / "examples" / f"{name}.pcbt.json")
        pr = getattr(pr, "problem", pr)
        res[f"example: {name} ({pr.board.layers} layers)"] = peaks(pr, cell=1.0)
    p = board(1)
    p.add_zone(1, rect=(5, 5, 15, 15))
    res["single-layer board, pad 10 x 10"] = peaks(p)
    p = board(2)
    p.add_zone(1, rect=(5, 5, 15, 15))
    res["two-layer board, pad 10 x 10 on top"] = peaks(p)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"fix_impact_{tag}.json").write_text(json.dumps(res, indent=1))
    print("saved", tag)


def compare():
    """!
    @brief Print the change of every case against the program as it is (tag max).
    @return None.
    """
    tags = [t for t in ("max", "additive", "union", "union_lam") if (OUT / f"fix_impact_{t}.json").exists()]
    data = {t: json.loads((OUT / f"fix_impact_{t}.json").read_text()) for t in tags}
    for case in data["max"]:
        print(f"\n{case}: peak rise (K) in the program as it is, and change (%) with each variant")
        print(f"{'':12s}" + "".join(f"{m:>12s}" for m in MODELS))
        print(f"{'max (today)':12s}" + "".join(f"{data['max'][case][m]!s:>12}" for m in MODELS))
        for t in tags[1:]:
            row = f"{t:12s}"
            for m in MODELS:
                a, b = data["max"][case][m], data[t][case].get(m)
                row += f"{100 * (b / a - 1):+11.1f}%" if isinstance(a, float) and isinstance(b, float) else f"{'-':>12s}"
            print(row)


if __name__ == "__main__":
    if sys.argv[1:] == ["--compare"]:
        compare()
    else:
        run(sys.argv[1])
