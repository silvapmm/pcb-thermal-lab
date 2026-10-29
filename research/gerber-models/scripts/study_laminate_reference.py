"""!
@file study_laminate_reference.py
@brief Review question: since the program gives a one-layer board two laminate nodes under the copper, which fine reference is right for the mapping studies, and how large is the bias of the fill fraction then?
@details The mapping studies of 4.4 to 4.9 use the research solver (`conduction.solve_faces`): ONE sheet that carries the copper and the whole laminate in the plane, with both
         films acting on it (the program's idealisation before `laminate.py`). The program now puts the laminate in two node layers under the copper, so the copper node has a
         contrast of about 36 instead of 9.4 and heat can pass under a clearance only through the laminate nodes. This study solves the same copper (one window per board of
         the 42, binary mask brought to 0.2 mm pixels) four ways:
         * an **independent 3D finite-volume solver** written here (no code of the program or of the research solver): a 35 um copper slab whose cells are copper (385 W/mK)
           or FR-4, and 1.565 mm of FR-4 in 8 sub-slabs, FR-4 anisotropic (0.9 W/mK in the plane, 0.3 across), 10 W/m2K on both faces (also under the heater, as the
           program), insulated sides, 1 W into the copper cells of the 6 x 6 mm heater;
         * the program's FVM on the 0.2 mm pixel grid (laminate nodes; the copper node conductance of every pixel from `faces.phases`);
         * the research solver on the same pixels (one sheet);
         * and on 0.8 and 1.2 mm cells, the fill fraction and the flow-based faces both in the program's network (`faces.FaceNetwork`) and in the research solver.
         Printed: the heater mean rise of every solution and the errors against the 3D solution and against each network's own fine run.
         Then our IC board (one layer, 11 % copper, 0.8 mm cells, 6.4 mm heater), not in the means. With `--nodes`: two windows with 1, 2, 4 and 8 laminate nodes (the test of
         the explanation in README Review R2); with `--rect`: the rectangle board of 4.35 and 4.37 against the program's FVM (Review R4).
         Run from the repository root: PYTHONPATH=<program> .venv/bin/python research/gerber-models/scripts/study_laminate_reference.py [--nodes] (about 7 minutes; one 3D solve of
         290 000 unknowns per board, about 8 GB of memory).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

try:
    import pcbthermal                                                   # noqa: F401  (a copy of the program on PYTHONPATH is used as it is)
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pcbthermal import fvm                                              # noqa: E402
from pcbthermal.model import Problem                                    # noqa: E402

import conduction as cd                                                 # noqa: E402
import faces                                                            # noqa: E402
import windows                                                          # noqa: E402

PIX = 0.2                        # mm: pixel of this study (the 0.1 mm windows brought to 0.2 mm so that the 3D solve stays small)
WIN = windows.WIN                # 36 mm (changed by `case` for our IC board)
HEAT = (12.0, 18.0)              # mm, heater block in both directions (idem)
HEAT_RECT = None                 # (x0, y0, x1, y1) mm of a heater that is not on the diagonal (the rectangle board)
K_CU, K_IN, K_TH = 385.0, 0.9, 0.3
T_CU, T_BOARD, H = 35e-6, 1.6e-3, 10.0
CELLS = (0.8, 1.2)               # mm: even numbers of 0.2 mm pixels (the flow-based faces need an even count)


def solve3d(mask, n_lam=8):
    """!
    @brief Independent 3D finite volumes of a one-layer board with patterned copper (anisotropic FR-4).
    @param mask Boolean copper mask (ny, nx) at PIX, row 0 at y = 0.
    @param n_lam Sub-slabs of the laminate.
    @return Mean rise (K) of the copper-slab cells under the heater.
    """
    ny, nx = mask.shape
    d = PIX * 1e-3
    dz = np.array([T_CU] + [(T_BOARD - T_CU) / n_lam] * n_lam)
    nz = len(dz)
    kin = np.empty((nz, ny, nx)); kth = np.empty((nz, ny, nx))
    kin[:] = K_IN; kth[:] = K_TH
    kin[0][mask] = K_CU; kth[0][mask] = K_CU                             # copper cells are isotropic
    idx = np.arange(nz * ny * nx).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * ny * nx)

    def link(a, b, g):
        """!@brief Symmetric conductance g (W/K) between node arrays a and b. @param a Nodes. @param b Nodes. @param g Conductances. @return None."""
        g = np.broadcast_to(g, a.shape).ravel()
        rows.extend([a.ravel(), b.ravel()]); cols.extend([b.ravel(), a.ravel()]); vals.extend([-g, -g])
        np.add.at(diag, a.ravel(), g); np.add.at(diag, b.ravel(), g)

    for k in range(nz):
        a, b = kin[k][:, :-1], kin[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))   # face width dz x d over distance d
        a, b = kin[k][:-1, :], kin[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2 * a * b / (a + b))
    area = d * d
    for k in range(nz - 1):
        r = dz[k] / (2 * kth[k] * area) + dz[k + 1] / (2 * kth[k + 1] * area)
        link(idx[k], idx[k + 1], 1.0 / r)
    g_top = 1.0 / (dz[0] / (2 * kth[0] * area) + 1.0 / (H * area))         # film through the half cell (top, also under the heater)
    g_bot = 1.0 / (dz[-1] / (2 * kth[-1] * area) + 1.0 / (H * area))
    np.add.at(diag, idx[0].ravel(), np.broadcast_to(g_top, (ny, nx)).ravel())
    np.add.at(diag, idx[-1].ravel(), np.broadcast_to(g_bot, (ny, nx)).ravel())
    r0, r1, c0, c1 = heater_index(PIX)
    q = np.zeros((nz, ny, nx))
    q[0, r0:r1, c0:c1] = 1.0 / ((r1 - r0) * (c1 - c0))
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * ny * nx,) * 2).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q.ravel()).reshape(nz, ny, nx)
    return float(T[0, r0:r1, c0:c1].mean())


def heater_index(cell):
    """!@brief Rows and columns of the heater block (HEAT_RECT if set, else the square HEAT x HEAT). @param cell Cell or pixel size (mm). @return Tuple (r0, r1, c0, c1)."""
    x0, y0, x1, y1 = HEAT_RECT if HEAT_RECT else (HEAT[0], HEAT[0], HEAT[1], HEAT[1])
    return int(round(y0 / cell)), int(round(y1 / cell)), int(round(x0 / cell)), int(round(x1 / cell))


def problem():
    """!@brief The program's one-layer 36 mm board with the 6 mm heater of 1 W. @return Problem."""
    p = Problem.new(width_mm=WIN, height_mm=WIN, layers=1, thickness_mm=T_BOARD * 1e3, copper_um=T_CU * 1e6, h_top=H, h_bottom=H, h_side=None)
    p.add_heater(1, 1.0, rect=(HEAT[0], HEAT[0], HEAT[1], HEAT[1]))
    return p


def heater_mean(field, cell):
    """!@brief Mean of the top layer over the heater block. @param field Array (ny, nx) of a top layer. @param cell Cell size (mm). @return K."""
    r0, r1, c0, c1 = heater_index(cell)
    return float(field[r0:r1, c0:c1].mean())


def program_fine(p, S):
    """!@brief The program's FVM on the pixel grid with the given copper-node conductances. @param p Problem. @param S Pixel conductances (ny, nx). @return Heater mean rise (K)."""
    n = S.shape[0]
    net = fvm.Network(p, n, n, assemble=False)
    net.S[0] = S * net.cover
    net.K = net._assemble()
    return heater_mean(net.solve_steady()[0][0], PIX)


def program_cells(p, gx, gy, cell):
    """!@brief The program's network on coarse cells with the given faces of the copper node. @param p Problem. @param gx x faces. @param gy y faces. @param cell Cell (mm). @return Heater mean rise (K)."""
    n = gx.shape[0]
    net = faces.FaceNetwork(p, n, n, assemble=False)
    net.set_faces([(gx, gy)])
    return heater_mean(net.solve_steady()[0][0], cell)


def research(gx, gy, cell):
    """!@brief The research solver (one sheet, both films on it) with given faces. @param gx x faces. @param gy y faces. @param cell Cell (mm). @return Heater mean rise (K)."""
    i0, i1 = int(round(HEAT[0] / cell)), int(round(HEAT[1] / cell))
    return heater_mean(cd.solve_faces(gx, gy, cell, i0, i1, i0, i1), cell)


def case(name, m, acc):
    """!
    @brief The four solutions of one board and its line of the table.
    @param name Label.
    @param m Boolean copper mask at PIX, rows from the bottom.
    @param acc Dict of lists of errors (%), filled in place.
    @return None.
    """
    p = problem()
    a, b = faces.phases(p, 0)                                           # copper node of the program (copper + half a laminate gap)
    ar, br = cd.S_CU + cd.K_LAM * (cd.T_LAM - cd.T_CU), cd.S_LAM        # one sheet of the research solver (the program before laminate.py)
    t3 = solve3d(m)
    S, Sr = np.where(m, a, b), np.where(m, ar, br)
    pf = program_fine(p, S)
    rf = research(cd.harm(Sr[:, :-1], Sr[:, 1:]), cd.harm(Sr[:-1, :], Sr[1:, :]), PIX)
    line = f"{name:8s} {m.mean():5.2f} | {t3:7.2f} {pf:9.2f} {rf:12.2f}   |"
    for c in CELLS:
        n = int(round(c / PIX))
        f = cd.cell_blocks(m.astype(float), n).mean(axis=(2, 3))
        pfill = program_cells(p, *cd.faces_from_cells(cd.map_power(f, 1.0, a, b), cd.map_power(f, 1.0, a, b)), c)
        pflow = program_cells(p, *cd.dual_faces(S, n, 0), c)
        rfill = research(*cd.faces_from_cells(cd.map_power(f, 1.0, ar, br), cd.map_power(f, 1.0, ar, br)), c)
        rflow = research(*cd.dual_faces(Sr, n, 0), c)
        e = {"program fill vs 3D": pfill / t3 - 1, "program flow vs 3D": pflow / t3 - 1, "program fill vs own fine": pfill / pf - 1, "program flow vs own fine": pflow / pf - 1,
             "research fill vs own fine": rfill / rf - 1, "research flow vs own fine": rflow / rf - 1}
        if acc is not None:
            for k, v in e.items():
                acc.setdefault((c, k), []).append(100 * v)
        line += f" {c} mm: {100 * e['program fill vs 3D']:+5.1f} / {100 * e['program flow vs 3D']:+5.1f}, {100 * e['program fill vs own fine']:+5.1f} / {100 * e['program flow vs own fine']:+5.1f} | {100 * e['research fill vs own fine']:+5.1f} / {100 * e['research flow vs own fine']:+5.1f} |"
    if acc is not None:
        acc.setdefault("program fine vs 3D", []).append(100 * (pf / t3 - 1))
        acc.setdefault("research fine vs 3D", []).append(100 * (rf / t3 - 1))
    print(line, flush=True)


def main():
    """!@brief One window per board, then our IC board (not in the means): the four solutions and the errors. @return None."""
    global WIN, HEAT, CELLS
    masks, meta = windows.load()
    seen, picks = set(), []
    for i, m in enumerate(meta):
        if m[0] not in seen:
            seen.add(m[0]); picks.append(i)
    a, b = faces.phases(problem(), 0)
    print(f"contrast of the copper node: program {a / b:.1f}, research sheet {(cd.S_CU + cd.K_LAM * (cd.T_LAM - cd.T_CU)) / cd.S_LAM:.1f}")
    print("board    copper | 3D (K)  program fine  research fine | program: fill / flow vs 3D, then vs own fine, at 0.8 and 1.2 mm | research: fill / flow vs own fine")
    acc = {}
    for i in picks:
        m01 = masks[i][::-1]                                            # rows from the bottom
        case(meta[i][0], m01.reshape(m01.shape[0] // 2, 2, m01.shape[1] // 2, 2).mean(axis=(1, 3)) >= 0.5, acc)
    print()
    for k in ("program fine vs 3D", "research fine vs 3D"):
        v = np.array(acc[k])
        print(f"{k:28s}: mean {v.mean():+5.1f} %, range {v.min():+5.1f} to {v.max():+5.1f} %")
    for c in CELLS:
        for k in ("program fill vs 3D", "program flow vs 3D", "program fill vs own fine", "program flow vs own fine", "research fill vs own fine", "research flow vs own fine"):
            v = np.array(acc[(c, k)])
            print(f"{c} mm  {k:28s}: MAE {np.abs(v).mean():4.1f} %, bias {v.mean():+5.1f} %, range {v.min():+5.1f} to {v.max():+5.1f} %")
    # Our IC board (one layer, 10 % copper; its 16 holes do nothing on a one-layer board of the program and are left out of the 3D solve too)
    import tempfile
    import our_board
    with tempfile.TemporaryDirectory() as tmp:
        g, d = our_board.write(Path(tmp))
        ib = faces.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=0.1, cell=1.0, box=(0.0, 0.0, our_board.SIZE, our_board.SIZE))
    m01 = ib.layers[0]["binary"][::-1]
    # 40 mm board: 0.8 mm cells only (40 mm is not a whole number of 1.2 mm cells); a 6.4 mm heater centred at 20 mm (edges on 0.8 mm cells)
    WIN, HEAT, CELLS = float(our_board.SIZE), (16.8, 23.2), (0.8,)
    print("\nour IC board, 6.4 mm heater at the centre, 0.8 mm cells:")
    case("IC board", m01.reshape(m01.shape[0] // 2, 2, m01.shape[1] // 2, 2).mean(axis=(1, 3)) >= 0.5, None)

def rect_board():
    """!
    @brief Review check of README 4.37: is the 3D solid's +7 to +9 % over the FVM on the rectangle board (two layers, the bottom one empty) the physics?
    @details The independent 3D solver on the board's copper drawn at 0.2 mm (35 um of copper, 1.565 mm of FR-4, which is the same board as two layers with an empty bottom copper), against the program's FVM on the same 0.2 mm mask (two layers).
    @return None.
    """
    global HEAT_RECT
    import rect_board as rb
    for shift in (0.0, 0.4):
        HEAT_RECT = rb.heater(shift)
        m = rb.mask(shift, pix=PIX)                                        # rows from the bottom
        t3 = solve3d(m)
        p = Problem.new(width_mm=rb.W, height_mm=rb.H, layers=2, thickness_mm=T_BOARD * 1e3, copper_um=T_CU * 1e6, h_top=H, h_bottom=H, h_side=None)
        p.add_heater(1, 1.0, rect=HEAT_RECT)
        a, b = faces.phases(p, 0)
        net = fvm.Network(p, m.shape[1], m.shape[0], assemble=False)
        net.S[0] = np.where(m, a, b) * net.cover
        net.K = net._assemble()
        pf = heater_mean(net.solve_steady()[0][0], PIX)
        print(f"rectangle board, shift {shift} mm, 0.2 mm mask: independent 3D {t3:.2f} K, program FVM (two layers) {pf:.2f} K, 3D over FVM {100 * (t3 / pf - 1):+.1f} %", flush=True)
    HEAT_RECT = None


def nodes_sweep():
    """!
    @brief Review check of the explanation: the program's fine run approaches the 3D solution when the laminate is cut into more nodes (laminate.LAMINATE_NODES set in this process only; the program's files are not changed), while the error of the fill fraction against the 3D solution does not move.
    @return None.
    """
    from pcbthermal import laminate
    masks, meta = windows.load()
    for bname in ("storm", "pcad"):
        i = [k for k, mm in enumerate(meta) if mm[0] == bname][0]
        m01 = masks[i][::-1]
        m = m01.reshape(m01.shape[0] // 2, 2, m01.shape[1] // 2, 2).mean(axis=(1, 3)) >= 0.5
        t3 = solve3d(m)
        out = [f"{bname}: 3D {t3:.2f} K"]
        for count in (1, 2, 4, 8):
            laminate.LAMINATE_NODES = count
            p = problem()
            a, b = faces.phases(p, 0)
            pf = program_fine(p, np.where(m, a, b))
            f = cd.cell_blocks(m.astype(float), 4).mean(axis=(2, 3))
            g = cd.map_power(f, 1.0, a, b)
            pfill = program_cells(p, *cd.faces_from_cells(g, g), 0.8)
            out.append(f"{count} nodes: fine {100 * (pf / t3 - 1):+.1f} %, 0.8 mm fill vs 3D {100 * (pfill / t3 - 1):+.1f} %, vs own fine {100 * (pfill / pf - 1):+.1f} %")
        laminate.LAMINATE_NODES = 2
        print(" | ".join(out), flush=True)


if __name__ == "__main__":
    if "--nodes" in sys.argv[1:]:
        nodes_sweep()
    elif "--rect" in sys.argv[1:]:
        rect_board()
    else:
        main()
