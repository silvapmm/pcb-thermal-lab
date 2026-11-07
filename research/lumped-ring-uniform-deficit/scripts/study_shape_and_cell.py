#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_shape_and_cell.py
@brief Review: does the capped first ring create hot cases, and does it hold at the Lumped cell of 1 mm, for square sources of 0.5 to 40 mm, rectangles of aspect 3 and a thin tab?
@details Boards of 100 x 80 and 200 x 150 mm, two layers of full copper (35 um, 1.6 mm, films 10/15 W/m2K, edge 10 W/m2K), one 1 W source at the centre. The Lumped is run at the
         two cells that the API lets it have (0.5 and 1 mm) as the program runs it, with the capped first ring exactly as INTEGRATION.md 1 writes it (lib/patch_program.py), and with
         the cap at 1.5, 2 and 3 equivalent radii (lib/lumped_log.py, FIRST_A) to see how smooth the answer is in the cap. Reference: the FVM hottest node at 0.25 mm (sources of
         at most 3 mm on 100 x 80 mm) or 0.5 mm, cached in out/review_fvm_cache.json. Writes out/shape_and_cell.json. Run from the repository root (about 1 minute the first time,
         peak under 1 GB): QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_shape_and_cell.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import lumped_log as LL  # noqa: E402
import patch_program as PP  # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate, api  # noqa: E402
from pcbthermal import lumped as PROG  # noqa: E402

CAPPED = PP.load_patched()
OUT = HERE.parent / "out"
CACHE = OUT / "review_fvm_cache.json"
SOURCES = [(s, s) for s in (0.5, 1, 2, 3, 5, 10, 20, 40)] + [(3, 1), (6, 2), (10, 0.5), (20, 2)]
BOARDS = [(100, 80), (200, 150)]
CAPS = (1.5, 2.0, 3.0)


def board(w, h, sx, sy):
    """!
    @brief The board of this study with one centred source.
    @param w Width in mm.
    @param h Height in mm.
    @param sx Source width in mm.
    @param sy Source height in mm.
    @return Problem.
    """
    p = Problem.new(w, h, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper(fill=1.0)
    p.add_heater(1, 1.0, rect=(w / 2 - sx / 2, h / 2 - sy / 2, w / 2 + sx / 2, h / 2 + sy / 2), name="U")
    return p


def rise(p, model, cell, mod=None):
    """!
    @brief Hottest rise of one model, optionally with a replacement Lumped module.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @param mod Module to use as pcbthermal.api.lumped (None: the program).
    @return float K.
    """
    api.lumped = mod or PROG
    try:
        return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient
    finally:
        api.lumped = PROG


def main():
    """!
    @brief Print the table and write out/shape_and_cell.json.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rows = []
    print("| board | source (mm) | cell | FVM (K) | program | capped (1 a) | " + " | ".join(f"cap {c:g} a" for c in CAPS) + " | Analytic |")
    print("| :-- | :-- | --: | --: | --: | --: | " + " | ".join("--:" for _ in CAPS) + " | --: |")
    for (w, h) in BOARDS:
        for (sx, sy) in SOURCES:
            p = board(w, h, sx, sy)
            rc = 0.25 if (w == 100 and min(sx, sy) <= 3) else 0.5
            key = f"{w}x{h}|{sx}x{sy}|{rc}"
            if key not in cache:
                cache[key] = rise(p, "fvm", rc)
                CACHE.write_text(json.dumps(cache))
            f = cache[key]
            an = rise(p, "analytic", 0.5)
            for cell in (0.5, 1.0):
                rec = {"board": [w, h], "source": [sx, sy], "cell": cell, "fvm": f, "ref_cell": rc, "program": rise(p, "lumped", cell),
                       "capped": rise(p, "lumped", cell, CAPPED), "analytic": an}
                for c in CAPS:
                    LL.configure(first_a=c)
                    rec[f"cap {c:g} a"] = rise(p, "lumped", cell, LL.MOD)
                LL.configure()
                rows.append(rec)
                e = {k: 100 * (v / f - 1) for k, v in rec.items() if isinstance(v, float) and k not in ("fvm", "cell", "ref_cell")}
                print(f"| {w} x {h} | {sx:g} x {sy:g} | {cell:g} | {f:.2f} | {e['program']:+.1f} | {e['capped']:+.1f} | "
                      + " | ".join(f"{e[f'cap {c:g} a']:+.1f}" for c in CAPS) + f" | {e['analytic']:+.1f} |", flush=True)
    for cell in (0.5, 1.0):
        sel = [r for r in rows if r["cell"] == cell]
        for k in ("program", "capped"):
            errs = [100 * (r[k] / r["fvm"] - 1) for r in sel]
            print(f"cell {cell:g} mm, {k}: mean |error| {sum(abs(x) for x in errs) / len(errs):.1f} %, most negative {min(errs):+.1f} %, most positive {max(errs):+.1f} % ({len(errs)} cases)")
    (OUT / "shape_and_cell.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
