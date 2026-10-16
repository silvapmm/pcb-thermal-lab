"""!
@file examples.py
@brief Ready-made boards for tests, the command line and the GUI.
"""

from .model import Problem, reference_problem


def example_board():
    """!
    @brief 100 x 80 mm, 4-layer board with two heaters, a via array, partial top copper and a sink.
    @return A Problem.
    """
    p = Problem.new(width_mm=100, height_mm=80, layers=4, name="example-4layer")
    p.add_zone(1, rect=(15, 15, 85, 65), name="top copper")
    p.add_full_copper([2, 3, 4])
    p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=6.0)
    p.add_heater(1, 1.5, rect=(65, 38, 71, 44), name="U2", theta_jb=12.0)
    p.add_via_array((30, 35, 40, 45), 3, 3, diameter=0.3)
    p.add_sink(4, 30.0, rect=(25, 30, 45, 50), name="bottom heatsink")
    return p


__all__ = ["example_board", "reference_problem"]
