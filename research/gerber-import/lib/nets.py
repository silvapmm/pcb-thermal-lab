"""!
@file nets.py
@brief Plated holes and nets: which holes of a drill file are vias or component holes, which pad and net each one touches on every copper layer.
@details The program's `Via` is a plated through hole (position, finished diameter, optional fill). In a Gerber set a hole is a position and a diameter in the Excellon file, plated or not
         (the X2 file function `Plated,1,4,PTH` or `NonPlated,...,NPTH`), and every copper layer has a pad flashed on top of it whose aperture function says what it is (`ViaPad`,
         `ComponentPad`, `SMDPad`, ...) and whose object attribute `TO.N` says the net. This module matches the three by position.
"""

import math

import numpy as np


def nearest_pad(layer, x, y, hole_d, search_mm=0.6):
    """!
    @brief The pad of a layer closest to a hole centre, if one lies on the hole.
    @param layer Parsed native_gerber.Layer.
    @param x Hole X (mm).
    @param y Hole Y (mm).
    @param hole_d Hole diameter (mm).
    @param search_mm Unused margin kept for the interface (the test is that the hole centre lies on the pad).
    @return Tuple (function, net, pad diameter mm, distance mm) or None.
    """
    best = None
    for px, py, pd, func, net in layer.flashes():
        d = math.hypot(px - x, py - y)
        if d <= max(pd / 2.0, hole_d / 2.0) + 1e-9:                    # the hole centre lies on the pad
            if best is None or d < best[3]:
                best = (func, net, pd, d)
    return best


def hole_report(holes, layers, search_mm=0.6):
    """!
    @brief For every hole: its plating, the pad, the aperture function and the net it meets on each copper layer, and a classification.
    @details kind is "via" when a pad of the hole has the aperture function ViaPad, "component" when it has ComponentPad (a lead hole), "unknown" when the files carry no aperture functions,
             "unplated" for a non-plated hole. `same_net` is True when all the pads that carry a net agree, None when no pad carries one.
    @param holes List of tuples (x, y, diameter, plated) from native_gerber.read_drill (mm).
    @param layers List of (layer name, native_gerber.Layer) for the copper layers the drill crosses.
    @param search_mm Extra distance accepted when looking for the pad of a hole (mm).
    @return List of dicts with keys x, y, d, plated, pads (dict layer name -> (function, net, pad diameter) or None), kind, same_net, net.
    """
    out = []
    for x, y, d, plated in holes:
        pads, nets, kinds = {}, set(), []
        for name, layer in layers:
            hit = nearest_pad(layer, x, y, d, search_mm)
            pads[name] = None if hit is None else (hit[0], hit[1], hit[2])
            if hit is not None:
                kinds.append(hit[0])
                if hit[1]:
                    nets.add(hit[1])
        if plated is False:
            kind = "unplated"
        elif any(k.startswith("ViaPad") for k in kinds):
            kind = "via"
        elif any(k.startswith("ComponentPad") for k in kinds):
            kind = "component"
        else:
            kind = "unknown"
        out.append({"x": x, "y": y, "d": d, "plated": plated, "pads": pads, "kind": kind, "same_net": (len(nets) == 1) if nets else None, "net": next(iter(nets)) if len(nets) == 1 else None})
    return out


def summarize(report):
    """!
    @brief Counts of a hole report.
    @param report Result of `hole_report`.
    @return Dict with the number of holes, plated ones, kinds, holes with a pad on every layer, holes whose pads agree on the net, holes with conflicting nets and holes without any net.
    """
    plated = [r for r in report if r["plated"] is not False]
    kinds = {}
    for r in report:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"holes": len(report), "plated": len(plated), "kinds": kinds,
            "pad_on_every_layer": sum(all(v is not None for v in r["pads"].values()) for r in plated),
            "same_net": sum(r["same_net"] is True for r in plated), "conflicting_nets": sum(r["same_net"] is False for r in plated), "no_net": sum(r["same_net"] is None for r in plated)}


def via_pads(layers, decimals=2):
    """!
    @brief The via pads (aperture function ViaPad) of several copper layers grouped by position: the nets a via meets on each layer.
    @param layers List of (layer name, native_gerber.Layer).
    @param decimals Rounding of the position used to match pads of different layers (2 = 0.01 mm).
    @return Dict (x, y) -> dict layer name -> net (None when the pad has none).
    """
    out = {}
    for name, layer in layers:
        for x, y, d, func, net in layer.flashes():
            if func.startswith("ViaPad"):
                out.setdefault((round(x, decimals), round(y, decimals)), {})[name] = net
    return out


def via_summary(groups, n_layers):
    """!
    @brief Consistency of the via pads found by `via_pads`.
    @param groups Result of `via_pads`.
    @param n_layers Number of copper layers given.
    @return Dict: vias, vias with a pad on every layer, vias whose pads agree on the net, vias with conflicting nets, vias with no net, vias that join more than two layers.
    """
    full = [g for g in groups.values() if len(g) == n_layers]
    agree = [g for g in groups.values() if len({n for n in g.values() if n}) == 1]
    return {"vias": len(groups), "on_every_layer": len(full), "same_net": len(agree), "conflicting": sum(len({n for n in g.values() if n}) > 1 for g in groups.values()),
            "no_net": sum(not any(g.values()) for g in groups.values()), "join_more_than_two": sum(len(g) > 2 for g in groups.values())}


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
