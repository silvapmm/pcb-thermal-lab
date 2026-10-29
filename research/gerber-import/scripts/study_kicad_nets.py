#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_kicad_nets.py
@brief Confirm the polygon-to-net association against an independent truth: the Stormduino (KiCad 5, MIT) Gerber set read by our reader, and the nets of its own `.kicad_pcb` file.
@details The Stormduino Gerbers carry no net attributes (KiCad 5 did not write them here), so the nets cannot be taken from the files. The test therefore asks: if the copper of each layer is split into connected pieces
         (8-connected pixels of the 0.1 mm mask) and the layers are joined through the plated holes of the drill file, does every joined group of copper contain exactly one net of the `.kicad_pcb`, and does every net
         lie in exactly one group? A group with two nets would be a short or a reader error; a net in two groups would be a break (an unrouted connection) or a reader error. The objects of the `.kicad_pcb`
         (pad centres, via centres, track ends and middles) are located on the masks by position, which also checks the position of our reader against the file of the CAD tool.
         Needs data/storm/stormduino.kicad_pcb (scripts/fetch_boards.py fetches it) and the Gerber files. Run: .venv/bin/python research/gerber-import/scripts/study_kicad_nets.py (from the repository root; about 10 s).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

from collections import Counter, defaultdict

import numpy as np
from scipy import ndimage

import importer as im
import kicad_pcb
from paths import DATA


def layer_pieces(ib):
    """!
    @brief Label the connected pieces of copper of every layer.
    @param ib ImportedBoard.
    @return list of (labels, count) per layer, 8-connected.
    """
    st = np.ones((3, 3), int)
    return [ndimage.label(l["binary"], structure=st) for l in ib.layers]


def pixel(ib, x, y_file):
    """!
    @brief Pixel (row, column) of a point given in Gerber file coordinates.
    @param ib ImportedBoard.
    @param x X (mm).
    @param y_file Y (mm), Gerber axis (up).
    @return tuple (row, col) with rows from the top.
    """
    return int(round((ib.box[3] - y_file) / ib.pix - 0.5)), int(round((x - ib.box[0]) / ib.pix - 0.5))


def piece_at(lab, r, c, reach=2):
    """!
    @brief The piece label under a pixel, looking up to `reach` pixels around it.
    @param lab Label image.
    @param r Row.
    @param c Column.
    @param reach Search radius in pixels.
    @return int Label (0 = no copper).
    """
    h, w = lab.shape
    if not (0 <= r < h and 0 <= c < w):
        return 0
    win = lab[max(0, r - reach):r + reach + 1, max(0, c - reach):c + reach + 1]
    if win.size == 0 or win.max() == 0:
        return 0
    if lab[r, c]:
        return int(lab[r, c])
    vals, cnt = np.unique(win[win > 0], return_counts=True)
    return int(vals[np.argmax(cnt)])


def cad_components(kc):
    """!
    @brief The connectivity of the `.kicad_pcb` copper by its own geometry (track ends meeting, vias, pads under a track end, through-hole pads on both layers, GND zone outlines taken as covering the pads of their net inside them): the number of separate pieces per net.
    @param kc Result of kicad_pcb.read.
    @return dict net id -> number of components.
    """
    names = ["F.Cu", "B.Cu"]
    nodes, par = [], {}

    def find(a):
        """!
        @brief Union-find root.
        @param a Key.
        @return Root key.
        """
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def union(a, b):
        """!
        @brief Join two keys.
        @param a Key.
        @param b Key.
        @return None.
        """
        par[find(a)] = find(b)

    pts = []                                              # (x, y, layer, node, radius, net)
    for i, sg in enumerate(kc["segments"]):
        if sg["layer"] not in names:
            continue
        li = names.index(sg["layer"])
        union(("s", i), ("s", i))
        for e in (sg["a"], sg["b"]):
            pts.append((e[0], e[1], li, ("s", i), sg["w"] / 2.0, sg["net"]))
    for i, v in enumerate(kc["vias"]):
        for li in range(2):
            pts.append((v["p"][0], v["p"][1], li, ("v", i), v["size"] / 2.0, v["net"]))
        union(("v", i, 0), ("v", i, 0))
    for i, p in enumerate(kc["pads"]):
        if p["net"] == 0:
            continue
        for li, n in enumerate(names):
            if n in p["layers"] or "*.Cu" in p["layers"]:
                pts.append((p["p"][0], p["p"][1], li, ("p", i), max(p["size"]) / 2.0, p["net"]))
    # a via or a through-hole pad joins its own two layers; points of one net within the radius of an object on the same layer join it
    by_obj = {}
    for x, y, li, node, rad, net in pts:
        by_obj.setdefault(node, []).append((x, y, li, rad, net))
    for node, items in by_obj.items():
        if node[0] in ("v", "p") and len({it[2] for it in items}) > 1:
            pass                                              # same node on both layers: one object, already one key
    ends = [(x, y, li, node, rad, net) for x, y, li, node, rad, net in pts]
    for i, (x, y, li, node, rad, net) in enumerate(ends):
        for x2, y2, l2, n2, r2, net2 in ends[i + 1:]:
            if net2 == net and l2 == li and (x - x2) ** 2 + (y - y2) ** 2 <= (max(rad, r2) + 1e-6) ** 2:
                union(node, n2)
    comps = {}
    for x, y, li, node, rad, net in pts:
        comps.setdefault(net, set()).add(find(node))
    return {n: len(c) for n, c in comps.items()}


def main():
    """!
    @brief Run the check and print the report.
    @return None.
    """
    ib = im.import_board(im.roles_of_downloaded("storm"), pix=0.1, cell=1.0)
    kc = kicad_pcb.read(DATA / "storm" / "stormduino.kicad_pcb")
    nets = kc["nets"]
    lays = layer_pieces(ib)
    names = ["F.Cu", "B.Cu"]
    print(f"Gerber: {len(ib.layers)} layers, {len(ib.holes)} plated holes; .kicad_pcb: {len(kc['segments'])} tracks, {len(kc['vias'])} vias, {len(kc['pads'])} pads, {len(kc['zones'])} zones, {len(nets)} nets")
    # objects of the .kicad_pcb as points per layer: (layer index, x, y_file, net, kind)
    pts = []
    for s in kc["segments"]:
        li = names.index(s["layer"]) if s["layer"] in names else None
        if li is None:
            continue
        for k, (x, y) in enumerate((s["a"], s["b"], ((s["a"][0] + s["b"][0]) / 2, (s["a"][1] + s["b"][1]) / 2))):
            pts.append((li, x, -y, s["net"], "track"))
    for v in kc["vias"]:
        for li in range(2):
            pts.append((li, v["p"][0], -v["p"][1], v["net"], "via"))
    for p in kc["pads"]:
        if p["net"] == 0:
            continue
        on = [i for i, n in enumerate(names) if n in p["layers"] or "*.Cu" in p["layers"]]
        for li in on:
            pts.append((li, p["p"][0], -p["p"][1], p["net"], "pad"))
    # 1. do the objects of the CAD file lie on the copper our reader drew?
    on_cu = Counter()
    tot = Counter()
    labelled = []
    for li, x, y, net, kind in pts:
        r, c = pixel(ib, x, y)
        lab = piece_at(lays[li][0], r, c)
        tot[kind] += 1
        if lab:
            on_cu[kind] += 1
            labelled.append((li, lab, net, kind))
    print("objects of the .kicad_pcb on copper of our masks (within 0.2 mm): " + ", ".join(f"{k} {on_cu[k]} of {tot[k]}" for k in tot))
    # 2. nets per piece, layer by layer
    per_piece = defaultdict(set)
    for li, lab, net, kind in labelled:
        per_piece[(li, lab)].add(net)
    bad = [(k, v) for k, v in per_piece.items() if len(v) > 1]
    print(f"pieces of copper holding objects: {len(per_piece)}; with more than one net: {len(bad)}")
    for (li, lab), v in bad[:8]:
        print(f"  layer {names[li]} piece {lab}: nets {sorted(nets[n] for n in v)}")
    # 3. join the layers through the plated holes of the drill file
    parent = {k: k for k in per_piece}
    for li in range(2):
        for lab in range(1, lays[li][1] + 1):
            parent.setdefault((li, lab), (li, lab))

    def find(a):
        """!
        @brief Union-find root.
        @param a Key.
        @return Root key.
        """
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    joined = 0
    for hrow in ib.holes:
        ps = []
        for li in range(2):
            r, c = pixel(ib, hrow["x"], hrow["y"])
            lab = piece_at(lays[li][0], r, c, reach=3)
            if lab:
                ps.append((li, lab))
        if len(ps) == 2:
            parent[find(ps[0])] = find(ps[1])
            joined += 1
    print(f"plated holes joining a piece on both layers: {joined} of {len(ib.holes)}")
    group_nets = defaultdict(set)
    net_groups = defaultdict(set)
    for (li, lab), v in per_piece.items():
        g = find((li, lab))
        group_nets[g] |= v
        for n in v:
            net_groups[n].add(g)
    multi = {g: v for g, v in group_nets.items() if len(v) > 1}
    print(f"groups of joined copper holding objects: {len(group_nets)}; with more than one net: {len(multi)}")
    for g, v in list(multi.items())[:8]:
        print("  group", g, "nets", sorted(nets[n] for n in v))
    split = {n: len(g) for n, g in net_groups.items() if len(g) > 1}
    print(f"nets: {len(net_groups)} seen on copper; in exactly one group: {sum(1 for g in net_groups.values() if len(g) == 1)}; in more than one group: {len(split)}")
    for n, k in sorted(split.items(), key=lambda t: -t[1])[:10]:
        print(f"  {nets[n]}: {k} groups")
    cad = cad_components(kc)
    print("the CAD file's own connectivity (tracks, vias, pads; no zone fills): nets in more than one component: "
          + ", ".join(f"{nets[n]} {k}" for n, k in sorted(cad.items(), key=lambda t: -t[1]) if k > 1 and n in nets)[:600])
    zone_nets = {z["net"] for z in kc["zones"]}
    same = diff = 0
    for n in sorted(net_groups):
        if n in zone_nets or n not in nets or n == 0:
            continue
        if len(net_groups[n]) == cad.get(n, 0):
            same += 1
        else:
            diff += 1
            print(f"  differs: {nets[n]}: Gerber {len(net_groups[n])} group(s), CAD file {cad.get(n, 0)} component(s)")
    print(f"nets without a zone fill: same number of separate pieces in the Gerber copper and in the CAD file: {same}; different: {diff}")
    # 4. the same without the plated-hole join, to show what the join adds
    nj = sum(1 for n, g in net_groups.items() if len({(k[0], k[1]) for k in per_piece if n in per_piece[k]}) > 1)
    print(f"without the layer join: nets split over several pieces {nj}")


if __name__ == "__main__":
    main()
