#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fetch_samples.py
@brief Download the open sample sets of the CAD-profile study into the git-ignored data/ folder.

Question answered: which real (or documented) outputs of which eCAD program can be had
without a licence problem?  The gerbonara test resources (https://gitlab.com/gerbolyze/gerbonara,
folder tests/resources, each with its own LICENSE/README) are fetched one file at a time
(polite: one request every 0.2 s), mapped to a tool key, and every folder's LICENSE, README
and SOURCE files are fetched with it so that the licence table of the README can be written
from what the source says.  Nothing is committed (data/ is git-ignored).

Run from the repository root:
    .venv-research/bin/python research/gerber-cad-profiles/scripts/fetch_samples.py [--only KEY ...]
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
RAW = "https://gitlab.com/gerbolyze/gerbonara/-/raw/main/"

# The listing of the test resources was saved by the earlier conformance study; the same
# listing is used here so that no directory page has to be crawled.
LISTING = os.path.join(HERE, "gerbonara_listing.json")

# gerbonara folder -> tool key of this study
FOLDERS = {
    "Target3001": "target3001", "altium-composite-drill": "altium", "fab-3000": "fab3000",
    "zuken-emulated": "zuken-emulated", "siemens": "siemens", "siemens-2": "siemens",
    "allegro": "cadence-allegro", "allegro-2": "cadence-allegro", "orcad": "cadence-orcad",
    "pads": "pads", "eagle-newer": "eagle", "eagle_files": "eagle", "fusion360": "fusion360",
    "diptrace": "diptrace", "easyeda": "easyeda", "fritzing": "fritzing", "geda": "geda",
    "kicad-older": "kicad", "kicad-x2-tests": "kicad", "world_clock_2": "kicad",
    "p-cad": "pcad", "pcb-rnd": "pcb-rnd", "upverter": "upverter",
}


def fetch(url, dest):
    """!
    @brief Download one file unless it is already there.

    @param url   Source address.
    @param dest  Local path (parent folders are created).

    @return bool True when the file is present afterwards.
    """
    if os.path.exists(dest):
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        return True
    except Exception as exc:  # network errors are reported, not fatal
        sys.stderr.write("failed %s: %s\n" % (url, exc))
        return False


def main(argv=None):
    """!
    @brief Entry point.

    @param argv  Optional argument list.

    @return int Exit code.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="tool keys to fetch (default: all)")
    args = ap.parse_args(argv)
    listing = json.load(open(LISTING))
    done = 0
    for path in listing:
        parts = path.split("/")
        if len(parts) < 4 or parts[2] not in FOLDERS:
            continue
        tool = FOLDERS[parts[2]]
        if args.only and tool not in args.only:
            continue
        rel = "/".join(parts[2:])
        url = RAW + urllib.parse.quote(path)
        if fetch(url, os.path.join(DATA, tool, rel)):
            done += 1
        time.sleep(0.2)
    print("files present:", done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
