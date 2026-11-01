#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file project_format.py
@brief A prototype of the project-file format 2: what an import stores (masks packed in the JSON, or references to the source files), and the migration from format 1 and back.
@details Format 1 is `pcbthermal-project-1` (pcbthermal/project.py): the native problem JSON plus "solver" and "view". Format 2 keeps every key of format 1 and adds one list, "imports", with one record per
         imported board: the source files (name, size, SHA-256, never the path of the user's disk), the settings of the import (pixel, box, layer roles and order, units), and per copper layer a mask that
         is either embedded (packed bits or 8-bit coverage, deflate, base64) or a reference to the file ("embed": false: the mask is redrawn from the Gerber when the project opens, which needs the file).
         Embedded masks make the project self-contained and its size grows with the board area over the pixel squared; `scripts/study_project_file.py` measures it. This module is a prototype for the
         design in INTEGRATION.md and does not touch pcbthermal/project.py.
"""

import base64
import hashlib
import zlib

import numpy as np

FORMAT_1 = "pcbthermal-project-1"
FORMAT_2 = "pcbthermal-project-2"


def pack_mask(mask, kind="binary"):
    """!
    @brief Pack a mask for the JSON file.
    @param mask 2D array: boolean (kind "binary") or float 0..1 (kind "coverage", stored as 8 bits).
    @param kind "binary" (bits, 1/8 byte per pixel before deflate) or "coverage" (a byte per pixel).
    @return dict with kind, shape, data (base64 text of the deflated bytes).
    @throws ValueError For an unknown kind.
    """
    a = np.asarray(mask)
    if kind == "binary":
        raw = np.packbits(a.astype(bool), axis=None).tobytes()
    elif kind == "coverage":
        raw = np.clip(np.rint(a.astype(float) * 255.0), 0, 255).astype(np.uint8).tobytes()
    else:
        raise ValueError(f"unknown mask kind {kind!r}")
    return {"kind": kind, "shape": [int(a.shape[0]), int(a.shape[1])], "data": base64.b64encode(zlib.compress(raw, 9)).decode("ascii")}


def unpack_mask(d):
    """!
    @brief Inverse of pack_mask.
    @param d Dict returned by pack_mask (after a JSON round trip).
    @return numpy.ndarray boolean (binary) or float 0..1 (coverage, with the 1/255 quantisation).
    """
    raw = zlib.decompress(base64.b64decode(d["data"]))
    ny, nx = d["shape"]
    if d["kind"] == "binary":
        return np.unpackbits(np.frombuffer(raw, np.uint8), count=ny * nx).reshape(ny, nx).astype(bool)
    return np.frombuffer(raw, np.uint8).reshape(ny, nx).astype(float) / 255.0


def sha256_of(path):
    """!
    @brief The SHA-256 of a file, to recognise a source file again.
    @param path File path.
    @return str hex digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def import_record(name, pix, box, layers, embed=True, kind="coverage", sources=None, holes=None, parts=None):
    """!
    @brief One record of the "imports" list.
    @param name Name of the board.
    @param pix Pixel of the masks (mm).
    @param box Board box (x0, y0, x1, y1) in mm in the file coordinates.
    @param layers List of (layer name, role, mask array) from the top copper layer down.
    @param embed True: the masks are in the record; False: only the roles (the masks are redrawn from the sources when the project opens).
    @param kind Mask kind when embedded ("binary" or "coverage").
    @param sources List of dicts name, size, sha256 of the source files (no paths).
    @param holes List of plated holes (x, y, diameter) in board coordinates.
    @param parts List of imported parts (reference, x, y, bbox of the paste group).
    @return dict.
    """
    rec = {"name": name, "pix": pix, "box": list(box), "embed": bool(embed), "sources": sources or [], "holes": holes or [], "parts": parts or [], "layers": []}
    for lname, role, m in layers:
        entry = {"name": lname, "role": role}
        if embed:
            entry["mask"] = pack_mask(m, kind)
        rec["layers"].append(entry)
    return rec


def migrate_1_to_2(d):
    """!
    @brief Upgrade a format 1 project dict to format 2 (no data change: an empty "imports" list is added).
    @param d Project dict of format 1 (or one with no "format" key: a plain native file).
    @return dict of format 2 (a new dict; the argument is not changed).
    @throws ValueError If the dict is of a newer format than 2.
    """
    fmt = d.get("format", FORMAT_1)
    if fmt == FORMAT_2:
        return dict(d)
    if fmt != FORMAT_1:
        raise ValueError(f"unknown project format {fmt!r}")
    out = dict(d)
    out["format"] = FORMAT_2
    out.setdefault("imports", [])
    return out


def downgrade_2_to_1(d):
    """!
    @brief The format 1 version of a format 2 project, for an older program.
    @details Possible only when there is nothing to lose: a project with imported boards keeps the copper only in "imports", so the downgrade refuses it (the old program would show an empty board).
    @param d Project dict of format 2.
    @return dict of format 1.
    @throws ValueError If the project has imported boards.
    """
    if d.get("imports"):
        raise ValueError("this project holds imported boards, which format 1 cannot store")
    out = {k: v for k, v in d.items() if k != "imports"}
    out["format"] = FORMAT_1
    return out
