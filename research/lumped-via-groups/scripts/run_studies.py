#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_studies.py
@brief Run every study of the folder in turn and write what each prints to out/<name>.txt (the numbers of the README come from these files).
@details Order: the Fish case, the cell problem, the cluster in a cell, the family of arrays under a footprint, the example board, the outside-the-footprint boards, the sensitivity
         of the zone model, the held-out boards and the independent checks of the review (after the family: they read out/family.json), then the figures. The fine-grid references are cached in out/refcache (the first run takes about an hour, the next ones minutes).
Usage: python research/lumped-via-groups/scripts/run_studies.py [name ...]   (from the repository root; with names, only those studies)
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
STUDIES = [("fish_case", "study_fish_case.py"), ("cell_link", "study_cell_link.py"), ("cluster_in_cell", "study_cluster_in_cell.py"), ("family", "study_family.py"),
           ("example_board", "study_example_board.py"), ("outside", "study_outside.py"), ("sensitivity", "study_zone_sensitivity.py"),
           ("holdout", "study_holdout.py"), ("review", "study_review.py")]


def main():
    """!
    @brief Run the studies named on the command line (all by default).
    @return None.
    """
    wanted = sys.argv[1:]
    os.makedirs(os.path.join(FOLDER, "out"), exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="2")
    for name, script in STUDIES:
        if wanted and name not in wanted:
            continue
        with open(os.path.join(FOLDER, "out", name + ".txt"), "w") as out, open(os.path.join(FOLDER, "out", name + ".err"), "w") as err:
            print("running", script, flush=True)
            subprocess.run([sys.executable, os.path.join(HERE, script)], stdout=out, stderr=err, env=env, check=False)
    if not wanted or "figures" in wanted:
        subprocess.run([sys.executable, os.path.join(HERE, "make_diagrams.py")], check=False)
        subprocess.run([sys.executable, os.path.join(HERE, "make_figures.py")], check=False)


if __name__ == "__main__":
    main()
