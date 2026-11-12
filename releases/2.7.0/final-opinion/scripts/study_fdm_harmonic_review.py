#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fdm_harmonic_review.py
@brief Review of `fix/fdm-harmonic-face-mean`: the FDM with the harmonic and the arithmetic face mean on the cases the branch did not check.
@details Each part prints the error of the FDM hottest rise against the FVM at 0.25 mm (the converged program) for both means, or the quantity named:
         `outline` (T, L, round and turned outlines with a top pad and with full copper), `harness` (the outline boards of the frozen-number harness, the three means,
         2 / 1 / 0.5 mm), `block` (an aluminium block over a copper edge, its edge off the grid), `hatch` (a solid pad over hatched copper), `imported` (the three
         copper mappings on a half-covered top), `profile` (power profiles through `api.simulate` and the time to 63 % of every heater) and `invariants` (symmetry,
         positive off-diagonal entries, row sums, balance, minimum against the ambient).
         Run from the repository root: `.venv/bin/python releases/2.7.0/final-opinion/scripts/study_fdm_harmonic_review.py <part>`; peak memory under 2.5 GB.
"""

import os
import sys

import numpy as np
import scipy.sparse as sp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))

from pcbthermal import Problem, copper, fdm, fvm, profiles          # noqa: E402
from pcbthermal.api import SolverOptions, simulate                  # noqa: E402
from pcbthermal.examples import example_board, example_profile_board   # noqa: E402
from pcbthermal.model import SquareWave                              # noqa: E402

DEFAULTS = fdm.Network.__init__.__defaults__


def use_mean(mean):
    """!
    @brief Set the default face mean of fdm.Network (the profile runner and the step responses build their own network).
    @param mean "arithmetic" or "harmonic".
    @return None.
    """
    d = list(DEFAULTS)
    d[1] = mean
    fdm.Network.__init__.__defaults__ = tuple(d)


def compare(p, cell, label, ref_cell=0.25):
    """!
    @brief Print the FDM error (both means) against the FVM at ref_cell.
    @param p Problem.
    @param cell FDM cell in mm.
    @param label Row label.
    @param ref_cell FVM reference cell in mm.
    @return None.
    """
    amb = p.board.ambient
    a = float(fdm.solve_steady(p, cell, "arithmetic").t_max) - amb
    h = float(fdm.solve_steady(p, cell).t_max) - amb
    f = float(fvm.solve_steady(p, ref_cell).t_max) - amb
    print(f"{label:28s} cell {cell}: FDM arithmetic {100 * (a / f - 1):+.2f} %  harmonic {100 * (h / f - 1):+.2f} %  (FVM {ref_cell} mm rise {f:.3f} K)", flush=True)


def outline_board(shape, partial=True, turn=0.4):
    """!
    @brief 40 mm box with an outline, two layers, a 15 x 18 mm top pad (or full copper) and a 1 W part near the pad edge.
    @param shape "T", "L", "round" or "turn" (a 28 mm square turned by `turn`).
    @param partial True for the top pad and a bottom plane, False for full copper.
    @param turn Angle of the turned square in radians.
    @return Problem.
    """
    p = Problem.new(40.0, 40.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=10.0)
    if shape == "T":
        pts = [[2, 26], [14, 26], [14, 2], [26, 2], [26, 26], [38, 26], [38, 38], [2, 38]]
    elif shape == "L":
        pts = [[2, 2], [18, 2], [18, 22], [38, 22], [38, 38], [2, 38]]
    elif shape == "round":
        pts = [[20 + 17 * np.cos(a), 20 + 17 * np.sin(a)] for a in np.linspace(0, 2 * np.pi, 97)[:-1]]
    else:
        c = np.array([20.0, 20.0])
        R = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
        pts = [list(c + R @ (np.array(v) - c)) for v in [[6, 6], [34, 6], [34, 34], [6, 34]]]
    p.set_outline(pts)
    if partial:
        p.add_zone(1, rect=(15, 15, 30, 33))
        p.add_zone(2, rect=(0, 0, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(17, 27, 23, 33))
    return p


def pad_profile_board():
    """!
    @brief 60 x 40 mm, a 20 mm top pad with a 20 s square wave part and a second part on bare laminate.
    @return Problem.
    """
    p = Problem.new(60.0, 40.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)
    p.add_zone(1, rect=(20, 10, 40, 30))
    p.add_heater(1, 2.0, rect=(27, 17, 33, 23), name="U")
    p.add_heater(1, 1.0, rect=(5, 5, 9, 9), name="V")
    p.heaters[0].set_profile(SquareWave(p_on=4.0, period=20.0, duty=0.5))
    return p


def t63(resp, i):
    """!
    @brief Time to 63.2 % of the final rise of heater i (bisection on the step response).
    @param resp profiles.StepResponse.
    @param i Heater index.
    @return float Time in s.
    """
    fin = float(resp.z_at(i, 1e6))
    lo, hi = 1e-3, 1e6
    for _ in range(80):
        m = (lo * hi) ** 0.5
        lo, hi = (m, hi) if float(resp.z_at(i, m)) < 0.632 * fin else (lo, m)
    return hi


def invariants(p, cell, label):
    """!
    @brief Print the matrix and solution invariants of the FDM (harmonic mean).
    @param p Problem.
    @param cell Cell in mm.
    @param label Row label.
    @return None.
    """
    net = fdm.Network(p, cell)
    K = sp.csr_matrix(net.K)
    sym = abs(K - K.T).max() / abs(K).max()
    npos = ((K - sp.diags(K.diagonal())) > 0).sum()
    rows = np.asarray(K.sum(axis=1)).ravel() - net.g_amb.ravel()
    r = fdm.solve_steady(p, cell)
    T = np.asarray(r.T)[:, net.active]
    print(f"{label:16s} symmetry {sym:.1e}  positive off-diagonal {npos}  row sums - g_amb {abs(rows).max():.1e}  balance {r.balance_error:.1e}  "
          f"min - ambient {T.min() - p.board.ambient:.2f} K", flush=True)


def main(part):
    """!
    @brief Run one part of the review.
    @param part One of outline, harness, block, hatch, imported, profile, invariants.
    @return None.
    """
    if part == "outline":
        for s in ("T", "L", "round", "turn"):
            for partial in (True, False):
                compare(outline_board(s, partial), 1.0, f"{s} {'pad' if partial else 'full copper'}")
    elif part == "harness":
        import regress_boards as rb
        for name in ("part_across_outline", "round_outline", "t_outline", "example_cut_to_T"):
            p = rb.build(name, os.path.join(ROOT, "examples"))
            f = float(fvm.solve_steady(p, 0.25).t_max) - p.board.ambient
            cols = []
            for cell in (2.0, 1.0, 0.5):
                r = {m: float(fdm.solve_steady(p, cell, m).t_max) - p.board.ambient for m in ("arithmetic", "harmonic", "harmonic_plain")}
                cols.append(f"{cell}: " + " ".join(f"{k} {100 * (v / f - 1):+.2f}" for k, v in r.items()))
            print(name, " | ".join(cols), flush=True)
    elif part == "block":
        for off in (0.0, 0.3, 0.5):
            p = Problem.new(60.0, 40.0, layers=2, h_top=10.0, h_bottom=10.0, h_side=None)
            p.add_zone(2, rect=(0, 0, 30, 40))                          # the bottom copper ends under the block
            p.add_zone(1, rect=(22, 14, 34, 26))
            p.add_heater(1, 3.0, rect=(25, 17, 31, 23))
            p.add_heatsink(2, 5.0, rect=(20 + off, 10 + off, 40.0 + off, 30 + off), thickness_mm=3.0, k=200.0)
            compare(p, 1.0, f"block edge off {off} mm")
    elif part == "hatch":
        for fill in (0.5, 0.25):
            p = Problem.new(40.0, 30.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)
            p.add_zone(1, rect=(0, 0, 40, 30), fill=fill)
            p.add_zone(1, rect=(15, 10, 25, 20))
            p.add_zone(2, rect=(0, 0, 40, 30))
            p.add_heater(1, 1.0, rect=(17, 12, 23, 18))
            compare(p, 1.0, f"pad over hatch {fill}")
    elif part == "imported":
        pix = 0.05
        nx, ny = int(30 / pix), int(20 / pix)
        x = (np.arange(nx) + 0.5) * pix
        top = np.zeros((ny, nx), np.uint8)
        top[:, x < 15] = 255                                            # copper on the left half of the top
        bottom = np.full((ny, nx), 255, np.uint8)
        for mapping in ("lambda", "faces", "fill"):
            p = Problem.new(30.0, 20.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)
            p.add_heater(1, 1.0, rect=(8, 8, 12, 12))
            p.imported = copper.imported_from_rasters([top, bottom], pix, mapping=mapping)
            compare(p, 1.0, f"imported {mapping}")
    elif part == "profile":
        for name, make in (("example profile board", example_profile_board), ("pad board", pad_profile_board)):
            for mean in ("arithmetic", "harmonic"):
                use_mean(mean)
                s = simulate(make(), SolverOptions(models=("fvm", "fdm"), cell_mm=1.0))
                d, f = s.profile_results["fdm"], s.profile_results["fvm"]
                resp = profiles.step_response_fdm(make(), 1.0)
                print(f"{name:22s} {mean:10s} FDM peak {d.peak:.3f}  FVM peak {f.peak:.3f}  error '{s.profile_error}'  t63 "
                      + " ".join(f"{t63(resp, i):.2f}" for i in range(len(make().heaters))), flush=True)
            use_mean("harmonic")
    elif part == "invariants":
        for s in ("T", "L", "round", "turn"):
            invariants(outline_board(s), 1.0, s)
        invariants(example_board(), 1.0, "example")
    else:
        raise SystemExit(f"unknown part {part!r}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "outline")
