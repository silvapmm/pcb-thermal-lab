#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fetch_repo.py
@brief List and download one folder of a public GitHub repository into data/<tool>/<name>/.

Question answered: how to get a real Gerber set of tool X with its licence recorded.
`list REPO [PREFIX]` prints the files of the repository tree (size, path) under a prefix;
`get TOOL NAME REPO PREFIX [MAXKB]` downloads every file under PREFIX (below MAXKB kilobytes,
default 1500) into data/TOOL/NAME/ and writes data/TOOL/NAME/_SOURCE.txt with the repository,
the commit, the licence reported by the GitHub API and the file list.  Downloaded boards are
never committed (data/ is git-ignored).

Run: .venv/bin/python research/gerber-cad-profiles/scripts/fetch_repo.py list|get ...
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def gh_api(path):
    """!
    @brief Call the GitHub API through the authenticated `gh` client.

    @param path  API path such as repos/OWNER/NAME/license.

    @return dict Decoded JSON, or an empty dict on failure.
    """
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        return {}
    return json.loads(out.stdout)


def tree(repo):
    """!
    @brief Return the file list of the default branch of a repository.

    @param repo  OWNER/NAME.

    @return tuple (commit sha, list of (path, size)).
    """
    info = gh_api("repos/%s" % repo)
    br = info.get("default_branch", "master")
    t = gh_api("repos/%s/git/trees/%s?recursive=1" % (repo, br))
    files = [(e["path"], e.get("size", 0)) for e in t.get("tree", []) if e["type"] == "blob"]
    return t.get("sha", ""), br, files


def cmd_list(repo, prefix=""):
    """!
    @brief Print files below a prefix.

    @param repo    OWNER/NAME.
    @param prefix  Folder prefix (may be empty).

    @return None
    """
    _, _, files = tree(repo)
    for p, s in files:
        if p.startswith(prefix):
            print("%9d  %s" % (s, p))


def cmd_get(tool, name, repo, prefix, maxkb=1500):
    """!
    @brief Download all files below a prefix.

    @param tool    Tool key (first level folder of data/).
    @param name    Sample name (second level).
    @param repo    OWNER/NAME.
    @param prefix  Folder prefix inside the repository.
    @param maxkb   Skip files larger than this many kilobytes.

    @return None
    """
    sha, br, files = tree(repo)
    lic = gh_api("repos/%s/license" % repo).get("license", {}).get("spdx_id", "none reported")
    dest = os.path.join(DATA, tool, name)
    os.makedirs(dest, exist_ok=True)
    got = []
    for p, s in files:
        if not p.startswith(prefix) or s > maxkb * 1024:
            continue
        local = os.path.join(dest, os.path.relpath(p, prefix) if prefix else p)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        url = "https://raw.githubusercontent.com/%s/%s/%s" % (repo, br, urllib.parse.quote(p))
        try:
            with urllib.request.urlopen(url, timeout=30) as r, open(local, "wb") as f:
                f.write(r.read())
            got.append(p)
        except Exception as exc:
            sys.stderr.write("failed %s: %s\n" % (p, exc))
        time.sleep(0.15)
    with open(os.path.join(dest, "_SOURCE.txt"), "w") as f:
        f.write("repo: https://github.com/%s\nprefix: %s\nbranch: %s\nlicence (GitHub API): %s\nfiles: %d\n%s\n"
                % (repo, prefix, br, lic, len(got), "\n".join(got)))
    print("%s/%s: %d files, licence %s" % (tool, name, len(got), lic))


def main(argv):
    """!
    @brief Dispatch the sub-command.

    @param argv  Command line.

    @return int Exit code.
    """
    if len(argv) >= 3 and argv[1] == "list":
        cmd_list(argv[2], argv[3] if len(argv) > 3 else "")
    elif len(argv) >= 6 and argv[1] == "get":
        cmd_get(argv[2], argv[3], argv[4], argv[5], int(argv[6]) if len(argv) > 6 else 1500)
    else:
        sys.stderr.write(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
