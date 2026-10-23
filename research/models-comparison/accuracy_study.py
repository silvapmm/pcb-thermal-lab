"""!
@file accuracy_study.py
@brief Accuracy of the simplified models against the FVM on the example board and its variants.

Usage: python research/models-comparison/accuracy_study.py [--markdown table.md]
"""

import argparse
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import analytic, fvm, lumped                                    # noqa: E402
from pcbthermal.examples import example_board                                   # noqa: E402
from pcbthermal.model import problem_from_dict, problem_to_dict, reference_problem   # noqa: E402

FULL = [[0, 0], [100, 0], [100, 80], [0, 80]]


def cases():
    """!
    @brief The studied boards.
    @return List of (name, Problem).
    """
    base = problem_to_dict(example_board())

    def variant(edit):
        d = copy.deepcopy(base)
        edit(d)
        return problem_from_dict(d)

    def only_a(d):
        d["heaters"] = d["heaters"][:1]

    def clean(d):
        d.update(heatsinks=[], vias=[])
        d["zones"][0]["polygon_mm"] = FULL

    out = [("reference board (centred 20 mm heater)", reference_problem()),
           ("example board (full)", example_board()),
           ("example, no heatsink", variant(lambda d: d.update(heatsinks=[]))),
           ("example, no vias", variant(lambda d: d.update(vias=[]))),
           ("example, top copper over the full board", variant(lambda d: d["zones"][0].update(polygon_mm=FULL))),
           ("example, uniform (no heatsink, no vias, full copper)", variant(clean)),
           ("example, only heater U1", variant(only_a)),
           ("example, only U1, uniform", variant(lambda d: (only_a(d), clean(d))))]
    d = problem_to_dict(reference_problem())
    d["heaters"][0]["polygon_mm"] = [[10, 10], [30, 10], [30, 30], [10, 30]]
    out.append(("reference board, heater in the corner", problem_from_dict(d)))
    out.append(("reference board, small 5 mm heater", reference_problem(heater_mm=5.0, power=3.0)))
    out.append(("reference board, 8 layers", reference_problem(layers=8)))
    return out


def run():
    """!
    @brief Run every case with the three models.
    @return Markdown table.
    """
    lines = ["| Case | FVM Tmax [°C] | Lumped Tmax | Lumped ΔT error | Analytic Tmax | Analytic ΔT error | Analytic warns |",
             "| :-- | --: | --: | --: | --: | --: | :-: |"]
    for name, p in cases():
        f = fvm.solve_steady(p, cell_mm=1.0)
        l = lumped.solve_steady(p)
        a = analytic.solve_steady(p)
        lines.append(f"| {name} | {f.t_max:.2f} | {l.t_max:.2f} | {100 * (l.delta_t / f.delta_t - 1):+.1f} % | "
                     f"{a.t_max:.2f} | {100 * (a.delta_t / f.delta_t - 1):+.1f} % | {'yes' if a.warnings else '-'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown")
    a = ap.parse_args()
    md = run()
    print(md)
    if a.markdown:
        open(a.markdown, "w", encoding="utf-8").write(md)
