#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fetch_boards.py
@brief Download the open boards of this investigation into data/ (git-ignored) under fixed local names, and print their licence, outline size, layer count and what each paste file holds.
@details Question answered: which real boards with paste layers and a placement file can the studies run on, and are they what the registry says? The files are NOT stored in the repository (their licences
         differ: GPL-3.0, GPL-2.0, BSD-3-Clause, CC-BY-SA-4.0); the results quoted in the documents are statistics, not copies.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/fetch_boards.py [board ...]   (no argument: all; needs network access)
         Add --odb to also download the three small ODB++ sample archives of the library mcix/odbpp (licence of the archives not stated: for reading the structure only),
         and --ucamco to download and extract Ucamco's sample archives (layer-format test files, fabrication examples with IPC-2581, X3 samples; licence not stated) into data/ucamco/.
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import native_gerber as ng
import registry
import rb_paths


def download(key):
    """!
    @brief Download the files of one board that are not on disk yet.
    @param key Board key of registry.BOARDS.
    @return list of local names that could not be downloaded (empty when all came).
    """
    out = registry.folder(key)
    out.mkdir(parents=True, exist_ok=True)
    missing = []
    zip_url = registry.BOARDS[key].get("zip_url")
    if zip_url:                                        # a board published as one zip: download once, take the members by name
        import io
        import zipfile
        todo = {k: v for k, v in registry.BOARDS[key]["files"].items() if not (out / k).exists()}
        if todo:
            with urllib.request.urlopen(zip_url, timeout=120) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            names = {Path(n).name: n for n in z.namelist()}
            for local, remote in todo.items():
                if remote in names:
                    (out / local).write_bytes(z.read(names[remote]))
                else:
                    print(f"  {key}/{local}: {remote} not in the zip")
                    missing.append(local)
        return missing
    for local in registry.BOARDS[key]["files"]:
        dest = out / local
        if dest.exists():
            continue
        try:
            with urllib.request.urlopen(registry.url(key, local), timeout=60) as r:
                dest.write_bytes(r.read())
        except Exception as exc:                       # a file may have been renamed upstream: report, do not stop
            print(f"  {key}/{local}: not downloaded ({exc})")
            missing.append(local)
    return missing


def describe(key):
    """!
    @brief Print what the board holds: licence, outline size, layers, and the paste files (number of reference designators written in them with the X2 attribute TO.C).
    @param key Board key.
    @return None.
    """
    b = registry.BOARDS[key]
    d = registry.folder(key)
    edge = d / "edge.gbr"
    size = "outline not read"
    if edge.exists():
        box = ng.layer_bbox(edge)
        if box:
            size = f"{box[2] - box[0]:.1f} x {box[3] - box[1]:.1f} mm"
    print(f"{key}: {b['repo']} | licence {b['licence']} | {b['layers']} layers | {b['tool']} | {size}")
    for role in ("pasteF.gbr", "pasteB.gbr"):
        p = d / role
        if p.exists():
            text = p.read_text(errors="replace")
            refs = set(re.findall(r"%TO\.C,([^*]+)\*%", text))
            print(f"  {role}: {len(text) // 1024} kB, {len(refs)} reference designators in TO.C attributes")
    pos = d / "pos.csv"
    if pos.exists():
        print(f"  pos.csv: {sum(1 for _ in pos.open(errors='replace')) - 1} lines after the header")


def fetch_odb():
    """!
    @brief Download the ODB++ sample archives (data/odb/).
    @return None.
    """
    out = rb_paths.DATA / "odb"
    out.mkdir(parents=True, exist_ok=True)
    for key, s in registry.ODB_SAMPLES.items():
        dest = out / s["name"]
        if not dest.exists():
            u = f"https://raw.githubusercontent.com/{s['repo']}/HEAD/{s['path']}/{urllib.parse.quote(s['name'])}"
            with urllib.request.urlopen(u, timeout=120) as r:
                dest.write_bytes(r.read())
        print(f"{key}: {dest} ({dest.stat().st_size // 1024} kB; licence of the archive not stated by the repository)")


def fetch_ucamco():
    """!
    @brief Download and extract the Ucamco sample archives (layer-format test files, fabrication examples with IPC-2581, other X3 examples) into data/ucamco/<key>/.
    @return None.
    """
    import io
    import zipfile
    for key, u in registry.UCAMCO_ZIP.items():
        dest = rb_paths.DATA / "ucamco" / key
        if dest.exists() and any(dest.iterdir()):
            continue
        dest.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(u, timeout=120) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        for info in z.infolist():
            if info.is_dir():
                continue
            # flatten the folder names and drop anything that is not a plain file name (no path tricks from an archive)
            name = Path(info.filename).name
            if name:
                (dest / name).write_bytes(z.read(info))
        print(f"{key}: {sum(1 for _ in dest.iterdir())} files in {dest} (licence not stated by the download page)")


def main(argv):
    """!
    @brief Download and describe the boards named on the command line, or all of them.
    @param argv List of board keys; "--odb" adds the ODB++ samples, "--ucamco" the Ucamco sample archives.
    @return None.
    """
    odb = "--odb" in argv
    keys = [a for a in argv if not a.startswith("--")] or list(registry.BOARDS)
    for k in keys:
        if k not in registry.BOARDS:
            raise SystemExit(f"unknown board {k!r}; known: {', '.join(registry.BOARDS)}")
        download(k)
        describe(k)
    if odb:
        fetch_odb()
    if "--ucamco" in argv:
        fetch_ucamco()


if __name__ == "__main__":
    main(sys.argv[1:])
