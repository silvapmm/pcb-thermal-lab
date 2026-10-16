"""!
@file fem3d_validation.py
@brief Independent 3D finite-element check of the three models (offline script, not part of the program).

The board is solved as a real 3D solid with hexahedral finite elements (scikit-fem): copper slabs of their true thickness
between FR-4 slabs, anisotropic FR-4, convection on the faces and edges, the heater as a heat flux on its footprint. The model
therefore does not use the "one node per copper layer" idea of the three models of the program, and gives a reference for the
error of that idea. The maximum surface temperature under the heater is compared with the FVM, Lumped and Analytic models.

Usage: python examples/fem3d_validation.py            (needs scikit-fem: pip install scikit-fem; not in requirements.txt)
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scipy.sparse.linalg as spla                                       # noqa: E402
from skfem import Basis, BilinearForm, ElementHex1, FacetBasis, LinearForm, MeshHex, asm   # noqa: E402

from pcbthermal import Problem, SolverOptions, simulate                  # noqa: E402


def _axis_lines(length, step, centres, half_width):
    """!
    @brief Mesh lines along one axis: a uniform grid plus fine lines around the given centres (for the vias).
    @param length Board size along the axis (m).
    @param step Uniform spacing (m).
    @param centres Positions (m) where the mesh is refined.
    @param half_width Half width (m) of the rod that must be resolved at every centre.
    @return Sorted array of line coordinates (m) starting at 0 and ending at the board size.
    """
    lines = list(np.linspace(0.0, length, int(round(length / step)) + 1))
    for c in centres:
        # The rod faces, then a graded transition to the uniform grid (spacing growing by about a factor of two)
        h = half_width
        for k, off in enumerate((h, h + 0.1e-3, h + 0.25e-3, h + 0.5e-3, h + 0.9e-3)):
            lines += [c - off, c + off]
    lines = np.sort(np.array([x for x in lines if 0.0 <= x <= length]))
    keep = [lines[0]]
    for x in lines[1:]:
        if x - keep[-1] > 0.02e-3:                                        # Drop lines closer than 20 micrometres
            keep.append(x)
    keep[-1] = length
    return np.array(keep)


def solve_fem(problem, dxy_mm=1.0, n_diel=4, with_vias=True):
    """!
    @brief Solve the steady state of a board as a 3D solid.
    @details Copper slabs have their true thickness (one element), every dielectric gap has n_diel elements, FR-4 is anisotropic,
             convection acts on both faces and the edges, a sink adds its coefficient on the bottom facets inside its polygon and
             a heater is a heat flux on its footprint. A via is a copper rod of the same copper area as the plated barrel (the wall
             of 25 micrometres is far below the mesh), running through the whole thickness; the mesh is refined around the rods.
    @param problem A Problem with rectangular zones, heaters, optional vias and rectangular sinks.
    @param dxy_mm Element size in the board plane (millimetres); it must divide the zone and heater edges.
    @param n_diel Elements across every dielectric gap.
    @param with_vias False to ignore the vias.
    @return Dict with the maximum temperature of the top face (degC), its mean under the first heater, the mesh size and the time.
    """
    t0 = time.time()
    b, m = problem.board, problem.board.materials
    W, H, L = b.width, b.height, b.layers
    tcu = np.asarray(b.copper_thickness)
    d = b.dielectric_thickness()
    vias = problem.vias if with_vias else []
    # Square rod with the copper area of the barrel
    side = np.sqrt(vias[0].copper_area(b.via_plating)) if vias else 0.0
    # Slabs from the top face down: copper 1, gap, copper 2, gap, ...
    zs_down, kinds = [0.0], []
    for l in range(L):
        zs_down.append(zs_down[-1] + tcu[l])
        kinds.append(("cu", l, 1))
        if l < L - 1:
            for _ in range(n_diel):
                zs_down.append(zs_down[-1] + d / n_diel)
                kinds.append(("fr4", l, 1))
    zs = b.thickness - np.array(zs_down)[::-1]                 # Heights from the bottom face up
    kinds = kinds[::-1]
    xl = _axis_lines(W, dxy_mm * 1e-3, sorted({v.x for v in vias}), side / 2.0)
    yl = _axis_lines(H, dxy_mm * 1e-3, sorted({v.y for v in vias}), side / 2.0)
    nx, ny = len(xl) - 1, len(yl) - 1
    mesh = MeshHex.init_tensor(xl, yl, zs)
    # Element ordering of init_tensor: y fastest, then x, then z (checked on a small mesh)
    ex = 0.5 * (xl[:-1] + xl[1:])
    ey = 0.5 * (yl[:-1] + yl[1:])
    XX, YY = np.meshgrid(ex, ey, indexing="ij")                 # Shape (nx, ny): the element index runs along y first
    rods = np.zeros((nx, ny), bool)
    for v in vias:
        rods |= (np.abs(XX - v.x) < side / 2.0) & (np.abs(YY - v.y) < side / 2.0)
    cu_idx, fr_idx = [], []
    for k, (kind, layer, _) in enumerate(kinds):
        base = k * nx * ny
        ids = base + np.arange(nx * ny)
        inside = rods.copy()                                    # A via is copper through every slab
        if kind == "cu":
            for z in problem.zones:
                if z.layer == layer:
                    x0, y0 = z.polygon.min(axis=0)
                    x1, y1 = z.polygon.max(axis=0)
                    inside |= (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)
        cu_idx.append(ids[inside.ravel()])
        fr_idx.append(ids[~inside.ravel()])
    cu_idx, fr_idx = np.concatenate(cu_idx), np.concatenate(fr_idx)
    elem = ElementHex1()

    def conduction(kxy, kz):
        @BilinearForm
        def form(u, v, w):
            return kxy * (u.grad[0] * v.grad[0] + u.grad[1] * v.grad[1]) + kz * u.grad[2] * v.grad[2]
        return form

    cb = Basis(mesh, elem, elements=cu_idx)
    K = asm(conduction(m.k_copper, m.k_copper), cb)
    fb = Basis(mesh, elem, elements=fr_idx)
    K = K + asm(conduction(m.k_fr4_inplane, m.k_fr4_through), fb)
    basis = Basis(mesh, elem)

    def facets(cond):
        return mesh.facets_satisfying(cond)

    top = facets(lambda x: np.isclose(x[2], b.thickness))
    bot = facets(lambda x: np.isclose(x[2], 0.0))
    side_f = facets(lambda x: np.isclose(x[0], 0) | np.isclose(x[0], W) | np.isclose(x[1], 0) | np.isclose(x[1], H))
    rhs = np.zeros(basis.N)
    for fs, h in ((top, b.h_top), (bot, b.h_bottom), (side_f, b.h_side or 0.0)):
        if len(fs) and h:
            fbasis = FacetBasis(mesh, elem, facets=fs)
            K = K + asm(BilinearForm(lambda u, v, w, h=h: h * u * v), fbasis)
    for sk in problem.sinks:
        x0, y0 = sk.polygon.min(axis=0)
        x1, y1 = sk.polygon.max(axis=0)
        z_face = b.thickness if sk.layer == 0 else 0.0
        sel = facets(lambda x, x0=x0, x1=x1, y0=y0, y1=y1, zf=z_face: np.isclose(x[2], zf)
                     & (x[0] >= x0 - 1e-9) & (x[0] <= x1 + 1e-9) & (x[1] >= y0 - 1e-9) & (x[1] <= y1 + 1e-9))
        K = K + asm(BilinearForm(lambda u, v, w, h=sk.h_extra: h * u * v), FacetBasis(mesh, elem, facets=sel))
    for hh in problem.heaters:
        x0, y0 = hh.polygon.min(axis=0)
        x1, y1 = hh.polygon.max(axis=0)
        area = (x1 - x0) * (y1 - y0)
        sel = facets(lambda x, x0=x0, x1=x1, y0=y0, y1=y1: np.isclose(x[2], b.thickness)
                     & (x[0] >= x0 - 1e-9) & (x[0] <= x1 + 1e-9) & (x[1] >= y0 - 1e-9) & (x[1] <= y1 + 1e-9))
        fbasis = FacetBasis(mesh, elem, facets=sel)
        rhs += asm(LinearForm(lambda v, w, flux=hh.power / area: flux * v), fbasis)
    theta = spla.spsolve(K.tocsc(), rhs, permc_spec="MMD_AT_PLUS_A")
    # Temperature of the top face under the first heater
    p = mesh.p
    on_top = np.isclose(p[2], b.thickness)
    x0, y0 = problem.heaters[0].polygon.min(axis=0)
    x1, y1 = problem.heaters[0].polygon.max(axis=0)
    under = on_top & (p[0] >= x0 - 1e-9) & (p[0] <= x1 + 1e-9) & (p[1] >= y0 - 1e-9) & (p[1] <= y1 + 1e-9)
    return {"t_max": float(theta[on_top].max() + b.ambient), "t_under_mean": float(theta[under].mean() + b.ambient),
            "t_top_mean": float(theta[on_top].mean() + b.ambient), "nodes": basis.N, "elements": mesh.t.shape[1],
            "seconds": time.time() - t0}


def board_full_copper():
    """!
    @brief 100 x 80 mm, 4 layers, copper on every layer, one 10 x 10 mm heater of 4 W (no vias).
    @return Problem.
    """
    p = Problem.new(100, 80, 4)
    p.add_full_copper()
    p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    return p


def board_partial_copper():
    """!
    @brief 100 x 80 mm, 2 layers; the top copper is only a 40 x 40 mm pad around the 10 x 10 mm heater, the bottom is solid.
    @return Problem.
    """
    p = Problem.new(100, 80, 2)
    p.add_zone(1, rect=(15, 20, 55, 60))
    p.add_zone(2, rect=(0, 0, 100, 80))
    p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    return p


def board_small_pad():
    """!
    @brief 100 x 80 mm, 2 layers; the top copper is a 20 x 20 mm pad (heater 10 x 10 mm), the bottom is solid.
    @return Problem.
    """
    p = Problem.new(100, 80, 2)
    p.add_zone(1, rect=(25, 30, 45, 50))
    p.add_zone(2, rect=(0, 0, 100, 80))
    p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    return p


def main():
    """!
    @brief Run the cases and print the comparison table (3D FEM at two resolutions to show convergence).
    @return List of result rows.
    """
    rows = []
    cases = (("4 layers, full copper", board_full_copper, (2.0, 1.0)),
             ("2 layers, 40 x 40 mm top pad", board_partial_copper, (1.0, 0.5)),
             ("2 layers, 20 x 20 mm top pad", board_small_pad, (1.0, 0.5)))
    for name, build, resolutions in cases:
        problem = build()
        fem = [solve_fem(problem, r) for r in resolutions]
        sim = simulate(problem, SolverOptions(cell_mm=0.5))
        ref = fem[-1]["t_max"]
        print(f"\n{name}")
        for r, f in zip(resolutions, fem):
            print(f"  3D FEM element {r:g} mm: {f['t_max']:.2f} degC ({f['nodes']} nodes, {f['seconds']:.0f} s)")
        row = {"case": name, "fem": ref}
        for k, r in sim.results.items():
            row[k] = r.t_max
            print(f"  {k:9s} {r.t_max:7.2f} degC   {100 * (r.t_max - 25) / (ref - 25) - 100:+6.1f} % of the rise against the 3D FEM")
        rows.append(row)
    return rows


if __name__ == "__main__":
    main()
