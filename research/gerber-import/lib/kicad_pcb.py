"""!
@file kicad_pcb.py
@brief A small reader of KiCad `.kicad_pcb` files (text, s-expressions): nets, tracks, vias, pads and zones, with the net of each, as an independent truth for the nets read from Gerber files.
@details Only what the net check needs is read: the net table, `segment` (start, end, width, layer, net), `via` (position, size, drill, layers, net), the pads of every module with their world position (module position and
         rotation applied; the KiCad axis is y down, so the Gerber y is the negative of the file y), and `zone` (net, layer, outline). Written for the 5.x format (version 20171130); the 6 and later formats name the
         objects the same way but put the net as a name, which is not handled.
"""

import math
import re


def parse(text):
    """!
    @brief Parse an s-expression into nested lists (atoms as strings, quotes removed).
    @param text File text.
    @return list The top-level expression.
    """
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()"]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t[1:-1] if t.startswith('"') else t)
    return cur[0]


def _find(node, key):
    """!
    @brief The first child list of a node that starts with a key.
    @param node List.
    @param key First atom to look for.
    @return list or None.
    """
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def _all(node, key):
    """!
    @brief Every child list of a node that starts with a key.
    @param node List.
    @param key First atom.
    @return list of lists.
    """
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def read(path):
    """!
    @brief Read the nets and copper objects of a `.kicad_pcb` file.
    @param path File path.
    @return dict with "nets" (id -> name), "segments", "vias", "pads", "zones" (lists of dicts; coordinates in mm in the file axes, y down).
    """
    root = parse(open(path, errors="replace").read())
    nets = {int(n[1]): n[2] for n in _all(root, "net")}
    out = {"nets": nets, "segments": [], "vias": [], "pads": [], "zones": []}
    for s in _all(root, "segment"):
        a, b = _find(s, "start"), _find(s, "end")
        out["segments"].append({"a": (float(a[1]), float(a[2])), "b": (float(b[1]), float(b[2])), "w": float(_find(s, "width")[1]), "layer": _find(s, "layer")[1], "net": int(_find(s, "net")[1])})
    for v in _all(root, "via"):
        at = _find(v, "at")
        out["vias"].append({"p": (float(at[1]), float(at[2])), "size": float(_find(v, "size")[1]), "drill": float(_find(v, "drill")[1]), "net": int(_find(v, "net")[1]), "layers": _find(v, "layers")[1:]})
    for z in _all(root, "zone"):
        pts = _find(_find(z, "polygon"), "pts")
        out["zones"].append({"net": int(_find(z, "net")[1]), "layer": _find(z, "layer")[1], "outline": [(float(p[1]), float(p[2])) for p in _all(pts, "xy")],
                           "min_thickness": float((_find(z, "min_thickness") or ["", "0.254"])[1]),
                           "filled": [[(float(q[1]), float(q[2])) for q in _all(_find(fp, "pts"), "xy")] for fp in _all(z, "filled_polygon")]})
    for m in _all(root, "module"):
        at = _find(m, "at")
        mx, my, mrot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        for p in _all(m, "pad"):
            pat = _find(p, "at")
            px, py = float(pat[1]), float(pat[2])
            th = math.radians(mrot)
            net = _find(p, "net")
            drill = _find(p, "drill")
            size = _find(p, "size")
            rr = _find(p, "roundrect_rratio")
            out["pads"].append({"angle": float(pat[3]) if len(pat) > 3 else mrot, "rratio": float(rr[1]) if rr else 0.25,
                                "p": (mx + px * math.cos(th) + py * math.sin(th), my - px * math.sin(th) + py * math.cos(th)),
                                "net": int(net[1]) if net else 0, "layers": _find(p, "layers")[1:], "kind": p[2], "shape": p[3],
                                "drill": float(drill[-1]) if drill and drill[-1].replace(".", "").isdigit() else 0.0,
                                "size": (float(size[1]), float(size[2])) if size else (0.0, 0.0), "module": m[1] if len(m) > 1 else ""})
    return out
