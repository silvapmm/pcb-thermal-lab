"""!
@file test_track_width_angle.py
@brief One track across the heater (README 4.42): the 1 mm cells reproduce an axis-aligned track and lose much of an isolated diagonal one; the baseline of the cells without copper is the grid error. Uses only the conduction solver of this folder; about 25 s.
"""

import study_track_width_angle as st


def test_axis_aligned_track_is_felt_and_a_diagonal_one_is_not():
    """!
    @brief 0.3 mm track: at 0 degrees the flow-based faces reproduce at least 90 % of its cooling and the fill fraction too; at 45 degrees the flow-based faces reproduce less than 60 % and the fill fraction more than they do; the track cools the reference heater by 10 to 20 %.
    @return None.
    """
    ref_none, grid = st.baseline()
    assert 6.0 < grid < 9.0                                              # the 1 mm cells overestimate the laminate-only heater by about 7.4 %
    data = {"_baseline": {"ref_none_K": ref_none, "grid_error_pct": grid}}
    for th in (0, 45):
        data[f"0.3/{th}"] = st.one(0.3, th, ref_none)
    assert -20.0 < data["0.3/0"]["effect"] < -10.0
    assert st.capture(data, "coverage 0.1", "flow-based faces", 0.3, 0) > 90.0
    assert st.capture(data, "coverage 0.1", "fill fraction (today)", 0.3, 0) > 90.0
    f45 = st.capture(data, "coverage 0.1", "flow-based faces", 0.3, 45)
    assert f45 < 60.0 and st.capture(data, "coverage 0.1", "fill fraction (today)", 0.3, 45) > f45
    assert data["0.3/0"]["pieces"]["0.1"] == 1 and data["0.3/45"]["pieces"]["0.05"] == 1
