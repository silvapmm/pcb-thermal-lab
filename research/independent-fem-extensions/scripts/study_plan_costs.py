#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plan_costs.py
@brief Which planned finite-element case fits under 2 GB: the unknown count and the memory estimate of every case of README 2, with no solve.
@details Run from the repository root: `.venv/bin/python research/independent-fem-extensions/scripts/study_plan_costs.py`. Prints a table of the
         estimated unknowns (plan nodes times z levels) and the estimated peak memory at B_PER_UNKNOWN bytes per unknown. The constant is an
         ASSUMPTION taken from the order of magnitude of independent-fem-edge README 5 (CG with the scaled AMG, up to 3 GB on the finest board); the
         first run of study 1 replaces it with a measured number. Nothing is solved here.
"""
import logging

LOG = logging.getLogger("plan_costs")
B_PER_UNKNOWN = 3000.0          # bytes per unknown, assumed (see the file header); direct solve would be far more, so CG + AMG is assumed
LIMIT_GB = 2.0                  # the budget of the planning pass

# case id -> (description, plan nodes, z levels, symmetry factor)
CASES = {
    "1a barrel 1 via, axisym-like quarter": ("single via, quarter, 0.025 mm near the barrel", 12000, 30, 1),
    "1b via array 3x3, quarter": ("3x3 vias, pitch 1 mm, quarter, 0.05 mm", 40000, 30, 1),
    "2a tab+cluster+plate, quarter, 0.1 mm": ("tab 6x6 mm, 5x5 vias, plate, quarter", 9000, 40, 1),
    "2b same, 0.05 mm": ("same, halved mesh", 36000, 40, 1),
    "2c same, 0.025 mm": ("same, halved again", 144000, 40, 1),
    "3 stripes 20 mm, aligned": ("stripes on mesh lines", 20000, 26, 1),
    "4 L outline 20 mm": ("L with reflex corner, two layers", 30000, 20, 1),
    "5 transient, 2a mesh, 400 steps": ("same system as 2a, 400 CN steps, 1 factor kept", 9000, 40, 1),
}


def main():
    """!
    @brief Print the cost table.
    @return None.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    LOG.info("%-40s %10s %9s  %s", "case", "unknowns", "GB est.", "under %.0f GB" % LIMIT_GB)
    for name, (_d, npl, nz, sym) in CASES.items():
        n = npl * nz * sym
        gb = n * B_PER_UNKNOWN / 1e9
        LOG.info("%-40s %10d %9.2f  %s", name, n, gb, "yes" if gb < LIMIT_GB else "WAIT")


if __name__ == "__main__":
    main()
