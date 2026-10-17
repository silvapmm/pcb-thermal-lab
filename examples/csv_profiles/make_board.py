"""!
@file make_board.py
@brief Writes board.pcbt.json: the 100 x 80 mm, 4-layer example board used by the tests (two heaters, vias, partial copper, a heatsink).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import Project, save_project                     # noqa: E402
from pcbthermal.examples import example_board                    # noqa: E402


def main():
    """!
    @brief Save the example board next to this script.
    @return Path of the written file.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "board.pcbt.json")
    save_project(path, Project(problem=example_board()))
    return path


if __name__ == "__main__":
    print(main())
