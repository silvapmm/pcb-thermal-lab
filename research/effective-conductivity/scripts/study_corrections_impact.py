"""!
@file study_corrections_impact.py
@brief What the corrections and proposals of this investigation would change, measured on copies of the program (nothing in pcbthermal/ is edited): the cell size of the plate check, the laminar form of Churchill and Chu, and the thick-plate criterion.
@details A. The plate model of the program (a layer of lateral conductance k t under a uniform film) against Seri Lee's centre, edge and corner values as the cell size is refined: the documented
            "+4.5 %" is the result at 1 mm cells, not the error of the model.
         B. The laminar form of the vertical-plate correlation, patched in at run time (convection.h_natural_vertical replaced in memory), on the example board and a reference board turned to the vertical
            with computed heat transfer coefficients, at three power levels: the change of the maximum temperature in the FVM.
         C. The criterion q'' t / (2 k) / rise of the thick-plate check for the 74 metal-block cases of research/block-and-fins (heat of the part through the contact patch, the thickness and conductivity of the block).
         Run: .venv/bin/python research/effective-conductivity/scripts/study_corrections_impact.py (from the repository root; about 2 minutes).
"""

import copy
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research" / "block-and-fins" / "scripts"))
import study_lee_spreading as lee                              # noqa: E402
import study_natural_convection as nc                          # noqa: E402
import block_equivalent_study as bes                           # noqa: E402
from pcbthermal import SolverOptions, simulate, convection     # noqa: E402
from pcbthermal.examples import example_board                  # noqa: E402


def plate_convergence(cells=(25, 50, 100, 200, 400)):
    """!
    @brief Constriction resistance of the thin plate of Seri Lee as the cell is refined.
    @param cells Cells per side (the plate is 100 mm).
    @return dict n -> {position: Rc}.
    """
    out = {}
    for n in cells:
        out[n] = {pos: lee.rc_2d(pos, n=n) for pos in lee.PAPER}
    return out


def alignment_sweep(ns=range(60, 241, 4)):
    """!
    @brief The centre value of the thin plate for many cell sizes (n cells over 100 mm): the error swings with how the source edges fall on the cells, not with the resolution.
    @param ns Cells per side to try.
    @return list of (cell size in mm, edge offset in cells, error against the article in percent).
    """
    out = []
    for n in ns:
        d = 100.0 / n
        edge = 37.5 / d
        off = abs(edge - round(edge))                              # distance of the source edge from the nearest cell edge, in cells
        out.append((d, off, 100.0 * (lee.rc_2d("centre", n=n) / lee.PAPER["centre"] - 1.0)))
    return out


def laminar_patch():
    """!
    @brief Replace the vertical-plate coefficient of the program by the laminar form below Ra = 1e9 (in memory only).
    @return The original function, to restore it.
    """
    original = convection.h_natural_vertical

    def patched(t_surface, t_ambient, height):
        h, ra = original(t_surface, t_ambient, height)
        if ra >= 1e9:
            return h, ra
        props = convection.air_properties(0.5 * (t_surface + t_ambient))
        return nc.nu_laminar(ra, props["pr"]) * props["k"] / height, ra

    convection.h_natural_vertical = patched
    return original


def vertical_boards():
    """!
    @brief The boards of the study: the example board and a bare 2-layer board, both vertical, with computed heat transfer coefficients, at three power levels.
    @return list of (label, Problem).
    """
    out = []
    for scale in (0.5, 1.0, 2.0):
        p = example_board()
        p.board.orientation, p.board.h_mode = "vertical", "computed"
        for h in p.heaters:
            h.power *= scale
        out.append((f"example board, powers x{scale:g}", p))
    from pcbthermal import Problem
    for height in (60.0, 120.0, 200.0):
        p = Problem.new(100.0, height, 2).add_full_copper()
        p.add_heater(1, 3.0, rect=(40, height / 2 - 5, 50, height / 2 + 5), name="U")
        p.board.orientation, p.board.h_mode = "vertical", "computed"
        out.append((f"2-layer board 100 x {height:g} mm, 3 W", p))
    return out


def run_forms():
    """!
    @brief Maximum temperature of every board with the general and with the laminar form.
    @return list of dicts.
    """
    rows = []
    for label, p in vertical_boards():
        t_general = simulate(copy.deepcopy(p), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"].t_max
        original = laminar_patch()
        try:
            t_laminar = simulate(copy.deepcopy(p), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"].t_max
        finally:
            convection.h_natural_vertical = original
        rows.append({"board": label, "t_general": t_general, "t_laminar": t_laminar, "ambient": p.board.ambient})
    return rows


def block_criterion():
    """!
    @brief The thick-plate criterion q'' t / (2 k) / rise for every metal-block case of research/block-and-fins.
    @return list of (label, criterion in percent).
    """
    out = []
    for label, p in bes.cases():
        blk = p.heatsinks[0]
        # heat of the part through the contact patch: the copper pad under the block (the zone on layer 2), the thickness and conductivity of the block
        pad = next(z for z in p.zones if z.layer == 1 and abs(z.polygon[:, 0].max() - z.polygon[:, 0].min()) < p.board.width - 1e-6) if len(p.zones) > 1 else p.zones[0]
        area = (pad.polygon[:, 0].max() - pad.polygon[:, 0].min()) * (pad.polygon[:, 1].max() - pad.polygon[:, 1].min())
        power = sum(h.power for h in p.heaters)
        t, k = blk.thickness, blk.k if hasattr(blk, "k") else 200.0
        rise = 90.0                                                # the rise of these boards is 70 to 100 K (research/block-and-fins 4.2)
        out.append((label, 100.0 * 0.5 * (power / area) * t / k / rise))
    return out


def main():
    """!
    @brief Print the three parts and write out/corrections_impact.json for the figures.
    @return None.
    """
    out = {}
    pc = plate_convergence()
    out["plate"] = {str(n): v for n, v in pc.items()}
    print("A. The plate of Seri Lee, thin-plate model, constriction resistance (K/W) against the cell size")
    print("| cell (mm) | centre (0.66) | edge midpoint (1.29) | corner (2.38) |")
    print("| --: | --: | --: | --: |")
    for n, v in pc.items():
        print(f"| {100.0 / n:g} | " + " | ".join(f"{v[p]:.3f} ({100 * (v[p] / lee.PAPER[p] - 1):+.1f} %)" for p in lee.PAPER) + " |", flush=True)
    sweep = alignment_sweep()
    out["alignment"] = sweep
    print(f"\nA2. Centre value for {len(sweep)} cell sizes (1.67 to 0.42 mm): error against the article from {min(e for _, _, e in sweep):+.1f} to {max(e for _, _, e in sweep):+.1f} %; "
          f"with the source edge on a cell edge (offset 0): {np.mean([e for _, o, e in sweep if o < 0.05]):+.1f} % on average, half a cell off (offset 0.5): {np.mean([e for _, o, e in sweep if o > 0.45]):+.1f} %", flush=True)
    rows = run_forms()
    out["forms"] = rows
    print("\nB. Laminar form of the vertical-plate correlation on the program (FVM, computed h, maximum temperature)")
    print("| board | general form (program) | laminar form | change of the rise |")
    print("| :-- | --: | --: | --: |")
    for r in rows:
        print(f"| {r['board']} | {r['t_general']:.2f} C | {r['t_laminar']:.2f} C | {r['t_laminar'] - r['t_general']:+.2f} K ({100 * ((r['t_laminar'] - r['ambient']) / (r['t_general'] - r['ambient']) - 1):+.1f} %) |", flush=True)
    crit = block_criterion()
    vals = np.array([c for _, c in crit])
    out["criterion"] = [{"case": l, "percent": v} for l, v in crit]
    print(f"\nC. Thick-plate criterion q'' t / (2 k) / rise over the {len(crit)} metal-block cases: maximum {vals.max():.2f} %, median {np.median(vals):.2f} %, cases above 5 %: {int((vals > 5).sum())}")
    worst = max(crit, key=lambda c: c[1])
    print(f"   largest: {worst[0]} ({worst[1]:.2f} %)")
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "corrections_impact.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
