"""!
@file examples.py
@brief Ready-made boards for tests, the command line and the GUI.
"""

from .model import Problem, SquareWave, reference_problem


def example_board():
    """!
    @brief 100 x 80 mm, 4-layer board with two heaters, a via array, partial top copper and a heatsink.
    @return A Problem.
    """
    p = Problem.new(width_mm=100, height_mm=80, layers=4, name="example-4layer")
    p.add_zone(1, rect=(15, 15, 85, 65), name="top copper")
    p.add_full_copper([2, 3, 4])
    p.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta=6.0)
    p.add_heater(1, 1.5, rect=(65, 38, 71, 44), name="U2", theta=12.0)
    # 3 x 3 vias with 3.5 mm pitch centred under U1 (the same positions as the legacy comparison board)
    for i in range(3):
        for j in range(3):
            p.add_via(31.5 + 3.5 * i, 36.5 + 3.5 * j, diameter=0.3)
    p.add_heatsink(4, 30.0, rect=(25, 30, 45, 50), name="bottom heatsink")
    return p


__all__ = ["example_board", "reference_problem"]


def example_profile_board():
    """!
    @brief The example board with power profiles: U1 switches at 100 Hz (averaged) and U2 runs a 20 s cycle (resolved).
    @return A Problem.
    """
    p = example_board()
    p.name = "example with power profiles"
    p.heaters[0].set_profile(SquareWave(p_on=4.0 / 0.30, period=0.01, duty=0.30))
    p.heaters[1].set_profile(SquareWave(p_on=1.5 / 0.25, period=20.0, duty=0.25))
    return p


def example_block_board():
    """!
    @brief The example board with a 3 mm aluminium block (60 x 50 mm, 5 K cm2/W gap pad) on the bottom face under U1, instead of the plain heatsink.
    @return A Problem.
    """
    p = example_board()
    p.name = "example with a metal block"
    p.heatsinks = []
    p.add_heatsink(4, 15.0, rect=(20, 15, 80, 65), name="Al block", thickness_mm=3.0, contact_r=5.0e-4)
    return p

