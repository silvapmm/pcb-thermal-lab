"""!
@file study_net_joule.py
@brief From a Gerber with net names to the heat of one net: read the net's copper, put 1 A through it between its two farthest pads and map the Joule power to 1 mm cells.
@details Uses the KiCad file of gerbonara's test resources (charliewatch-v2 panel, X2 attribute TO.N on every object; downloaded by study_reader_conformance.py, git-ignored).
         For every net with at least two pads: the share of the layer's copper it owns, the resistance between its two farthest pads, I^2 R at 1 A, the hottest 1 mm cell of the
         Joule map and the check that the cell map keeps the total. The per-net areas must add up to the copper of the layer (nets overlap only at their borders).
         Run: python study_net_joule.py
"""

import numpy as np
from scipy import ndimage

import joule
import native_gerber as ng
from study_reader_conformance import DEST

PIX = 0.05                       # mm
T_CU = 35e-6                     # m
CURRENT = 1.0                    # A
FILES = ["zero-length-lines__charliewatch-v2.panel-F_Cu.gbr", "zero-length-lines__charliewatch-v2.panel-B_Cu.gbr"]


def net_pads(layer, net):
    """!
    @brief Flash positions (pads) of a net.
    @param layer Parsed layer.
    @param net Net name.
    @return List of (x, y) in mm.
    """
    return [(a[1], a[2]) for (kind, dark, a), n in zip(layer.ops, layer.nets) if kind == "flash" and dark and n == net]


def disc(canvas_shape, canvas, x, y, r):
    """!
    @brief Boolean mask of a disc of radius r (mm) around a point, on the canvas pixels.
    @param canvas_shape Shape of the mask.
    @param canvas Canvas that maps mm to pixels.
    @param x X (mm).
    @param y Y (mm).
    @param r Radius (mm).
    @return Boolean array.
    """
    cx = (np.arange(canvas_shape[1]) + 0.5) * canvas.pix + canvas.x0
    cy = canvas.y0 - (np.arange(canvas_shape[0]) + 0.5) * canvas.pix
    return (cx[None, :] - x) ** 2 + (cy[:, None] - y) ** 2 <= r * r


def run(name):
    """!
    @brief Study one layer file.
    @details The nets of the objects (pads, tracks) are known from the file; zone fills often carry no net, so the net of every piece of connected copper is found from the labelled objects
             it contains (a piece with two nets would be a short circuit or a panel with repeated names). For every net the largest piece with two or more pads is solved between its two
             farthest pads.
    @param name File name in the conformance folder.
    @return None (prints).
    """
    layer = ng.Layer((DEST / name).read_text(errors="replace"))
    bb = layer.bbox()
    w, h = bb[2] - bb[0] + 0.4, bb[3] - bb[1] + 0.4
    cv_all = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, PIX)
    layer.draw(cv_all)
    lab, ncomp = ndimage.label(cv_all.mask)                              # 4-connected pieces of copper
    nets = layer.net_names()
    print(f"\n{name}: {len(nets)} nets, {cv_all.mask.sum() * PIX ** 2:.1f} mm2 of copper in {ncomp} pieces, objects without a net: {sum(1 for n in layer.nets if n is None)}")
    owner = {}                                                          # piece -> set of nets
    for net in nets:
        cv = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, PIX)
        layer.draw(cv, [net])
        for c in np.unique(lab[cv.mask & (lab > 0)]):
            owner.setdefault(int(c), set()).add(net)
    sizes = np.bincount(lab.ravel())
    covered = sum(sizes[c] for c, v in owner.items() if len(v) == 1)
    multi = [c for c, v in owner.items() if len(v) > 1]
    print(f"  pieces with exactly one net: {sum(1 for v in owner.values() if len(v) == 1)}, with several nets: {len(multi)}, with none: {ncomp - len(owner)}")
    print(f"  copper in pieces with exactly one net: {covered / cv_all.mask.sum():.3f} of the layer")
    rows, skipped = [], 0
    for net in nets:
        pieces = [c for c, v in owner.items() if v == {net}]
        pads = [pt for pt in net_pads(layer, net)]
        best = None
        for c in pieces:
            pa = [pt for pt in pads if lab[int((cv_all.y0 - pt[1]) / PIX), int((pt[0] - cv_all.x0) / PIX)] == c]
            if len(pa) >= 2 and (best is None or sizes[c] > sizes[best[0]]):
                best = (c, np.array(pa))
        if best is None:
            continue
        c, pa = best
        d = np.hypot(pa[:, None, 0] - pa[None, :, 0], pa[:, None, 1] - pa[None, :, 1])
        i, j = np.unravel_index(d.argmax(), d.shape)
        mask = lab == c
        src = disc(mask.shape, cv_all, pa[i][0], pa[i][1], 0.25) & mask
        snk = disc(mask.shape, cv_all, pa[j][0], pa[j][1], 0.25) & mask
        try:
            r, v, q = joule.solve_net(mask, joule.resistivity(20.0) / T_CU, src, snk, CURRENT)
        except ValueError:                                              # coincident pads (zero-length objects of the file) or unconnected terminals
            skipped += 1
            continue
        cells = joule.to_cells(q, int(round(1.0 / PIX)))
        assert abs(cells.sum() - q.sum()) < 1e-12 * max(q.sum(), 1e-30)
        rows.append((net, sizes[c] * PIX ** 2, d.max(), len(pa), r * 1000, q.sum() * 1000, cells.max() * 1000))
    print(f"  nets skipped because the two terminals coincide or are not connected: {skipped}")
    print(f"  {'net (largest piece with 2+ pads)':34s} {'area mm2':>9s} {'pad span mm':>11s} {'pads':>5s} {'R mOhm':>8s} {'I2R mW @1A':>11s} {'hottest 1mm cell mW':>20s}")
    for r in sorted(rows, key=lambda x: -x[4])[:10]:
        print(f"  {r[0][:34]:34s} {r[1]:9.1f} {r[2]:11.1f} {r[3]:5d} {r[4]:8.1f} {r[5]:11.1f} {r[6]:20.1f}")


def main():
    """!
    @brief Run the study on the KiCad files.
    @return None.
    """
    for f in FILES:
        run(f)


if __name__ == "__main__":
    main()
