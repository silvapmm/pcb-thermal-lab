#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_parts.py
@brief What do the parts rules of `feature/paste-parts` (paste openings, TO.C, placement files, bottom X sign) do on the paste layers of each tool?
@details Question answered (README 6): for every sample set that has a paste layer, how many openings are read, does the paste file
         carry reference designators (`TO.C`), and, where a placement file exists, which parts come from which rule and which bottom-side
         X convention the data choose.  The parts module is the one of the branch `feature/paste-parts` (a worktree of the repository;
         path in PARTS_TREE, override with the environment variable PCBT_PARTS_TREE), imported from there and not changed.
         Run: .venv-research/bin/python research/gerber-cad-profiles/scripts/study_parts.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PARTS_TREE = os.environ.get("PCBT_PARTS_TREE", os.path.abspath(os.path.join(ROOT, "..", "agent-aececd0cc4500867e")))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, PARTS_TREE)
import study_markers as sm  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402
from pcbthermal.gerber import parts as P  # noqa: E402

DATA = sm.DATA
# (label, folder, placement files). The placement file of a side may be one file with both sides.
CASES = [
    ("kicad 5.1 cmm2", "realboards-cmm2", ["pos.csv"]), ("kicad 5.1 isastm", "realboards-isastm", ["pos.csv"]),
    ("kicad 5.1 oswlight", "realboards-oswlight", ["pos.csv"]), ("kicad 5.1 co60", "realboards-co60", ["pos.csv"]),
    ("kicad 7 rp2040", "realboards-rp2040", ["pos.csv"]), ("kicad 6 vstcm", "realboards-vstcm", ["pos.csv"]),
    ("kicad 9 librevna", "heldout/kicad__librevna", ["VNA-top-pos.csv", "VNA-bottom-pos.csv"]),
    ("kicad 8.99 stickhub (X3)", "realboards-stickhub", []),
    ("kicad 5.1 wc2", "kicad-wc2", []), ("kicad 7 watchy", "kicad7/watchy", []), ("kicad 8 oneinchEye", "kicad8/oneinchEye", []),
    ("kicad 9 badgemagic", "kicad9/badgemagic", []), ("kicad 7 voltlink", "heldout/kicad__voltlink", []),
    ("pulsonix 8.5 rabbit", "pulsonix/rabbit", ["rabbit watch(Component Positions).csv"]),
    ("allegro 17.2", "allegro", []), ("allegro 16.6 minnowmax", "allegro-2", []), ("altium x2 note", "altium-x2/note", []),
    ("altium x2 linkcard", "altium-x2/linkcard", []), ("eagle x2 16n", "eagle-x2/16n", []), ("eagle 9 newer", "eagle-newer", []),
    ("xpedition siemens-2", "siemens-2", []), ("xpedition bouled", "xpedition/bouled", []), ("proteus breath", "proteus/breath", []),
    ("easyeda 6.4", "easyeda-gerbonara", []), ("diptrace 2.4", "diptrace", []), ("librepcb desklift", "librepcb/desklift", []),
    ("designspark picovdp", "designspark/picovdp", []), ("upverter", "upverter", []), ("pcb-rnd", "pcb-rnd", []),
]


def find_paste(folder):
    """!
    @brief The paste layers of a folder by the program's own detector (name and head).
    @param folder  Folder.
    @return dict side -> Layer.
    """
    out = {}
    for dp, _, fs in os.walk(folder):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if os.path.splitext(f)[1].lower() in sm.SKIP_EXT or os.path.getsize(p) == 0 or os.path.getsize(p) > 3_000_000:
                continue
            fn = G.detect_file(p)
            if fn.kind == "paste" and fn.side in ("top", "bottom") and fn.side not in out:
                try:
                    out[fn.side] = G.read_layer(p)
                except Exception as exc:
                    out[fn.side + "_error"] = str(exc)[:80]
    return out


def main():
    """!
    @brief Run the parts rules on each case and print the table.
    @return int Exit code.
    """
    print("| case | paste layers | with TO.C | openings | placement parts | parts by source | bottom convention | note |")
    print("| :-- | :-- | :-- | --: | --: | :-- | :-- | :-- |")
    for label, rel, pl in CASES:
        folder = os.path.join(DATA, rel)
        if not os.path.isdir(folder):
            continue
        paste = {k: v for k, v in find_paste(folder).items() if not k.endswith("_error")}
        errs = [v for k, v in find_paste(folder).items() if k.endswith("_error")]
        if not paste:
            print("| %s | none found | | | | | | %s |" % (label, errs[0] if errs else "no paste file recognised"))
            continue
        placement = []
        for f in pl:
            try:
                placement += P.read_placement(os.path.join(folder, f))
            except Exception as exc:
                errs.append("placement: %s" % str(exc)[:60])
        toc = [s for s, L in paste.items() if any(a.ref for a in getattr(L, "obj_attrs", []) if hasattr(a, "ref"))] if False else []
        try:
            res = P.build_parts(paste=paste, placement=placement or None, copper=None)
            src = {}
            for part in res.parts:
                s = part.from_file.get("source", "?") if hasattr(part, "from_file") else "?"
                src[s] = src.get(s, 0) + 1
            info = res.info
            tocn = sum(1 for o in res.openings if getattr(o, "ref", ""))
            print("| %s | %s | %d of %d | %d | %d | %s | %s | %s |" % (
                label, "+".join(sorted(paste)), tocn, len(res.openings), len(res.openings), len(placement),
                ", ".join("%s %d" % kv for kv in sorted(src.items())) or "none", info.get("bottom_convention", info.get("convention", "")),
                "; ".join(list(info.get("warnings", []))[:2])[:100] + (" " + errs[0] if errs else "")))
        except Exception as exc:
            print("| %s | %s | | | %d | | | build_parts failed: %s |" % (label, "+".join(sorted(paste)), len(placement), str(exc)[:90]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
