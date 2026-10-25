"""!
@file study_lumped_analytic.py
@brief What does the copper mapping do in the Lumped (ring network) and Analytic (cosine series) models of the program?
@details Both models take the copper only through the fraction per cell of the zones: the Lumped model reads the sheet conductance of the FVM network and averages it over rings around the heater,
         the Analytic model averages the fraction over the whole board with the influence of the heater and treats the board as a uniform sheet (plus local corrections for vias and heatsinks).
         So an imported mask can enter through the public API with no change of the program: one zone per 1 mm cell whose `fill` is the one that gives, through the program's own formula
         S = b + f (a - b), the conductance wanted for that cell. Four conductances per cell are compared (from the 0.1 mm mask of 42 windows): the arithmetic fraction (today), the geometric mean,
         the mean of the two directional conductances of the bounds mapping (lambda 0.5) and the mean of the four flow-based faces of the cell. The three models are run by the program itself (`simulate`);
         the reference is the 0.1 mm mask solved pixel by pixel. Error of the mean temperature rise of the 6 x 6 mm heater. Needs the repository's dependencies.
         Run: .venv/bin/python research/gerber-models/scripts/study_lumped_analytic.py (from the repository root) (about 15 minutes with the five models).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

try:
    import pcbthermal                                                      # noqa: F401  (a copy of the program on PYTHONPATH is used as it is)
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # the repository root, to import pcbthermal

from pcbthermal import Problem, SolverOptions, simulate                # noqa: E402
from pcbthermal.analysis import heater_stats                           # noqa: E402

import conduction as cd                                                # noqa: E402
import windows                                                         # noqa: E402

WIN, PIX = windows.WIN, windows.PIX
CELL = 1.0                                                             # mm: the Lumped and Analytic models of the application work on 0.5 to 1 mm rasters
VARIANTS = ("arithmetic (today)", "geometric", "lam 0.5 mean", "dual faces mean")
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def make_problem():
    """!
    @brief One layer, 36 x 36 mm, 10 W/m2K on both faces, insulated edges, 1 W on a 6 x 6 mm block at (12..18, 18..24) mm (y up).
    @return Problem without zones.
    """
    p = Problem.new(width_mm=WIN, height_mm=WIN, layers=1, thickness_mm=cd.T_LAM * 1000.0, copper_um=cd.T_CU * 1e6, h_top=cd.H_FACE, h_bottom=cd.H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=(12.0, 18.0, 18.0, 24.0))
    return p


def phases(p):
    """!
    @brief The two phase conductances of the program's formula S = b + f (a - b) for the copper node (faces.phases: on a one-layer board the copper node holds the copper and half a laminate gap, the rest of the laminate is in the program's laminate nodes).
    @param p Problem.
    @return Tuple (a, b) in W/K.
    """
    import faces
    return faces.phases(p, 0)


def reference(S):
    """!
    @brief The reference: the program's own FVM on the 0.1 mm pixel grid with the copper-node conductance of every pixel (with the laminate nodes of a one-layer board).
    @details Before the review the reference was the research solver (one sheet with both films on it), which is the program's physics before laminate.py:
             since that correction the program's models and that reference no longer describe the same board (README, section Review).
    @param S Pixel conductances of the copper node (rows from the bottom).
    @return Mean rise (K) over the heater block.
    """
    from pcbthermal import fvm
    n = S.shape[0]
    net = fvm.Network(make_problem(), n, n, assemble=False)
    net.S[0] = S * net.cover
    net.K = net._assemble()
    ys, ye, hs, he = int(round((WIN - 18) / PIX)), int(round((WIN - 12) / PIX)), int(12 / PIX), int(18 / PIX)
    return float(net.solve_steady()[0][0][ys:ye, hs:he].mean())


def cell_values(S, n):
    """!
    @brief The four isotropic cell conductances of every 1 mm cell.
    @param S Pixel sheet conductances (rows from the bottom).
    @param n Pixels per cell side.
    @return Dict variant -> array (cells, cells).
    """
    a, b = float(S.max()), float(S.min())
    blk = cd.cell_blocks(S, n)
    f = (blk == a).mean(axis=(2, 3))
    sx, sy = cd.map_lambda(blk, 0.5)
    gx, gy = cd.dual_faces(S, n, 0)
    # The cell value of the flow-based mapping: the mean of its (up to) four faces; at the border the missing faces are not counted
    tot = np.zeros(f.shape)
    cnt = np.zeros(f.shape)
    tot[:, :-1] += gx; cnt[:, :-1] += 1; tot[:, 1:] += gx; cnt[:, 1:] += 1
    tot[:-1, :] += gy; cnt[:-1, :] += 1; tot[1:, :] += gy; cnt[1:, :] += 1
    return {"arithmetic (today)": cd.map_power(f, 1.0, a, b), "geometric": cd.map_power(f, 0.0, a, b), "lam 0.5 mean": 0.5 * (sx + sy), "dual faces mean": tot / cnt}


def run(args):
    """!
    @brief One window: the reference and the three models for each variant.
    @param args Tuple (key, mask).
    @return List of records (variant, model, error of the mean rise %).
    """
    key, mask = args
    p0 = make_problem()
    a, b = phases(p0)
    S = np.where(mask[::-1], a, b)                                      # row 0 = bottom (y up), as the program's grid
    n = int(round(CELL / PIX))
    ref = reference(S)
    out = []
    for name, sc in cell_values(S, n).items():
        p = make_problem()
        feff = np.clip((sc - b) / (a - b), 0.0, 1.0)
        for i in range(feff.shape[0]):
            for j in range(feff.shape[1]):
                if feff[i, j] > 1e-6:
                    p.add_zone(1, rect=(j * CELL, i * CELL, (j + 1) * CELL, (i + 1) * CELL), fill=float(feff[i, j]))
        sim = simulate(p, SolverOptions(models=MODELS, cell_mm=CELL))
        for m in MODELS:
            rise = heater_stats(sim.results[m], p)[0]["t_mean"] - p.board.ambient
            out.append((name, m, 100 * (rise / ref - 1)))
    return out


POWERS = (-0.2, -0.1, 0.1, 0.2)
REGION = ("whole board arithmetic of S (today, weighted)", "weighted geometric mean of S", "weighted harmonic mean of S", "effective conductance of the window (flow)") + tuple(f"weighted power mean p={p:+.1f}" for p in POWERS)


def region_values(S, a, b):
    """!
    @brief Four ways to give the Analytic model ONE conductance for the whole board (it treats the board as a uniform sheet around the heater).
    @details The weights are the influence of the heater, K0(r / lambda) with lambda the spreading length of the layer, as the model itself uses for the copper fraction.
    @param S Pixel sheet conductances (rows from the bottom).
    @param a Copper phase conductance.
    @param b Laminate phase conductance.
    @return Dict name -> conductance in W/K.
    """
    from scipy.special import k0
    n = S.shape[0]
    c = (np.arange(n) + 0.5) * PIX * 1e-3
    X, Y = np.meshgrid(c, c)
    lam = np.sqrt(float(S.mean()) / (2 * cd.H_FACE))                        # spreading length of the layer (m), as the model estimates it
    r0 = np.sqrt((6e-3) ** 2 / np.pi)
    d = np.maximum(np.hypot(X - 15e-3, Y - 21e-3), max(r0, 0.5e-3))        # heater centre at (15, 21) mm
    w = k0(d / lam)
    w /= w.sum()
    gx = cd.local_flux(S[None], 0)[0]
    gy = cd.local_flux(np.ascontiguousarray(S.T)[None], 0)[0]
    out = {REGION[0]: float((w * S).sum()), REGION[1]: float(np.exp((w * np.log(S)).sum())), REGION[2]: float(1.0 / (w / S).sum()), REGION[3]: float(np.sqrt(gx * gy))}
    for p in POWERS:
        out[f"weighted power mean p={p:+.1f}"] = float((w * S ** p).sum() ** (1.0 / p))
    return out


def run_region(args):
    """!
    @brief One window: the Analytic model with one uniform conductance of each kind.
    @param args Tuple (key, mask).
    @return List of records (name, error of the mean rise %).
    """
    key, mask = args
    p0 = make_problem()
    a, b = phases(p0)
    S = np.where(mask[::-1], a, b)
    ref = reference(S)
    out = []
    for name, s_eff in region_values(S, a, b).items():
        p = make_problem()
        p.add_zone(1, rect=(0, 0, WIN, WIN), fill=float(np.clip((s_eff - b) / (a - b), 0.0, 1.0)))
        sim = simulate(p, SolverOptions(models=("analytic",), cell_mm=CELL))
        out.append((name, 100 * (heater_stats(sim.results["analytic"], p)[0]["t_mean"] - p.board.ambient) / ref * 1.0 - 100))
    return out


def main():
    """!
    @brief Run the windows and print the MAE and the bias of every variant in every model.
    @return None.
    """
    masks, meta = windows.load()
    tasks = [(m[0], masks[i]) for i, m in enumerate(meta)]
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(run, tasks):
            out += r
    reg = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(run_region, tasks):
            reg += r
    print(f"{len(tasks)} windows, 1 mm cells; MAE of the heater mean-temperature rise error % (bias in brackets) against the resolved copper")
    print(f"{'conductance of the cell':24s}" + "".join(f"{m:>18}" for m in MODELS))
    for v in VARIANTS:
        row = ""
        for m in MODELS:
            e = np.array([o[2] for o in out if o[0] == v and o[1] == m])
            row += f"{np.abs(e).mean():9.1f} ({e.mean():+6.1f})"
        print(f"{v:24s}{row}")
    print("\nAnalytic model given ONE conductance for the whole board (uniform sheet), error of the heater mean rise %")
    for name in REGION:
        e = np.array([o[1] for o in reg if o[0] == name])
        print(f"  {name:48s} MAE {np.abs(e).mean():5.1f} % (bias {e.mean():+6.1f} %)")


if __name__ == "__main__":
    main()
