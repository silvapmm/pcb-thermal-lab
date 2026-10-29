#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file profile_io.py
@brief Read and write power profiles as CSV files.
@details Format (documented with an example in examples/led_driver_board/):

             # free comment lines start with #
             # repeat: yes            (yes: the table repeats; no: it runs once and the last power is held)
             time_s,power_w
             0,6.0
             5,0.0
             20,0.0                   (the last row is the END of the profile; its power is ignored)

         Row i gives the power from its time until the next row. The first time must be 0 and times must increase.
         Header units are optional: time_s, time_ms, time_us, time_min, time_h and power_w, power_mw, power_kw.
         Columns may be separated by comma, semicolon or tab; the decimal separator is a point.
"""

import re

from .model import TableProfile

_TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "min": 60.0, "h": 3600.0}
_POWER_UNITS = {"w": 1.0, "mw": 1e-3, "kw": 1e3}


class ProfileFileError(ValueError):
    """!
    @brief A power-profile CSV file that cannot be used; the message says what to fix and where.
    """


def parse_profile_csv(text):
    """!
    @brief Parse the text of a profile CSV file.
    @param text File contents.
    @return TableProfile (validated).
    @throws ProfileFileError With the line number and the reason if the file is wrong.
    """
    repeat, tscale, pscale = True, 1.0, 1.0
    times, powers, header_seen = [], [], False
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*repeat\s*[:=]\s*(\w+)", line, re.I)
            if m:
                value = m.group(1).lower()
                if value not in ("yes", "no", "true", "false", "1", "0"):
                    raise ProfileFileError(f"line {number}: 'repeat' must be yes or no")
                repeat = value in ("yes", "true", "1")
            continue
        cells = [c.strip() for c in re.split(r"[,;\t]", line)]
        if len(cells) < 2:
            raise ProfileFileError(f"line {number}: expected two columns (time and power), found {len(cells)}")
        try:
            t, p = float(cells[0]), float(cells[1])
        except ValueError:
            if header_seen or times:
                raise ProfileFileError(f"line {number}: '{cells[0]}', '{cells[1]}' are not numbers") from None
            # The first non-numeric line is the header; read the units from its names
            header_seen = True
            tm = re.search(r"time[_\s\[(]*([a-zµ]+)", cells[0], re.I)
            pm = re.search(r"power[_\s\[(]*([a-z]+)", cells[1], re.I)
            if tm:
                if tm.group(1).lower() not in _TIME_UNITS:
                    raise ProfileFileError(f"line {number}: unknown time unit '{tm.group(1)}' (use s, ms, us, min or h)")
                tscale = _TIME_UNITS[tm.group(1).lower()]
            if pm:
                if pm.group(1).lower() not in _POWER_UNITS:
                    raise ProfileFileError(f"line {number}: unknown power unit '{pm.group(1)}' (use w, mw or kw)")
                pscale = _POWER_UNITS[pm.group(1).lower()]
            continue
        times.append(t * tscale)
        powers.append(p * pscale)
    if len(times) < 2:
        raise ProfileFileError("the file needs at least two rows: the start of the first stretch and the end of the profile")
    # The last row only marks the end of the profile: its power is dropped
    profile = TableProfile(times, powers[:-1], repeat)
    try:
        profile.validate()
    except ValueError as exc:
        raise ProfileFileError(str(exc)) from None
    return profile


def read_profile_csv(path):
    """!
    @brief Read a power profile from a CSV file.
    @param path File path.
    @return TableProfile.
    @throws ProfileFileError If the file is not valid.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        return parse_profile_csv(fh.read())


def profile_to_csv(profile, name=""):
    """!
    @brief Text of the CSV file of a profile (a square wave is written as its table).
    @param profile SquareWave or TableProfile.
    @param name Optional heater name written in a comment.
    @return String.
    """
    t = profile.as_table()
    lines = ["# PCB Thermal Lab power profile" + (f" of {name}" if name else ""),
             "# Row i gives the power from its time until the next row; the last row is the end of the profile.",
             f"# repeat: {'yes' if t.repeat else 'no'}", "time_s,power_w"]
    for i, tm in enumerate(t.times):
        p = t.powers[min(i, len(t.powers) - 1)]
        lines.append(f"{tm:.9g},{p:.9g}")
    return "\n".join(lines) + "\n"


def write_profile_csv(profile, path, name=""):
    """!
    @brief Write a power profile to a CSV file.
    @param profile SquareWave or TableProfile.
    @param path File path.
    @param name Optional heater name written in a comment.
    """
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(profile_to_csv(profile, name))
