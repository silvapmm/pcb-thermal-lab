"""!
@file stress_study.py
@brief Stress cases for the Lumped and Analytic models: where do they stop being reliable?

Usage: python research/models-comparison/stress_study.py [--markdown table.md]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import Problem, analytic, check_problem, fvm, lumped   # noqa: E402


def base():
    """!
    @brief A 100 x 80 mm, 4-layer board with full copper planes on the three lower layers.
    @return A Problem without heaters.
    """
    return Problem.new(100, 80, 4).add_full_copper([2, 3, 4])


def cases():
    """!
    @brief The stress boards.
    @return List of (name, Problem).
    """
    return [
        ("heater 5 mm inside the top-copper edge", base().add_zone(1, rect=(15, 15, 85, 65)).add_heater(1, 4.0, rect=(20, 35, 30, 45))),
        ("heater straddling the top-copper edge", base().add_zone(1, rect=(15, 15, 85, 65)).add_heater(1, 4.0, rect=(10, 35, 20, 45))),
        ("no copper on the heater layer", base().add_heater(1, 4.0, rect=(40, 35, 50, 45))),
        ("30 x 30 mm copper island around the heater", base().add_zone(1, rect=(35, 25, 65, 55)).add_heater(1, 4.0, rect=(45, 35, 55, 45))),
        ("hatched copper (fill 0.5) on the top layer", base().add_zone(1, rect=(0, 0, 100, 80), fill=0.5).add_heater(1, 4.0, rect=(45, 35, 55, 45))),
        ("heater on the bottom layer", base().add_zone(1, rect=(0, 0, 100, 80)).add_heater(4, 4.0, rect=(45, 35, 55, 45))),
        ("long thin heater, 40 x 4 mm", base().add_zone(1, rect=(0, 0, 100, 80)).add_heater(1, 4.0, rect=(30, 38, 70, 42))),
        ("heater in the corner (10 mm from two edges)", base().add_zone(1, rect=(0, 0, 100, 80)).add_heater(1, 4.0, rect=(10, 10, 20, 20))),
        ("two heaters 60 mm apart (4 W + 2 W)", base().add_zone(1, rect=(0, 0, 100, 80)).add_heater(1, 4.0, rect=(15, 35, 25, 45)).add_heater(1, 2.0, rect=(75, 35, 85, 45))),
    ]


def run():
    """!
    @brief Solve every stress case with the three models.
    @return Markdown table.
    """
    lines = ["| Case | FVM Tmax [°C] | Lumped Tmax | Lumped ΔT error | Analytic Tmax | Analytic ΔT error | Input check |",
             "| :-- | --: | --: | --: | --: | --: | :-- |"]
    for name, p in cases():
        f, l, a = fvm.solve_steady(p, cell_mm=1.0), lumped.solve_steady(p), analytic.solve_steady(p)
        w = check_problem(p, 1.0) + a.warnings
        lines.append(f"| {name} | {f.t_max:.2f} | {l.t_max:.2f} | {100 * (l.delta_t / f.delta_t - 1):+.1f} % | "
                     f"{a.t_max:.2f} | {100 * (a.delta_t / f.delta_t - 1):+.1f} % | {'warns' if w else '-'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown")
    a = ap.parse_args()
    md = run()
    print(md)
    if a.markdown:
        open(a.markdown, "w", encoding="utf-8").write(md)
