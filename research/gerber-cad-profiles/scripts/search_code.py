#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file search_code.py
@brief Find public repositories that hold Gerber output of a given eCAD program (banner search).

Question answered: where are open sample outputs of tool X?  Uses `gh search code` (code
search, rate limited to about 10 requests a minute, so one query every 8 s) with the banner
text each tool writes, and prints the repositories and paths found.  Nothing is downloaded.

Run: .venv/bin/python research/gerber-cad-profiles/scripts/search_code.py "query" ["query" ...]
"""
import json
import subprocess
import sys
import time


def search(query, limit=30):
    """!
    @brief Run one `gh search code` query.

    @param query  Text to search for.
    @param limit  Maximum number of hits.

    @return list Entries (repository, path) found.
    """
    # "text|ext" restricts the search to files with that extension
    ext = []
    if "|" in query:
        query, e = query.split("|", 1)
        ext = ["--extension", e]
    out = subprocess.run(["gh", "search", "code", query, "--limit", str(limit), "--json", "repository,path"] + ext,
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write(out.stderr[:200] + "\n")
        return []
    return [(h["repository"]["nameWithOwner"], h["path"]) for h in json.loads(out.stdout)]


def main(argv):
    """!
    @brief Search every query and print repositories with the number of hits and one example path.

    @param argv  Command-line arguments (queries after the program name).

    @return int Exit code.
    """
    for q in argv[1:]:
        hits = search(q)
        repos = {}
        for r, p in hits:
            repos.setdefault(r, []).append(p)
        print("== %s: %d hits, %d repos" % (q, len(hits), len(repos)))
        for r, ps in repos.items():
            print("   %-50s %2d  %s" % (r, len(ps), ps[0]))
        time.sleep(8)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
