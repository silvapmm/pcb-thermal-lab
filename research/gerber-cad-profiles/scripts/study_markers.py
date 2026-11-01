#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_markers.py
@brief Does the marker table recognise the generating program of every sample set, and how many single files identify themselves?
@details Question answered (README 3): for each sample set of data/ (the truth is the program the repository or the folder
         says wrote it), run `cadprofiles.detect_set` on the whole set and on every file alone, and print the table:
         set, truth, detected, confidence, version, files, files whose own markers name the truth, and the decisive evidence.
         Run from the repository root: .venv/bin/python research/gerber-cad-profiles/scripts/study_markers.py [--files]
         (`--files` also lists the files that carry no decisive marker).  Output goes to stdout; the README quotes it.
"""
import io
import os
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cadprofiles as cp  # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data")

# (root relative to data/, truth profile, sub-folder to leave out or None). The truth is the program the source says wrote the files.
ROOTS = [
    ("altium", "altium", None), ("altium-x2/simplefoc", "altium", None), ("altium-x2/note", "altium", None),
    ("altium-x2/linkcard", "altium", None), ("circuitmaker/yaduino", "circuitmaker", None),
    ("allegro", "allegro", None), ("allegro-2", "allegro", None), ("orcad", "allegro", None),
    ("siemens", "xpedition", None), ("siemens-2", "xpedition", None), ("xpedition/bouled", "xpedition", None),
    ("xpedition/spirose", "xpedition", None), ("xpedition/hw0004", "xpedition", None), ("pads", "pads", None),
    ("eagle", "eagle", None), ("eagle-newer", "eagle", None), ("eagle-x2/16n", "eagle", None),
    ("fusion360", "eagle", None), ("fusion/arduTouch", "eagle", None), ("diptrace", "diptrace", None),
    ("easyeda-gerbonara", "easyeda", None), ("fritzing", "fritzing", None), ("geda", "geda", None),
    ("pcb-rnd", "pcbrnd", None), ("upverter", "upverter", None), ("target3001", "target3001", None),
    ("pcad", "pcad", None), ("pulsonix/zx81", "pulsonix", None), ("pulsonix/rabbit", "pulsonix", None),
    ("proteus/breath", "proteus", None), ("designspark/picovdp", "designspark", None),
    ("librepcb/desklift", "librepcb", None), ("orcad/cc1310", "cam350", None),
    ("kicad-older", "kicad", None), ("kicad-wc2", "kicad", None), ("kicad-x2-tests", "kicad", None),
    ("kicad6/tdrgb", "kicad", None), ("kicad7/watchy", "kicad", None), ("kicad8/oneinchEye", "kicad", None),
    ("kicad9/badgemagic", "kicad", None),
    ("realboards-cmm2", "kicad", None), ("realboards-co60", "kicad", None), ("realboards-isastm", "kicad", None),
    ("realboards-oswlight", "kicad", None), ("realboards-rp2040", "kicad", None), ("realboards-stickhub", "kicad", None),
    ("realboards-vstcm", "kicad", None),
    ("realboards-ucamco/fabrication_example_1", "ucamx", None), ("realboards-ucamco/fabrication_example_2", "ucamx", None),
    ("zuken-emulated/Gerber", "zuken", None), ("zuken-emulated/Drill", "zuken", None), ("zuken-emulated/orig", "kicad", None),
    ("fab3000", "unknown", None), ("proteus/ottosdiy", "proteus", None),
]
# nested folders that are another set (orcad/cc1310 is CAM350 output) or a copy (target3001/Target3001): left out when walking their parent
NESTED = {"orcad": {"cc1310"}, "target3001": {"Target3001"}}
SKIP_EXT = {".zip", ".tgz", ".pdf", ".png", ".bmp", ".jpg", ".dxf", ".3ds", ".gz"}


def walk(root):
    """!
    @brief os.walk of a set that leaves out the nested sets and copies of NESTED.
    @param root  Folder (absolute).
    @return generator of (folder, sub-folders, files) as os.walk gives them.
    """
    skip = NESTED.get(os.path.basename(root.rstrip("/")), set())
    for dp, dn, fs in os.walk(root):
        dn[:] = [d for d in dn if d not in skip]
        yield dp, dn, fs


def collect(root):
    """!
    @brief Read the first bytes of every usable file under a folder.
    @param root  Folder (absolute).
    @return dict Name relative to the folder -> first bytes.
    """
    out = {}
    for dp, _, fs in walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            if os.path.splitext(f)[1].lower() in SKIP_EXT or os.path.getsize(p) == 0 or f == "_SOURCE.txt":
                continue
            if f in ("LICENSE", "README", "SOURCE", "listing.json"):
                continue
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = fh.read(cp.HEAD_BYTES)
    return out


def main(argv):
    """!
    @brief Run the detection on every set and print the table.
    @param argv  Command line.
    @return int Exit code.
    """
    table = cp.load_table()
    show_files = "--files" in argv
    print("| set | truth | detected | confidence | version | files | files naming the truth | strongest evidence |")
    print("| :-- | :-- | :-- | :-- | :-- | --: | --: | :-- |")
    ok = total = 0
    per_tool = {}                                             # truth -> [sets, files, files naming the truth]
    for rel, truth, _ in ROOTS:
        root = os.path.join(DATA, rel)
        if not os.path.isdir(root):
            print("| %s | %s | (missing) | | | | | |" % (rel, truth))
            continue
        files = collect(root)
        det = cp.detect_set(files, table)
        own = 0
        silent = []
        for name, raw in files.items():
            hits = [h for h in cp.scan_file(table, name, raw) if h.profile == truth and h.weight >= cp.DECISIVE]
            if hits:
                own += 1
            else:
                silent.append(name)
        good = det.profile == truth
        agg = per_tool.setdefault(truth, [0, 0, 0])
        agg[0] += 1
        agg[1] += len(files)
        agg[2] += own
        ok += good
        total += 1
        ev = det.evidence[0] if det.evidence else None
        print("| %s | %s | %s%s | %s | %s | %d | %d | %s |" % (
            rel, truth, det.profile, "" if good else " (WRONG)", det.confidence, det.version or det.declared, len(files), own,
            ("%s: %s" % (ev.marker, ev.text.replace("|", "/"))) if ev else ""))
        if show_files and silent:
            print("<!-- no decisive marker for the truth: %s -->" % ", ".join(sorted(silent)[:12]))
    # ODB++ archives: only misc/info is read, in memory
    odb_dir = os.path.join(DATA, "realboards-odb")
    for f in sorted(os.listdir(odb_dir)) if os.path.isdir(odb_dir) else []:
        if not f.endswith(".tgz"):
            continue
        with tarfile.open(os.path.join(odb_dir, f)) as tf:
            info = [n for n in tf.getnames() if n.endswith("misc/info")]
            files = {n: tf.extractfile(n).read(cp.HEAD_BYTES) for n in info}
        det = cp.detect_set(files, table)
        print("| odb %s | %s | %s | %s | %s | %d | | %s |" % (
            f, "kicad" if "flat" in f else "unknown", det.profile, det.confidence, det.version, len(files),
            det.evidence[0].text if det.evidence else "no misc/info in the archive"))
    print("\nsets recognised as the truth: %d of %d" % (ok, total))
    print("\n| tool | sets | files | files that name the tool by themselves |")
    print("| :-- | --: | --: | --: |")
    for t, (n, nf, no) in sorted(per_tool.items()):
        print("| %s | %d | %d | %d (%.0f %%) |" % (t, n, nf, no, 100.0 * no / max(nf, 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
