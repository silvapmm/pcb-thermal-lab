"""!
@file study_complex_boards.py
@brief How do the five models compare with the 3D solid on boards closer to real ones, and what did the corrections of the review change?

@details Nine boards: the example board (four layers, vias, a heatsink), the same with a metal block, a six-layer board with inner planes, a part on the bottom and
         via arrays, a two-layer round board, three one-layer boards (an LED strip with three pads, a power board in the vertical position with computed
         coefficients, a round one-layer board) and two one-layer boards with partial copper. Every board runs in the FVM, FDM, Lumped, Analytic and 3D solid; the
         3D solid is the reference (it has the real slabs, and on one-layer boards it agrees with an independent 3D solver within 0.2 %,
         research/effective-conductivity 4.11 on the research branch). The metric is the maximum temperature of the board as a rise over the ambient (the
         Lumped model gives its peak as a separate number, not in its field, so the maximum is the quantity every model reports in the same way); the error
         is against the 3D solid.

         The script imports the program from the folder given with --root (default: this repository), so the same boards can be run on an older version for a
         before/after comparison:

             git worktree add /tmp/pcbthermal-before <commit before the corrections>
             .venv/bin/python research/models-comparison/scripts/study_complex_boards.py --root /tmp/pcbthermal-before --out before.json
             .venv/bin/python research/models-comparison/scripts/study_complex_boards.py --out after.json
             .venv/bin/python research/models-comparison/scripts/study_complex_boards.py --compare before.json after.json

         Usage (from the repository root; about 2 minutes per run).
"""

import argparse
import contextlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CELL_MM = 1.0


def boards(api):
    """!
    @brief The boards of the study, built with the program's own builder.
    @param api Dict with the Problem class and the example builders of the program being tested.
    @return List of (name, Problem).
    """
    Problem, example_board, example_block_board = api["Problem"], api["example_board"], api["example_block_board"]
    out = [("example board (4 layers, vias, heatsink)", example_board()), ("example board with a metal block", example_block_board())]

    p = Problem.new(120.0, 90.0, layers=6, thickness_mm=1.6, copper_um=35)
    p.add_zone(1, rect=(10, 10, 60, 50)); p.add_zone(1, rect=(70, 20, 110, 70))
    p.add_full_copper([2, 5]); p.add_zone(3, rect=(5, 5, 115, 45)); p.add_zone(4, rect=(5, 50, 115, 85))
    p.add_zone(6, rect=(30, 55, 90, 85))
    p.add_heater(1, 3.0, rect=(25, 25, 35, 35), name="U1"); p.add_heater(1, 2.0, rect=(85, 40, 93, 48), name="U2")
    p.add_heater(6, 1.5, rect=(55, 65, 61, 71), name="U3 (bottom)")
    p.add_via_array((26, 26, 34, 34), 4, 4, diameter=0.3)
    p.add_via_array((56, 66, 60, 70), 3, 3, diameter=0.3)
    out.append(("6 layers, inner planes, a part on the bottom", p))

    rnd = [[40 + 39.5 * math.cos(a), 40 + 39.5 * math.sin(a)] for a in (2 * math.pi * k / 72 for k in range(72))]
    p = Problem.new(80.0, 80.0, layers=2).add_full_copper()
    p.add_heater(1, 2.5, rect=(34, 34, 46, 46), name="U1"); p.add_heater(1, 1.0, rect=(15, 37, 21, 43), name="U2")
    p.set_outline(rnd)
    out.append(("2 layers, round board", p))

    p = Problem.new(150.0, 30.0, layers=1, thickness_mm=1.6, copper_um=35)
    for k, x in enumerate((25.0, 75.0, 125.0)):
        p.add_zone(1, rect=(x - 12, 5, x + 12, 25))
        p.add_heater(1, 1.0, rect=(x - 2.5, 12.5, x + 2.5, 17.5), name=f"LED{k + 1}")
    p.add_zone(1, rect=(5, 13, 145, 17))
    out.append(("1 layer, LED strip, three pads on a trace", p))

    p = Problem.new(80.0, 100.0, layers=1, thickness_mm=1.6, copper_um=70)
    p.board.h_mode, p.board.orientation = "computed", "vertical"
    p.add_zone(1, rect=(10, 10, 70, 50)); p.add_zone(1, rect=(15, 60, 45, 90))
    p.add_heater(1, 2.0, rect=(30, 22, 40, 32), name="Q1"); p.add_heater(1, 0.8, rect=(25, 70, 33, 78), name="U2")
    out.append(("1 layer, power board, vertical, computed h", p))

    p = Problem.new(80.0, 80.0, layers=1, thickness_mm=1.0, copper_um=35)
    p.add_zone(1, polygon=[(10, 10), (70, 10), (70, 70), (10, 70)])
    p.add_heater(1, 1.5, rect=(35, 35, 45, 45), name="U1")
    p.set_outline(rnd)
    out.append(("1 layer, round board, 1.0 mm", p))

    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=1.6, copper_um=35)
    p.add_zone(1, rect=(20, 20, 40, 40))
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U1")
    out.append(("1 layer, 20 mm pad", p))

    p = Problem.new(100.0, 70.0, layers=1, thickness_mm=3.2, copper_um=35).add_full_copper()
    p.add_heater(1, 3.0, rect=(20, 30, 30, 40), name="U1"); p.add_heater(1, 1.0, rect=(70, 30, 76, 36), name="U2")
    out.append(("1 layer, full copper, 3.2 mm", p))
    return out


def run(root):
    """!
    @brief Run every board in every model with the program found at root.
    @param root Folder of the program (a checkout of the repository).
    @return Dict board -> {"ambient", "parts", model: [board maximum in degC]}.
    """
    sys.path.insert(0, str(root))
    from pcbthermal import Problem, SolverOptions, simulate                 # noqa: E402
    from pcbthermal.examples import example_block_board, example_board     # noqa: E402
    from pcbthermal import solid3d                                         # noqa: E402
    api = {"Problem": Problem, "example_board": example_board, "example_block_board": example_block_board}
    out = {}
    # The 6-layer board has about 281 000 3D unknowns at 1 mm, above the application's limit (solid3d.MAX_CELLS, 250 000 after the model corrections);
    # the study accepts the longer solve. Older checkouts have no size_limit and their limit (2 million) already lets it run.
    def limit():
        """!
        @brief The 3D size limit of the study (a fresh context for every board).
        @return Context manager.
        """
        return solid3d.size_limit(2_000_000) if hasattr(solid3d, "size_limit") else contextlib.nullcontext()
    for name, p in boards(api):
        with limit():
            res = simulate(p, SolverOptions(models=MODELS, cell_mm=CELL_MM)).results
        out[name] = {"ambient": p.board.ambient, "parts": ["maximum"]}
        for m in MODELS:
            out[name][m] = [res[m].t_max] if m in res else None
        print(f"{name}: " + ", ".join(f"{m} {out[name][m][0]:.2f}" for m in MODELS if out[name][m]), flush=True)
    return out


def errors(data):
    """!
    @brief Error of every model against the 3D solid for every part, in percent of the rise.
    @param data Output of run().
    @return Dict board -> {model: [errors]}.
    """
    out = {}
    for name, d in data.items():
        ref = [t - d["ambient"] for t in d["solid3d"]]
        out[name] = {m: [100.0 * ((t - d["ambient"]) / r - 1.0) for t, r in zip(d[m], ref)] for m in MODELS if m != "solid3d" and d[m]}
    return out


def compare(before, after):
    """!
    @brief Print the table of errors before and after for every board, part and model, and the mean absolute error of each model.
    @param before Output of run() on the older program.
    @param after Output of run() on this program.
    @return None.
    """
    eb, ea = errors(before), errors(after)
    print("| board | 3D solid rise (K) | " + " | ".join(f"{m} before → after" for m in MODELS if m != "solid3d") + " |")
    print("| :-- | --: | " + " | ".join("--:" for m in MODELS if m != "solid3d") + " |")
    totals = {m: ([], []) for m in MODELS if m != "solid3d"}
    for name, d in after.items():
        for k, part in enumerate(d["parts"]):
            cells = []
            for m in totals:
                b, a = eb[name][m][k], ea[name][m][k]
                totals[m][0].append(abs(b)); totals[m][1].append(abs(a))
                cells.append(f"{b:+.1f} → {a:+.1f} %")
            print(f"| {name} | {d['solid3d'][k] - d['ambient']:.2f} | " + " | ".join(cells) + " |")
    print("\nMean absolute error against the 3D solid, before → after: " + "; ".join(f"{m} {sum(b) / len(b):.1f} → {sum(a) / len(a):.1f} %" for m, (b, a) in totals.items()))
    one = [(n, k) for n, d in after.items() if n.startswith("1 layer") for k in range(len(d["parts"]))]
    print("Mean absolute error on the one-layer boards only, before → after: " + "; ".join(
        f"{m} {sum(abs(eb[n][m][k]) for n, k in one) / len(one):.1f} → {sum(abs(ea[n][m][k]) for n, k in one) / len(one):.1f} %" for m in totals))


def main():
    """!
    @brief Run the boards (writing the JSON) or compare two runs.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--root", default=str(HERE.parents[2]), help="folder of the program to import")
    ap.add_argument("--out", default=str(HERE.parent / "out" / "complex_boards.json"), help="JSON file to write")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="compare two JSON files instead of running")
    args = ap.parse_args()
    if args.compare:
        compare(*(json.loads(Path(f).read_text()) for f in args.compare))
        return
    data = run(args.root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
