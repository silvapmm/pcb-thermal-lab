#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_imported_via_rim_review.py
@brief Review of fix/imported-via-rim-mask: does the ray test of the via rim on imported masks hold in the cases the branch did not measure?
@details Parts (each under a few minutes, under 2 GB):
         * `real <board> <cells> <reaches>`: the hottest rise of the parts with the most vias (or a drawn 3 x 3 mm, 1 W part on the densest via group when the board has none),
           FVM and FDM, the full contact of before against the ray test at several reaches (third-party boards of the local library: numbers only, nothing committed);
         * `edge`: a row of vias whose pad islands lie just outside the edge of an imported top plane, against an independent 3D reference with the same masks;
         * `relief4`: four layers, inner layer 2 a thermal relief with narrow spokes, against the reference;
         * `pixels`: the synthetic antipad and relief boards with coarse mask pixels (the three-pixel floor of the reach);
         * `hostile`: masks all copper, a pixel checkerboard, an empty layer, and a large random board (time and memory of the rim test).
         The reference `solve_reference` imports nothing from pcbthermal (Cartesian finite volumes, copper slabs, laminate sub-slabs, via blocks, ILU-preconditioned BiCGSTAB),
         adapted from research/imported-via-rim/lib/truth_via.py to take any mask per layer.
         Run (from the repository root): .venv/bin/python releases/2.7.0/final-opinion/scripts/study_imported_via_rim_review.py <part> [arguments]
         (`real` needs the library: eval "$(pcb-library/scripts/link_env.sh)").
"""

import os
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PCBTHERMAL_CONFIG", "/tmp/pcbt-review-config")   # private configuration, before the program reads its defaults
from pcbthermal import api, checks, copper, viawell        # noqa: E402
from pcbthermal.model import Problem                         # noqa: E402

K_CU, K_XY, K_Z = 385.0, 0.9, 0.3                           # copper and the anisotropic laminate of the reference, W/mK
PITCH, CENTRE = 0.7e-3, 5.1e-3                               # the 4 x 4 via field of the synthetic board of the research
HEATER = (3.6e-3, 3.6e-3, 6.6e-3, 6.6e-3)
ORIGINAL = viawell.rim_copper_shares


def full_contact(on):
    """!
    @brief Switch the rim test of imported copper back to the full contact of before the branch, or restore the branch's rule.
    @param on True: every imported via is in full contact with every layer.
    @return None.
    """
    def old(problem, v, n_layers, zone_index, masks=None):
        """!
        @brief The rule before the branch.
        @param problem Problem.
        @param v Via.
        @param n_layers Layers.
        @param zone_index Zone index.
        @param masks Ignored for imported copper.
        @return list of shares.
        """
        if problem.imported is not None:
            return [1.0] * n_layers
        return ORIGINAL(problem, v, n_layers, zone_index, masks)
    viawell.rim_copper_shares = old if on else ORIGINAL


def via_field():
    """!
    @brief Centres of the 4 x 4 via field in m.
    @return list of (x, y).
    """
    o = (np.arange(4) - 1.5) * PITCH
    return [(CENTRE + a, CENTRE + b) for a in o for b in o]


def ring_mask(centres, kind, pad_r=0.25e-3, anti_r=0.55e-3, spoke_w=0.25e-3):
    """!
    @brief A mask function: a plane with an antipad ('anti') or a thermal relief ('relief') around every via, or a solid plane.
    @param centres Via centres in m.
    @param kind 'solid', 'anti' or 'relief'.
    @param pad_r Pad island radius in m.
    @param anti_r Clearance radius in m.
    @param spoke_w Spoke width in m.
    @return function (X, Y) -> bool array.
    """
    def f(X, Y):
        """!
        @brief Copper at the points.
        @param X x in m.
        @param Y y in m.
        @return bool array.
        """
        m = np.ones_like(X, bool)
        if kind == "solid":
            return m
        for (cx, cy) in centres:
            r = np.hypot(X - cx, Y - cy)
            ring = (r > pad_r) & (r <= anti_r)
            if kind == "relief":
                ring &= ~((np.abs(X - cx) <= spoke_w / 2) | (np.abs(Y - cy) <= spoke_w / 2))
            m &= ~ring
        return m
    return f


def coverage(fn, pix_mm, width_mm=10.0, ss=4):
    """!
    @brief Coverage raster (rows from the top, 0..255) of a mask function, supersampled ss x ss per pixel.
    @param fn Mask function.
    @param pix_mm Pixel in mm.
    @param width_mm Square board side in mm.
    @param ss Samples per pixel side.
    @return uint8 array.
    """
    n, p = int(round(width_mm / pix_mm)), pix_mm * 1e-3
    xs = ((np.arange(n)[:, None] + ((np.arange(ss) + 0.5) / ss)[None, :]) * p).ravel()
    X, Y = np.meshgrid(xs, xs)
    m = fn(X, Y).reshape(n, ss, n, ss).mean(axis=(1, 3))
    return np.flipud(np.round(m * 255)).astype(np.uint8)


def program_problem(fns, centres, heater, pix_mm=0.05, vias=True):
    """!
    @brief The 10 mm synthetic board given to the program as imported copper, the vias as 0.3 mm plated holes.
    @param fns Mask function per layer.
    @param centres Via centres in m.
    @param heater (x0, y0, x1, y1) in m on layer 1, 1 W.
    @param pix_mm Mask pixel in mm.
    @param vias False: the same board without vias.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, layers=len(fns), thickness_mm=1.6, copper_um=35.0, name="review")
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", 10.0, 10.0, None
    p.imported = copper.imported_from_rasters([coverage(f, pix_mm) for f in fns], pix_mm, names=[f"L{i + 1}" for i in range(len(fns))])
    if vias:
        for (x, y) in centres:
            p.add_via(x * 1e3, y * 1e3, diameter=0.3)
    p.add_heater(1, 1.0, rect=tuple(v * 1e3 for v in heater))
    return p


def rise(p, cell, model):
    """!
    @brief Hottest rise of the program.
    @param p Problem.
    @param cell Cell in mm.
    @param model Model key.
    @return float K.
    """
    return api.simulate(p, api.SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient


def shares(p):
    """!
    @brief Rim shares of every via, as `viawell.build` reads them.
    @param p Problem.
    @return array (vias, layers).
    """
    L = p.board.layers
    m = viawell.rim_masks(p)
    zi = viawell._zone_index(p, L, m)
    return np.array([viawell.rim_copper_shares(p, v, L, zi, m) for v in p.vias])


def solve_reference(masks, centres, heater, nlam=6, n=100, d=1e-4, drill=0.3e-3, plating=25e-6, h=10.0, board_t=1.6e-3, t_cu=35e-6, with_vias=True):
    """!
    @brief Independent 3D steady reference of the 10 mm board (no pcbthermal import): copper slabs, laminate sub-slabs, square via blocks carrying the barrel copper.
    @param masks bool arrays (n, n) per layer, rows from the bottom.
    @param centres Via centres in m (cell centres).
    @param heater (x0, y0, x1, y1) in m on the top face, 1 W.
    @param nlam Laminate sub-slabs per gap.
    @param n Cells per side.
    @param d Cell in m.
    @param drill Drill in m.
    @param plating Barrel plating in m.
    @param h Film of both faces in W/m2K.
    @param board_t Board thickness in m.
    @param t_cu Copper thickness in m.
    @param with_vias False: no vias.
    @return dict with 'max' (top rise K) and 'balance'.
    """
    L = len(masks)
    gap = (board_t - L * t_cu) / (L - 1)
    c = (np.arange(n) + 0.5) * d
    X, Y = np.meshgrid(c, c)
    block = np.zeros((n, n), bool)
    for (cx, cy) in centres:
        block |= (np.abs(X - cx) <= drill / 2 + 1e-12) & (np.abs(Y - cy) <= drill / 2 + 1e-12)
    a_barrel = np.pi * (drill ** 2 / 4 - (drill / 2 - plating) ** 2)
    kz_block = K_CU * a_barrel / (block.sum() / max(len(centres), 1) * d * d) if centres else 0.0
    if not with_vias:
        block[:] = False
    dz, kxy_l, kz_l = [], [], []
    for li in range(L):
        mk = masks[li]
        dz.append(t_cu)
        kxy_l.append(np.where(mk, K_CU, K_XY))
        kz_l.append(np.where(block & ~mk, kz_block, np.where(mk, K_CU, K_Z)))   # where the layer is bare the barrel passes through
        if li < L - 1:
            for _ in range(nlam):
                dz.append(gap / nlam)
                kxy_l.append(np.full((n, n), K_XY))
                kz_l.append(np.where(block, kz_block, K_Z))
    nz, N = len(dz), n * n
    kxy, kz = np.array(kxy_l), np.array(kz_l)
    idx = np.arange(nz * N).reshape(nz, n, n)
    rows, cols, vals, diag = [], [], [], np.zeros(nz * N)

    def link(a, b, g):
        """!
        @brief Symmetric link between two node arrays.
        @param a Nodes.
        @param b Nodes.
        @param g Conductance.
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)
    for k in range(nz):
        a, b = kxy[k][:, :-1], kxy[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))
        a, b = kxy[k][:-1, :], kxy[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2 * a * b / (a + b))
    for k in range(nz - 1):
        link(idx[k], idx[k + 1], 1.0 / (dz[k] / (2 * kz[k] * d * d) + dz[k + 1] / (2 * kz[k + 1] * d * d)))
    gt = 1.0 / (dz[0] / (2 * kz[0] * d * d) + 1.0 / (h * d * d))
    gb = 1.0 / (dz[-1] / (2 * kz[-1] * d * d) + 1.0 / (h * d * d))
    np.add.at(diag, idx[0].ravel(), gt.ravel())
    np.add.at(diag, idx[-1].ravel(), gb.ravel())
    x0, y0, x1, y1 = heater
    hm = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
    q = np.zeros(nz * N)
    q[idx[0].ravel()] = (hm / hm.sum()).ravel()
    K = (sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * N, nz * N)).tocsr() + sp.diags(diag)).tocsc()
    # Symmetric diagonal scaling and an ILU-preconditioned BiCGSTAB to a tight tolerance: about 0.7 GB where the direct LU of the research took 3.5 GB
    s = 1.0 / np.sqrt(K.diagonal())
    Ks = (sp.diags(s) @ K @ sp.diags(s)).tocsc()
    ilu = spla.spilu(Ks, drop_tol=1e-5, fill_factor=20)
    y, info = spla.bicgstab(Ks, s * q, M=spla.LinearOperator(Ks.shape, ilu.solve), rtol=1e-11, atol=0, maxiter=5000)
    if info != 0:
        raise RuntimeError(f"the reference did not converge ({info})")
    T = (s * y).reshape(nz, n, n)
    return {"max": float(T[0].max()), "balance": float((gt * T[0]).sum() + (gb * T[-1]).sum() - 1.0)}


def grid_masks(fns, n=100, d=1e-4):
    """!
    @brief The mask functions sampled at the reference cell centres.
    @param fns Mask functions.
    @param n Cells per side.
    @param d Cell in m.
    @return list of bool arrays.
    """
    c = (np.arange(n) + 0.5) * d
    X, Y = np.meshgrid(c, c)
    return [f(X, Y) for f in fns]


def compare(name, fns, centres, heater, nlam=6, cells=(1.0, 0.5, 0.25)):
    """!
    @brief Print the reference and the program (full contact and ray test, FVM and FDM) for one board.
    @param name Label.
    @param fns Mask functions.
    @param centres Via centres in m.
    @param heater Heater rectangle in m.
    @param nlam Sub-slabs of the reference.
    @param cells Program cells in mm.
    @return None.
    """
    g = grid_masks(fns)
    t = solve_reference(g, centres, heater, nlam)
    t0 = solve_reference(g, centres, heater, nlam, with_vias=False)
    p, pn = program_problem(fns, centres, heater), program_problem(fns, centres, heater, vias=False)
    print("%s: reference %.3f K, via effect %.3f K, balance %.1e; rim shares per layer %s" % (name, t["max"], t0["max"] - t["max"], t["balance"],
                                                                                           np.round(shares(p).mean(0), 3)), flush=True)
    for cell in cells:
        for m in ("fvm", "fdm"):
            full_contact(True)
            a = rise(p, cell, m)
            full_contact(False)
            b = rise(p, cell, m)
            nv = rise(pn, cell, m)
            print("   %s %.2f mm: full contact %.3f K (%+.2f %%, effect %.3f K)  ray test %.3f K (%+.2f %%, effect %.3f K)"
                  % (m, cell, a, 100 * (a / t["max"] - 1), nv - a, b, 100 * (b / t["max"] - 1), nv - b), flush=True)


def part_edge():
    """!
    @brief A row of four vias whose pad islands lie 0.15, 0.35 and 0.75 mm outside the edge of an imported top plane (bottom solid, a part on the plane beside them).
    @return None.
    """
    edge, heater = 5.0e-3, (2.0e-3, 3.5e-3, 4.8e-3, 6.5e-3)
    for gap in (0.40e-3, 0.60e-3, 1.0e-3):
        centres = [(round((edge + gap) / 1e-4 - 0.5) * 1e-4 + 0.5e-4, round(y / 1e-4 - 0.5) * 1e-4 + 0.5e-4) for y in (3.55e-3, 4.55e-3, 5.55e-3, 6.45e-3)]

        def top(X, Y, centres=centres):
            """!
            @brief The top plane up to the edge and the pad islands of the vias.
            @param X x in m.
            @param Y y in m.
            @param centres Via centres.
            @return bool array.
            """
            m = X <= edge
            for (cx, cy) in centres:
                m |= np.hypot(X - cx, Y - cy) <= 0.25e-3
            return m
        compare("islands %.2f mm from the plane" % ((gap - 0.25e-3) * 1e3), [top, ring_mask([], "solid")], centres, heater, nlam=8)


def part_relief4():
    """!
    @brief Four layers over the 4 x 4 via field: layer 2 a thermal relief with 0.15 mm spokes, layer 3 an antipad or solid.
    @return None.
    """
    c = via_field()
    compare("4L, L2 relief 0.15 mm, L3 antipad", [ring_mask(c, "solid"), ring_mask(c, "relief", spoke_w=0.15e-3), ring_mask(c, "anti"), ring_mask(c, "solid")], c, HEATER)
    compare("4L, L2 relief 0.15 mm, L3 solid", [ring_mask(c, "solid"), ring_mask(c, "relief", spoke_w=0.15e-3), ring_mask(c, "solid"), ring_mask(c, "solid")], c, HEATER)


def part_pixels():
    """!
    @brief The two-layer antipad and relief boards with mask pixels of 0.05 to 0.25 mm (references of the research: 517.12 and 509.14 K).
    @return None.
    """
    c = via_field()
    for kind, ref in (("anti", 517.12), ("relief", 509.14)):
        for pix in (0.05, 0.1, 0.15, 0.2, 0.25):
            p = program_problem([ring_mask(c, "solid"), ring_mask(c, kind)], c, HEATER, pix_mm=pix)
            s = shares(p)[:, 1]
            out = " ".join("%.1f mm %+.2f %%" % (cell, 100 * (rise(p, cell, "fvm") / ref - 1)) for cell in (1.0, 0.5))
            print("%-6s pixel %.2f mm, reach %.2f mm: layer 2 share mean %.2f (%.2f..%.2f) | %s" % (kind, pix, viawell.rim_masks(p).reach * 1e3, s.mean(), s.min(), s.max(), out), flush=True)


def part_hostile():
    """!
    @brief Degenerate masks on the synthetic board and the time of the rim test on a large random board.
    @return None.
    """
    c = via_field()

    def checker(X, Y):
        """!
        @brief A checkerboard of 0.05 mm pixels.
        @param X x in m.
        @param Y y in m.
        @return bool array.
        """
        return ((np.floor(X / 0.05e-3) + np.floor(Y / 0.05e-3)) % 2) == 0
    solid = ring_mask(c, "solid")
    for name, fns in (("all copper", [solid, solid]), ("checkerboard", [solid, checker]), ("empty layer", [solid, lambda X, Y: np.zeros_like(X, bool)])):
        p = program_problem(fns, c, HEATER)
        r = {m: api.simulate(p, api.SolverOptions(models=(m,), cell_mm=0.5)).results[m] for m in ("fvm", "fdm")}
        print(name, "shares", np.round(shares(p).mean(0), 2), {m: (round(x.t_max - p.board.ambient, 3), x.balance_error) for m, x in r.items()}, flush=True)
    p = Problem.new(60.0, 60.0, layers=4, thickness_mm=1.6, copper_um=35.0, name="big")
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", 10.0, 10.0, None
    p.imported = copper.imported_from_rasters([(np.random.default_rng(i).random((3000, 3000)) > 0.5).astype(np.uint8) * 255 for i in range(4)], 0.02, names=list("abcd"))
    for x, y in np.random.default_rng(1).uniform(1, 59, (2000, 2)):
        p.add_via(x, y, diameter=0.3)
    t = time.time()
    s = shares(p)
    t1 = time.time() - t
    t = time.time()
    checks.check_input(p, ("fvm",), 1.0, live=True, ui="gui")
    print("60 mm, 4 random 3000 x 3000 masks, 2000 vias: rim test %.2f s (mean share %.3f), live check %.2f s" % (t1, s.mean(), time.time() - t), flush=True)


def part_real(board, cells, reaches):
    """!
    @brief Full contact against the ray test on a library board, FVM and FDM.
    @param board Folder name in the library (PCBT_REAL_BOARDS or pcb-library/real).
    @param cells Cells in mm.
    @param reaches Reaches of the ray test in mm.
    @return None.
    """
    from pcbthermal.gui.import_session import ImportSession
    import subprocess
    # The library lives in the main checkout (a worktree has none): its folder is next to the common .git directory
    common = Path(subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip())
    main_root = (ROOT / common).resolve().parent if not common.is_absolute() else common.parent
    real = Path(os.environ.get("PCBT_REAL_BOARDS_ROOT", main_root / "pcb-library" / "real"))

    def session(cell):
        """!
        @brief Import session of the board.
        @param cell Cell in mm.
        @return ImportSession.
        """
        sx = ImportSession()
        sx.set_files(str(real / board / "gerber"))
        for i, f in enumerate(sx.files):
            if f.name == "cpl_jlc.csv":
                sx.set_use(i, False)
        sx.load()
        sx.cell_mm = cell
        return sx
    sx = session(cells[0])
    p0 = sx.build_problem()
    vx = np.array([[v.x, v.y] for v in p0.vias]).reshape(-1, 2)
    print(board, "layers", p0.board.layers, "vias", len(p0.vias), "uncoupled-via warnings", len(checks.uncoupled_vias(p0)), "named live", len(checks.uncoupled_vias(p0, drawn_only=True)), flush=True)
    for pp in sx.parts():
        sx.set_part(pp.designator, power=1.0)
    score = []
    for h in sx.build_problem().heaters:
        poly = np.asarray(h.polygon, float)
        score.append((int(((vx >= poly.min(0) - 3e-3) & (vx <= poly.max(0) + 3e-3)).all(1).sum()), h.name))
    score.sort(reverse=True)
    parts = [d for k, d in score[:3] if k > 0]
    if not parts:                                                     # no part near the vias: a drawn part on the densest via group
        cnt = sorted(((((np.abs(vx - c) <= 2.5e-3).all(1)).sum(), i) for i, c in enumerate(vx)), reverse=True)
        parts = [tuple(vx[cnt[0][1]])]
    for cell in cells:
        for d in parts:
            s2 = session(cell)
            if isinstance(d, tuple):
                prob = s2.build_problem()
                prob.add_heater(1, 1.0, rect=(d[0] * 1e3 - 1.5, d[1] * 1e3 - 1.5, d[0] * 1e3 + 1.5, d[1] * 1e3 + 1.5))
                label = "drawn"
            else:
                s2.set_part(d, power=1.0)
                prob, label = s2.build_problem(), d
            for m in ("fvm", "fdm"):
                full_contact(True)
                old = rise(prob, cell, m)
                full_contact(False)
                out = []
                for r in reaches:
                    viawell.RIM_MASK_REACH_MM = r
                    out.append("reach %.2f %+.2f %%" % (r, 100 * (rise(prob, cell, m) / old - 1)))
                viawell.RIM_MASK_REACH_MM = 0.5
                print("%-9s %.2f mm %-4s %-6s full contact %.3f K | %s" % (board, cell, m, label, old, "  ".join(out)), flush=True)


def main(argv):
    """!
    @brief Run one part.
    @param argv part name and its arguments.
    @return int exit code.
    """
    part = argv[1] if len(argv) > 1 else "relief4"
    if part == "real":
        part_real(argv[2], [float(c) for c in argv[3].split(",")], [float(r) for r in (argv[4] if len(argv) > 4 else "0.5").split(",")])
    else:
        {"edge": part_edge, "relief4": part_relief4, "pixels": part_pixels, "hostile": part_hostile}[part]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
