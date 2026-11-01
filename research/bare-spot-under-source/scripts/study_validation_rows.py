#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_validation_rows.py
@brief Q5: what the treatments change on the validation scenarios of docs/validation.md section 2 and on the example projects (FVM, 1 mm cells), and where nothing changes.
@details Question answered: on the boards that the program is validated on (reference board, example board and its variants, partial and hatched copper, a heater straddling a copper edge, a board with no
         copper under the heater, ...), how much does the proposed treatment move the peak, how many cells does it refine, and are the boards fully covered by copper left exactly as they are?
         The scenarios are those of research/models-comparison (accuracy_study.cases(), stress_study.cases(), read only) plus the three example projects of examples/. For every board the program's
         FVM peak (net.solve_steady), the copy with no refinement (checks the copy), the vertical correction and n = 2 and 4 nodes with it, and the 3D solid (the comparison) are printed with the
         refined cells and the unknowns. Boards with metal blocks are skipped (the copy does not model them).
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_validation_rows.py; out/validation_rows.json and .txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

from _bootstrap import HERE, OUT

sys.path.append(str(HERE.parent / "models-comparison" / "scripts"))

import layered as LY                                                        # noqa: E402
import treatments as TR                                                     # noqa: E402

TREATS = [{"kind": "none"}, {"kind": "vert"}, {"kind": "nodes", "n": 2, "vert": True}, {"kind": "nodes", "n": 4, "vert": True}]


def boards():
    """!
    @brief The scenarios and the example projects.
    @return list of (name, Problem).
    """
    import accuracy_study
    import stress_study
    from pcbthermal.project import load_project
    out = list(accuracy_study.cases()) + list(stress_study.cases())
    for f in ("example_board", "profile_board", "reference_board"):
        out.append((f"project {f}", load_project(str(HERE.parents[1] / "examples" / f"{f}.pcbt.json")).problem))
    return out


def main():
    """!
    @brief Run every board.
    @return None.
    """
    from pcbthermal import SolverOptions, simulate
    rows, lines = [], []
    for name, p in boards():
        cell = 1.0
        net = LY.network(p, cell)
        if net.nl != p.board.layers:
            lines.append(f"{name:<52} skipped (metal block)")
            print(lines[-1], flush=True)
            continue
        net.K = net._assemble()
        th, _ = net.solve_steady()
        amb = p.board.ambient
        gaps, kz, kxy = LY.gap_data(p)
        row = {"name": name, "program": float(th.max() + amb), "treat": {}}
        for t in TREATS:
            r = TR.run(p, net, t, gaps, kz, kxy)
            row["treat"][json.dumps(t)] = r
        try:
            row["solid3d"] = float(simulate(p, SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max - amb + amb)
        except Exception as e:                                               # reported, not hidden
            row["solid3d"] = type(e).__name__
        rows.append(row)
        cells = [TR.run(p, net, {"kind": "nodes", "n": 2}, gaps, kz, kxy)["flagged"]][0]
        base = row["program"] - amb
        txt = f"{name:<52} program {row['program']:8.2f} copy {row['treat'][json.dumps(TREATS[0])]['peak_all'] + amb:8.2f} "
        for t in TREATS[1:]:
            r = row["treat"][json.dumps(t)]
            txt += f"| {('vert' if t['kind'] == 'vert' else 'n=%d+v' % t['n'])} {r['peak_all'] + amb:8.2f} ({100 * (r['peak_all'] / base - 1):+5.1f} %) "
        txt += f"| refined cells {cells} | 3D solid {row['solid3d'] if isinstance(row['solid3d'], str) else round(row['solid3d'], 2)}"
        lines.append(txt)
        print(txt, flush=True)
    json.dump(rows, open(OUT / "validation_rows.json", "w"), indent=1)
    (OUT / "validation_rows.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
