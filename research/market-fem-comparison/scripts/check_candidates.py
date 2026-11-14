#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_candidates.py
@brief Question: can the Python-installable candidates of the market comparison be had on this machine (version and platform), without installing anything?
@details Runs `pip index versions <name>` (no download of the package) and prints the first line of its answer, `name (latest version)`, per package (this pip has no download dry run, so the platform wheel tag is read from the PyPI pages, see README 2.3). The review found that an earlier version kept only the last 300 characters of the output and so printed a fragment of the OLDEST versions for packages with a long version list (scikit-fem read 0.2.0, meshio 1.2.0); it now keeps the head. Needs the network. Installs nothing.
Run (repository root): .venv/bin/python research/market-fem-comparison/scripts/check_candidates.py
"""

import subprocess
import sys

# PyPI names of the candidates that have a pip route (the others are conda, Homebrew, Docker or source builds)
PACKAGES = ["gmsh", "meshio", "scikit-fem", "pygmsh", "mfem", "fenics-dolfinx", "fenics-basix", "pyvista", "pyfreefem", "fipy", "femm"]


def pip(args):
    """!
    @brief Run pip with the interpreter that runs this script.
    @param args List of pip arguments.
    @return tuple (return code, first 300 characters of the combined output).
    """
    proc = subprocess.run([sys.executable, "-I", "-m", "pip"] + args, capture_output=True, text=True, timeout=120)
    return proc.returncode, (proc.stdout + proc.stderr).strip()[:300]


def main():
    """!
    @brief Print the latest version (or the error line) for each package.
    @return None.
    """
    for name in PACKAGES:
        code, out = pip(["index", "versions", name])
        first = out.splitlines()[0] if out else "(no output)"
        print("%-16s index rc=%d  %s" % (name, code, first[:110]))


if __name__ == "__main__":
    main()
