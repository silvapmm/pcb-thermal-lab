#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_baseline_release.py
@brief Question: what did the released program (v2.4.4) give on the regression boards? Extracts the tag with `git archive` into a scratch folder outside the repository and runs the suite on it in a separate Python process.
@details Usage, from the repository root:

         .venv/bin/python research/release-regression-245/scripts/study_baseline_release.py                 # tag v2.4.4 -> out/v2.4.4.json
         .venv/bin/python research/release-regression-245/scripts/study_baseline_release.py --tag v2.4.4 --dest /path/outside/the/repo --quick

         Only the `pcbthermal` package is extracted (`git archive <tag> pcbthermal`; its data files are inside it). The scratch folder defaults to a new temporary folder, is refused
         if it lies inside the repository, and is kept (the run can be repeated with `--reuse-dest`). The child process gets the extracted tree as `--program-root`, so the working
         tree of the repository is never imported by the baseline run; the example files and the harness are the ones of the current tree, so both revisions read the same input.
         The other arguments after `--` are passed to `study_run_suite.py`.
"""

import argparse
import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = HERE.parents[2]


def extract(tag, dest):
    """!
    @brief Extract the `pcbthermal` package of a tag into a folder.
    @param tag Git tag or revision (for example "v2.4.4").
    @param dest Empty or new folder, outside the repository.
    @return Path of the folder.
    @throws RuntimeError If the folder is inside the repository or git fails.
    """
    dest = Path(dest).resolve()
    if REPO in dest.parents or dest == REPO:
        raise RuntimeError(f"{dest} is inside the repository; give a scratch folder outside it")
    dest.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", tag, "pcbthermal"], capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"git archive {tag} failed: {res.stderr.decode(errors='replace')}")
    with tarfile.open(fileobj=io.BytesIO(res.stdout)) as tf:
        tf.extractall(dest, filter="data")                                      # 'data' filter: no absolute paths, no links outside the folder
    return dest


def main(argv=None):
    """!
    @brief Extract the tag and run the suite on it.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code of the child process.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tag", default="v2.4.4")
    ap.add_argument("--dest", default=None, help="scratch folder outside the repository (default: a new temporary folder)")
    ap.add_argument("--reuse-dest", action="store_true", help="the folder already holds the extracted tree")
    ap.add_argument("--label", default=None, help="label and output name (default: the tag)")
    ap.add_argument("rest", nargs="*", help="further arguments for study_run_suite.py (after --)")
    a = ap.parse_args(argv)
    dest = Path(a.dest) if a.dest else Path(tempfile.mkdtemp(prefix="pcbt_baseline_"))
    if not a.reuse_dest:
        extract(a.tag, dest)
    print(f"{a.tag} extracted to {dest.resolve()}")
    label = a.label or a.tag
    cmd = [sys.executable, str(HERE / "study_run_suite.py"), "--program-root", str(dest.resolve()), "--label", label] + a.rest
    return subprocess.run(cmd, cwd=str(dest.resolve())).returncode          # cwd is the extracted tree: the repository is not on any path


if __name__ == "__main__":
    sys.exit(main())
