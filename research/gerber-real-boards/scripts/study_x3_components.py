#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_x3_components.py
@brief What does a Gerber X3 component layer give the import (reference, footprint, value, mount, rotation, outline, pins), and does it link every part to its paste openings and copper pads exactly?
@details Questions, on the three Ucamco X3 sample boards (StickHub, Kit Dev Coldfire Xilinx, Li-ion charger; component, paste and copper files in `data/`):
         A. Counts: components, with origin, outline (by type), pins, height, each characteristic attribute; three readers must agree on the references: `lib/x3_components.py` (the prototype of
            `pcbthermal/gerber/components.py`), `lib/x3.py` (the regex reader of the earlier study) and, when the path given by the environment variable PCBT_GERBER_READER (default: the worktree of
            feature/gerber-reader) exists, the program's reader `pcbthermal.gerber` (`Layer.references()` and the pin flashes).
         B. The rotation rule of the specification (page 166: positive counter-clockwise seen from the top, a bottom part is the top part flipped along the X axis): for every footprint used by two or more parts,
            the pins of each part are brought back to the footprint frame under the rule and under the other sign / flip choices; the rule is right when the footprint frames agree (spread below 5 micrometres).
         C. Links: the references of the paste file (`TO.C`) and of the copper files (`TO.P`, first field) against the component layer; the paste box against the courtyard and the pin hull
            (area ratios; the courtyard also against the paste box in the frame of the part, which does not grow with a 45-degree rotation); the offset of `ComponentMain` from the centre of the paste group; the pin positions of the component layer against the copper pads with the same `TO.P` (reference and pin).
         D. The heat shape per part (`heat_shape`): which source it comes from on these files.
         Output: out/x3_components.json and the printed tables (the data of README 12). NOT verified: a file with Body or Lead2Lead outlines or `.CHgt` (none of the samples has them), Altium, Cadence or Eagle output.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_x3_components.py   (about 2 s, 130 MB)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import math
import os
import statistics
import sys
from pathlib import Path

import numpy as np

import paste
import x3
import x3_components as xc

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
OUT = HERE / "out"
READER = os.environ.get("PCBT_GERBER_READER", "/Volumes/SSD/PROJETOS/pcb-thermal-lab/.claude/worktrees/agent-af0e0978b5e34e481")

## board -> {side: (component layer, paste layer, copper layer)}; relative to data/
BOARDS = {
    "stickhub": {"top": ("stickhub/compF.gbr", "stickhub/pasteF.gbr", "stickhub/F.gbr"),
                 "bottom": ("stickhub/compB.gbr", "stickhub/pasteB.gbr", "stickhub/B.gbr")},
    "coldfire": {"top": ("ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-pnp_top.gbr", "ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-F_Paste.gbr",
                         "ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-Top_layer.gbr"),
                 "bottom": ("ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-pnp_bottom.gbr", "ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-B_Paste.gbr",
                            "ucamco/x3_coldfire/kit-dev-coldfire-xilinx_5213-Bottom_layer.gbr")},
    "liion": {"top": ("ucamco/x3_liion/li-ion_charger-pnp_top.gbr", "ucamco/x3_liion/li-ion_charger-F_Paste.gbr", "ucamco/x3_liion/li-ion_charger-Composant.gbr"),
              "bottom": ("ucamco/x3_liion/li-ion_charger-pnp_bottom.gbr", "ucamco/x3_liion/li-ion_charger-B_Paste.gbr", "ucamco/x3_liion/li-ion_charger-Cuivre.gbr")},
}


def program_layer(path):
    """!
    @brief Read a file with the program's reader when it is available.
    @param path File path.
    @return pcbthermal.gerber.Layer or None when the reader package is not found.
    """
    if not Path(READER, "pcbthermal", "gerber").is_dir():
        return None
    if READER not in sys.path:
        sys.path.insert(0, READER)
    from pcbthermal import gerber as g  # noqa: PLC0415
    return g.read_layer(path)


def local_pins(part, variant):
    """!
    @brief The pins of a part in the footprint frame under one convention.
    @param part Component.
    @param variant Tuple (sign of the rotation, mirror) with sign +1 or -1 (the rotation that is undone is sign * CRot) and mirror "none", "x" (x changes sign) or "y" (y changes sign), applied after the rotation is undone.
    @return dict pin number -> (x, y) in mm.
    """
    sgn, mir = variant
    a = math.radians(sgn * part.rotation)
    c, s = math.cos(a), math.sin(a)
    out = {}
    for p in part.pins:
        dx, dy = p.x - part.origin[0], p.y - part.origin[1]
        lx, ly = c * dx + s * dy, -s * dx + c * dy
        if mir == "x":
            lx = -lx
        elif mir == "y":
            ly = -ly
        out[p.number] = (lx, ly)
    return out


def spread(parts, variant):
    """!
    @brief The largest distance of a pin of any part from the same pin of the first part, in the footprint frame.
    @param parts List of Component with the same footprint.
    @param variant See `local_pins`.
    @return float mm; inf when the pin numbers differ.
    """
    ref = local_pins(parts[0], variant)
    worst = 0.0
    for p in parts[1:]:
        q = local_pins(p, variant)
        if set(q) != set(ref):
            return math.inf
        worst = max(worst, max(math.hypot(q[k][0] - ref[k][0], q[k][1] - ref[k][1]) for k in ref))
    return worst


def local_pins_order(part, sgn, mir, before):
    """!
    @brief Like `local_pins` with the mirror applied either after the rotation is undone (`before` False) or on the board offsets before it is undone (`before` True).
    @param part Component.
    @param sgn Sign of the rotation that is undone (+1 or -1).
    @param mir "none", "x" or "y".
    @param before True to mirror first.
    @return dict pin number -> (x, y).
    """
    a = math.radians(sgn * part.rotation)
    c, s = math.cos(a), math.sin(a)
    out = {}
    for p in part.pins:
        dx, dy = p.x - part.origin[0], p.y - part.origin[1]
        if before:
            dx, dy = (-dx if mir == "x" else dx), (-dy if mir == "y" else dy)
        lx, ly = c * dx + s * dy, -s * dx + c * dy
        if not before:
            lx, ly = (-lx if mir == "x" else lx), (-ly if mir == "y" else ly)
        out[p.number] = (lx, ly)
    return out


def cross_side_test(top, bottom):
    """!
    @brief Which convention for a bottom part makes the footprint frame equal to that of the same footprint on the top (top part: rotation undone with the CCW rule, no mirror).
    @param top Components of the top layer.
    @param bottom Components of the bottom layer.
    @return dict variant text -> (footprints that agree within 5 micrometres, footprints tested); a footprint is tested when it has at least 2 pins and a top and a bottom part
            and the top and the bottom parts do not both lie on a symmetry (the pin sets differ under every mirror, so the test can tell them apart).
    """
    tf = {}
    for p in top:
        if len(p.pins) >= 2 and p.footprint not in tf:
            tf[p.footprint] = p
    bf = {}
    for p in bottom:
        if len(p.pins) >= 2 and p.footprint not in bf:
            bf[p.footprint] = p
    shared = [k for k in tf if k in bf]
    res = {}
    for before in (False, True):
        for sgn in (1, -1):
            for mir in ("none", "x", "y"):
                ok = 0
                for k in shared:
                    a, b = local_pins_order(tf[k], 1, "none", False), local_pins_order(bf[k], sgn, mir, before)
                    if set(a) == set(b) and max(math.hypot(a[n][0] - b[n][0], a[n][1] - b[n][1]) for n in a) < 0.005:
                        ok += 1
                res[f"bottom: sign {sgn:+d}, mirror {mir}, {'before' if before else 'after'} the rotation"] = (ok, len(shared))
    return res


def rotation_test(parts):
    """!
    @brief For the footprints used by two or more parts of one side, how many are consistent under each convention.
    @param parts List of Component of one side.
    @return dict variant text -> (footprints consistent, footprints tested); only footprints with at least two parts and two pins whose rotations are not all equal (equal rotations cannot tell the signs apart).
    """
    groups = {}
    for p in parts:
        if len(p.pins) >= 2 and p.origin is not None:
            groups.setdefault(p.footprint, []).append(p)
    groups = {k: v for k, v in groups.items() if len(v) >= 2 and len({round(q.rotation % 360, 3) for q in v}) >= 2}
    res = {}
    for sgn in (1, -1):
        for mir in ("none", "x", "y"):
            ok = sum(1 for v in groups.values() if spread(v, (sgn, mir)) < 0.005)
            res[f"sign {sgn:+d}, mirror {mir}"] = (ok, len(groups))
    return res


def main():
    """!
    @brief Run the study and print the tables.
    @return int Process exit code (0).
    """
    OUT.mkdir(exist_ok=True)
    out = {}
    for board, sides in BOARDS.items():
        rows = {}
        cross = {}
        for side, (comp_f, paste_f, cu_f) in sides.items():
            cp, pp, cf = DATA / comp_f, DATA / paste_f, DATA / cu_f
            if not cp.exists():
                print(f"{board} {side}: component layer missing, run fetch_boards.py --ucamco")
                continue
            parts = xc.parse(cp.read_text(errors="replace"), cp.name)
            old = x3.components(cp)
            refs = [p.ref for p in parts]
            row = {"components": len(parts), "unique_refs": len(set(refs)), "duplicate_refs": xc.duplicate_references(parts),
                   "with_origin": sum(1 for p in parts if p.origin), "with_pins": sum(1 for p in parts if p.pins),
                   "pins": sum(len(p.pins) for p in parts), "key_pins": sum(1 for p in parts for q in p.pins if q.key),
                   "with_height": sum(1 for p in parts if p.height_mm is not None),
                   "mount": {m: sum(1 for p in parts if p.mount == m) for m in sorted({p.mount for p in parts})},
                   "outline_types": {k: sum(1 for p in parts if p.outlines.get(k)) for k in xc.OUTLINE_TYPES},
                   "no_outline": sum(1 for p in parts if not p.outlines), "with_footprint": sum(1 for p in parts if p.footprint),
                   "with_value": sum(1 for p in parts if p.value), "with_mpn": sum(1 for p in parts if p.mpn),
                   "notes": sum(len(p.notes) for p in parts)}
            row["old_reader_same_refs"] = [o["ref"] for o in old] == refs
            row["old_reader_same_pins"] = sum(len(o["pins"]) for o in old) == row["pins"]
            lay = program_layer(cp)
            if lay is not None:
                prog_refs = lay.references()
                prog_pins = sum(1 for f in lay.flashes() if f.pin)
                row["program_reader_same_refs"] = set(prog_refs) == set(refs)
                row["program_reader_pin_flashes"] = prog_pins
                row["program_reader_function"] = lay.file_function
            # B. rotation rule
            row["rotation_test"] = rotation_test(parts)
            # C. paste links
            groups = paste.by_reference(pp) if pp.exists() else {}
            link = [r for r in refs if r in groups]
            row["paste_refs"] = len(groups)
            row["x3_in_paste"] = len(link)
            row["x3_without_paste"] = len(refs) - len(link)
            row["paste_not_in_x3"] = sorted(set(groups) - set(refs))
            noPaste = [p for p in parts if p.ref not in groups]
            row["without_paste_mount"] = {m: sum(1 for p in noPaste if p.mount == m) for m in sorted({p.mount for p in noPaste})}
            ratio_c, ratio_cl, ratio_h, off, off_pin, in_box = [], [], [], [], [], 0
            for p in parts:
                g = groups.get(p.ref)
                if g is None or p.origin is None:
                    continue
                bx = g["bbox"]
                box_area = (bx[2] - bx[0]) * (bx[3] - bx[1])
                cy = p.outlines.get("Courtyard")
                if cy and box_area > 0:
                    ratio_c.append(xc.polygon_area(max(cy, key=xc.polygon_area)) / box_area)
                    # The same ratio with the paste box taken in the frame of the part (review: the board-axis box of a part turned 45 degrees is twice too large, StickHub bottom read 0.74)
                    iy, ix = np.nonzero(g["mask"])
                    px = g["pix"]
                    loc = np.array(xc.to_local(p, list(zip(g["x_left"] + (ix + 0.5) * px, g["y_top"] - (iy + 0.5) * px))))
                    ratio_cl.append(xc.polygon_area(max(cy, key=xc.polygon_area)) / ((np.ptp(loc[:, 0]) + px) * (np.ptp(loc[:, 1]) + px)))
                h = xc.hull(p.pin_points())
                if box_area > 0 and xc.polygon_area(h) > 1e-6:
                    ratio_h.append(xc.polygon_area(h) / box_area)
                off.append(math.hypot(p.origin[0] - g["x"], p.origin[1] - g["y"]))
                if p.pins:
                    pc = np.mean(p.pin_points(), axis=0)
                    off_pin.append(math.hypot(pc[0] - g["x"], pc[1] - g["y"]))
                if bx[0] - 0.05 <= p.origin[0] <= bx[2] + 0.05 and bx[1] - 0.05 <= p.origin[1] <= bx[3] + 0.05:
                    in_box += 1
            med = lambda v: (statistics.median(v) if v else None)  # noqa: E731
            row.update(courtyard_over_paste_box=med(ratio_c), courtyard_over_paste_box_part_frame=med(ratio_cl),
                       courtyard_over_paste_box_part_frame_range=(min(ratio_cl), max(ratio_cl)) if ratio_cl else None, courtyard_over_paste_box_part_frame_all=ratio_cl, pinhull_over_paste_box=med(ratio_h), origin_to_paste_centre_median=med(off),
                       origin_to_paste_centre_max=max(off) if off else None, pin_centroid_to_paste_centre_median=med(off_pin), origin_inside_paste_box=in_box)
            # copper links: TO.P (reference, pin) of the copper file against the pins of the component layer
            cl = program_layer(cf) if cf.exists() else None
            if cl is not None:
                cu = {}
                for f in cl.flashes():
                    if f.pin:
                        cu.setdefault((f.pin[0], f.pin[1]), []).append((f.x, f.y))
                x3pins = {(p.ref, q.number): (q.x, q.y) for p in parts for q in p.pins}
                both = [k for k in x3pins if k in cu]
                d = [min(math.hypot(x3pins[k][0] - x, x3pins[k][1] - y) for x, y in cu[k]) for k in both]
                cu_refs = {k[0] for k in cu}
                row.update(copper_pin_keys=len(cu), x3_pins=len(x3pins), x3_pins_found_in_copper=len(both),
                           pin_offset_median_mm=med(d), pin_offset_max_mm=max(d) if d else None,
                           copper_refs=len(cu_refs), copper_refs_in_x3=len(cu_refs & set(refs)), x3_refs_without_copper_pin=len(set(refs) - cu_refs))
            # D. heat shape source
            src = {}
            for p in parts:
                s = xc.heat_shape(p)[1]
                src[s] = src.get(s, 0) + 1
            row["heat_shape_source"] = src
            rows[side] = row
            cross[side] = parts
            print(f"== {board} {side} ({cp.name})")
            for k, v in row.items():
                print(f"   {k}: {v}")
        # Board level: the references of the copper files (TO.P) against the union of the component layers of both sides
        x3refs = {p.ref for ps in cross.values() for p in ps}
        curefs = set()
        for _side, (_c, _p, cf_) in sides.items():
            lay_ = program_layer(DATA / cf_) if (DATA / cf_).exists() else None
            if lay_ is not None:
                curefs |= {f.pin[0] for f in lay_.flashes() if f.pin}
        rows["board_links"] = {"x3_refs": len(x3refs), "copper_pin_refs": len(curefs), "copper_refs_not_in_x3": sorted(curefs - x3refs), "x3_refs_not_in_copper": sorted(x3refs - curefs)}
        print(f"== {board} board: {rows['board_links']}")
        if "top" in cross and "bottom" in cross:
            rows["cross_side"] = cross_side_test(cross["top"], cross["bottom"])
            print(f"== {board} cross side: {rows['cross_side']}")
        out[board] = rows
    (OUT / "x3_components.json").write_text(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
