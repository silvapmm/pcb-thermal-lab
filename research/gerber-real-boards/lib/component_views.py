#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file component_views.py
@brief Pictures of the matching of paste openings to parts on the RP2040 board: the 30 parts against the prototype's groups and against the envelope rule, three crops, and the box-or-hull heat-source shapes.
@details The board is the RP2040 minimal design (BSD-3-Clause, see research/README.md), read from the git-ignored data/rp2040; the data side is `component_match.py` and the prototype backend.
         `draw_all(figdir, first_number)` writes the overview of both rules and the crops, `draw_source_shape` the box-or-hull sheet. Lengths in mm.
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Polygon, Patch, Rectangle          # noqa: E402
from matplotlib.lines import Line2D                               # noqa: E402

import component_match as cm                                      # noqa: E402

GREEN, ORANGE, BLUE = "#2e9e4f", "#f08c00", "#1c6dd0"
## Module state set by setup(): the rows, unclaimed groups, board and openings the drawing helpers read.
S = {}


def setup(name="rp2040"):
    """!
    @brief Read the board and fill the module state used by the drawing helpers.
    @param name board folder name under data/.
    @return None
    """
    rows, unclaimed, ctx = cm.part_rows(name)
    bd = ctx["bd"]
    box = bd["box"]
    S.update(rows=rows, unclaimed=unclaimed, bd=bd, box=box, parts={p["ref"]: p for p in bd["placement"]}, pads=ctx["pads"], byref=ctx["byref"], bypad=ctx["bypad"],
             cu=dict(bd["copper"])["Top copper"], ext=[box[0], box[2], box[1], box[3]])


def base(ax, xlim=None, ylim=None):
    """!
    @brief Draw the top copper (light grey) and the board outline on an axis.
    @param ax matplotlib axis.
    @param xlim optional (xmin, xmax) in mm.
    @param ylim optional (ymin, ymax) in mm.
    @return None
    """
    box, bd = S["box"], S["bd"]
    ax.imshow(1 - 0.22 * S["cu"], cmap="gray", vmin=0, vmax=1, extent=S["ext"], origin="upper", interpolation="nearest")
    ax.contour(np.linspace(box[0], box[2], bd["outline"].shape[1]), np.linspace(box[3], box[1], bd["outline"].shape[0]), bd["outline"].astype(float), [0.5], colors="k", linewidths=0.8)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    if xlim:
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
    else:
        ax.set_xlim(box[0] - 1, box[2] + 1)
        ax.set_ylim(box[1] - 1, box[3] + 1)


def draw_parts(ax, col_of, only=None, lw=1.4, fill=0.28):
    """!
    @brief Draw the pad envelope of every part (dashed when through-hole), filled with the colour that col_of gives.
    @param ax matplotlib axis.
    @param col_of function row -> colour.
    @param only optional set of designators to draw.
    @param lw line width in points.
    @param fill alpha of the fill.
    @return dict ref -> (cx, cy, polygon) in mm.
    """
    cents = {}
    for r in S["rows"]:
        if only and r["ref"] not in only:
            continue
        poly = cm.part_polygon(S["parts"][r["ref"]])
        c = col_of(r)
        ax.add_patch(Polygon(poly, closed=True, fc=c, ec=c, alpha=fill, lw=0))
        ax.add_patch(Polygon(poly, closed=True, fc="none", ec=c, lw=lw, ls="-" if r["kind"] == "smd" else "--"))
        cents[r["ref"]] = (poly[:, 0].mean(), poly[:, 1].mean(), poly)
    return cents


def place_labels(ax, cents, fs=8):
    """!
    @brief Label the parts: inside the big envelopes, and for small ones pushed apart by a repulsion and joined by a leader line.
    @param ax matplotlib axis.
    @param cents result of draw_parts.
    @param fs font size in points.
    @return None
    """
    items = []
    for ref, (cx, cy, poly) in cents.items():
        w, h = np.ptp(poly[:, 0]), np.ptp(poly[:, 1])
        items.append(dict(ref=ref, cx=cx, cy=cy, big=(w > 4.5 and h > 2.2)))
    pos = {i["ref"]: np.array([i["cx"], i["cy"]], float) for i in items}
    small = [i for i in items if not i["big"]]
    ctr = np.array([np.mean([i["cx"] for i in items]), np.mean([i["cy"] for i in items])])
    for i in small:   # start the label away from the middle of the group
        d = np.array([i["cx"], i["cy"]]) - ctr
        n = np.hypot(*d) or 1
        pos[i["ref"]] = np.array([i["cx"], i["cy"]]) + d / n * 2.0
    wid, hei = 2.3 * fs / 8, 1.0 * fs / 8
    for _ in range(400):
        moved = False
        for a in small:
            for o in items:
                if o["ref"] == a["ref"]:
                    continue
                dx, dy = pos[a["ref"]][0] - pos[o["ref"]][0], pos[a["ref"]][1] - pos[o["ref"]][1]
                if abs(dx) < wid and abs(dy) < hei:
                    if abs(dx) / wid > abs(dy) / hei:
                        pos[a["ref"]][0] += 0.12 * (1 if dx >= 0 else -1)
                    else:
                        pos[a["ref"]][1] += 0.12 * (1 if dy >= 0 else -1)
                    moved = True
            c = np.array([a["cx"], a["cy"]])
            dd = pos[a["ref"]] - c
            if np.hypot(*dd) > 5:     # keep the label near its part
                pos[a["ref"]] = c + dd / np.hypot(*dd) * 5
        if not moved:
            break
    for i in items:
        p = pos[i["ref"]]
        if i["big"]:
            ax.text(i["cx"], i["cy"], i["ref"], ha="center", va="center", fontsize=fs + 1, weight="bold", color="k")
        else:
            ax.annotate(i["ref"], xy=(i["cx"], i["cy"]), xytext=(p[0], p[1]), fontsize=fs, ha="center", va="center", color="k",
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8),
                        arrowprops=dict(arrowstyle="-", lw=0.5, color="0.25", shrinkA=0, shrinkB=0))


def proto_col(r):
    """!
    @brief Colour of a part by the prototype's status.
    @param r row of part_rows.
    @return str colour
    """
    return GREEN if r["proto"] == "matched" else ORANGE


def impr_col(r):
    """!
    @brief Colour of a part by the envelope rule's status.
    @param r row of part_rows.
    @return str colour
    """
    return GREEN if r["improved"] else ORANGE


def paste_boxes(ax, alpha=0.55):
    """!
    @brief Draw every paste opening as a red rectangle.
    @param ax matplotlib axis.
    @param alpha opacity.
    @return None
    """
    for p in S["pads"]:
        x0, y0, x1, y1 = p["bbox"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#d62728", ec="none", alpha=alpha, zorder=2))


def draw_overviews(out_proto, out_impr):
    """!
    @brief The two overview pictures: the prototype's statuses and the envelope rule's.
    @param out_proto path of the prototype overview PNG.
    @param out_impr path of the improved-rule overview PNG.
    @return None
    """
    rows, n = S["rows"], len(S["pads"])
    nm = sum(r["proto"] == "matched" for r in rows)
    fig, ax = plt.subplots(figsize=(12, 11.7), dpi=100)
    base(ax)
    paste_boxes(ax)
    place_labels(ax, draw_parts(ax, proto_col), fs=7)
    for u in S["unclaimed"]:
        x0, y0, x1, y1 = u["bbox"]
        ax.add_patch(Rectangle((x0 - .08, y0 - .08), x1 - x0 + .16, y1 - y0 + .16, fc="none", ec=BLUE, lw=1.6))
    leg = [Patch(fc=GREEN, ec=GREEN, alpha=.5, label=f"part matched to a paste group by the prototype ({nm})"),
           Patch(fc=ORANGE, ec=ORANGE, alpha=.5, label=f"part in pos.csv, NOT matched by the prototype ({len(rows) - nm})"),
           Patch(fc="none", ec=BLUE, lw=1.8, label=f"paste group with no part ({len(S['unclaimed'])})"),
           Patch(fc="#d62728", alpha=.55, label=f"solder paste openings ({n})"),
           Line2D([0], [0], color="k", ls="--", label="dashed outline = through-hole part"),
           Patch(fc="0.8", label="top copper (light grey); black line = board outline")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=9, frameon=False)
    ax.set_title("RP2040 minimal board: the 30 parts of pos.csv against the paste groups (prototype rule, 0.6 mm link, 0.8 mm pick)", fontsize=11)
    fig.savefig(out_proto, bbox_inches="tight", dpi=100)
    plt.close(fig)
    ni = sum(r["improved"] for r in rows)
    fig, ax = plt.subplots(figsize=(12, 11.7), dpi=100)
    base(ax)
    paste_boxes(ax)
    place_labels(ax, draw_parts(ax, impr_col), fs=7)
    leg = [Patch(fc=GREEN, ec=GREEN, alpha=.5, label=f"part with at least one opening inside its pad envelope ({ni})"),
           Patch(fc=ORANGE, ec=ORANGE, alpha=.5, label=f"no paste opening in its envelope ({len(rows) - ni}: the three through-hole pin headers)"),
           Patch(fc="#d62728", alpha=.55, label=f"paste openings ({len(S['bypad'])} of {n} assigned)"),
           Line2D([0], [0], color="k", ls="--", label="dashed = through-hole part")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=9, frameon=False)
    ax.set_title("Same board, envelope rule: every opening goes to the part whose rotated pad envelope contains it", fontsize=11)
    fig.savefig(out_impr, bbox_inches="tight", dpi=100)
    plt.close(fig)


def draw_crops(out):
    """!
    @brief Three crops, each with the prototype on the left (groups drawn) and the envelope rule on the right, stacked in one picture.
    @param out path of the PNG.
    @return None
    """
    crops = [("RP2040 QFN, decoupling caps and resistors (six 0402 parts end in one group)", (91.5, 108.5), (-110.5, -90.0), ["U3", "C10", "C11", "C13", "C9", "R3", "R4", "C6", "C12", "R5", "C14", "C15", "C8", "C16", "C7", "C4", "C5"]),
             ("SOIC-8 (U2) and SOT-223 regulator (U1): pads 2 to 3 mm from the part origin, each pad its own group", (86.0, 113.0), (-91.5, -76.0), ["U1", "U2", "C17", "C2", "C3", "R1", "R2", "C1"]),
             ("Crystal Y1: two 5.6 mm pads either side of the part origin, so no group holds the origin", (88.0, 108.0), (-117.0, -103.5), ["Y1", "C14", "C15", "R5"])]
    unc = {u["id"] for u in S["unclaimed"]}
    # one row per crop: the axes are equal-aspect, so the row height follows the crop's aspect ratio
    heights = [(c[2][1] - c[2][0]) / (c[1][1] - c[1][0]) for c in crops]
    fig, axs = plt.subplots(3, 2, figsize=(11, 4.6 * sum(heights) + 3.2), gridspec_kw=dict(height_ratios=heights, hspace=0.45))
    for row, (title, xl, yl, only) in enumerate(crops):
        for k in (0, 1):
            ax = axs[row][k]
            base(ax, xl, yl)
            paste_boxes(ax, 0.6)
            cc = draw_parts(ax, proto_col if k == 0 else impr_col, only=set(only), lw=1.8, fill=0.2)
            if k == 0:
                for g in S["bd"]["groups"]["top"]:
                    x0, y0, x1, y1 = g["bbox"]
                    if xl[0] - 3 < x0 < xl[1] + 3 and yl[0] - 3 < y0 < yl[1] + 3:
                        ax.add_patch(Rectangle((x0 - .06, y0 - .06), x1 - x0 + .12, y1 - y0 + .12, fc="none", ec=BLUE if g["id"] in unc else "#6b6b6b", lw=1.2, ls="-" if g["id"] in unc else ":"))
                ax.set_title("prototype: blue box = unclaimed group, grey dotted = claimed", fontsize=8)
            else:
                ax.set_title("envelope rule", fontsize=8)
            for r in S["rows"]:
                if r["ref"] in cc:
                    p = S["parts"][r["ref"]]
                    ax.plot([p["x"]], [p["y"]], "k+", ms=6, mew=1.1, zorder=5)
            place_labels(ax, cc, fs=7)
        axs[row][0].annotate(title, xy=(0, 1.16), xycoords="axes fraction", fontsize=9, weight="bold")
    fig.savefig(out, bbox_inches="tight", dpi=100)
    plt.close(fig)


def _area(poly):
    """!
    @brief Area of a polygon by the shoelace formula.
    @param poly sequence of (x, y) in mm.
    @return float area in mm2
    """
    x, y = np.array(poly).T
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _hot_spot(poly, rects=None):
    """!
    @brief Indicative hot-spot rise for 1 W on a synthetic 30 x 30 mm two-layer board with full copper (FVM, 0.25 mm cell), the source centred.
    @param poly source polygon (x, y) in mm.
    @param rects optional list of rectangles (x0, y0, x1, y1) in mm: the openings heated by area instead of the polygon.
    @return float rise of the hottest cell above ambient in K
    """
    from pcbthermal import api
    from pcbthermal.model import Problem
    p = Problem.new(30, 30, layers=2)
    p.add_zone(1, rect=(0, 0, 30, 30))
    p.add_zone(2, rect=(0, 0, 30, 30))
    pts = np.array(poly)
    c = (pts.min(0) + pts.max(0)) / 2
    if rects is None:
        p.add_heater(1, 1.0, polygon=(pts - c + 15).tolist(), name="src")
    else:
        tot = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)
        for r in rects:
            p.add_heater(1, 1.0 * (r[2] - r[0]) * (r[3] - r[1]) / tot, rect=(r[0] - c[0] + 15, r[1] - c[1] + 15, r[2] - c[0] + 15, r[3] - c[1] + 15))
    res = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=0.25)).results["fvm"]
    return res.t_max - res.ambient


def draw_source_shape(out, refs=(("U1", "SOT-223 regulator"), ("U2", "SOIC-8 flash"), ("U3", "QFN-56 RP2040"), ("J3", "USB micro-B connector"))):
    """!
    @brief The sheet "bounding box or convex hull of the openings as the heat-source shape" on four parts of the board, with the areas and the indicative hot-spot rise of each.
    @param out path of the PNG.
    @param refs sequence of (designator, label) of the parts to show.
    @return list of tuples (ref, n openings, paste mm2, box mm2, hull mm2, hull over box %, T box K, T hull K, T openings K)
    """
    from scipy.spatial import ConvexHull
    bx, pix = S["box"], S["bd"]["pix"]
    out_rows = []
    fig = plt.figure(figsize=(12, 7.2), dpi=100)
    fig.suptitle("Heat-source shape from the paste openings: A = bounding box   vs   B = convex hull", fontsize=13, fontweight="bold", y=0.985)
    for k, (ref, label) in enumerate(refs):
        pads = [S["pads"][i]["bbox"] for i in S["byref"].get(ref, [])]
        pts = np.array([(b[a], b[c]) for b in pads for a, c in ((0, 1), (2, 1), (2, 3), (0, 3))])
        box = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
        boxpoly = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
        hull = pts[ConvexHull(pts).vertices]
        a_box, a_hull = _area(boxpoly), _area(hull)
        a_open = sum((b[2] - b[0]) * (b[3] - b[1]) for b in pads)
        t_box, t_hull, t_open = _hot_spot(boxpoly), _hot_spot(hull), _hot_spot(boxpoly, rects=pads)
        out_rows.append((ref, len(pads), a_open, a_box, a_hull, 100 * (a_hull - a_box) / a_box, t_box, t_hull, t_open))
        ax = fig.add_axes([0.03 + 0.245 * k, 0.5, 0.225, 0.4])
        m = 1.2
        x0, x1, y0, y1 = box[0] - m, box[2] + m, box[1] - m, box[3] + m
        # the copper raster has row 0 at the top edge of the board box
        c0, c1 = int((x0 - bx[0]) / pix), int((x1 - bx[0]) / pix)
        r0, r1 = int((bx[3] - y1) / pix), int((bx[3] - y0) / pix)
        ax.imshow(S["cu"][r0:r1, c0:c1], extent=(x0, x1, y0, y1), cmap="YlOrBr", vmin=0, vmax=1.6, origin="upper", interpolation="nearest")
        for b in pads:
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="white", ec="#333", lw=0.6, alpha=0.85))
        ax.add_patch(Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1], fc="none", ec="#d62728", lw=2.2))
        ax.add_patch(Polygon(hull, closed=True, fc="none", ec="#0b8f6a", lw=2.2, ls=(0, (4, 2))))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{ref}  {label}", fontsize=9, fontweight="bold")
        r = out_rows[-1]
        fig.text(0.03 + 0.245 * k, 0.46, f"{r[1]} openings, {r[2]:.1f} mm$^2$ of paste\nA box:  {r[3]:6.1f} mm$^2$\nB hull: {r[4]:6.1f} mm$^2$ ({r[5]:+.1f}% of A)\n\n"
                 f"hot-spot rise, 1 W (indicative):\nA box   {r[6]:5.1f} K\nB hull  {r[7]:5.1f} K ({100 * (r[7] - r[6]) / r[6]:+.1f} %)\nopenings only {r[8]:5.1f} K",
                 fontsize=8, family="monospace", va="top")
    fig.text(0.03, 0.17, "Red solid = A, bounding box of the openings. Green dashed = B, convex hull. White = openings, brown = top copper.\n"
             "Hot-spot rise: program FVM (0.25 mm cell) on a synthetic 30 x 30 mm board, two layers of full copper (35 um), 1 W, source centred, default h.\n"
             "INDICATIVE only: not the RP2040 board, not a measurement. 'openings only' = the power on the openings alone; not a bound (below the box for spread pads, above it for the QFN).",
             fontsize=8.5, color="#444", va="top")
    fig.savefig(out)
    plt.close(fig)
    return out_rows
